"""AI-based feature tagging using OpenAI."""

import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from openai import OpenAI

from app.config import settings
from app.ai.embedder import OpenAIEmbedder


class FeatureTagger:
    """AI-based feature tagger using OpenAI."""
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: Optional[str] = None,
        threshold: float = None
    ):
        """Initialize feature tagger."""
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
    
    def generate_feature_from_document(
        self, 
        document_title: str, 
        document_content: str,
        max_content_length: int = 4000
    ) -> Tuple[str, str]:
        """Generate feature name and description from document content."""
        # Truncate content to avoid token limits
        content = document_content[:max_content_length]
        
        prompt = f"""
Analyze the following technical document and create a concise feature category for it.

Document Title: {document_title}

Document Content:
{content}

Based on this document, provide:
1. A short feature name (2-4 words, like "Authentication", "Payment Processing", "User Interface")
2. A brief description (1-2 sentences explaining what this feature covers)

Respond in JSON format:
{{
  "name": "Feature Name",
  "description": "Brief description of what this feature encompasses"
}}

Focus on the main functionality or system component this document describes.
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a technical analyst that categorizes software documentation into functional features. Always respond with valid JSON."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Try to parse JSON response
            try:
                result = json.loads(result_text)
                return result.get("name", "General"), result.get("description", "")
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                print(f"Failed to parse JSON response: {result_text}")
                return "General", "Automatically categorized document"
            
        except Exception as e:
            print(f"Error generating feature from document: {e}")
            return "General", "Automatically categorized document"
    
    def prepare_features_with_embeddings(
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
    
    def tag_document(
        self, 
        document_title: str,
        document_content: str,
        document_embeddings: List[List[float]],
        existing_features: List[Dict[str, Any]]
    ) -> Tuple[str, str, int]:
        """
        Tag a document with a feature.
        
        Returns:
            Tuple of (feature_name, feature_description, feature_id)
            If feature_id is None, it means a new feature should be created.
        """
        # Calculate average document embedding
        if not document_embeddings:
            # Generate embedding if not provided
            doc_embedding = self.embedder.embed_text(
                f"{document_title}\n\n{document_content[:2000]}"
            )
            if not doc_embedding:
                return "General", "Failed to generate embedding", None
        else:
            # Average multiple chunk embeddings
            doc_embedding = np.mean(document_embeddings, axis=0).tolist()
        
        # Prepare existing features with embeddings
        features_with_embeddings = self.prepare_features_with_embeddings(existing_features)
        
        # Find best matching feature
        best_feature, best_similarity = self.find_best_feature_match(
            doc_embedding, 
            features_with_embeddings
        )
        
        # If similarity is above threshold, use existing feature
        if best_feature and best_similarity >= self.threshold:
            return (
                best_feature["name"], 
                best_feature.get("description", ""), 
                best_feature["id"]
            )
        
        # Generate new feature
        feature_name, feature_description = self.generate_feature_from_document(
            document_title, 
            document_content
        )
        
        return feature_name, feature_description, None
    
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
