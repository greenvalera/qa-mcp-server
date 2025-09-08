#!/usr/bin/env python3
"""Confluence loader script for importing documents into QA MCP system."""

import os
import sys
import hashlib
import argparse
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import click
import tiktoken

# Add app to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.config import settings
from app.data import MySQLRepository, VectorDBRepository
from app.ai import OpenAIEmbedder, FeatureTagger
from app.models import IngestionJob
from confluence_mock import MockConfluenceAPI
from confluence_real import RealConfluenceAPI


class ChunkProcessor:
    """Text chunking processor."""
    
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        """Initialize chunker."""
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        self.tokenizer = tiktoken.get_encoding("cl100k_base")  # GPT-4 tokenizer
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.tokenizer.encode(text))
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks."""
        if not text.strip():
            return []
        
        # Split by paragraphs first
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        chunks = []
        current_chunk = ""
        current_tokens = 0
        
        for paragraph in paragraphs:
            paragraph_tokens = self.count_tokens(paragraph)
            
            # If single paragraph is too big, split it
            if paragraph_tokens > self.chunk_size:
                # Save current chunk if it has content
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                
                # Split large paragraph by sentences
                sentences = [s.strip() + '.' for s in paragraph.split('.') if s.strip()]
                chunk_sentences = []
                chunk_tokens = 0
                
                for sentence in sentences:
                    sentence_tokens = self.count_tokens(sentence)
                    
                    if chunk_tokens + sentence_tokens > self.chunk_size and chunk_sentences:
                        chunks.append(' '.join(chunk_sentences))
                        # Keep some overlap
                        overlap_sentences = chunk_sentences[-2:] if len(chunk_sentences) > 2 else chunk_sentences
                        chunk_sentences = overlap_sentences + [sentence]
                        chunk_tokens = sum(self.count_tokens(s) for s in chunk_sentences)
                    else:
                        chunk_sentences.append(sentence)
                        chunk_tokens += sentence_tokens
                
                if chunk_sentences:
                    chunks.append(' '.join(chunk_sentences))
                
                current_chunk = ""
                current_tokens = 0
                continue
            
            # Check if adding this paragraph would exceed chunk size
            if current_tokens + paragraph_tokens > self.chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                
                # Create overlap with previous chunk
                overlap_text = self._get_overlap_text(current_chunk)
                current_chunk = overlap_text + "\n\n" + paragraph if overlap_text else paragraph
                current_tokens = self.count_tokens(current_chunk)
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
                current_tokens += paragraph_tokens
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _get_overlap_text(self, chunk: str) -> str:
        """Get overlap text from the end of a chunk."""
        overlap_tokens = 0
        sentences = chunk.split('.')
        overlap_sentences = []
        
        # Take sentences from the end until we reach overlap size
        for sentence in reversed(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_tokens = self.count_tokens(sentence)
            if overlap_tokens + sentence_tokens > self.chunk_overlap:
                break
            
            overlap_sentences.insert(0, sentence)
            overlap_tokens += sentence_tokens
        
        return '. '.join(overlap_sentences) + '.' if overlap_sentences else ""


class ConfluenceLoader:
    """Main confluence loader class."""
    
    def __init__(self, use_mock: bool = True):
        """Initialize loader."""
        self.use_mock = use_mock
        self.mysql_repo = MySQLRepository()
        self.vector_repo = VectorDBRepository()
        self.embedder = OpenAIEmbedder()
        self.feature_tagger = FeatureTagger()
        self.chunker = ChunkProcessor()
        
        if use_mock:
            self.confluence_api = MockConfluenceAPI()
        else:
            self.confluence_api = RealConfluenceAPI()
    
    async def load_pages(
        self,
        space_keys: Optional[List[str]] = None,
        labels: Optional[List[str]] = None,
        updated_since: Optional[str] = None,
        once: bool = False,
        page_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Load pages from Confluence."""
        click.echo(f"Starting Confluence import...")
        click.echo(f"Spaces: {space_keys or 'all'}")
        click.echo(f"Labels: {labels or 'all'}")
        click.echo(f"Updated since: {updated_since or 'all time'}")
        
        # Create ingestion job
        job = self.mysql_repo.create_ingestion_job(
            details=f"Import from spaces: {space_keys}, labels: {labels}"
        )
        
        try:
            # Parse updated_since
            since_date = None
            if updated_since:
                since_date = datetime.fromisoformat(updated_since)
            
            # Fetch pages
            if page_ids and not self.use_mock:
                # Load specific pages with children for real API
                pages = self.confluence_api.get_pages_by_ids(
                    page_ids=page_ids,
                    include_children=True
                )
            else:
                # Use regular filtering method
                pages = self.confluence_api.get_pages(
                    space_keys=space_keys,
                    labels=labels,
                    updated_since=since_date
                )
            
            click.echo(f"Found {len(pages)} pages to process")
            
            documents_processed = 0
            chunks_created = 0
            features_created = 0
            
            for i, page in enumerate(pages):
                try:
                    click.echo(f"Processing page {i+1}/{len(pages)}: {page['title']}")
                    
                    # Process single page
                    doc_result = await self._process_page(page)
                    
                    documents_processed += 1
                    chunks_created += doc_result['chunks_created']
                    features_created += doc_result['features_created']
                    
                    click.echo(f"  ✓ Created {doc_result['chunks_created']} chunks")
                    
                except Exception as e:
                    click.echo(f"  ✗ Error processing page: {e}", err=True)
                    continue
            
            # Update job as successful
            self.mysql_repo.update_ingestion_job(
                job_id=job.id,
                status="success",
                details=f"Successfully processed {documents_processed} documents",
                documents_processed=documents_processed,
                chunks_created=chunks_created,
                features_created=features_created
            )
            
            click.echo(f"\n✓ Import completed successfully!")
            click.echo(f"  Documents processed: {documents_processed}")
            click.echo(f"  Chunks created: {chunks_created}")
            click.echo(f"  Features created: {features_created}")
            
            return {
                "success": True,
                "documents_processed": documents_processed,
                "chunks_created": chunks_created,
                "features_created": features_created
            }
            
        except Exception as e:
            # Update job as failed
            self.mysql_repo.update_ingestion_job(
                job_id=job.id,
                status="failed",
                details=f"Import failed: {str(e)}"
            )
            
            click.echo(f"\n✗ Import failed: {e}", err=True)
            return {"success": False, "error": str(e)}
    
    async def _process_page(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single Confluence page."""
        # Normalize content
        normalized_content = self.confluence_api.normalize_content(page["content"])
        
        # Create or update document
        document = self.mysql_repo.create_or_update_document(
            confluence_page_id=page["id"],
            title=page["title"],
            url=page["url"],
            space_key=page["space"],
            content=normalized_content,
            labels=page["labels"],
            version=page["version"]
        )
        
        # Chunk the content
        chunks = self.chunker.chunk_text(normalized_content)
        
        if not chunks:
            return {"chunks_created": 0, "features_created": 0}
        
        # Generate embeddings for chunks
        chunk_embeddings = self.embedder.embed_batch([f"{page['title']}\n\n{chunk}" for chunk in chunks])
        
        # Tag document with feature
        existing_features = self.mysql_repo.get_all_features_with_embeddings()
        feature_name, feature_description, feature_id = self.feature_tagger.tag_document(
            document_title=page["title"],
            document_content=normalized_content,
            document_embeddings=[emb for emb in chunk_embeddings if emb],
            existing_features=existing_features
        )
        
        features_created = 0
        if feature_id is None:
            # Create new feature
            feature = self.mysql_repo.create_feature(feature_name, feature_description)
            feature_id = feature.id
            features_created = 1
        
        # Associate document with feature
        self.mysql_repo.remove_document_features(document.id)  # Remove old associations
        self.mysql_repo.associate_document_with_feature(document.id, feature_id, confidence_score=0.95)
        
        # Upsert chunks to vector database
        chunks_data = []
        for i, (chunk_text, embedding) in enumerate(zip(chunks, chunk_embeddings)):
            if embedding is None:
                continue
            
            chunk_id = f"{document.id}_{i}"
            chunk_data = {
                "chunk_id": chunk_id,
                "embedding": embedding,
                "document_id": document.id,
                "confluence_page_id": page["id"],
                "title": page["title"],
                "url": page["url"],
                "space": page["space"],
                "labels": page["labels"],
                "feature_id": feature_id,
                "feature_name": feature_name,
                "chunk_ordinal": i,
                "text": chunk_text
            }
            chunks_data.append(chunk_data)
        
        # Batch upsert to vector database
        successful_chunks, failed_chunks = self.vector_repo.upsert_chunks_batch(chunks_data)
        
        return {
            "chunks_created": successful_chunks,
            "features_created": features_created
        }
    
    def close(self):
        """Clean up resources."""
        self.mysql_repo.close()
        self.vector_repo.close()


@click.command()
@click.option('--spaces', help='Comma-separated list of space keys (e.g., QA,ENG)')
@click.option('--labels', help='Comma-separated list of labels to filter by')
@click.option('--since', help='Load documents updated since this date (ISO format)')
@click.option('--once', is_flag=True, help='Run once and exit (vs continuous sync)')
@click.option('--use-real-api', is_flag=True, help='Use real Confluence API instead of mock')
@click.option('--test-connection', is_flag=True, help='Test Confluence connection and exit')
@click.option('--page-ids', help='Comma-separated list of specific page IDs to load with children')
@click.option('--use-config-pages', is_flag=True, help='Use root pages from configuration')
def main(spaces, labels, since, once, use_real_api, test_connection, page_ids, use_config_pages):
    """Load documents from Confluence into QA MCP system."""
    
    # Validate environment
    if not settings.openai_api_key:
        click.echo("Error: OPENAI_API_KEY not set", err=True)
        sys.exit(1)
    
    # Parse arguments
    space_keys = spaces.split(',') if spaces else None
    label_list = labels.split(',') if labels else None
    
    # Determine page IDs to load
    pages_to_load = None
    if use_config_pages:
        # Use root pages from configuration
        pages_to_load = settings.confluence_root_pages.split(',') if settings.confluence_root_pages else None
    elif page_ids:
        pages_to_load = page_ids.split(',')
    
    # Auto-configure for real API if no specific parameters provided
    if use_real_api:
        if not pages_to_load and not space_keys:
            if settings.confluence_root_pages and settings.confluence_space_key:
                click.echo("Using configuration from .env file:")
                click.echo(f"  Space: {settings.confluence_space_key}")
                click.echo(f"  Root pages: {settings.confluence_root_pages}")
                pages_to_load = settings.confluence_root_pages.split(',')
            else:
                click.echo("❌ Error: CONFLUENCE_SPACE_KEY and CONFLUENCE_ROOT_PAGES must be set in .env file")
                return
        
        # Show current Confluence configuration
        click.echo(f"Confluence URL: {settings.confluence_base_url}")
        click.echo(f"Auth token: {'***set***' if settings.confluence_auth_token else 'NOT SET'}")
    
    # Initialize loader
    loader = ConfluenceLoader(use_mock=not use_real_api)
    
    # Test connection if requested
    if test_connection:
        if not use_real_api:
            click.echo("Connection test is only available with --use-real-api flag")
            sys.exit(1)
        
        click.echo("Testing Confluence connection...")
        result = loader.confluence_api.test_connection()
        
        if result["success"]:
            click.echo(f"✓ Connection successful!")
            click.echo(f"  User: {result['user']}")
            click.echo(f"  Accessible spaces: {result['spaces_count']}")
            if result['spaces']:
                click.echo(f"  Spaces: {', '.join(result['spaces'])}")
            sys.exit(0)
        else:
            click.echo(f"✗ Connection failed: {result['error']}")
            sys.exit(1)
    
    try:
        # Run the loading process
        result = asyncio.run(loader.load_pages(
            space_keys=space_keys,
            labels=label_list,
            updated_since=since,
            once=once,
            page_ids=pages_to_load
        ))
        
        if result["success"]:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        click.echo("\n\nInterrupted by user", err=True)
        sys.exit(130)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)
    finally:
        loader.close()


if __name__ == "__main__":
    main()
