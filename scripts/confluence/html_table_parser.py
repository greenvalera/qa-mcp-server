#!/usr/bin/env python3
"""
Покращений HTML Table Parser для витягування тесткейсів з Confluence таблиць
На основі аналізу реальних структур чеклістів
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup, Tag
import logging

logger = logging.getLogger(__name__)

class EnhancedConfluenceTableParser:
    """Покращений парсер для витягування тесткейсів з HTML таблиць Confluence"""
    
    def __init__(self):
        self.priority_map = {
            'HIGHEST': 'HIGHEST',
            'HIGH': 'HIGH', 
            'MEDIUM': 'MEDIUM',
            'LOW': 'LOW',
            'CRITICAL': 'CRITICAL'
        }
        
        # Схема розпізнавання на основі аналізу реальних структур
        self.table_schemas = {
            'standard_7_col': {
                'columns': 7,
                'headers': ['№', 'STEP', 'EXPECTED RESULT', 'SCREENSHOT', 'PRIORITY', 'CONFIG', 'QA AUTO COVERAGE'],
                'column_mapping': {
                    'number': 0,
                    'step': 1,
                    'expected': 2,
                    'screenshot': 3,
                    'priority': 4,
                    'config': 5,
                    'qa_coverage': 6
                }
            },
            'standard_8_col': {
                'columns': 8,
                'headers': ['№', 'STEP', 'EXPECTED RESULT', 'SCREENSHOT', 'PRIORITY', 'CONFIG', 'QA AUTO COVERAGE', 'EXTRA'],
                'column_mapping': {
                    'number': 0,
                    'step': 1,
                    'expected': 2,
                    'screenshot': 3,
                    'priority': 4,
                    'config': 5,
                    'qa_coverage': 6,
                    'extra': 7
                }
            },
            'simple_4_col': {
                'columns': 4,
                'headers': ['№', 'STEP', 'EXPECTED RESULT', 'PRIORITY'],
                'column_mapping': {
                    'number': 0,
                    'step': 1,
                    'expected': 2,
                    'priority': 3
                }
            },
            'simple_3_col': {
                'columns': 3,
                'headers': ['STEP', 'EXPECTED RESULT', 'PRIORITY'],
                'column_mapping': {
                    'step': 0,
                    'expected': 1,
                    'priority': 2
                }
            }
        }
        
        # Розширені ключові слова для функціональності
        self.functionality_keywords = {
            'registration': ['регистр', 'зарегистр', 'registration', 'signup', 'sign up'],
            'validation': ['валидац', 'validation', 'сработала', 'проверка', 'check'],
            'navigation': ['перейти', 'кликнуть', 'navigate', 'click', 'переход'],
            'form': ['форма', 'поле', 'form', 'field', 'input'],
            'email': ['email', 'мейл', 'почта', 'mail'],
            'password': ['пароль', 'password', 'pwd'],
            'location': ['локация', 'location', 'live in', 'место'],
            'logo': ['логотип', 'фавикон', 'logo', 'favicon'],
            'search': ['поиск', 'search', 'найти', 'find'],
            'profile': ['профиль', 'profile', 'профіль'],
            'settings': ['настройки', 'settings', 'налаштування'],
            'notification': ['уведомление', 'notification', 'повідомлення'],
            'upload': ['загрузка', 'upload', 'завантаження'],
            'download': ['скачивание', 'download', 'завантаження'],
            'authentication': ['авторизация', 'authentication', 'автентифікація'],
            'authorization': ['авторизация', 'authorization', 'авторизація']
        }
        
        # Розширені ключові слова для підкатегорій
        self.subcategory_keywords = {
            'UI Elements': ['кнопка', 'форма', 'поле', 'button', 'form', 'field', 'элемент', 'element'],
            'Validation': ['валидация', 'validation', 'сработала', 'проверка', 'check'],
            'Navigation': ['перейти', 'переход', 'navigate', 'redirect', 'клик', 'click'],
            'Data Input': ['ввести', 'заполн', 'input', 'fill', 'ввод', 'введення'],
            'Visual Check': ['отображ', 'проверить', 'display', 'check', 'визуальн', 'visual'],
            'API Testing': ['api', 'запрос', 'request', 'response', 'endpoint'],
            'Performance': ['производительность', 'performance', 'скорость', 'speed'],
            'Security': ['безопасность', 'security', 'защита', 'protection']
        }
    
    def parse_testcases_from_html(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Витягує тесткейси з HTML контенту Confluence сторінки
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            testcases = []
            
            # Знаходимо всі таблиці з тесткейсами
            testcase_tables = self._find_testcase_tables(soup)
            
            for table in testcase_tables:
                table_testcases = self._parse_table(table)
                testcases.extend(table_testcases)
            
            logger.info(f"Витягнуто {len(testcases)} тесткейсів з HTML")
            return testcases
            
        except Exception as e:
            logger.error(f"Помилка при парсингу HTML: {e}")
            return []
    
    def _find_testcase_tables(self, soup: BeautifulSoup) -> List[Tag]:
        """Знаходить всі таблиці з тесткейсами"""
        
        tables = soup.find_all('table')
        testcase_tables = []
        
        for table in tables:
            if self._is_testcase_table(table):
                testcase_tables.append(table)
        
        return testcase_tables
    
    def _is_testcase_table(self, table: Tag) -> bool:
        """Перевіряє чи є таблиця таблицею з тесткейсами"""
        
        rows = table.find_all('tr')
        if not rows:
            return False
        
        # Перевіряємо заголовки таблиці
        header_row = rows[0]
        headers = [th.get_text(strip=True).upper() for th in header_row.find_all(['th', 'td'])]
        
        # Перевіряємо наявність ключових колонок
        key_columns = ['STEP', 'EXPECTED', 'PRIORITY', 'CONFIG', 'ШАГ', 'ОЖИДАЕМЫЙ', 'ПРИОРИТЕТ']
        header_text = ' '.join(headers)
        
        return any(col in header_text for col in key_columns)
    
    def _parse_table(self, table: Tag) -> List[Dict[str, Any]]:
        """Парсить одну таблицю"""
        
        rows = table.find_all('tr')
        if not rows:
            return []
        
        # Визначаємо схему таблиці
        schema = self._detect_table_schema(rows[0])
        if not schema:
            logger.warning("Не вдалося визначити схему таблиці")
            return []
        
        testcases = []
        current_section = "GENERAL"
        current_functionality = None
        
        for i, row in enumerate(rows[1:], 1):  # Пропускаємо заголовок
            cells = row.find_all(['td', 'th'])
            
            # Перевіряємо чи це заголовок секції
            if self._is_section_header_row(row, cells):
                section_info = self._extract_section_info(cells)
                current_section = section_info['section']
                current_functionality = section_info['functionality']
                continue
            
            # Перевіряємо чи це розділовий рядок (підзаголовок)
            if self._is_subsection_header(cells):
                # Витягуємо функціональність з розділового рядка
                divider_functionality = self._extract_functionality_from_divider_row(cells)
                if divider_functionality:
                    current_functionality = divider_functionality
                continue
            
            # Парсимо тесткейс
            testcase = self._parse_testcase_row(cells, schema, current_section, current_functionality)
            if testcase:
                testcases.append(testcase)
        
        return testcases
    
    def _detect_table_schema(self, header_row: Tag) -> Optional[Dict[str, Any]]:
        """Визначає схему таблиці на основі заголовків"""
        
        headers = [th.get_text(strip=True).upper() for th in header_row.find_all(['th', 'td'])]
        column_count = len(headers)
        
        # Спробуємо знайти найкращу відповідність
        best_match = None
        best_score = 0
        
        for schema_name, schema in self.table_schemas.items():
            if schema['columns'] == column_count:
                # Перевіряємо схожість заголовків
                score = self._calculate_header_similarity(headers, schema['headers'])
                if score > best_score:
                    best_score = score
                    best_match = schema
        
        # Якщо не знайшли точну відповідність, створюємо адаптивну схему
        if not best_match or best_score < 0.5:
            best_match = self._create_adaptive_schema(headers)
        
        return best_match
    
    def _calculate_header_similarity(self, headers1: List[str], headers2: List[str]) -> float:
        """Обчислює схожість між заголовками"""
        
        if len(headers1) != len(headers2):
            return 0.0
        
        matches = 0
        for h1, h2 in zip(headers1, headers2):
            if h1 == h2 or any(keyword in h1 for keyword in h2.split()) or any(keyword in h2 for keyword in h1.split()):
                matches += 1
        
        return matches / len(headers1)
    
    def _create_adaptive_schema(self, headers: List[str]) -> Dict[str, Any]:
        """Створює адаптивну схему на основі заголовків"""
        
        column_mapping = {}
        
        for i, header in enumerate(headers):
            header_upper = header.upper()
            
            if any(keyword in header_upper for keyword in ['№', 'NUMBER', 'NUM', 'НОМЕР']):
                column_mapping['number'] = i
            elif any(keyword in header_upper for keyword in ['STEP', 'ШАГ', 'ДЕЙСТВИЕ']):
                column_mapping['step'] = i
            elif any(keyword in header_upper for keyword in ['EXPECTED', 'ОЖИДАЕМЫЙ', 'RESULT', 'РЕЗУЛЬТАТ']):
                column_mapping['expected'] = i
            elif any(keyword in header_upper for keyword in ['SCREENSHOT', 'СКРИНШОТ', 'SCREEN']):
                column_mapping['screenshot'] = i
            elif any(keyword in header_upper for keyword in ['PRIORITY', 'ПРИОРИТЕТ', 'PRIOR']):
                column_mapping['priority'] = i
            elif any(keyword in header_upper for keyword in ['CONFIG', 'КОНФИГ', 'CONFIGURATION']):
                column_mapping['config'] = i
            elif any(keyword in header_upper for keyword in ['QA', 'COVERAGE', 'ПОКРЫТИЕ']):
                column_mapping['qa_coverage'] = i
        
        return {
            'columns': len(headers),
            'headers': headers,
            'column_mapping': column_mapping
        }
    
    def _is_section_header_row(self, row: Tag, cells: List[Tag]) -> bool:
        """Перевіряє чи є рядок заголовком секції"""
        
        # Перевіряємо colspan
        for cell in cells:
            colspan = cell.get('colspan')
            if colspan and int(colspan) >= 3:
                text = cell.get_text(strip=True).upper()
                if self._is_section_name(text):
                    return True
        
        return False
    
    def _is_section_name(self, text: str) -> bool:
        """Перевіряє чи є текст назвою секції"""
        
        section_names = ['GENERAL', 'CUSTOM', 'SECTION', 'РАЗДЕЛ', 'ЧАСТЬ']
        return any(name in text for name in section_names)
    
    def _extract_section_info(self, cells: List[Tag]) -> Dict[str, str]:
        """Витягує інформацію про секцію"""
        
        section = "GENERAL"
        functionality = None
        
        for cell in cells:
            text = cell.get_text(strip=True).upper()
            
            if text in ['GENERAL', 'CUSTOM']:
                section = text
            elif self._is_section_name(text):
                # Спробуємо визначити функціональність з назви секції
                functionality = self._extract_functionality_from_text(text)
        
        return {
            'section': section,
            'functionality': functionality
        }
    
    def _is_subsection_header(self, cells: List[Tag]) -> bool:
        """Перевіряє чи є рядок підзаголовком або розділовим рядком"""
        
        # Перевіряємо colspan (рядки що займають всю ширину таблиці)
        for cell in cells:
            colspan = cell.get('colspan')
            if colspan and int(colspan) >= 3:
                text = cell.get_text(strip=True).lower()
                subsection_keywords = ['pre condition', 'steps', 'precondition', 'условие', 'шаги']
                if any(keyword in text for keyword in subsection_keywords):
                    return True
        
        # Перевіряємо чи це розділовий рядок (має тільки один заповнений стовпець або colspan)
        if len(cells) >= 2:
            # Перевіряємо чи є комірка з colspan (розділовий рядок)
            for cell in cells:
                if cell.get('colspan'):
                    text = cell.get_text(strip=True)
                    if text:
                        functionality_keywords = [
                            'подписка', 'трекинг', 'уведомления', 'тайминги', 'route', 
                            'addfirstfavorite', 'openprofile', 'addlike', 'sendsecondmessage',
                            'windows', 'macos', 'кастомных', 'попапов', 'бейдж', 'счетчик',
                            'получение', 'прочтение', 'удаление', 'пуш', 'уведомлений'
                        ]
                        text_lower = text.lower()
                        if any(keyword in text_lower for keyword in functionality_keywords):
                            return True
            
            # Перевіряємо чи перший стовпець заповнений, а решта порожні
            first_cell_text = cells[0].get_text(strip=True)
            other_cells_empty = all(not cell.get_text(strip=True) for cell in cells[1:])
            
            if first_cell_text and other_cells_empty:
                # Додаткові перевірки для розділових рядків
                functionality_keywords = [
                    'подписка', 'трекинг', 'уведомления', 'тайминги', 'route', 
                    'addfirstfavorite', 'openprofile', 'addlike', 'sendsecondmessage',
                    'windows', 'macos', 'кастомных', 'попапов', 'бейдж', 'счетчик',
                    'получение', 'прочтение', 'удаление', 'пуш', 'уведомлений'
                ]
                text_lower = first_cell_text.lower()
                if any(keyword in text_lower for keyword in functionality_keywords):
                    return True
        
        return False
    
    def _extract_functionality_from_divider_row(self, cells: List[Tag]) -> Optional[str]:
        """Витягує функціональність з розділового рядка"""
        
        if not cells:
            return None
        
        # Спочатку шукаємо комірку з colspan (розділовий рядок)
        for cell in cells:
            if cell.get('colspan'):
                text = cell.get_text(strip=True)
                if text:
                    break
        else:
            # Якщо немає colspan, беремо текст з першого стовпця
            text = cells[0].get_text(strip=True)
        
        if not text:
            return None
        
        # Мапінг розділових рядків на функціональності
        functionality_mapping = {
            'подписка - windows': 'Подписка - Windows',
            'подписка - macos': 'Подписка - MacOS', 
            'трекинг': 'Трекинг',
            'уведомления': 'Уведомления',
            'тайминги появления попапов': 'Тайминги',
            'route': 'Route',
            'addfirstfavorite': 'AddFirstFavorite',
            'openprofile': 'OpenProfile',
            'addlike': 'AddLike',
            'sendsecondmessage': 'SendSecondMessage',
            'работа кастомных попапов на macos': 'Кастомные попапы MacOS',
            # Додаткові варіанти
            'подписка': 'Подписка',
            'windows': 'Подписка - Windows',
            'macos': 'Подписка - MacOS',
            'кастомных попапов': 'Кастомные попапы',
            'попапов': 'Попапы'
        }
        
        text_lower = text.lower()
        for key, value in functionality_mapping.items():
            if key in text_lower:
                return value
        
        # Якщо не знайшли точну відповідність, повертаємо оригінальний текст
        return text
    
    def _is_likely_divider_row(self, step_text: str) -> bool:
        """Перевіряє чи схожий текст на розділовий рядок"""
        
        step_lower = step_text.lower()
        
        # Ключові слова що вказують на розділові рядки
        divider_keywords = [
            'подписка - windows',
            'подписка - macos', 
            'трекинг',
            'уведомления',
            'тайминги появления попапов',
            'route',
            'addfirstfavorite',
            'openprofile',
            'addlike',
            'sendsecondmessage',
            'работа кастомных попапов на macos',
            'бейдж со счетчиком',
            'получение уведомлений',
            'прочтение уведомлений',
            'удаление уведомлений',
            'кастомные попапы'
        ]
        
        # Якщо текст короткий і містить ключові слова
        if len(step_text.strip()) < 50:
            for keyword in divider_keywords:
                if keyword in step_lower:
                    return True
        
        return False
    
    def _parse_testcase_row(self, cells: List[Tag], schema: Dict[str, Any], 
                           current_section: str, current_functionality: str) -> Optional[Dict[str, Any]]:
        """Парсить рядок тесткейсу"""
        
        if len(cells) < 2:
            return None
        
        try:
            # Витягуємо дані згідно зі схемою
            step = self._extract_cell_content(cells, schema, 'step')
            expected = self._extract_cell_content(cells, schema, 'expected')
            
            # Перевіряємо чи це валідний тесткейс
            if not step or len(step.strip()) < 10:
                return None
            
            # Додаткова перевірка: якщо expected_result порожній, це може бути розділовий рядок
            if not expected or not expected.strip():
                # Перевіряємо чи це не розділовий рядок
                if self._is_likely_divider_row(step):
                    return None
            
            # Витягуємо інші поля
            priority = self._extract_priority_from_cell(cells, schema)
            config = self._extract_cell_content(cells, schema, 'config')
            qa_coverage = self._extract_cell_content(cells, schema, 'qa_coverage')
            screenshot = self._extract_cell_content(cells, schema, 'screenshot')
            
            # Визначаємо функціональність
            functionality = current_functionality or self._extract_functionality(step, config)
            
            # Визначаємо test_group
            test_group = "CUSTOM" if current_section == "CUSTOM" else "GENERAL"
            
            return {
                'step': step.strip(),
                'expected_result': expected.strip() if expected else "",
                'priority': priority,
                'test_group': test_group,
                'functionality': functionality,
                'subcategory': self._extract_subcategory(step),
                'config': config.strip() if config else None,
                'qa_auto_coverage': qa_coverage.strip() if qa_coverage else None,
                'screenshot': screenshot.strip() if screenshot else None,
                'section': current_section
            }
            
        except Exception as e:
            logger.error(f"Помилка при парсингу рядка: {e}")
            return None
    
    def _extract_cell_content(self, cells: List[Tag], schema: Dict[str, Any], field: str) -> Optional[str]:
        """Витягує вміст комірки за схемою"""
        
        column_mapping = schema.get('column_mapping', {})
        if field not in column_mapping:
            return None
        
        cell_index = column_mapping[field]
        if cell_index >= len(cells):
            return None
        
        return self._extract_text_from_cell(cells[cell_index])
    
    def _extract_text_from_cell(self, cell: Tag) -> str:
        """Витягує текст з комірки, обробляючи списки та посилання"""
        
        if not cell:
            return ""
        
        # Обробляємо списки
        lists = cell.find_all(['ul', 'ol'])
        for list_elem in lists:
            items = list_elem.find_all('li')
            list_text = '\n'.join([f"- {item.get_text(strip=True)}" for item in items])
            list_elem.replace_with(list_text)
        
        # Витягуємо текст
        text = cell.get_text(separator=' ', strip=True)
        
        # Очищаємо зайві пробіли
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    def _extract_priority_from_cell(self, cells: List[Tag], schema: Dict[str, Any]) -> Optional[str]:
        """Витягує пріоритет з комірки"""
        
        priority_text = self._extract_cell_content(cells, schema, 'priority')
        if not priority_text:
            return None
        
        priority_upper = priority_text.upper()
        
        for priority in self.priority_map.keys():
            if priority in priority_upper:
                return priority
        
        return None
    
    def _extract_functionality(self, step: str, config: str) -> Optional[str]:
        """Витягує функціональність на основі кроку та конфігу"""
        
        step_lower = step.lower()
        config_lower = config.lower() if config else ""
        combined_text = f"{step_lower} {config_lower}"
        
        # Спеціальна логіка для Navigation - перевіряємо чи це дійсно навігаційний тесткейс
        if self._is_navigation_testcase(step_lower):
            return "Navigation"
        
        # Перевіряємо інші функціональності
        for func, keywords in self.functionality_keywords.items():
            if func == 'navigation':  # Пропускаємо navigation, вже обробили
                continue
            if any(keyword in combined_text for keyword in keywords):
                return func.title()
        
        return None
    
    def _is_navigation_testcase(self, step_lower: str) -> bool:
        """Перевіряє чи є тесткейс дійсно навігаційним"""
        
        # Ключові фрази що вказують на навігаційні тесткейси
        navigation_phrases = [
            'переход на',
            'перейти на страницу',
            'кликнуть на кнопку',
            'кликнуть на пункт',
            'кликнуть на иконку',
            'тапнуть кнопку',
            'тапнуть по',
            'переход по кнопке',
            'переход с',
            'переход на платежку'
        ]
        
        # Якщо є одна з цих фраз - це навігаційний тесткейс
        for phrase in navigation_phrases:
            if phrase in step_lower:
                return True
        
        # Додаткові перевірки для специфічних навігаційних слів
        navigation_words = ['кликнуть', 'переход', 'перейти']
        navigation_contexts = ['кнопку', 'пункт', 'иконку', 'страницу', 'платежку', 'профиль', 'меню']
        
        # Перевіряємо чи є навігаційні слова в контексті навігації
        has_navigation_word = any(word in step_lower for word in navigation_words)
        has_navigation_context = any(context in step_lower for context in navigation_contexts)
        
        # Тільки якщо є і навігаційне слово і контекст
        return has_navigation_word and has_navigation_context
    
    def _extract_functionality_from_text(self, text: str) -> Optional[str]:
        """Витягує функціональність з тексту"""
        
        text_lower = text.lower()
        
        for func, keywords in self.functionality_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return func.title()
        
        return None
    
    def _extract_subcategory(self, step: str) -> Optional[str]:
        """Витягує підкатегорію на основі кроку"""
        
        step_lower = step.lower()
        
        for subcat, keywords in self.subcategory_keywords.items():
            if any(keyword in step_lower for keyword in keywords):
                return subcat
        
        return None


def main():
    """Тестування покращеного парсера"""
    
    # Тестовий HTML (фрагмент)
    test_html = """
    <table class="confluenceTable">
        <tr>
            <th>№</th>
            <th>STEP</th>
            <th>EXPECTED RESULT</th>
            <th>SCREENSHOT</th>
            <th>PRIORITY</th>
            <th>CONFIG</th>
            <th>QA AUTO COVERAGE</th>
        </tr>
        <tr>
            <td colspan="7"><h3>GENERAL</h3></td>
        </tr>
        <tr>
            <td>1</td>
            <td>Проверить логотип, фавикон.</td>
            <td>Отображается согласно теме сайта.</td>
            <td></td>
            <td>HIGH</td>
            <td>Logos</td>
            <td>IndexPageTests faviconIndexPageTest</td>
        </tr>
        <tr>
            <td colspan="7"><h3>CUSTOM</h3></td>
        </tr>
        <tr>
            <td>2</td>
            <td>Проверить регистрацию пользователя.</td>
            <td>Пользователь успешно зарегистрирован.</td>
            <td></td>
            <td>MEDIUM</td>
            <td>Registration</td>
            <td>RegistrationTests</td>
        </tr>
    </table>
    """
    
    parser = EnhancedConfluenceTableParser()
    testcases = parser.parse_testcases_from_html(test_html)
    
    print(f"Знайдено {len(testcases)} тесткейсів:")
    for tc in testcases:
        print(f"- {tc['step'][:50]}... (Priority: {tc['priority']}, Functionality: {tc['functionality']})")


if __name__ == "__main__":
    main()
