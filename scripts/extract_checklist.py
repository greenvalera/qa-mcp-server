#!/usr/bin/env python3
"""
Універсальний скрипт для витягування та додавання тесткейсів будь-якого чекліста до бази даних.
Цей скрипт вирішує проблему відсутності тесткейсів для конкретних чеклістів з покращеним парсингом.
"""

import os
import sys
import hashlib
import asyncio
import click
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# Add app to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.config import settings
from app.data.qa_repository import QARepository
from app.models.qa_models import QASection, Checklist, TestCase, Config
from app.ai.qa_analyzer import QAContentAnalyzer
from scripts.confluence.confluence_real import RealConfluenceAPI
from scripts.confluence.html_table_parser import EnhancedConfluenceTableParser


class UniversalChecklistExtractor:
    """Універсальний екстрактор для будь-якого чекліста."""
    
    def __init__(self, checklist_identifier: str = None):
        """Ініціалізація.
        
        Args:
            checklist_identifier: Назва чекліста або його ID
        """
        self.qa_repo = QARepository()
        self.confluence_api = RealConfluenceAPI()
        self.qa_analyzer = QAContentAnalyzer()
        self.html_parser = EnhancedConfluenceTableParser()
        
        # Визначаємо чекліст для обробки
        self.checklist_info = None
        if checklist_identifier:
            self.checklist_info = self._resolve_checklist(checklist_identifier)
    
    def _resolve_checklist(self, identifier: str) -> Dict[str, Any]:
        """Визначає чекліст за назвою або ID."""
        session = self.qa_repo.get_session()
        
        try:
            # Спробуємо як ID
            if identifier.isdigit():
                checklist = session.query(Checklist).filter(Checklist.id == int(identifier)).first()
                if checklist:
                    return {
                        'id': checklist.id,
                        'title': checklist.title,
                        'page_id': checklist.confluence_page_id
                    }
            
            # Спробуємо як назву (точне співпадіння)
            checklist = session.query(Checklist).filter(Checklist.title == identifier).first()
            if checklist:
                return {
                    'id': checklist.id,
                    'title': checklist.title,
                    'page_id': checklist.confluence_page_id
                }
            
            # Спробуємо як частину назви (LIKE пошук)
            checklist = session.query(Checklist).filter(Checklist.title.ilike(f'%{identifier}%')).first()
            if checklist:
                return {
                    'id': checklist.id,
                    'title': checklist.title,
                    'page_id': checklist.confluence_page_id
                }
            
            raise ValueError(f"Чекліст з ідентифікатором '{identifier}' не знайдено")
            
        finally:
            session.close()
    
    async def extract_and_populate_testcases(self, checklist_identifier: str = None) -> Dict[str, Any]:
        """Основна функція витягування та додавання тесткейсів."""
        try:
            # Визначаємо чекліст
            if checklist_identifier:
                self.checklist_info = self._resolve_checklist(checklist_identifier)
            elif not self.checklist_info:
                raise ValueError("Не вказано ідентифікатор чекліста")
            
            print(f"🚀 Починаємо витягування тесткейсів для {self.checklist_info['title']}")
            
            # 1. Отримуємо контент з Confluence
            print("📄 Отримуємо контент з Confluence...")
            page_content = self.confluence_api.get_page_content(self.checklist_info['page_id'])
            
            if not page_content:
                return {"success": False, "error": "Не вдалося отримати контент з Confluence"}
            
            print(f"✅ Отримано контент: {len(page_content['content'])} символів")
            
            # 1.1. Спробуємо HTML парсер спочатку
            print("🔍 Аналізуємо HTML структуру...")
            html_testcases = self.html_parser.parse_testcases_from_html(page_content['content'])
            print(f"✅ HTML парсер знайшов {len(html_testcases)} тесткейсів")
            
            # 2. Нормалізуємо контент
            normalized_content = self.confluence_api.normalize_content(page_content['content'])
            print(f"✅ Нормалізовано контент: {len(normalized_content)} символів")
            
            # 3. Аналізуємо контент з AI
            print("🤖 Аналізуємо контент з AI...")
            analysis = self.qa_analyzer.analyze_qa_content(page_content['title'], normalized_content)
            
            print(f"✅ AI аналіз завершено:")
            print(f"   - Знайдено тесткейсів: {len(analysis.testcases)}")
            print(f"   - Знайдено конфігів: {len(analysis.configs)}")
            print(f"   - Рівень впевненості: {analysis.analysis_confidence}")
            
            # 4. Покращуємо аналіз додатковими методами
            enhanced_testcases = await self._enhance_testcase_extraction(normalized_content, analysis.testcases)
            print(f"✅ Покращено аналіз: {len(enhanced_testcases)} тесткейсів")
            
            # 4.1. Об'єднуємо HTML та AI результати
            all_testcases = []
            
            # Додаємо HTML тесткейси (пріоритет)
            if len(html_testcases) > 10:  # Якщо HTML знайшов достатньо
                print(f"🎯 Використовуємо HTML результати як основні: {len(html_testcases)} тесткейсів")
                all_testcases.extend(html_testcases)
                # Додаємо AI результати як доповнення
                all_testcases.extend(enhanced_testcases)
            else:
                print(f"🤖 Використовуємо AI результати як основні: {len(enhanced_testcases)} тесткейсів")
                all_testcases.extend(enhanced_testcases)
                # Додаємо HTML результати як доповнення
                all_testcases.extend(html_testcases)
            
            # Видаляємо дублікати
            unique_testcases = self._remove_duplicates_enhanced(all_testcases)
            print(f"✅ Унікальних тесткейсів після об'єднання: {len(unique_testcases)}")
            
            enhanced_testcases = unique_testcases
            
            # 5. Додаємо тесткейси до бази даних
            print("💾 Додаємо тесткейси до бази даних...")
            result = await self._add_testcases_to_database(enhanced_testcases, analysis.configs)
            
            return result
            
        except Exception as e:
            print(f"❌ Помилка: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    async def _enhance_testcase_extraction(self, content: str, initial_testcases: List[Dict]) -> List[Dict]:
        """Покращує витягування тесткейсів додатковими методами."""
        
        # Спробуємо витягти більше тесткейсів, розбивши контент на частини
        enhanced_testcases = list(initial_testcases)  # Копіюємо початкові
        
        # Розділяємо контент на логічні блоки
        content_blocks = self._split_content_into_blocks(content)
        
        for i, block in enumerate(content_blocks):
            if len(block.strip()) < 100:  # Пропускаємо дуже короткі блоки
                continue
            
            try:
                print(f"🔍 Аналізуємо блок {i+1}/{len(content_blocks)}")
                
                # Аналізуємо кожен блок окремо
                block_analysis = self.qa_analyzer.analyze_qa_content(f"WEB: Search - Block {i+1}", block)
                
                # Додаємо нові унікальні тесткейси
                for testcase in block_analysis.testcases:
                    if not self._is_duplicate_testcase(testcase, enhanced_testcases):
                        testcase['order_index'] = len(enhanced_testcases)
                        enhanced_testcases.append(testcase)
                
            except Exception as e:
                print(f"⚠️ Помилка аналізу блоку {i+1}: {e}")
                continue
        
        return enhanced_testcases
    
    def _split_content_into_blocks(self, content: str) -> List[str]:
        """Розділяє контент на логічні блоки для кращого аналізу."""
        
        # Покращені розділювачі для різних типів чеклістів
        delimiters = [
            "# GENERAL",
            "# CUSTOM", 
            "GENERAL",
            "CUSTOM",
            "Pre condition",
            "Steps",
            "Header",
            "View after registration", 
            "Search parameters",
            "Short info",
            "Personal info",
            "Member photos",
            "Member videos", 
            "Status",
            "Looking for",
            "Location",
            "Additional info",
            "Toolbar",
            "Similar users",
            "Age Verification",
            "PMA photo request",
            "Tribe",
            "Sex role",
            "Fetish niche",
            "Profession",
            "Custom attributes",
            "Photo Censor Asia",
            "Moon тема",
            "Fresh тема",
            "Поисковая выдача",
            "Flirtcast",
            "Widget",
            "Footer Info"
        ]
        
        blocks = []
        current_block = ""
        lines = content.split('\n')
        
        for line in lines:
            line_stripped = line.strip()
            
            # Перевіряємо чи є це розділювач
            is_delimiter = False
            for delimiter in delimiters:
                if delimiter.lower() in line_stripped.lower():
                    # Додаткова перевірка - рядок не повинен бути занадто довгим (не частина тексту)
                    if len(line_stripped) < 100 and (
                        line_stripped.lower() == delimiter.lower() or 
                        line_stripped.lower().startswith(delimiter.lower())
                    ):
                        is_delimiter = True
                        break
            
            if is_delimiter and current_block.strip():
                # Зберігаємо поточний блок
                blocks.append(current_block.strip())
                current_block = line + '\n'
            else:
                current_block += line + '\n'
        
        # Додаємо останній блок
        if current_block.strip():
            blocks.append(current_block.strip())
        
        # Покращена фільтрація блоків
        filtered_blocks = []
        for block in blocks:
            if len(block) > 300 and self._is_quality_block(block):  # Збільшили мінімальний розмір
                # Розбиваємо великі блоки на менші частини
                if len(block) > 8000:  # Якщо блок дуже великий
                    sub_blocks = self._split_large_block(block)
                    filtered_blocks.extend(sub_blocks)
                else:
                    filtered_blocks.append(block)
        
        print(f"📊 Розділено на {len(filtered_blocks)} якісних блоків (з {len(blocks)} загалом)")
        return filtered_blocks
    
    def _split_large_block(self, block: str) -> List[str]:
        """Розбиває великий блок на менші частини."""
        
        # Розбиваємо по пріоритетах, тест кейсах та структурним елементам
        priority_markers = ["HIGHEST", "HIGH", "MEDIUM", "LOW", "CRITICAL"]
        structure_markers = ["Pre condition:", "Steps:", "Validation Suite:", "IndexPageTests", "FiveStepPageTests"]
        
        sub_blocks = []
        current_sub_block = ""
        lines = block.split('\n')
        testcase_count = 0
        
        for line in lines:
            line_stripped = line.strip()
            
            # Перевіряємо на маркери розділення
            is_split_marker = False
            
            # Маркери пріоритету
            if any(priority in line_stripped for priority in priority_markers):
                is_split_marker = True
            
            # Структурні маркери
            elif any(marker in line_stripped for marker in structure_markers):
                is_split_marker = True
            
            # Якщо накопичилося багато тесткейсів (по табуляції та структурі)
            elif line_stripped and not line.startswith('\t') and not line.startswith(' ') and len(current_sub_block) > 3000:
                is_split_marker = True
            
            if is_split_marker and current_sub_block.strip():
                if len(current_sub_block.strip()) > 300:  # Знизили мінімальний розмір
                    sub_blocks.append(current_sub_block.strip())
                    testcase_count = 0
                current_sub_block = line + '\n'
            else:
                current_sub_block += line + '\n'
                # Підрахунок можливих тесткейсів
                if '\t' in line and any(word in line_stripped.lower() for word in ['проверить', 'ввести', 'кликнуть', 'сменить', 'оставить']):
                    testcase_count += 1
        
        # Додаємо останній підблок
        if current_sub_block.strip() and len(current_sub_block.strip()) > 300:
            sub_blocks.append(current_sub_block.strip())
        
        print(f"🔄 Великий блок розділено на {len(sub_blocks)} підблоків")
        return sub_blocks if sub_blocks else [block]
    
    def _is_quality_block(self, block: str) -> bool:
        """Перевіряє чи є блок якісним для аналізу."""
        
        # Повинен містити ключові слова тестування
        quality_keywords = [
            'step', 'expected', 'result', 'test', 'check', 'verify', 
            'должен', 'должна', 'отображается', 'проверить',
            'зарегистрировать', 'пользователь', 'кнопка', 'поле',
            'priority', 'config', 'screenshot', 'при', 'клик',
            'открыть', 'перейти', 'высок', 'средн', 'низк',
            'highest', 'high', 'medium', 'low', 'critical',
            # Додаткові ключові слова для Registration чеклістів
            'ввести', 'кликнуть', 'сменить', 'оставить', 'форма',
            'регистрация', 'validation', 'валидация', 'email', 'password',
            'логотип', 'фавикон', 'возраст', 'локация', 'пароль'
        ]
        
        block_lower = block.lower()
        keyword_count = sum(1 for keyword in quality_keywords if keyword in block_lower)
        
        # Перевіряємо наявність табличної структури (характерна для тесткейсів)
        has_table_structure = '\t' in block and block.count('\t') > 3
        
        # Перевіряємо наявність пріоритетів
        has_priorities = any(priority in block.upper() for priority in ['HIGH', 'MEDIUM', 'LOW', 'CRITICAL', 'HIGHEST'])
        
        # Блок вважається якісним якщо:
        # 1. Має достатньо ключових слів ТА табличну структуру
        # 2. АБО має пріоритети (означає тесткейси)
        # 3. АБО має багато ключових слів
        return (keyword_count >= 2 and has_table_structure) or has_priorities or keyword_count >= 5
    
    def _remove_duplicates_enhanced(self, testcases: List[Dict]) -> List[Dict]:
        """Покращений метод видалення дублікатів з урахуванням різних джерел."""
        
        unique_testcases = []
        seen_steps = set()
        
        for testcase in testcases:
            step = (testcase.get('step') or '').strip()
            
            if not step or len(step) < 10:
                continue  # Пропускаємо занадто короткі кроки
            
            # Створюємо нормалізований ключ для порівняння
            normalized_step = self._normalize_step_for_comparison(step)
            
            # Перевіряємо на дублікат
            is_duplicate = False
            for seen_step in seen_steps:
                if self._calculate_similarity(normalized_step, seen_step) > 0.85:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                seen_steps.add(normalized_step)
                unique_testcases.append(testcase)
        
        return unique_testcases
    
    def _normalize_step_for_comparison(self, step: str) -> str:
        """Нормалізує крок для порівняння."""
        
        import re
        
        # Приводимо до нижнього регістру
        normalized = step.lower().strip()
        
        # Видаляємо зайві пробіли
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Видаляємо розділові знаки
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        return normalized
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Обчислює схожість між двома текстами (простий алгоритм)."""
        
        if not text1 or not text2:
            return 0.0
        
        # Простий алгоритм на основі спільних слів
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0

    def _is_duplicate_testcase(self, testcase: Dict, existing_testcases: List[Dict]) -> bool:
        """Перевіряє чи є тесткейс дублікатом."""
        
        step = (testcase.get('step') or '').strip().lower()
        expected = (testcase.get('expected_result') or '').strip().lower()
        
        if not step and not expected:
            return True
        
        for existing in existing_testcases:
            existing_step = (existing.get('step') or '').strip().lower()
            existing_expected = (existing.get('expected_result') or '').strip().lower()
            
            # Простий алгоритм схожості
            if (step and existing_step and step[:50] == existing_step[:50]) or \
               (expected and existing_expected and expected[:50] == existing_expected[:50]):
                return True
        
        return False
    
    async def _add_testcases_to_database(self, testcases: List[Dict], configs: List[str]) -> Dict[str, Any]:
        """Додає тесткейси до бази даних."""
        
        session = self.qa_repo.get_session()
        
        try:
            # Отримуємо чекліст
            checklist_id = self.checklist_info['id']
            checklist = session.query(Checklist).filter(Checklist.id == checklist_id).first()
            
            if not checklist:
                return {"success": False, "error": f"Чекліст з ID {checklist_id} не знайдено"}
            
            # Видаляємо існуючі тесткейси (якщо є)
            existing_count = session.query(TestCase).filter(TestCase.checklist_id == checklist_id).count()
            if existing_count > 0:
                print(f"🗑️ Видаляємо {existing_count} існуючих тесткейсів")
                session.query(TestCase).filter(TestCase.checklist_id == checklist_id).delete()
            
            # Створюємо конфіги
            config_map = {}
            for config_name in configs:
                config = self._get_or_create_config(session, config_name)
                if config:
                    config_map[config_name] = config.id
            
            # Додаємо тесткейси
            added_testcases = 0
            
            for i, testcase_data in enumerate(testcases):
                if not testcase_data.get('step') or not testcase_data.get('expected_result'):
                    continue  # Пропускаємо порожні тесткейси
                
                # Знаходимо відповідний конфіг
                config_id = None
                config_name = testcase_data.get('config')
                if config_name and config_name in config_map:
                    config_id = config_map[config_name]
                
                # Валідуємо пріоритет
                priority = testcase_data.get('priority')
                if priority and priority not in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']:
                    priority = 'MEDIUM'
                
                # Обмежуємо довжину qa_auto_coverage
                qa_auto_coverage = testcase_data.get('qa_auto_coverage')
                if qa_auto_coverage and len(qa_auto_coverage) > 255:  # Обмежуємо до 255 символів
                    qa_auto_coverage = qa_auto_coverage[:252] + "..."
                
                # Обмежуємо довжину functionality
                functionality = testcase_data.get('functionality')
                if functionality and len(functionality) > 255:  # Обмежуємо до 255 символів
                    functionality = functionality[:252] + "..."
                
                # Обмежуємо довжину subcategory
                subcategory = testcase_data.get('subcategory')
                if subcategory and len(subcategory) > 255:  # Обмежуємо до 255 символів
                    subcategory = subcategory[:252] + "..."
                
                # Створюємо тесткейс
                testcase = TestCase(
                    checklist_id=checklist_id,
                    step=testcase_data.get('step', 'No step defined')[:2000],  # Обмежуємо довжину
                    expected_result=testcase_data.get('expected_result', 'No result defined')[:2000],
                    screenshot=testcase_data.get('screenshot'),
                    priority=priority,
                    test_group=testcase_data.get('test_group', 'GENERAL'),
                    functionality=functionality,
                    subcategory=subcategory,
                    order_index=testcase_data.get('order_index', i),
                    config_id=config_id,
                    qa_auto_coverage=qa_auto_coverage
                )
                
                session.add(testcase)
                added_testcases += 1
            
            # Оновлюємо чекліст
            checklist.description = f"QA тестування функціональності {self.checklist_info['title']}, включаючи перевірку параметрів, відображення елементів інтерфейсу та поведінку системи при різних умовах."
            checklist.updated_at = datetime.now(timezone.utc)
            
            session.commit()
            
            print(f"✅ Успішно додано {added_testcases} тесткейсів")
            print(f"✅ Створено {len(config_map)} конфігів")
            
            return {
                "success": True,
                "testcases_added": added_testcases,
                "configs_created": len(config_map),
                "checklist_updated": True
            }
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def _get_or_create_config(self, session, config_name: str) -> Optional[Config]:
        """Отримує або створює конфігурацію."""
        if not config_name:
            return None
        
        # Витягуємо назву конфігу з URL
        if 'fileName=' in config_name:
            # Витягуємо назву файлу з URL
            config_display_name = config_name.split('fileName=')[-1].split('&')[0]
            config_display_name = config_display_name.replace('%2F', '/').replace('%2f', '/')
        else:
            config_display_name = config_name
        
        # Шукаємо існуючий конфіг
        config = session.query(Config).filter(Config.name == config_display_name).first()
        if config:
            return config
        
        # Створюємо новий
        config = Config(
            name=config_display_name,
            description=f"Configuration: {config_display_name}",
            url=config_name if config_name.startswith('http') else None
        )
        session.add(config)
        session.flush()
        return config
    
    def close(self):
        """Закриває ресурси."""
        if self.qa_repo:
            self.qa_repo.close()


@click.command()
@click.option('--checklist', '-c', help='Назва чекліста або його ID')
@click.option('--list-checklists', '-l', is_flag=True, help='Показати список доступних чеклістів')
@click.option('--dry-run', is_flag=True, help='Тільки аналіз без збереження в базу')
def main(checklist, list_checklists, dry_run):
    """Універсальний екстрактор тесткейсів для будь-якого чекліста."""
    
    if list_checklists:
        asyncio.run(list_available_checklists())
        return
    
    if not checklist:
        print("❌ Помилка: Потрібно вказати --checklist або --list-checklists")
        print("Використовуйте --help для довідки")
        return
    
    print("🎯 Універсальний екстрактор тесткейсів")
    print("=" * 60)
    
    extractor = UniversalChecklistExtractor()
    
    try:
        if dry_run:
            print("🔍 РЕЖИМ АНАЛІЗУ (без збереження)")
            
        result = asyncio.run(extractor.extract_and_populate_testcases(checklist))
        
        if result["success"]:
            print("\n🎉 УСПІШНО ЗАВЕРШЕНО!")
            print("=" * 60)
            print(f"✅ Додано тесткейсів: {result['testcases_added']}")
            print(f"✅ Створено конфігів: {result['configs_created']}")
            print(f"✅ Чекліст оновлено: {result['checklist_updated']}")
        else:
            print(f"\n❌ ПОМИЛКА: {result['error']}")
            
    except KeyboardInterrupt:
        print("\n\n⏹️ Перервано користувачем")
    except Exception as e:
        print(f"\n❌ Неочікувана помилка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        extractor.close()


async def list_available_checklists():
    """Показує список доступних чеклістів."""
    print("📋 Доступні чекліст:")
    print("=" * 60)
    
    qa_repo = QARepository()
    session = qa_repo.get_session()
    
    try:
        checklists = session.query(Checklist).order_by(Checklist.title).all()
        
        for checklist in checklists:
            testcase_count = session.query(TestCase).filter(TestCase.checklist_id == checklist.id).count()
            status = "✅ Заповнений" if testcase_count > 0 else "❌ Порожній"
            
            print(f"ID: {checklist.id:3d} | {status} | {checklist.title} ({testcase_count} тесткейсів)")
            
    finally:
        session.close()
        qa_repo.close()


if __name__ == "__main__":
    main()
