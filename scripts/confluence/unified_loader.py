#!/usr/bin/env python3
"""Unified Confluence loader - об'єднує qa_loader.py та confluence_loader.py функціональність."""

import os
import sys
import hashlib
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import click
import tiktoken
from dataclasses import dataclass

# Add app to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from app.config import settings
from app.data.qa_repository import QARepository
from app.data.vectordb_repo import VectorDBRepository
from app.models.qa_models import QASection, Checklist, TestCase, Config, IngestionJob
from app.ai import OpenAIEmbedder
try:
    from .confluence_mock import MockConfluenceAPI
    from .confluence_real import RealConfluenceAPI
    from .html_table_parser import EnhancedConfluenceTableParser
except ImportError:
    # Fallback for direct script execution
    from confluence_mock import MockConfluenceAPI
    from confluence_real import RealConfluenceAPI
    from html_table_parser import EnhancedConfluenceTableParser


@dataclass
class LoadingProgress:
    """Клас для відстеження прогресу завантаження."""
    total_pages: int = 0
    processed_pages: int = 0
    total_checklists: int = 0
    processed_checklists: int = 0
    skipped_checklists: int = 0
    created_checklists: int = 0
    created_testcases: int = 0
    created_configs: int = 0
    sections_processed: int = 0
    chunks_created: int = 0
    
    def get_page_progress_percent(self) -> float:
        if self.total_pages == 0:
            return 0.0
        return (self.processed_pages / self.total_pages) * 100


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


