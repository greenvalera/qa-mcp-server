#!/usr/bin/env python3
"""
Покращений QA аналізатор з логікою з універсального скрипта.
Включає розбивку контенту на блоки та покращений парсинг.
"""

import os
import sys
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# Add app to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from app.ai.qa_analyzer import QAContentAnalyzer, QAAnalysisResult


class EnhancedQAAnalyzer(QAContentAnalyzer):
    """Покращений QA аналізатор з кращим парсингом."""
    
    def __init__(self, *args, **kwargs):
        """Ініціалізація."""
        super().__init__(*args, **kwargs)
    
    def analyze_qa_content_enhanced(self, title: str, content: str) -> QAAnalysisResult:
        """Покращений аналіз контенту з розбивкою на блоки."""
        
        # Спочатку стандартний аналіз
        initial_analysis = self.analyze_qa_content(title, content)
        
        # Якщо знайдено мало тесткейсів, спробуємо покращений метод
        if len(initial_analysis.testcases) < 10:
            print(f"🔍 Знайдено лише {len(initial_analysis.testcases)} тесткейсів, застосовуємо покращений аналіз")
            enhanced_testcases = self._enhance_testcase_extraction(content, initial_analysis.testcases)
            
            # Створюємо покращений результат
            return QAAnalysisResult(
                section_title=initial_analysis.section_title,
                checklist_title=initial_analysis.checklist_title,
                checklist_description=initial_analysis.checklist_description,
                additional_content=initial_analysis.additional_content,
                feature_name=initial_analysis.feature_name,
                feature_description=initial_analysis.feature_description,
                feature_id=initial_analysis.feature_id,
                testcases=enhanced_testcases,
                configs=initial_analysis.configs,
                analysis_confidence=initial_analysis.analysis_confidence,
                parsing_method="enhanced_llm"
            )
        
        return initial_analysis
    
    def _enhance_testcase_extraction(self, content: str, initial_testcases: List[Dict]) -> List[Dict]:
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
                block_analysis = self.analyze_qa_content(f"Block {i+1} - {self._get_block_title(block)}", block)
                
                # Додаємо нові унікальні тесткейси
                for testcase in block_analysis.testcases:
                    if not self._is_duplicate_testcase(testcase, enhanced_testcases):
                        testcase['order_index'] = len(enhanced_testcases)
                        enhanced_testcases.append(testcase)
                
            except Exception as e:
                print(f"⚠️ Помилка аналізу блоку {i+1}: {e}")
                continue
        
        print(f"✅ Покращений аналіз: {len(enhanced_testcases)} тесткейсів (було {len(initial_testcases)})")
        return enhanced_testcases
    
    def _split_content_into_blocks(self, content: str) -> List[str]:
        """Розділяє контент на логічні блоки для кращого аналізу."""
        
        # Розділяємо по заголовках та ключових словах
        delimiters = [
            "# GENERAL",
            "# CUSTOM", 
            "Header",
            "View after registration",
            "Search parameters",
            "Поисковая выдача",
            "Flirtcast",
            "Widget",
            "Footer Info",
            "CUSTOM",
            "GENERAL",
            "Login",
            "Registration",
            "Profile",
            "Settings",
            "Chat",
            "Payment",
            "Notification",
            "Menu",
            "Navigation"
        ]
        
        blocks = []
        current_block = ""
        
        lines = content.split('\n')
        
        for line in lines:
            # Перевіряємо чи є це розділювач
            is_delimiter = any(delimiter.lower() in line.lower() for delimiter in delimiters)
            
            if is_delimiter and current_block.strip():
                # Зберігаємо поточний блок
                blocks.append(current_block.strip())
                current_block = line + '\n'
            else:
                current_block += line + '\n'
        
        # Додаємо останній блок
        if current_block.strip():
            blocks.append(current_block.strip())
        
        # Фільтруємо блоки за розміром та якістю
        filtered_blocks = []
        for block in blocks:
            if len(block) > 200 and self._is_quality_block(block):
                filtered_blocks.append(block)
        
        print(f"📊 Розділено на {len(filtered_blocks)} якісних блоків (з {len(blocks)} загалом)")
        return filtered_blocks
    
    def _is_quality_block(self, block: str) -> bool:
        """Перевіряє чи є блок якісним для аналізу."""
        
        # Повинен містити ключові слова тестування
        quality_keywords = [
            'step', 'expected', 'result', 'test', 'check', 'verify', 
            'должен', 'должна', 'отображается', 'проверить',
            'зарегистрировать', 'пользователь', 'кнопка', 'поле',
            'priority', 'config', 'screenshot'
        ]
        
        block_lower = block.lower()
        keyword_count = sum(1 for keyword in quality_keywords if keyword in block_lower)
        
        # Повинен мати принаймні 2 ключові слова
        return keyword_count >= 2
    
    def _get_block_title(self, block: str) -> str:
        """Витягує заголовок блоку."""
        lines = block.split('\n')
        for line in lines[:3]:  # Перевіряємо перші 3 рядки
            line = line.strip()
            if line and not line.startswith('|') and len(line) < 100:
                return line[:50]
        return "Content Block"
    
    def _is_duplicate_testcase(self, testcase: Dict, existing_testcases: List[Dict]) -> bool:
        """Перевіряє чи є тесткейс дублікатом."""
        
        step = testcase.get('step', '').strip().lower()
        expected = testcase.get('expected_result', '').strip().lower()
        
        if not step and not expected:
            return True
        
        for existing in existing_testcases:
            existing_step = existing.get('step', '').strip().lower()
            existing_expected = existing.get('expected_result', '').strip().lower()
            
            # Простий алгоритм схожості
            if (step and existing_step and step[:50] == existing_step[:50]) or \
               (expected and existing_expected and expected[:50] == existing_expected[:50]):
                return True
        
        return False
