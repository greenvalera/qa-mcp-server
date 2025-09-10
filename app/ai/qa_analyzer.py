"""AI-based QA content analyzer using OpenAI for comprehensive checklist analysis."""

import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from openai import OpenAI

from ..config import settings
from .embedder import OpenAIEmbedder


@dataclass
class QAAnalysisResult:
    """Result of QA content analysis."""
    # Section/Checklist info
    section_title: str
    checklist_title: str
    checklist_description: str
    additional_content: str
    
    # Feature classification
    feature_name: str
    feature_description: str
    feature_id: Optional[int]
    
    # Test cases
    testcases: List[Dict[str, Any]]
    configs: List[str]
    
    # Quality metrics
    analysis_confidence: float
    parsing_method: str  # "llm" or "fallback"


class QAContentAnalyzer:
    """Comprehensive QA content analyzer that replaces FeatureTagger."""
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: Optional[str] = None,
        threshold: float = None
    ):
        """Initialize QA analyzer."""
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_model
        self.threshold = threshold or settings.feature_sim_threshold
        self.client = OpenAI(api_key=self.api_key)
        self.embedder = OpenAIEmbedder(api_key=self.api_key)
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        vec1_np = np.array(vec1)
        vec2_np = np.array(vec2)
        
        dot_product = np.dot(vec1_np, vec2_np)
        norm1 = np.linalg.norm(vec1_np)
        norm2 = np.linalg.norm(vec2_np)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def analyze_qa_content(self, title: str, content: str) -> QAAnalysisResult:
        """Comprehensive analysis of QA content using LLM."""
        
        prompt = self._create_comprehensive_analysis_prompt(title, content)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=4000
            )
            
            result_text = response.choices[0].message.content
            analysis_data = self._parse_llm_response(result_text)
            
            return QAAnalysisResult(
                section_title=analysis_data.get('section_title', ''),
                checklist_title=title,
                checklist_description=analysis_data.get('checklist_description', ''),
                additional_content=analysis_data.get('additional_content', ''),
                feature_name=analysis_data.get('feature_name', 'General'),
                feature_description=analysis_data.get('feature_description', ''),
                feature_id=None,  # Will be resolved later
                testcases=analysis_data.get('testcases', []),
                configs=analysis_data.get('configs', []),
                analysis_confidence=analysis_data.get('confidence', 0.0),
                parsing_method="llm"
            )
            
        except Exception as e:
            print(f"LLM analysis failed: {e}")
            return self._fallback_analysis(title, content)
    
    def _get_system_prompt(self) -> str:
        """System prompt for comprehensive QA analysis."""
        return """
Ти експерт по аналізу QA чеклістів. Твоя задача - повністю розібрати HTML контент QA сторінки і витягти всю структуровану інформацію.

СТРУКТУРА QA КОНТЕНТУ:
1. Section (розділ) - глобальний розділ типу "Checklist WEB", "Checklist MOB"
2. Checklist (чекліст) - конкретна функціональність типу "WEB: Billing History"
3. Feature - категорія функціональності для класифікації
4. Additional content - весь текст/інформація ДО таблиці з тесткейсами
5. Test cases - структуровані тесткейси з таблиці

СТРУКТУРА ТЕСТКЕЙСІВ:
- step: опис кроку який треба зробити QA
- expected_result: що має відбутися  
- screenshot: зображення (може бути відсутнє)
- priority: пріоритетність (LOW, MEDIUM, HIGH, CRITICAL)
- test_group: GENERAL або CUSTOM (розділяється спеціальними рядками)
- functionality: конкретна функціональність (підгрупа в межах test_group)
- config: посилання на конфіг для цього тесткейсу
- qa_auto_coverage: покриття автотестами
- order_index: порядковий номер

ВАЖЛИВО:
- Розділювальні рядки в таблиці вказують на test_group (GENERAL/CUSTOM) або functionality
- Якщо рядок містить тільки одну заповнену комірку - це розділювач
- Additional content - це ВСЕ що йде до таблиці тесткейсів
- Feature name має бути коротким і описувати основну функціональність

Відповідь дай у форматі JSON.
"""
    
    def _create_comprehensive_analysis_prompt(self, title: str, content: str) -> str:
        """Create comprehensive analysis prompt."""
        return f"""
Проаналізуй цей QA контент і витягни ВСЮ структуровану інформацію:

НАЗВА: {title}

КОНТЕНТ:
{content[:8000]}  # Обмежуємо довжину

Поверни результат у такому JSON форматі:
{{
  "section_title": "назва глобального розділу (якщо можна визначити)",
  "checklist_description": "короткий опис функціональності чекліста",
  "additional_content": "весь текст/інформація до таблиці тесткейсів",
  "feature_name": "коротка назва фічі (2-4 слова)",
  "feature_description": "опис фічі для класифікації",
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
2. Підрозділи functionality
3. Всі посилання на конфіги
4. Правильний порядок тесткейсів
5. Весь додатковий контент до таблиці
"""
    
    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response."""
        try:
            # Extract JSON from response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("JSON not found in response")
            
            json_text = response_text[start_idx:end_idx]
            return json.loads(json_text)
            
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            return {
                "section_title": "",
                "checklist_description": "",
                "additional_content": "",
                "feature_name": "General",
                "feature_description": "",
                "testcases": [],
                "configs": [],
                "confidence": 0.0
            }
    
    def _fallback_analysis(self, title: str, content: str) -> QAAnalysisResult:
        """Fallback analysis without LLM."""
        return QAAnalysisResult(
            section_title="",
            checklist_title=title,
            checklist_description="",
            additional_content=content[:1000],  # First 1000 chars as additional content
            feature_name="General",
            feature_description="Automatically categorized document",
            feature_id=None,
            testcases=[],
            configs=[],
            analysis_confidence=0.1,
            parsing_method="fallback"
        )
    
    def find_best_feature_match(
        self, 
        document_embedding: List[float], 
        existing_features: List[Dict[str, Any]]
    ) -> Tuple[Optional[Dict[str, Any]], float]:
        """Find the best matching feature for a document embedding."""
        if not existing_features:
            return None, 0.0
        
        best_feature = None
        best_similarity = 0.0
        
        for feature in existing_features:
            if feature.get("vector") is None:
                continue
            
            similarity = self.cosine_similarity(
                document_embedding, 
                feature["vector"]
            )
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_feature = feature
        
        return best_feature, best_similarity
    
    def resolve_feature_id(
        self, 
        analysis_result: QAAnalysisResult,
        document_embeddings: List[List[float]],
        existing_features: List[Dict[str, Any]]
    ) -> QAAnalysisResult:
        """Resolve feature ID by matching with existing features."""
        if not document_embeddings:
            return analysis_result
        
        # Calculate average document embedding
        doc_embedding = np.mean(document_embeddings, axis=0).tolist()
        
        # Prepare existing features with embeddings
        features_with_embeddings = self._prepare_features_with_embeddings(existing_features)
        
        # Find best matching feature
        best_feature, best_similarity = self.find_best_feature_match(
            doc_embedding, 
            features_with_embeddings
        )
        
        # If similarity is above threshold, use existing feature
        if best_feature and best_similarity >= self.threshold:
            analysis_result.feature_name = best_feature["name"]
            analysis_result.feature_description = best_feature.get("description", "")
            analysis_result.feature_id = best_feature["id"]
        
        return analysis_result
    
    def _prepare_features_with_embeddings(
        self, 
        existing_features: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Add embeddings to existing features for similarity comparison."""
        features_with_embeddings = []
        
        for feature in existing_features:
            if feature.get("vector") is not None:
                # Already has embedding
                features_with_embeddings.append(feature)
                continue
            
            # Generate embedding for feature description
            feature_text = f"{feature['name']}: {feature.get('description', '')}"
            embedding = self.embedder.embed_text(feature_text)
            
            if embedding:
                feature_copy = feature.copy()
                feature_copy["vector"] = embedding
                features_with_embeddings.append(feature_copy)
        
        return features_with_embeddings
    
    def test_connection(self) -> bool:
        """Test the connection to OpenAI API."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=5
            )
            return True
        except Exception as e:
            print(f"OpenAI LLM connection test failed: {e}")
            return False
