#!/usr/bin/env python3
"""Скрипт для аналізу структури QA чеклистів у Confluence."""

import os
import sys
import re
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import click

# Add app to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from app.config import settings
from scripts.confluence.confluence_real import RealConfluenceAPI


@dataclass
class TestCase:
    """Структура тесткейсу."""
    step: str
    expected_result: str
    screenshot: str = ""
    priority: str = ""
    config: str = ""
    category: str = ""  # GENERAL or CUSTOM
    subcategory: str = ""  # конкретна функціональність
    order: int = 0


@dataclass
class Checklist:
    """Структура чекліста."""
    title: str
    description: str
    configs: List[str]
    testcases: List[TestCase]
    page_id: str
    url: str


@dataclass
class QASection:
    """Глобальний розділ QA (наприклад, Checklist WEB)."""
    title: str
    description: str
    checklists: List[Checklist]
    subcategories: List['QASection']  # субкатегорії
    page_id: str
    url: str


class QAStructureAnalyzer:
    """Аналізатор структури QA чеклистів."""
    
    def __init__(self):
        """Ініціалізація."""
        self.confluence_api = RealConfluenceAPI()
    
    def analyze_page_structure(self, page_id: str) -> Dict[str, Any]:
        """Аналізує структуру сторінки."""
        print(f"Аналізую сторінку {page_id}...")
        
        # Отримуємо дані сторінки
        page = self.confluence_api.get_page_content(page_id)
        if not page:
            return {"error": f"Не вдалося отримати сторінку {page_id}"}
        
        print(f"Назва сторінки: {page['title']}")
        print(f"URL: {page['url']}")
        print(f"Простір: {page['space']}")
        
        # Нормалізуємо контент
        normalized_content = self.confluence_api.normalize_content(page["content"])
        
        # Аналізуємо структуру
        structure = self._analyze_content_structure(normalized_content, page)
        
        return {
            "page": page,
            "structure": structure,
            "content": normalized_content
        }
    
    def _analyze_content_structure(self, content: str, page: Dict[str, Any]) -> Dict[str, Any]:
        """Аналізує структуру контенту для виявлення тесткейсів."""
        lines = content.split('\n')
        
        structure = {
            "type": "unknown",
            "has_testcases": False,
            "has_table": False,
            "tables": [],
            "sections": [],
            "configs": [],
            "testcases": []
        }
        
        current_section = ""
        in_table = False
        table_headers = []
        table_rows = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Виявляємо заголовки секцій
            if line.startswith('#'):
                current_section = line.lstrip('#').strip()
                structure["sections"].append(current_section)
                print(f"Секція: {current_section}")
                continue
            
            # Виявляємо таблиці (простий підхід)
            if '|' in line and line.count('|') >= 2:
                if not in_table:
                    in_table = True
                    table_headers = [cell.strip() for cell in line.split('|')[1:-1]]
                    structure["has_table"] = True
                    print(f"Знайдена таблиця з заголовками: {table_headers}")
                else:
                    # Це рядок даних таблиці
                    cells = [cell.strip() for cell in line.split('|')[1:-1]]
                    if len(cells) == len(table_headers) and cells != table_headers:
                        table_rows.append(cells)
            else:
                if in_table and table_rows:
                    # Кінець таблиці
                    table_data = {
                        "headers": table_headers,
                        "rows": table_rows,
                        "section": current_section
                    }
                    structure["tables"].append(table_data)
                    
                    # Аналізуємо чи це таблиця тесткейсів
                    if self._is_testcase_table(table_headers):
                        structure["has_testcases"] = True
                        testcases = self._parse_testcases_from_table(table_data)
                        structure["testcases"].extend(testcases)
                        print(f"Знайдено {len(testcases)} тесткейсів у таблиці")
                    
                    in_table = False
                    table_headers = []
                    table_rows = []
            
            # Виявляємо посилання на конфіги
            if 'config' in line.lower() and ('http' in line or 'confluence' in line):
                structure["configs"].append(line)
        
        # Визначаємо тип сторінки
        if structure["has_testcases"]:
            structure["type"] = "checklist"
        elif structure["sections"] and not structure["has_testcases"]:
            structure["type"] = "section"  # можливо це секція з субсторінками
        else:
            structure["type"] = "documentation"
        
        return structure
    
    def _is_testcase_table(self, headers: List[str]) -> bool:
        """Перевіряє чи є це таблиця тесткейсів."""
        headers_lower = [h.lower() for h in headers]
        testcase_keywords = ['step', 'expected', 'result', 'priority', 'config']
        
        # Якщо є принаймні 2 ключових слова, вважаємо це таблицею тесткейсів
        matches = sum(1 for keyword in testcase_keywords if any(keyword in h for h in headers_lower))
        return matches >= 2
    
    def _parse_testcases_from_table(self, table_data: Dict[str, Any]) -> List[TestCase]:
        """Парсить тесткейси з таблиці."""
        headers = table_data["headers"]
        rows = table_data["rows"]
        
        # Мапимо заголовки до полів
        header_mapping = {}
        for i, header in enumerate(headers):
            header_lower = header.lower()
            if 'step' in header_lower:
                header_mapping['step'] = i
            elif 'expected' in header_lower or 'result' in header_lower:
                header_mapping['expected_result'] = i
            elif 'screenshot' in header_lower:
                header_mapping['screenshot'] = i
            elif 'priority' in header_lower:
                header_mapping['priority'] = i
            elif 'config' in header_lower:
                header_mapping['config'] = i
        
        testcases = []
        current_category = ""
        current_subcategory = ""
        
        for order, row in enumerate(rows):
            # Перевіряємо чи це розділювач категорій
            if len(row) > 0 and row[0] and not any(row[1:]):  # Тільки перша комірка заповнена
                if 'general' in row[0].lower():
                    current_category = "GENERAL"
                elif 'custom' in row[0].lower():
                    current_category = "CUSTOM"
                else:
                    current_subcategory = row[0]
                continue
            
            # Створюємо тесткейс
            testcase = TestCase(
                step=row[header_mapping.get('step', 0)] if 'step' in header_mapping else "",
                expected_result=row[header_mapping.get('expected_result', 1)] if 'expected_result' in header_mapping else "",
                screenshot=row[header_mapping.get('screenshot', -1)] if 'screenshot' in header_mapping else "",
                priority=row[header_mapping.get('priority', -1)] if 'priority' in header_mapping else "",
                config=row[header_mapping.get('config', -1)] if 'config' in header_mapping else "",
                category=current_category,
                subcategory=current_subcategory,
                order=order
            )
            
            # Додаємо тільки валідні тесткейси
            if testcase.step and testcase.expected_result:
                testcases.append(testcase)
        
        return testcases
    
    def get_child_pages(self, parent_page_id: str) -> List[Dict[str, Any]]:
        """Отримує дочірні сторінки."""
        return self.confluence_api._get_child_pages_recursive(parent_page_id)
    
    def analyze_qa_section(self, root_page_id: str) -> QASection:
        """Аналізує повну QA секцію з усіма підсторінками."""
        print(f"\n=== Аналіз QA секції {root_page_id} ===")
        
        # Аналізуємо кореневу сторінку
        root_analysis = self.analyze_page_structure(root_page_id)
        if "error" in root_analysis:
            raise Exception(root_analysis["error"])
        
        root_page = root_analysis["page"]
        
        # Отримуємо дочірні сторінки
        child_pages = self.get_child_pages(root_page_id)
        print(f"Знайдено {len(child_pages)} дочірніх сторінок")
        
        checklists = []
        subcategories = []
        
        for child in child_pages:
            print(f"\nАналізую дочірню сторінку: {child['title']}")
            child_analysis = self.analyze_page_structure(child['id'])
            
            if child_analysis["structure"]["type"] == "checklist":
                # Це чекліст з тесткейсами
                checklist = Checklist(
                    title=child['title'],
                    description=child_analysis["structure"]["sections"][0] if child_analysis["structure"]["sections"] else "",
                    configs=child_analysis["structure"]["configs"],
                    testcases=child_analysis["structure"]["testcases"],
                    page_id=child['id'],
                    url=child['url']
                )
                checklists.append(checklist)
                print(f"  -> Чекліст з {len(checklist.testcases)} тесткейсами")
            
            elif child_analysis["structure"]["type"] == "section":
                # Це субкатегорія, треба аналізувати її дочірні сторінки
                subcategory = self.analyze_qa_section(child['id'])
                subcategories.append(subcategory)
                print(f"  -> Субкатегорія з {len(subcategory.checklists)} чекліст(ами)")
        
        return QASection(
            title=root_page['title'],
            description=root_analysis["structure"]["sections"][0] if root_analysis["structure"]["sections"] else "",
            checklists=checklists,
            subcategories=subcategories,
            page_id=root_page['id'],
            url=root_page['url']
        )


