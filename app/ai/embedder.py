"""OpenAI embeddings provider."""

import time
from typing import List, Optional, Union
import openai
from openai import OpenAI

from ..config import settings


class OpenAIEmbedder:
    """OpenAI embeddings provider."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize OpenAI embedder."""
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_embedding_model
        self.client = OpenAI(api_key=self.api_key)
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
    
    def _rate_limit(self) -> None:
        """Simple rate limiting."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
    
    def embed_text(self, text: str) -> Optional[List[float]]:
        """Get embedding for a single text."""
        try:
            self._rate_limit()
            
            response = self.client.embeddings.create(
                input=text,
                model=self.model
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            print(f"Error getting embedding for text: {e}")
            return None
    
    def embed_batch(
        self, 
        texts: List[str], 
        batch_size: int = 64
    ) -> List[Optional[List[float]]]:
        """Get embeddings for multiple texts in batches."""
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self._embed_batch_internal(batch)
            embeddings.extend(batch_embeddings)
        
        return embeddings
    
    def _embed_batch_internal(
        self, 
        texts: List[str]
    ) -> List[Optional[List[float]]]:
        """Internal method to embed a single batch."""
        try:
            self._rate_limit()
            
            response = self.client.embeddings.create(
                input=texts,
                model=self.model
            )
            
            # Extract embeddings in order
            embeddings = []
            for data in response.data:
                embeddings.append(data.embedding)
            
            return embeddings
            
        except Exception as e:
            print(f"Error getting batch embeddings: {e}")
            # Return None for each text in case of error
            return [None] * len(texts)
    
    def embed_texts_with_retry(
        self, 
        texts: List[str], 
        max_retries: int = 3,
        batch_size: int = 64
    ) -> List[Optional[List[float]]]:
        """Get embeddings with retry logic."""
        for attempt in range(max_retries):
            try:
                return self.embed_batch(texts, batch_size)
            except Exception as e:
                print(f"Embedding attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    # Last attempt failed, return None for all texts
                    return [None] * len(texts)
                # Exponential backoff
                time.sleep(2 ** attempt)
        
        return [None] * len(texts)
    
    def get_dimension(self) -> int:
        """Get the embedding dimension for the current model."""
        # Known dimensions for OpenAI models
        model_dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536
        }
        
        return model_dimensions.get(self.model, 1536)
    
    def test_connection(self) -> bool:
        """Test the connection to OpenAI API."""
        try:
            test_embedding = self.embed_text("test")
            return test_embedding is not None and len(test_embedding) > 0
        except Exception as e:
            print(f"OpenAI connection test failed: {e}")
            return False