class UnifiedConfluenceLoader:
    """Об'єднаний завантажувач Confluence даних для MySQL та векторної бази."""
    
    def __init__(self, use_mock: bool = True, load_mysql: bool = True, load_vector: bool = True):
        """Initialize unified loader."""
        self.use_mock = use_mock
        self.load_mysql = load_mysql
        self.load_vector = load_vector
        self.progress = LoadingProgress()
        
        # Initialize repositories
        if self.load_mysql:
            self.qa_repo = QARepository()
            self.html_parser = EnhancedConfluenceTableParser()  # Додаємо HTML парсер
            self._existing_checklists = set()
            self._load_existing_checklists()
        
        if self.load_vector:
            self.vector_repo = VectorDBRepository()
            self.embedder = OpenAIEmbedder()
            self.chunker = ChunkProcessor()
        
        # Initialize Confluence API
        if use_mock:
            self.confluence_api = MockConfluenceAPI()
        else:
            self.confluence_api = RealConfluenceAPI()
    
    def _load_existing_checklists(self):
        """Завантажуємо список існуючих чеклістів для пропуску."""
        try:
            session = self.qa_repo.get_session()
            existing = session.query(Checklist.confluence_page_id).all()
            self._existing_checklists = {page_id[0] for page_id in existing}
            click.echo(f"📋 Завантажено {len(self._existing_checklists)} існуючих чеклістів для пропуску")
            session.close()
        except Exception as e:
            click.echo(f"⚠️ Не вдалося завантажити існуючі чекліст: {e}")
    
    async def load_data(
        self,
        page_ids: Optional[List[str]] = None,
        space_keys: Optional[List[str]] = None,
        labels: Optional[List[str]] = None,
        updated_since: Optional[str] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Об'єднане завантаження даних в MySQL та векторну базу."""
        
        click.echo(f"🚀 Об'єднане завантаження Confluence даних...")
        click.echo(f"📊 MySQL завантаження: {'✅' if self.load_mysql else '❌'}")
        click.echo(f"🔍 Векторна база: {'✅' if self.load_vector else '❌'}")
        click.echo(f"🌐 Confluence API: {'Mock' if self.use_mock else 'Real'}")
        
        if page_ids:
            click.echo(f"📄 Page IDs: {', '.join(page_ids)}")
        if space_keys:
            click.echo(f"🏢 Spaces: {', '.join(space_keys)}")
        if labels:
            click.echo(f"🏷️ Labels: {', '.join(labels)}")
        if limit:
            click.echo(f"📋 Ліміт: {limit} чеклістів")
        
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
        
        click.echo(f"📄 Знайдено {len(pages)} сторінок для обробки")
        self.progress.total_pages = len(pages)
        self.progress.total_checklists = len(pages)
        
        # Create ingestion job
        job_desc = f"Unified loading: {len(pages)} pages, MySQL: {self.load_mysql}, Vector: {self.load_vector}"
        if limit:
            job_desc += f", max {limit} checklists"
        job = self._create_ingestion_job(job_desc) if self.load_mysql else None
        
        try:
            documents_processed = 0
            chunks_created = 0
            
            for i, page in enumerate(pages):
                if limit and self.progress.created_checklists >= limit:
                    click.echo(f"🛑 Досягнуто ліміт {limit} чекліст, зупиняємо")
                    break
                
                try:
                    click.echo(f"\n🔄 Обробка сторінки {i+1}/{len(pages)}: {page['title']}")
                    
                    # Process page for both MySQL and Vector DB
                    result = await self._process_page_unified(page)
                    
                    documents_processed += 1
                    chunks_created += result.get('chunks_created', 0)
                    
                    if result.get('mysql_success'):
                        self.progress.created_checklists += 1
                        self.progress.created_testcases += result.get('testcases_created', 0)
                        self.progress.created_configs += result.get('configs_created', 0)
                        click.echo(f"  ✅ MySQL: Створено {result.get('testcases_created', 0)} тесткейсів")
                    else:
                        self.progress.skipped_checklists += 1
                        click.echo(f"  ⏭️ MySQL: Пропущено ({result.get('mysql_reason', 'Unknown')})")
                    
                    if result.get('vector_success'):
                        click.echo(f"  ✅ Vector: Створено {result.get('chunks_created', 0)} чанків")
                    else:
                        click.echo(f"  ⏭️ Vector: Пропущено ({result.get('vector_reason', 'Unknown')})")
                    
                    self.progress.processed_pages += 1
                    
                except Exception as e:
                    click.echo(f"  ❌ Помилка обробки сторінки: {e}", err=True)
                    continue
            
            # Update job
            if job:
                self._update_ingestion_job(job, "success", {
                    'checklists': self.progress.created_checklists,
                    'testcases': self.progress.created_testcases,
                    'configs': self.progress.created_configs,
                    'chunks': chunks_created,
                    'skipped': self.progress.skipped_checklists
                })
            
            self._print_final_summary()
            
            return {
                "success": True,
                "documents_processed": documents_processed,
                "checklists_created": self.progress.created_checklists,
                "testcases_created": self.progress.created_testcases,
                "configs_created": self.progress.created_configs,
                "chunks_created": chunks_created,
                "skipped_checklists": self.progress.skipped_checklists
            }
            
        except Exception as e:
            if job:
                self._update_ingestion_job(job, "failed", {'error': str(e)})
            click.echo(f"❌ Помилка завантаження: {e}")
            raise
    
    async def _process_page_unified(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """Обробляє одну сторінку для MySQL та векторної бази."""
        result = {
            'mysql_success': False,
            'vector_success': False,
            'testcases_created': 0,
            'configs_created': 0,
            'chunks_created': 0,
            'mysql_reason': '',
            'vector_reason': ''
        }
        
        page_id = page['id']
        title = page['title']
        
        # Check if already exists in MySQL
        if self.load_mysql and page_id in self._existing_checklists:
            result['mysql_reason'] = 'Вже існує в БД'
        elif self.load_mysql:
            # Process for MySQL
            try:
                mysql_result = await self._process_page_mysql(page)
                if mysql_result['success']:
                    result['mysql_success'] = True
                    result['testcases_created'] = mysql_result['testcases_created']
                    result['configs_created'] = mysql_result['configs_created']
                    self._existing_checklists.add(page_id)
                else:
                    result['mysql_reason'] = mysql_result['reason']
            except Exception as e:
                result['mysql_reason'] = f'Помилка: {str(e)}'
        
        # Process for Vector DB
        if self.load_vector:
            try:
                vector_result = await self._process_page_vector(page)
                if vector_result['success']:
                    result['vector_success'] = True
                    result['chunks_created'] = vector_result['chunks_created']
                else:
                    result['vector_reason'] = vector_result['reason']
            except Exception as e:
                result['vector_reason'] = f'Помилка: {str(e)}'
        
        return result
    
    async def _process_page_mysql(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """Обробляє сторінку для MySQL (структуровані QA дані) тільки з HTML парсером."""
        try:
            page_id = page['id']
            title = page['title']
            
            # Get page content
            page_content = self.confluence_api.get_page_content(page_id)
            if not page_content:
                return {'success': False, 'reason': 'Не вдалося отримати контент'}
            
            content = page_content.get('content', '')
            
            # Використовуємо тільки HTML парсер
            html_start_time = datetime.now()
            try:
                html_testcases = self.html_parser.parse_testcases_from_html(content, title)
                html_duration = (datetime.now() - html_start_time).total_seconds()
                click.echo(f"  🔍 HTML парсер знайшов {len(html_testcases)} тесткейсів за {html_duration:.2f}с")
                
                # Логуємо статистику HTML парсера
                self._log_parser_stats("HTML", len(html_testcases), html_duration, True)
            except Exception as e:
                html_duration = (datetime.now() - html_start_time).total_seconds()
                click.echo(f"  ⚠️ HTML парсер не спрацював: {e}")
                self._log_parser_stats("HTML", 0, html_duration, False, str(e))
                return {'success': False, 'reason': f'HTML парсер не спрацював: {e}'}
            
            # Check if result is valid
            if not html_testcases:
                return {'success': False, 'reason': 'Немає тесткейсів'}
            
            # Create checklist in DB
            session = self.qa_repo.get_session()
            try:
                # Find or create section (simplified - use first available section)
                section = session.query(QASection).first()
                if not section:
                    # Create default section
                    section = QASection(
                        confluence_page_id="default",
                        title="Default Section",
                        description="Default section for imported checklists",
                        url="https://confluence.togethernetworks.com/pages/default",
                        space_key=page_content.get('space', 'QMT')
                    )
                    session.add(section)
                    session.flush()
                
                # Create checklist
                content_hash = hashlib.md5(content.encode()).hexdigest()
                
                # Determine subcategory from page hierarchy
                subcategory = self._determine_subcategory(page_content, title)
                
                checklist = Checklist(
                    confluence_page_id=page_id,
                    title=title,
                    description=title,  # Використовуємо title як description
                    additional_content=None,
                    url=f"https://confluence.togethernetworks.com/pages/{page_id}",
                    space_key=page_content.get('space', 'QMT'),
                    section_id=section.id,
                    subcategory=subcategory,
                    content_hash=content_hash,
                    version=page_content.get('version', 1)
                )
                
                session.add(checklist)
                session.flush()
                
                # Create testcases and configs
                configs_created = 0
                testcases_created = 0
                
                for testcase_data in html_testcases:
                    # Create config if needed
                    config_id = None
                    if testcase_data.get('config'):
                        config = self._get_or_create_config(
                            session, testcase_data['config'], None
                        )
                        if config:
                            config_id = config.id
                            configs_created += 1
                    
                    # Create testcase
                    if testcase_data.get('expected_result') and testcase_data.get('step'):
                        priority = testcase_data.get('priority')
                        if priority and priority not in ['LOWEST', 'LOW', 'MEDIUM', 'HIGH', 'HIGHEST', 'CRITICAL']:
                            priority = 'MEDIUM'
                        
                        # Handle screenshot
                        screenshot = testcase_data.get('screenshot')
                        if isinstance(screenshot, list) and screenshot:
                            screenshot = screenshot[0]
                        elif isinstance(screenshot, list):
                            screenshot = None
                        
                        # Обмежуємо довжину qa_auto_coverage
                        qa_auto_coverage = testcase_data.get('qa_auto_coverage')
                        if qa_auto_coverage and len(qa_auto_coverage) > 255:
                            qa_auto_coverage = qa_auto_coverage[:252] + "..."
                        
                        testcase = TestCase(
                            checklist_id=checklist.id,
                            step=testcase_data.get('step', 'No step defined'),
                            expected_result=testcase_data.get('expected_result', 'No result defined'),
                            screenshot=screenshot,
                            priority=priority,
                            test_group=testcase_data.get('test_group'),
                            functionality=testcase_data.get('functionality'),
                            order_index=testcase_data.get('order_index', 0),
                            config_id=config_id,
                            qa_auto_coverage=qa_auto_coverage
                        )
                        session.add(testcase)
                        testcases_created += 1
                
                session.commit()
                
                return {
                    'success': True,
                    'testcases_created': testcases_created,
                    'configs_created': configs_created
                }
                
            finally:
                session.close()
                
        except Exception as e:
            return {'success': False, 'reason': f'Помилка: {str(e)}'}
    
    async def _process_page_vector(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """Обробляє сторінку для векторної бази."""
        try:
            # Normalize content
            normalized_content = self.confluence_api.normalize_content(page["content"])
            
            # Chunk the content
            chunks = self.chunker.chunk_text(normalized_content)
            
            if not chunks:
                return {'success': False, 'reason': 'Немає контенту для чанків'}
            
            # Generate embeddings for chunks
            chunk_embeddings = self.embedder.embed_batch([f"{page['title']}\n\n{chunk}" for chunk in chunks])
            
            # Upsert chunks to vector database
            chunks_data = []
            for i, (chunk_text, embedding) in enumerate(zip(chunks, chunk_embeddings)):
                if embedding is None:
                    continue
                
                chunk_id = f"{page['id']}_{i}"
                chunk_data = {
                    "chunk_id": chunk_id,
                    "embedding": embedding,
                    "document_id": page['id'],
                    "confluence_page_id": page["id"],
                    "title": page["title"],
                    "url": page["url"],
                    "space": page["space"],
                    "labels": page["labels"],
                    "feature_id": None,
                    "feature_name": None,
                    "chunk_ordinal": i,
                    "text": chunk_text
                }
                chunks_data.append(chunk_data)
            
            # Batch upsert to vector database
            successful_chunks, failed_chunks = self.vector_repo.upsert_chunks_batch(chunks_data)
            
            return {
                'success': True,
                'chunks_created': successful_chunks
            }
            
        except Exception as e:
            return {'success': False, 'reason': f'Помилка: {str(e)}'}
    
    
    def _log_parser_stats(self, parser_type: str, testcases_count: int, duration: float, success: bool, error: str = None, confidence: float = None):
        """Логує статистику парсера"""
        import logging
        
        logger = logging.getLogger(__name__)
        
        log_data = {
            'parser_type': parser_type,
            'testcases_count': testcases_count,
            'duration_seconds': duration,
            'success': success,
            'timestamp': datetime.now().isoformat()
        }
        
        if error:
            log_data['error'] = error
        
        if confidence is not None:
            log_data['confidence'] = confidence
        
        if success:
            logger.info(f"Parser {parser_type}: {testcases_count} testcases in {duration:.2f}s", extra=log_data)
        else:
            logger.warning(f"Parser {parser_type} failed: {error}", extra=log_data)
    
    
    def _get_or_create_config(self, session, config_name: str, config_url: str = None) -> Optional[Config]:
        """Отримує або створює конфігурацію."""
        if not config_name:
            return None
        
        # Look for existing config
        config = session.query(Config).filter(Config.name == config_name).first()
        if config:
            return config
        
        # Create new
        config = Config(
            name=config_name,
            description=config_name,
            url=config_url
        )
        session.add(config)
        session.flush()
        return config
    
    def _create_ingestion_job(self, description: str) -> IngestionJob:
        """Створює job для відстеження."""
        session = self.qa_repo.get_session()
        try:
            job = IngestionJob(details=description)
            session.add(job)
            session.commit()
            return job
        finally:
            session.close()
    
    def _update_ingestion_job(self, job: IngestionJob, status: str, details: Dict[str, Any]):
        """Оновлює job."""
        session = self.qa_repo.get_session()
        try:
            job.status = status
            job.details = f"Completed: {details}"
            job.documents_processed = details.get('checklists', 0)
            job.chunks_created = details.get('chunks', 0)
            job.features_created = details.get('configs', 0)
            session.merge(job)
            session.commit()
        finally:
            session.close()
    
    def _print_final_summary(self):
        """Виводить фінальну статистику."""
        click.echo(f"\n🎉 ОБ'ЄДНАНЕ ЗАВАНТАЖЕННЯ ЗАВЕРШЕНО!")
        click.echo("=" * 60)
        click.echo(f"📊 Оброблено сторінок: {self.progress.processed_pages}/{self.progress.total_pages}")
        if self.load_mysql:
            click.echo(f"📋 Створено чеклістів: {self.progress.created_checklists}")
            click.echo(f"🧪 Створено тесткейсів: {self.progress.created_testcases}")
            click.echo(f"⚙️ Створено конфігів: {self.progress.created_configs}")
            click.echo(f"⏭️ Пропущено чеклістів: {self.progress.skipped_checklists}")
        if self.load_vector:
            click.echo(f"🔍 Створено чанків: {self.progress.chunks_created}")
    
    def _determine_subcategory(self, page_content: Dict[str, Any], title: str) -> Optional[str]:
        """
        Визначає subcategory на основі ієрархії сторінок Confluence.
        Subcategory - це тайтл батьківського документа, який не містить таблицю тесткейсів,
        але є батьківським для документів з тесткейсами.
        """
        try:
            # Отримуємо інформацію про батьківську сторінку
            parent_info = page_content.get('parent', {})
            if not parent_info:
                return None
            
            parent_title = parent_info.get('title', '')
            if not parent_title:
                return None
            
            # Перевіряємо, чи батьківська сторінка не є секцією (Checklist WEB, Checklist MOB)
            if parent_title.startswith('Checklist '):
                return None
            
            # Перевіряємо, чи батьківська сторінка не є кореневою секцією
            if parent_title in ['QA', 'Quality Assurance', 'Testing']:
                return None
            
            # Якщо батьківська сторінка має осмислену назву, використовуємо її як subcategory
            # Обмежуємо довжину до 255 символів
            if len(parent_title) > 255:
                parent_title = parent_title[:252] + "..."
            
            return parent_title
            
        except Exception as e:
            # Якщо виникла помилка, повертаємо None
            return None
    
    def close(self):
        """Clean up resources."""
        if self.load_mysql:
            self.qa_repo.close()
        if self.load_vector:
            self.vector_repo.close()


@click.command()
@click.option('--page-ids', help='Comma-separated list of root page IDs')
@click.option('--spaces', help='Comma-separated list of space keys (e.g., QA,ENG)')
@click.option('--labels', help='Comma-separated list of labels to filter by')
@click.option('--since', help='Load documents updated since this date (ISO format)')
@click.option('--limit', type=int, help='Maximum number of checklists to process')
@click.option('--use-config', is_flag=True, help='Use page IDs from config')
@click.option('--use-real-api', is_flag=True, help='Use real Confluence API instead of mock')
@click.option('--test-connection', is_flag=True, help='Test Confluence connection and exit')
@click.option('--mysql-only', is_flag=True, help='Load only to MySQL (skip vector DB)')
@click.option('--vector-only', is_flag=True, help='Load only to vector DB (skip MySQL)')
def main(page_ids, spaces, labels, since, limit, use_config, use_real_api, test_connection, mysql_only, vector_only):
    """Unified Confluence loader - завантажує дані в MySQL та векторну базу."""
    
    # Validate environment
    if not settings.openai_api_key:
        click.echo("Error: OPENAI_API_KEY not set", err=True)
        sys.exit(1)
    
    # Determine what to load
    load_mysql = not vector_only
    load_vector = not mysql_only
    
    if not load_mysql and not load_vector:
        click.echo("Error: Must load to at least one destination (MySQL or Vector DB)", err=True)
        sys.exit(1)
    
    # Parse arguments
    space_keys = spaces.split(',') if spaces else None
    label_list = labels.split(',') if labels else None
    
    # Determine page IDs to load
    pages_to_load = None
    if use_config:
        if not settings.confluence_root_pages:
            click.echo("❌ CONFLUENCE_ROOT_PAGES не налаштовано в .env")
            sys.exit(1)
        pages_to_load = settings.confluence_root_pages.split(',')
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
    loader = UnifiedConfluenceLoader(
        use_mock=not use_real_api,
        load_mysql=load_mysql,
        load_vector=load_vector
    )
    
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
        result = asyncio.run(loader.load_data(
            page_ids=pages_to_load,
            space_keys=space_keys,
            labels=label_list,
            updated_since=since,
            limit=limit
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
