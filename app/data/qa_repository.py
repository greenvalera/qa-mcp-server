"""Repository для роботи з QA структурою."""

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import sessionmaker, Session, joinedload
from sqlalchemy import create_engine, func, and_, or_, text
from sqlalchemy.exc import SQLAlchemyError
import json
import math

from ..config import settings
from ..models.qa_models import Base, QASection, Checklist, TestCase, Config, IngestionJob
from ..ai.embedder import OpenAIEmbedder


class QARepository:
    """Repository для роботи з QA чекліст і тесткейсами."""
    
    def __init__(self):
        """Ініціалізація repository."""
        self.engine = create_engine(settings.mysql_dsn, pool_pre_ping=True)
        self.Session = sessionmaker(bind=self.engine)
        self.embedder = OpenAIEmbedder()
    
    def create_tables(self):
        """Створює таблиці якщо їх немає."""
        Base.metadata.create_all(self.engine)
        # Ініціалізуємо секції після створення таблиць
        self.initialize_default_sections()
    
    def initialize_default_sections(self):
        """Ініціалізує базові секції якщо їх немає."""
        import logging
        import json
        import os
        logger = logging.getLogger(__name__)
        
        session = self.get_session()
        try:
            # Перевіряємо, чи є вже секції
            existing_sections = session.query(QASection).count()
            logger.info(f"🔍 Перевірка секцій: знайдено {existing_sections} секцій")
            
            if existing_sections > 0:
                logger.info("✅ Секції вже існують, пропускаємо ініціалізацію")
                return  # Секції вже існують
            
            logger.info("🔧 Створюємо базові секції...")
            
            # Читаємо дані секцій з JSON файлу
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'sections.json')
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    sections_data = config_data['default_sections']
                logger.info(f"📄 Завантажено конфігурацію секцій з {config_path}")
            except FileNotFoundError:
                logger.error(f"❌ Файл конфігурації не знайдено: {config_path}")
                raise
            except json.JSONDecodeError as e:
                logger.error(f"❌ Помилка парсингу JSON: {str(e)}")
                raise
            
            for section_data in sections_data:
                logger.info(f"➕ Створюємо секцію: {section_data['title']}")
                section = QASection(
                    confluence_page_id=section_data["confluence_page_id"],
                    title=section_data["title"],
                    description=section_data["description"],
                    url=section_data["url"],
                    space_key=section_data["space_key"]
                )
                session.add(section)
            
            session.commit()
            logger.info("✅ Базові секції успішно створені")
            
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Помилка при створенні секцій: {str(e)}")
            raise
        finally:
            session.close()
    
    def get_session(self) -> Session:
        """Повертає сесію БД."""
        return self.Session()
    
    def close(self):
        """Закриває з'єднання."""
        if hasattr(self, 'engine'):
            self.engine.dispose()
    
    # QA Sections methods
    
    def get_qa_sections(self, limit: int = 100, offset: int = 0) -> Tuple[List[QASection], int]:
        """Отримує список QA секцій."""
        session = self.get_session()
        try:
            query = session.query(QASection).options(joinedload(QASection.checklists)).filter(QASection.parent_section_id.is_(None))
            total = query.count()
            sections = query.offset(offset).limit(limit).all()
            return sections, total
        finally:
            session.close()
    
    def get_qa_section_by_id(self, section_id: int) -> Optional[QASection]:
        """Отримує QA секцію за ID."""
        session = self.get_session()
        try:
            return session.query(QASection).options(
                joinedload(QASection.checklists),
                joinedload(QASection.child_sections)
            ).filter_by(id=section_id).first()
        finally:
            session.close()
    
    def search_qa_sections(self, query: str, limit: int = 50) -> List[QASection]:
        """Пошук QA секцій за назвою або описом."""
        session = self.get_session()
        try:
            return session.query(QASection).filter(
                or_(
                    QASection.title.contains(query),
                    QASection.description.contains(query)
                )
            ).limit(limit).all()
        finally:
            session.close()
    
    # Checklists methods
    
    def get_checklists(self, 
                      section_id: Optional[int] = None,
                      limit: int = 100, 
                      offset: int = 0) -> Tuple[List[Checklist], int]:
        """Отримує список чекліст."""
        session = self.get_session()
        try:
            query = session.query(Checklist).options(
                joinedload(Checklist.section),
                joinedload(Checklist.testcases),
                joinedload(Checklist.configs)
            )
            if section_id:
                query = query.filter_by(section_id=section_id)
            
            total = query.count()
            checklists = query.offset(offset).limit(limit).all()
            return checklists, total
        finally:
            session.close()
    
    def get_checklist_by_id(self, checklist_id: int) -> Optional[Checklist]:
        """Отримує чекліст за ID."""
        session = self.get_session()
        try:
            return session.query(Checklist).options(
                joinedload(Checklist.section),
                joinedload(Checklist.testcases),
                joinedload(Checklist.configs)
            ).filter_by(id=checklist_id).first()
        finally:
            session.close()
    
    def search_checklists(self, query: str, limit: int = 50) -> List[Checklist]:
        """Пошук чекліст за назвою або описом."""
        session = self.get_session()
        try:
            return session.query(Checklist).filter(
                or_(
                    Checklist.title.contains(query),
                    Checklist.description.contains(query)
                )
            ).limit(limit).all()
        finally:
            session.close()
    
    # TestCases methods
    
    def get_testcases(self,
                     checklist_id: Optional[int] = None,
                     test_group: Optional[str] = None,
                     functionality: Optional[str] = None,
                     priority: Optional[str] = None,
                     limit: int = 100,
                     offset: int = 0) -> Tuple[List[TestCase], int]:
        """Отримує список тесткейсів з фільтрами."""
        session = self.get_session()
        try:
            query = session.query(TestCase).options(
                joinedload(TestCase.checklist).joinedload(Checklist.section)
            )
            
            if checklist_id:
                query = query.filter_by(checklist_id=checklist_id)
            if test_group:
                query = query.filter_by(test_group=test_group)
            if functionality:
                query = query.filter_by(functionality=functionality)
            if priority:
                query = query.filter_by(priority=priority)
            
            query = query.order_by(TestCase.checklist_id, TestCase.order_index)
            
            total = query.count()
            testcases = query.offset(offset).limit(limit).all()
            return testcases, total
        finally:
            session.close()
    
    def get_testcase_by_id(self, testcase_id: int) -> Optional[TestCase]:
        """Отримує тесткейс за ID."""
        session = self.get_session()
        try:
            return session.query(TestCase).options(
                joinedload(TestCase.checklist).joinedload(Checklist.section),
                joinedload(TestCase.config)
            ).filter_by(id=testcase_id).first()
        finally:
            session.close()
    
    def search_testcases(self, 
                        query: str,
                        section_id: Optional[int] = None,
                        checklist_id: Optional[int] = None,
                        test_group: Optional[str] = None,
                        functionality: Optional[str] = None,
                        priority: Optional[str] = None,
                        limit: int = 100) -> List[TestCase]:
        """Пошук тесткейсів за текстом в step або expected_result."""
        session = self.get_session()
        try:
            q = session.query(TestCase).join(Checklist).options(
                joinedload(TestCase.checklist).joinedload(Checklist.section)
            )
            
            # Текстовий пошук
            q = q.filter(
                or_(
                    TestCase.step.contains(query),
                    TestCase.expected_result.contains(query),
                    TestCase.functionality.contains(query),
                )
            )
            
            # Фільтри
            if section_id:
                q = q.filter(Checklist.section_id == section_id)
            if checklist_id:
                q = q.filter(TestCase.checklist_id == checklist_id)
            if test_group:
                q = q.filter(TestCase.test_group == test_group)
            if functionality:
                q = q.filter(TestCase.functionality == functionality)
            if priority:
                q = q.filter(TestCase.priority == priority)
            
            q = q.order_by(TestCase.checklist_id, TestCase.order_index)
            
            return q.limit(limit).all()
        finally:
            session.close()
    
    def get_testcases_by_config(self, config_id: int, limit: int = 100) -> List[TestCase]:
        """Отримує тесткейси які використовують конкретний конфіг."""
        session = self.get_session()
        try:
            return session.query(TestCase).filter_by(config_id=config_id).limit(limit).all()
        finally:
            session.close()
    
    # Configs methods
    
    def get_configs(self, limit: int = 100, offset: int = 0) -> Tuple[List[Config], int]:
        """Отримує список конфігів."""
        session = self.get_session()
        try:
            query = session.query(Config)
            total = query.count()
            configs = query.offset(offset).limit(limit).all()
            return configs, total
        finally:
            session.close()
    
    def get_config_by_id(self, config_id: int) -> Optional[Config]:
        """Отримує конфіг за ID."""
        session = self.get_session()
        try:
            return session.query(Config).options(
                joinedload(Config.testcases)
            ).filter_by(id=config_id).first()
        finally:
            session.close()
    
    def search_configs(self, query: str, limit: int = 50) -> List[Config]:
        """Пошук конфігів за назвою або описом."""
        session = self.get_session()
        try:
            return session.query(Config).filter(
                or_(
                    Config.name.contains(query),
                    Config.description.contains(query),
                    Config.url.contains(query)
                )
            ).limit(limit).all()
        finally:
            session.close()
    
    # Statistics methods
    
    def get_qa_statistics(self) -> Dict[str, Any]:
        """Отримує статистику по QA структурі."""
        session = self.get_session()
        try:
            stats = {}
            
            # Загальна кількість
            stats['sections_count'] = session.query(QASection).count()
            stats['checklists_count'] = session.query(Checklist).count()
            stats['testcases_count'] = session.query(TestCase).count()
            stats['configs_count'] = session.query(Config).count()
            
            # Статистика по test_group
            test_group_stats = session.query(
                TestCase.test_group,
                func.count(TestCase.id).label('count')
            ).group_by(TestCase.test_group).all()
            
            stats['test_groups'] = {group.value if group else None: count for group, count in test_group_stats if group}
            
            # Статистика по functionality
            functionality_stats = session.query(
                TestCase.functionality,
                func.count(TestCase.id).label('count')
            ).filter(TestCase.functionality.isnot(None)).group_by(
                TestCase.functionality
            ).order_by(func.count(TestCase.id).desc()).limit(20).all()
            
            stats['top_functionalities'] = {func: count for func, count in functionality_stats}
            
            # Статистика по пріоритетах
            priority_stats = session.query(
                TestCase.priority,
                func.count(TestCase.id).label('count')
            ).group_by(TestCase.priority).all()
            
            stats['priorities'] = {pri.value if pri else None: count for pri, count in priority_stats if pri}
            
            
            # Топ чекліст по кількості тесткейсів
            checklist_stats = session.query(
                Checklist.title,
                func.count(TestCase.id).label('testcases_count')
            ).join(TestCase).group_by(
                Checklist.id, Checklist.title
            ).order_by(func.count(TestCase.id).desc()).limit(10).all()
            
            stats['top_checklists'] = {title: count for title, count in checklist_stats}
            
            return stats
        finally:
            session.close()
    
    # Complex queries
    
    def get_full_qa_structure(self) -> List[Dict[str, Any]]:
        """Отримує повну QA структуру з вкладеністю."""
        session = self.get_session()
        try:
            # Отримуємо кореневі секції
            root_sections = session.query(QASection).filter(
                QASection.parent_section_id.is_(None)
            ).all()
            
            result = []
            for section in root_sections:
                section_data = self._build_section_tree(session, section)
                result.append(section_data)
            
            return result
        finally:
            session.close()
    
    def _build_section_tree(self, session: Session, section: QASection) -> Dict[str, Any]:
        """Рекурсивно будує дерево секцій."""
        section_data = {
            'id': section.id,
            'title': section.title,
            'description': section.description,
            'url': section.url,
            'checklists': [],
            'subsections': []
        }
        
        # Додаємо чекліст
        for checklist in section.checklists:
            checklist_data = {
                'id': checklist.id,
                'title': checklist.title,
                'description': checklist.description,
                'url': checklist.url,
                'testcases_count': len(checklist.testcases),
                'configs_count': len(checklist.configs)
            }
            section_data['checklists'].append(checklist_data)
        
        # Додаємо субсекції рекурсивно
        child_sections = session.query(QASection).filter_by(
            parent_section_id=section.id
        ).all()
        
        for child in child_sections:
            child_data = self._build_section_tree(session, child)
            section_data['subsections'].append(child_data)
        
        return section_data
    
    # Semantic search methods
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Обчислює косинусну подібність між двома векторами."""
        if not vec1 or not vec2:
            return 0.0
        
        # Скалярний добуток
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        
        # Норми векторів
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def update_testcase_embedding(self, testcase_id: int) -> bool:
        """Оновлює embedding для конкретного тесткейса."""
        session = self.get_session()
        try:
            testcase = session.query(TestCase).filter(TestCase.id == testcase_id).first()
            if not testcase:
                return False
            
            # Створюємо текст для embedding (step + expected_result)
            text_for_embedding = f"{testcase.step} {testcase.expected_result}"
            
            # Отримуємо embedding
            embedding = self.embedder.embed_text(text_for_embedding)
            if embedding is None:
                return False
            
            # Оновлюємо в БД
            testcase.embedding = embedding
            session.commit()
            return True
            
        except Exception as e:
            session.rollback()
            print(f"Error updating embedding for testcase {testcase_id}: {e}")
            return False
        finally:
            session.close()
    
    def update_all_embeddings(self, batch_size: int = 50) -> Dict[str, Any]:
        """Оновлює embeddings для всіх тесткейсів які їх не мають."""
        session = self.get_session()
        try:
            # Знаходимо тесткейси без embeddings
            testcases_without_embeddings = session.query(TestCase).filter(
                TestCase.embedding.is_(None)
            ).all()
            
            total_count = len(testcases_without_embeddings)
            if total_count == 0:
                return {
                    'success': True,
                    'message': 'All testcases already have embeddings',
                    'total': 0,
                    'updated': 0
                }
            
            updated_count = 0
            failed_count = 0
            
            # Обробляємо батчами
            for i in range(0, total_count, batch_size):
                batch = testcases_without_embeddings[i:i + batch_size]
                
                # Підготовляємо тексти для embedding
                texts = []
                for testcase in batch:
                    text = f"{testcase.step} {testcase.expected_result}"
                    texts.append(text)
                
                # Отримуємо embeddings для батчу
                embeddings = self.embedder.embed_batch(texts)
                
                # Оновлюємо в БД
                for testcase, embedding in zip(batch, embeddings):
                    if embedding is not None:
                        testcase.embedding = embedding
                        updated_count += 1
                    else:
                        failed_count += 1
                
                # Комітимо батч
                session.commit()
                print(f"Updated embeddings for batch {i//batch_size + 1}: {len([e for e in embeddings if e is not None])}/{len(embeddings)}")
            
            return {
                'success': True,
                'message': f'Updated embeddings for {updated_count} testcases',
                'total': total_count,
                'updated': updated_count,
                'failed': failed_count
            }
            
        except Exception as e:
            session.rollback()
            return {
                'success': False,
                'error': f'Error updating embeddings: {str(e)}',
                'total': 0,
                'updated': 0
            }
        finally:
            session.close()
    
    def semantic_search_testcases(
        self,
        query: str,
        limit: int = 20,
        min_similarity: float = 0.5,
        section_id: Optional[int] = None,
        checklist_id: Optional[int] = None,
        test_group: Optional[str] = None,
        functionality: Optional[str] = None,
        priority: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Семантичний пошук тесткейсів за запитом."""
        session = self.get_session()
        try:
            # Отримуємо embedding для запиту
            query_embedding = self.embedder.embed_text(query)
            if query_embedding is None:
                return []
            
            # Базовий запит для тесткейсів з embeddings
            query_builder = session.query(TestCase).options(
                joinedload(TestCase.checklist).joinedload(Checklist.section),
                joinedload(TestCase.config)
            ).filter(TestCase.embedding.isnot(None))
            
            # Додаємо фільтри
            if section_id:
                query_builder = query_builder.join(Checklist).filter(
                    Checklist.section_id == section_id
                )
            
            if checklist_id:
                query_builder = query_builder.filter(TestCase.checklist_id == checklist_id)
            
            if test_group:
                query_builder = query_builder.filter(TestCase.test_group == test_group)
            
            if functionality:
                query_builder = query_builder.filter(TestCase.functionality == functionality)
            
            if priority:
                query_builder = query_builder.filter(TestCase.priority == priority)
            
            # Отримуємо всі тесткейси з embeddings
            testcases = query_builder.all()
            
            # Обчислюємо подібність
            results = []
            for testcase in testcases:
                if testcase.embedding:
                    similarity = self.cosine_similarity(query_embedding, testcase.embedding)
                    
                    if similarity >= min_similarity:
                        results.append({
                            'testcase': testcase,
                            'similarity': similarity,
                            'checklist_title': testcase.checklist.title if testcase.checklist else None,
                            'config_name': testcase.config.name if testcase.config else None
                        })
            
            # Сортуємо за подібністю (найбільша спочатку)
            results.sort(key=lambda x: x['similarity'], reverse=True)
            
            # Обмежуємо результати
            return results[:limit]
            
        except Exception as e:
            print(f"Error in semantic search: {e}")
            return []
        finally:
            session.close()

    # Feature/document helpers

    def list_functionalities(self, limit: int = 100, offset: int = 0) -> Tuple[List[str], int]:
        """Повертає унікальні значення functionality з тесткейсів."""
        session = self.get_session()
        try:
            query = session.query(TestCase.functionality).filter(
                TestCase.functionality.isnot(None),
                TestCase.functionality != ''
            ).distinct()
            total = query.count()
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            functionalities = [row[0] for row in query.all()]
            return functionalities, total
        finally:
            session.close()

    def resolve_functionality_by_id(self, feature_id: Optional[int]) -> str:
        """Повертає назву functionality за порядковим індексом."""
        if feature_id is None:
            raise ValueError("feature_id is required when feature_name is not provided")

        session = self.get_session()
        try:
            query = session.query(TestCase.functionality).filter(
                TestCase.functionality.isnot(None),
                TestCase.functionality != ''
            ).distinct().order_by(TestCase.functionality)
            functionalities = [row[0] for row in query.all()]
            if feature_id <= 0 or feature_id > len(functionalities):
                raise ValueError(f"Invalid feature_id: {feature_id}")
            return functionalities[feature_id - 1]
        finally:
            session.close()

    def list_checklists_for_functionality(
        self,
        functionality: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> Tuple[List[Checklist], int]:
        """Повертає чеклісти, що містять задану functionality."""
        session = self.get_session()
        try:
            query = session.query(Checklist).join(TestCase).filter(
                TestCase.functionality == functionality
            ).distinct()
            total = query.count()
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            return query.all(), total
        finally:
            session.close()

    def list_documents_for_functionality(self, functionality: str) -> List[Checklist]:
        """Повертає всі чеклісти для заданої functionality без пагінації."""
        checklists, _ = self.list_checklists_for_functionality(functionality, limit=None, offset=0)
        return checklists
