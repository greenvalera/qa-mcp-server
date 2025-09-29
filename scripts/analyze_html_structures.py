#!/usr/bin/env python3
"""
Скрипт для аналізу HTML структур різних чеклістів
"""

import os
import sys
import asyncio
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup, Tag
import json

# Add app to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.data.qa_repository import QARepository
from app.models.qa_models import Checklist
from scripts.confluence.confluence_real import RealConfluenceAPI


class HTMLStructureAnalyzer:
    """Аналізатор HTML структур чеклістів"""
    
    def __init__(self):
        self.qa_repo = QARepository()
        self.confluence_api = RealConfluenceAPI()
        self.analysis_results = []
    
    def analyze_checklist_structures(self, checklist_ids: List[int]) -> Dict[str, Any]:
        """Аналізує структури HTML таблиць для списку чеклістів"""
        
        print(f"🔍 Аналізуємо структури {len(checklist_ids)} чеклістів...")
        
        for checklist_id in checklist_ids:
            try:
                print(f"\n📋 Аналізуємо чекліст ID: {checklist_id}")
                result = self._analyze_single_checklist(checklist_id)
                if result:
                    self.analysis_results.append(result)
            except Exception as e:
                print(f"❌ Помилка аналізу чекліста {checklist_id}: {e}")
        
        return self._generate_summary()
    
    def _analyze_single_checklist(self, checklist_id: int) -> Optional[Dict[str, Any]]:
        """Аналізує структуру одного чекліста"""
        
        session = self.qa_repo.get_session()
        try:
            checklist = session.query(Checklist).filter(Checklist.id == checklist_id).first()
            if not checklist:
                print(f"❌ Чекліст {checklist_id} не знайдено")
                return None
            
            print(f"   📄 {checklist.title}")
            
            # Отримуємо контент
            page_content = self.confluence_api.get_page_content(checklist.confluence_page_id)
            if not page_content:
                print(f"❌ Не вдалося отримати контент")
                return None
            
            # Аналізуємо HTML структуру
            analysis = self._analyze_html_structure(page_content['content'], checklist.title)
            analysis['checklist_id'] = checklist_id
            analysis['checklist_title'] = checklist.title
            
            return analysis
            
        finally:
            session.close()
    
    def _analyze_html_structure(self, html_content: str, title: str) -> Dict[str, Any]:
        """Аналізує HTML структуру контенту"""
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        analysis = {
            'title': title,
            'tables_found': 0,
            'table_structures': [],
            'sections_found': [],
            'testcase_patterns': [],
            'html_size': len(html_content),
            'normalized_size': len(self.confluence_api.normalize_content(html_content))
        }
        
        # Знаходимо всі таблиці
        tables = soup.find_all('table')
        analysis['tables_found'] = len(tables)
        
        for i, table in enumerate(tables):
            table_analysis = self._analyze_table_structure(table, i)
            if table_analysis:
                analysis['table_structures'].append(table_analysis)
        
        # Знаходимо секції
        analysis['sections_found'] = self._find_sections(soup)
        
        # Аналізуємо паттерни тесткейсів
        analysis['testcase_patterns'] = self._analyze_testcase_patterns(soup)
        
        return analysis
    
    def _analyze_table_structure(self, table: Tag, table_index: int) -> Optional[Dict[str, Any]]:
        """Аналізує структуру таблиці"""
        
        rows = table.find_all('tr')
        if not rows:
            return None
        
        # Аналізуємо заголовки
        header_row = rows[0]
        headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
        
        # Перевіряємо чи це таблиця з тесткейсами
        is_testcase_table = self._is_testcase_table(headers)
        
        table_analysis = {
            'table_index': table_index,
            'rows_count': len(rows),
            'columns_count': len(headers),
            'headers': headers,
            'is_testcase_table': is_testcase_table,
            'sections_in_table': [],
            'testcase_rows': 0,
            'section_headers': []
        }
        
        if is_testcase_table:
            # Аналізуємо рядки на предмет секцій та тесткейсів
            for i, row in enumerate(rows[1:], 1):  # Пропускаємо заголовок
                cells = row.find_all(['td', 'th'])
                
                # Перевіряємо чи це заголовок секції
                if self._is_section_header_row(row, cells):
                    section_name = self._extract_section_name_from_row(cells)
                    table_analysis['sections_in_table'].append(section_name)
                    table_analysis['section_headers'].append({
                        'row_index': i,
                        'section_name': section_name,
                        'colspan': self._get_colspan(cells)
                    })
                else:
                    # Перевіряємо чи це тесткейс
                    if self._is_testcase_row(cells):
                        table_analysis['testcase_rows'] += 1
        
        return table_analysis
    
    def _is_testcase_table(self, headers: List[str]) -> bool:
        """Перевіряє чи є таблиця таблицею з тесткейсами"""
        
        header_text = ' '.join(headers).upper()
        
        # Ключові слова для тесткейс таблиць
        testcase_keywords = [
            'STEP', 'EXPECTED', 'PRIORITY', 'CONFIG', 'SCREENSHOT',
            'ШАГ', 'ОЖИДАЕМЫЙ', 'ПРИОРИТЕТ', 'КОНФИГ', 'СКРИНШОТ'
        ]
        
        return any(keyword in header_text for keyword in testcase_keywords)
    
    def _is_section_header_row(self, row: Tag, cells: List[Tag]) -> bool:
        """Перевіряє чи є рядок заголовком секції"""
        
        # Перевіряємо colspan
        for cell in cells:
            colspan = cell.get('colspan')
            if colspan and int(colspan) >= 3:  # Заголовок секції займає кілька колонок
                text = cell.get_text(strip=True).upper()
                if text in ['GENERAL', 'CUSTOM'] or any(keyword in text for keyword in ['SECTION', 'РАЗДЕЛ']):
                    return True
        
        return False
    
    def _extract_section_name_from_row(self, cells: List[Tag]) -> str:
        """Витягує назву секції з рядка"""
        
        for cell in cells:
            text = cell.get_text(strip=True).upper()
            if text in ['GENERAL', 'CUSTOM']:
                return text
            elif 'SECTION' in text or 'РАЗДЕЛ' in text:
                return text
        
        return 'UNKNOWN'
    
    def _get_colspan(self, cells: List[Tag]) -> int:
        """Отримує максимальний colspan з комірок"""
        
        max_colspan = 0
        for cell in cells:
            colspan = cell.get('colspan')
            if colspan:
                max_colspan = max(max_colspan, int(colspan))
        
        return max_colspan
    
    def _is_testcase_row(self, cells: List[Tag]) -> bool:
        """Перевіряє чи є рядок тесткейсом"""
        
        if len(cells) < 3:
            return False
        
        # Перевіряємо чи є вміст в ключових колонках
        step_cell = cells[1] if len(cells) > 1 else None
        expected_cell = cells[2] if len(cells) > 2 else None
        
        if step_cell and expected_cell:
            step_text = step_cell.get_text(strip=True)
            expected_text = expected_cell.get_text(strip=True)
            
            # Тесткейс повинен мати достатньо вмісту
            return len(step_text) > 10 and len(expected_text) > 5
        
        return False
    
    def _find_sections(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Знаходить всі секції в документі"""
        
        sections = []
        
        # Шукаємо заголовки секцій
        section_patterns = [
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'div[class*="section"]',
            'div[class*="header"]'
        ]
        
        for pattern in section_patterns:
            elements = soup.select(pattern)
            for element in elements:
                text = element.get_text(strip=True).upper()
                if any(keyword in text for keyword in ['GENERAL', 'CUSTOM', 'SECTION', 'РАЗДЕЛ']):
                    sections.append({
                        'tag': element.name,
                        'text': text,
                        'class': element.get('class', [])
                    })
        
        return sections
    
    def _analyze_testcase_patterns(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Аналізує паттерни тесткейсів"""
        
        patterns = []
        
        # Шукаємо рядки з номерами та кроками
        rows = soup.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 3:
                first_cell = cells[0].get_text(strip=True)
                second_cell = cells[1].get_text(strip=True)
                
                # Перевіряємо чи це номерований рядок
                if first_cell.isdigit() and len(second_cell) > 10:
                    patterns.append({
                        'type': 'numbered_testcase',
                        'number': first_cell,
                        'step_preview': second_cell[:50] + '...' if len(second_cell) > 50 else second_cell
                    })
        
        return patterns[:10]  # Повертаємо перші 10 прикладів
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Генерує підсумок аналізу"""
        
        if not self.analysis_results:
            return {'error': 'Немає результатів для аналізу'}
        
        summary = {
            'total_checklists': len(self.analysis_results),
            'table_statistics': {
                'total_tables': sum(r['tables_found'] for r in self.analysis_results),
                'testcase_tables': sum(len([t for t in r['table_structures'] if t['is_testcase_table']]) for r in self.analysis_results),
                'avg_tables_per_checklist': sum(r['tables_found'] for r in self.analysis_results) / len(self.analysis_results)
            },
            'section_analysis': {
                'unique_sections': set(),
                'section_frequency': {}
            },
            'structure_variations': [],
            'recommendations': []
        }
        
        # Аналізуємо секції
        for result in self.analysis_results:
            for section in result['sections_found']:
                section_name = section['text']
                summary['section_analysis']['unique_sections'].add(section_name)
                summary['section_analysis']['section_frequency'][section_name] = \
                    summary['section_analysis']['section_frequency'].get(section_name, 0) + 1
        
        # Конвертуємо set в list для JSON серіалізації
        summary['section_analysis']['unique_sections'] = list(summary['section_analysis']['unique_sections'])
        
        # Аналізуємо варіації структур
        for result in self.analysis_results:
            for table in result['table_structures']:
                if table['is_testcase_table']:
                    structure_variation = {
                        'checklist_title': result['checklist_title'],
                        'columns': table['columns_count'],
                        'headers': table['headers'],
                        'sections': table['sections_in_table'],
                        'testcase_count': table['testcase_rows']
                    }
                    summary['structure_variations'].append(structure_variation)
        
        # Генеруємо рекомендації
        summary['recommendations'] = self._generate_recommendations(summary)
        
        return summary
    
    def _generate_recommendations(self, summary: Dict[str, Any]) -> List[str]:
        """Генерує рекомендації на основі аналізу"""
        
        recommendations = []
        
        # Аналізуємо варіації структур
        if summary['structure_variations']:
            column_counts = [v['columns'] for v in summary['structure_variations']]
            unique_columns = set(column_counts)
            
            if len(unique_columns) > 1:
                recommendations.append(f"Виявлено {len(unique_columns)} різних структур таблиць з кількістю колонок: {sorted(unique_columns)}")
            
            # Аналізуємо заголовки
            all_headers = []
            for variation in summary['structure_variations']:
                all_headers.extend(variation['headers'])
            
            unique_headers = set(all_headers)
            if len(unique_headers) > 10:
                recommendations.append(f"Виявлено {len(unique_headers)} унікальних заголовків колонок - потрібна адаптивна логіка розпізнавання")
        
        # Аналізуємо секції
        sections = summary['section_analysis']['unique_sections']
        if len(sections) > 2:
            recommendations.append(f"Виявлено {len(sections)} різних типів секцій: {list(sections)}")
        
        return recommendations
    
    def close(self):
        """Закриває ресурси"""
        if self.qa_repo:
            self.qa_repo.close()


def main():
    """Основна функція"""
    
    # Список чеклістів для аналізу
    checklist_ids = [286, 287, 288, 289, 290, 291, 292, 293, 294, 295]
    
    analyzer = HTMLStructureAnalyzer()
    
    try:
        # Аналізуємо структури
        summary = analyzer.analyze_checklist_structures(checklist_ids)
        
        # Виводимо результати
        print("\n" + "="*80)
        print("📊 ПІДСУМОК АНАЛІЗУ HTML СТРУКТУР")
        print("="*80)
        
        print(f"\n📋 Загальна статистика:")
        print(f"   - Проаналізовано чеклістів: {summary['total_checklists']}")
        print(f"   - Знайдено таблиць: {summary['table_statistics']['total_tables']}")
        print(f"   - Таблиць з тесткейсами: {summary['table_statistics']['testcase_tables']}")
        print(f"   - Середня кількість таблиць на чекліст: {summary['table_statistics']['avg_tables_per_checklist']:.1f}")
        
        print(f"\n🏷️ Аналіз секцій:")
        print(f"   - Унікальних секцій: {len(summary['section_analysis']['unique_sections'])}")
        for section, count in summary['section_analysis']['section_frequency'].items():
            print(f"     • {section}: {count} разів")
        
        print(f"\n🔧 Варіації структур:")
        for i, variation in enumerate(summary['structure_variations'][:5], 1):
            print(f"   {i}. {variation['checklist_title']}")
            print(f"      - Колонок: {variation['columns']}")
            print(f"      - Секцій: {variation['sections']}")
            print(f"      - Тесткейсів: {variation['testcase_count']}")
        
        print(f"\n💡 Рекомендації:")
        for i, rec in enumerate(summary['recommendations'], 1):
            print(f"   {i}. {rec}")
        
        # Зберігаємо детальний аналіз
        with open('/home/vpogorelov/projects/qa_mcp/html_structure_analysis.json', 'w', encoding='utf-8') as f:
            json.dump({
                'summary': summary,
                'detailed_results': analyzer.analysis_results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Детальний аналіз збережено в html_structure_analysis.json")
        
    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        analyzer.close()


if __name__ == "__main__":
    main()
