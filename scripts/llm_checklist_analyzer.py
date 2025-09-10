#!/usr/bin/env python3
"""LLM-based analyzer для розбору структури чеклістів."""

import os
import sys
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import click
from openai import OpenAI

# Add app to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.config import settings


@dataclass
class ChecklistAnalysis:
    """Результат аналізу чеклісту."""
    title: str
    description: str
    additional_content: str  # Додатковий контент до таблиці
    testcases: List[Dict[str, Any]]
    configs: List[str]
    structure_confidence: float  # Впевненість в правильності розбору


class LLMChecklistAnalyzer:
    """Аналізатор чеклістів з використанням LLM."""
    
    def __init__(self):
        """Ініціалізація."""
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY не встановлений")
        
        self.client = OpenAI(api_key=settings.openai_api_key)
    
    def analyze_checklist_content(self, title: str, content: str) -> ChecklistAnalysis:
        """Аналізує контент чеклісту за допомогою LLM."""
        
        prompt = self._create_analysis_prompt(title, content)
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=4000
            )
            
            result_text = response.choices[0].message.content
            analysis_data = self._parse_llm_response(result_text)
            
            return ChecklistAnalysis(
                title=title,
                description=analysis_data.get('description', ''),
                additional_content=analysis_data.get('additional_content', ''),
                testcases=analysis_data.get('testcases', []),
                configs=analysis_data.get('configs', []),
                structure_confidence=analysis_data.get('confidence', 0.0)
            )
            
        except Exception as e:
            click.echo(f"Помилка LLM аналізу: {e}")
            # Fallback до простого парсингу
            return self._fallback_analysis(title, content)
    
    def _get_system_prompt(self) -> str:
        """Системний промпт для LLM."""
        return """
Ти експерт по аналізу QA чеклістів. Твоя задача - розібрати HTML контент чеклісту і витягти структуровану інформацію.

СТРУКТУРА ЧЕКЛІСТУ:
1. Заголовок (title) - назва чеклісту
2. Опис (description) - короткий опис функціональності
3. Додатковий контент (additional_content) - весь текст/інформація ДО таблиці з тесткейсами
4. Тесткейси (testcases) - таблиця з тесткейсами
5. Конфіги (configs) - посилання на конфігурації

СТРУКТУРА ТЕСТКЕЙСІВ:
- step: опис кроку який треба зробити QA
- expected_result: що має відбутися
- screenshot: зображення (може бути відсутнє)
- priority: пріоритетність (LOW, MEDIUM, HIGH, CRITICAL)
- test_group: GENERAL або CUSTOM (розділяється спеціальними рядками в таблиці)
- functionality: конкретна функціональність (підгрупа в межах test_group)
- config: посилання на конфіг для цього тесткейсу
- qa_auto_coverage: покриття автотестами

ВАЖЛИВО:
- Розділювальні рядки в таблиці вказують на test_group (GENERAL/CUSTOM) або functionality
- Якщо рядок містить тільки одну заповнену комірку - це розділювач
- Конфіги можуть бути як в окремій колонці, так і в тексті
- Додатковий контент - це ВСЕ що йде до таблиці тесткейсів

Відповідь дай у форматі JSON.
"""
    
    def _create_analysis_prompt(self, title: str, content: str) -> str:
        """Створює промпт для аналізу конкретного чеклісту."""
        return f"""
Проаналізуй цей QA чекліст і витягни структуровану інформацію:

НАЗВА: {title}

КОНТЕНТ:
{content[:8000]}  # Обмежуємо довжину

Поверни результат у такому JSON форматі:
{{
  "description": "короткий опис функціональності",
  "additional_content": "весь текст/інформація до таблиці тесткейсів",
  "testcases": [
    {{
      "step": "опис кроку",
      "expected_result": "очікуваний результат",
      "screenshot": "посилання на скріншот або null",
      "priority": "LOW|MEDIUM|HIGH|CRITICAL або null",
      "test_group": "GENERAL|CUSTOM або null",
      "functionality": "назва функціональності або null",
      "config": "посилання на конфіг або null",
      "qa_auto_coverage": "покриття автотестами або null",
      "order_index": номер_порядку
    }}
  ],
  "configs": ["список всіх згаданих конфігів"],
  "confidence": 0.95
}}

Зверни особливу увагу на:
1. Розділювальні рядки які вказують test_group (GENERAL/CUSTOM)
2. Підрозділи функціональності
3. Всі посилання на конфіги
4. Правильний порядок тесткейсів
"""
    
    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Парсить відповідь LLM."""
        try:
            # Витягуємо JSON з відповіді
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("JSON не знайдений в відповіді")
            
            json_text = response_text[start_idx:end_idx]
            return json.loads(json_text)
            
        except Exception as e:
            click.echo(f"Помилка парсингу LLM відповіді: {e}")
            return {
                "description": "",
                "additional_content": "",
                "testcases": [],
                "configs": [],
                "confidence": 0.0
            }
    
    def _fallback_analysis(self, title: str, content: str) -> ChecklistAnalysis:
        """Резервний аналіз без LLM."""
        return ChecklistAnalysis(
            title=title,
            description="",
            additional_content=content[:1000],  # Перші 1000 символів як додатковий контент
            testcases=[],
            configs=[],
            structure_confidence=0.1  # Низька впевненість
        )
    
    def batch_analyze_checklists(self, checklists: List[Dict[str, str]]) -> List[ChecklistAnalysis]:
        """Аналізує список чеклістів."""
        results = []
        
        for i, checklist in enumerate(checklists):
            click.echo(f"Аналіз чеклісту {i+1}/{len(checklists)}: {checklist['title']}")
            
            try:
                analysis = self.analyze_checklist_content(
                    title=checklist['title'],
                    content=checklist['content']
                )
                results.append(analysis)
                
                click.echo(f"  ✓ Знайдено {len(analysis.testcases)} тесткейсів "
                          f"(впевненість: {analysis.structure_confidence:.2f})")
                
            except Exception as e:
                click.echo(f"  ✗ Помилка: {e}")
                # Додаємо fallback результат
                results.append(self._fallback_analysis(
                    checklist['title'], 
                    checklist.get('content', '')
                ))
        
        return results


@click.command()
@click.option('--input-file', required=True, help='JSON файл з чеклістами для аналізу')
@click.option('--output-file', required=True, help='JSON файл для збереження результатів')
@click.option('--confidence-threshold', default=0.7, help='Мінімальна впевненість для прийняття результату')
def main(input_file, output_file, confidence_threshold):
    """Аналізує чекліст за допомогою LLM."""
    
    if not os.path.exists(input_file):
        click.echo(f"Файл {input_file} не знайдений")
        sys.exit(1)
    
    # Завантажуємо дані
    with open(input_file, 'r', encoding='utf-8') as f:
        checklists_data = json.load(f)
    
    # Перетворюємо в список чеклістів
    checklists = []
    for page_id, page_data in checklists_data.items():
        if 'qa_section' in page_data:
            for checklist in page_data['qa_section'].get('checklists', []):
                checklists.append({
                    'page_id': page_id,
                    'title': checklist['title'],
                    'content': page_data.get('content', ''),
                    'url': page_data.get('page', {}).get('url', '')
                })
    
    if not checklists:
        click.echo("Чекліст для аналізу не знайдено")
        sys.exit(1)
    
    click.echo(f"Знайдено {len(checklists)} чеклістів для аналізу")
    
    # Аналізуємо
    analyzer = LLMChecklistAnalyzer()
    results = analyzer.batch_analyze_checklists(checklists)
    
    # Фільтруємо по впевненості
    high_confidence_results = [r for r in results if r.structure_confidence >= confidence_threshold]
    low_confidence_results = [r for r in results if r.structure_confidence < confidence_threshold]
    
    click.echo(f"\nРезультати:")
    click.echo(f"  Високої впевненості: {len(high_confidence_results)}")
    click.echo(f"  Низької впевненості: {len(low_confidence_results)}")
    
    # Зберігаємо результати
    output_data = {
        'high_confidence': [
            {
                'title': r.title,
                'description': r.description,
                'additional_content': r.additional_content,
                'testcases': r.testcases,
                'configs': r.configs,
                'confidence': r.structure_confidence
            } for r in high_confidence_results
        ],
        'low_confidence': [
            {
                'title': r.title,
                'description': r.description,
                'additional_content': r.additional_content,
                'testcases': r.testcases,
                'configs': r.configs,
                'confidence': r.structure_confidence
            } for r in low_confidence_results
        ],
        'summary': {
            'total_checklists': len(results),
            'high_confidence_count': len(high_confidence_results),
            'low_confidence_count': len(low_confidence_results),
            'confidence_threshold': confidence_threshold
        }
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    click.echo(f"\nРезультати збережено у {output_file}")


if __name__ == "__main__":
    main()