@click.command()
@click.option('--page-id', help='ID сторінки для аналізу')
@click.option('--use-config', is_flag=True, help='Використовувати сторінки з конфігурації')
@click.option('--output', help='Файл для збереження результатів (JSON)')
def main(page_id, use_config, output):
    """Аналізує структуру QA чеклистів у Confluence."""
    
    if not settings.confluence_auth_token:
        click.echo("Помилка: CONFLUENCE_AUTH_TOKEN не встановлений", err=True)
        sys.exit(1)
    
    analyzer = QAStructureAnalyzer()
    
    # Визначаємо які сторінки аналізувати
    pages_to_analyze = []
    
    if use_config and settings.confluence_root_pages:
        pages_to_analyze = settings.confluence_root_pages.split(',')
    elif page_id:
        pages_to_analyze = [page_id]
    else:
        click.echo("Вкажіть --page-id або --use-config", err=True)
        sys.exit(1)
    
    results = {}
    
    for page_id in pages_to_analyze:
        page_id = page_id.strip()
        try:
            # Спочатку простий аналіз сторінки
            simple_analysis = analyzer.analyze_page_structure(page_id)
            
            # Потім повний аналіз як QA секції
            qa_section = analyzer.analyze_qa_section(page_id)
            
            results[page_id] = {
                "simple_analysis": simple_analysis,
                "qa_section": {
                    "title": qa_section.title,
                    "description": qa_section.description,
                    "checklists_count": len(qa_section.checklists),
                    "subcategories_count": len(qa_section.subcategories),
                    "total_testcases": sum(len(c.testcases) for c in qa_section.checklists),
                    "checklists": [
                        {
                            "title": c.title,
                            "testcases_count": len(c.testcases),
                            "configs_count": len(c.configs),
                            "categories": list(set(tc.category for tc in c.testcases if tc.category)),
                            "subcategories": list(set(tc.subcategory for tc in c.testcases if tc.subcategory))
                        } for c in qa_section.checklists
                    ]
                }
            }
            
            # Виводимо короткий звіт
            print(f"\n=== ЗВІТ для {qa_section.title} ===")
            print(f"Чекліст(ів): {len(qa_section.checklists)}")
            print(f"Субкатегорій: {len(qa_section.subcategories)}")
            print(f"Всього тесткейсів: {sum(len(c.testcases) for c in qa_section.checklists)}")
            
            for checklist in qa_section.checklists:
                print(f"\n  📋 {checklist.title}")
                print(f"    Тесткейсів: {len(checklist.testcases)}")
                print(f"    Конфігів: {len(checklist.configs)}")
                
                categories = set(tc.category for tc in checklist.testcases if tc.category)
                subcategories = set(tc.subcategory for tc in checklist.testcases if tc.subcategory)
                
                if categories:
                    print(f"    Категорії: {', '.join(categories)}")
                if subcategories:
                    print(f"    Підкategорії: {', '.join(subcategories)}")
        
        except Exception as e:
            print(f"Помилка при аналізі сторінки {page_id}: {e}")
            results[page_id] = {"error": str(e)}
    
    # Зберігаємо результати
    if output:
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        print(f"\nРезультати збережено у {output}")
    
    print("\n=== Аналіз завершено ===")


if __name__ == "__main__":
    main()
