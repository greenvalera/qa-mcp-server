"""Vector database repository using Qdrant."""

import uuid
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, CollectionInfo, PointStruct, 
    Filter, FieldCondition, MatchValue, SearchRequest
)
from qdrant_client.http.exceptions import UnexpectedResponse

from ..config import settings


class VectorDBRepository:
    """Repository for vector database operations using Qdrant."""
    
    COLLECTION_NAME = "qa_chunks"
    
    def __init__(self, url: Optional[str] = None):
        """Initialize Qdrant client."""
        self.url = url or settings.vectordb_url
        self.client = QdrantClient(url=self.url)
        self._ensure_collection()
    
    def _ensure_collection(self) -> None:
        """Ensure the collection exists."""
        try:
            self.client.get_collection(self.COLLECTION_NAME)
        except UnexpectedResponse:
            # Collection doesn't exist, create it
            self.client.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=1536,  # OpenAI text-embedding-3-small dimension
                    distance=Distance.COSINE
                )
            )
    
    def upsert_chunk(
        self,
        chunk_id: str,
        embedding: List[float],
        document_id: int,
        confluence_page_id: str,
        title: str,
        url: str,
        space: str,
        labels: Optional[List[str]],
        feature_id: Optional[int],
        feature_name: Optional[str],
        chunk_ordinal: int,
        text: str
    ) -> bool:
        """Upsert a single chunk into the vector database."""
        try:
            # Prepare payload (metadata)
            payload = {
                "document_id": document_id,
                "confluence_page_id": confluence_page_id,
                "title": title,
                "url": url,
                "space": space,
                "labels": labels or [],
                "feature_id": feature_id,
                "feature_name": feature_name,
                "chunk_ordinal": chunk_ordinal,
                "text": text[:512] if text else ""  # Truncate for storage
            }
            
            # Convert chunk_id to integer hash for Qdrant compatibility
            point_id = int(hashlib.md5(chunk_id.encode()).hexdigest()[:8], 16)
            
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={**payload, "original_chunk_id": chunk_id}
            )
            
            self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=[point]
            )
            return True
            
        except Exception as e:
            print(f"Error upserting chunk {chunk_id}: {e}")
            return False
    
    def upsert_chunks_batch(
        self,
        chunks_data: List[Dict[str, Any]]
    ) -> Tuple[int, int]:
        """Upsert multiple chunks in batch."""
        points = []
        successful = 0
        failed = 0
        
        for chunk_data in chunks_data:
            try:
                payload = {
                    "document_id": chunk_data["document_id"],
                    "confluence_page_id": chunk_data["confluence_page_id"],
                    "title": chunk_data["title"],
                    "url": chunk_data["url"],
                    "space": chunk_data["space"],
                    "labels": chunk_data.get("labels", []),
                    "feature_id": chunk_data.get("feature_id"),
                    "feature_name": chunk_data.get("feature_name"),
                    "chunk_ordinal": chunk_data["chunk_ordinal"],
                    "text": chunk_data["text"][:512] if chunk_data["text"] else ""
                }
                
                # Convert chunk_id to integer hash for Qdrant compatibility
                chunk_id = chunk_data["chunk_id"]
                point_id = int(hashlib.md5(chunk_id.encode()).hexdigest()[:8], 16)
                
                point = PointStruct(
                    id=point_id,
                    vector=chunk_data["embedding"],
                    payload={**payload, "original_chunk_id": chunk_id}
                )
                points.append(point)
                
            except Exception as e:
                print(f"Error preparing chunk {chunk_data.get('chunk_id', 'unknown')}: {e}")
                failed += 1
        
        # Batch upsert
        if points:
            try:
                self.client.upsert(
                    collection_name=self.COLLECTION_NAME,
                    points=points
                )
                successful = len(points)
            except Exception as e:
                print(f"Error in batch upsert: {e}")
                failed += len(points)
                successful = 0
        
        return successful, failed
    
    def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        feature_names: Optional[List[str]] = None,
        space_keys: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks."""
        try:
            # Build filter conditions
            filter_conditions = []
            
            if feature_names:
                filter_conditions.append(
                    FieldCondition(
                        key="feature_name",
                        match=MatchValue(value=feature_names[0] if len(feature_names) == 1 else feature_names)
                    )
                )
            
            if space_keys:
                filter_conditions.append(
                    FieldCondition(
                        key="space",
                        match=MatchValue(value=space_keys[0] if len(space_keys) == 1 else space_keys)
                    )
                )
            
            # Add custom filters
            if filters:
                for key, value in filters.items():
                    if key in ["space", "feature_name", "document_id"]:
                        filter_conditions.append(
                            FieldCondition(
                                key=key,
                                match=MatchValue(value=value)
                            )
                        )
            
            # Perform search
            search_filter = Filter(must=filter_conditions) if filter_conditions else None
            
            search_results = self.client.search(
                collection_name=self.COLLECTION_NAME,
                query_vector=query_vector,
                query_filter=search_filter,
                limit=top_k,
                with_payload=True,
                with_vectors=False
            )
            
            # Format results
            results = []
            for hit in search_results:
                result = {
                    "score": float(hit.score),
                    "feature": {
                        "name": hit.payload.get("feature_name"),
                        "id": hit.payload.get("feature_id")
                    },
                    "document": {
                        "id": hit.payload.get("document_id"),
                        "title": hit.payload.get("title"),
                        "url": hit.payload.get("url"),
                        "space": hit.payload.get("space"),
                        "labels": hit.payload.get("labels", [])
                    },
                    "chunk": {
                        "id": str(hit.id),
                        "text": hit.payload.get("text", ""),
                        "position": hit.payload.get("chunk_ordinal", 0)
                    }
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"Error searching vector database: {e}")
            return []
    
    def delete_document_chunks(self, document_id: int) -> bool:
        """Delete all chunks for a specific document."""
        try:
            filter_condition = Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id)
                    )
                ]
            )
            
            self.client.delete(
                collection_name=self.COLLECTION_NAME,
                points_selector=filter_condition
            )
            return True
            
        except Exception as e:
            print(f"Error deleting chunks for document {document_id}: {e}")
            return False
    
    def update_chunks_feature(
        self, 
        document_id: int, 
        feature_id: int, 
        feature_name: str
    ) -> bool:
        """Update feature information for all chunks of a document."""
        try:
            filter_condition = Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id)
                    )
                ]
            )
            
            # Set new feature information
            self.client.set_payload(
                collection_name=self.COLLECTION_NAME,
                payload={
                    "feature_id": feature_id,
                    "feature_name": feature_name
                },
                points=filter_condition
            )
            return True
            
        except Exception as e:
            print(f"Error updating chunks feature for document {document_id}: {e}")
            return False
    
    def health_check(self) -> bool:
        """Simple health check for the vector database."""
        try:
            self.client.get_collection(self.COLLECTION_NAME)
            return True
        except Exception:
            return False
    
    def get_health_stats(self) -> Dict[str, Any]:
        """Get health statistics for the vector database."""
        try:
            collection_info = self.client.get_collection(self.COLLECTION_NAME)
            
            return {
                "status": "ok",
                "collections": [self.COLLECTION_NAME],
                "count": collection_info.points_count,
                "vectors_count": collection_info.vectors_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "collections": [],
                "count": 0
            }
    
    def get_collection_info(self) -> Optional[CollectionInfo]:
        """Get detailed collection information."""
        try:
            return self.client.get_collection(self.COLLECTION_NAME)
        except Exception:
            return None
    
    def close(self) -> None:
        """Close the client connection."""
        if hasattr(self.client, 'close'):
            self.client.close()
