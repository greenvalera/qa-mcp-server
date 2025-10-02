#!/usr/bin/env python3
"""
Скрипт для повної переініціалізації бази даних з новою структурою.
Видаляє всі дані та створює нові таблиці з оновленою структурою.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.data.qa_repository import QARepository
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reinit_database():
    """Повністю переініціалізує базу даних з новою структурою."""
    
    qa_repo = QARepository()
    session = qa_repo.get_session()
    
    try:
        logger.info("🚀 Починаємо повну переініціалізацію бази даних...")
        
        # 1. Видаляємо всі таблиці
        logger.info("🗑️ Видаляємо всі таблиці...")
        
        tables_to_drop = [
            'checklist_configs',
            'testcases', 
            'checklists',
            'configs',
            'qa_sections',
            'ingestion_jobs'
        ]
        
        for table in tables_to_drop:
            try:
                session.execute(text(f"DROP TABLE IF EXISTS {table}"))
                logger.info(f"✅ Видалено таблицю {table}")
            except Exception as e:
                logger.warning(f"⚠️ Не вдалося видалити таблицю {table}: {e}")
        
        # 2. Створюємо нові таблиці з оновленою структурою
        logger.info("🔧 Створюємо нові таблиці з оновленою структурою...")
        
        # Створюємо qa_sections
        session.execute(text("""
            CREATE TABLE qa_sections (
                id INT AUTO_INCREMENT PRIMARY KEY,
                confluence_page_id VARCHAR(64) NOT NULL UNIQUE,
                title VARCHAR(512) NOT NULL,
                description TEXT NULL,
                url VARCHAR(1024) NOT NULL,
                space_key VARCHAR(64) NOT NULL,
                parent_section_id INT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                
                INDEX idx_qa_sections_confluence_id (confluence_page_id),
                INDEX idx_qa_sections_space (space_key),
                INDEX idx_qa_sections_parent (parent_section_id),
                FOREIGN KEY (parent_section_id) REFERENCES qa_sections(id) ON DELETE CASCADE
            )
        """))
        logger.info("✅ Створено таблицю qa_sections")
        
        # Створюємо checklists з subcategory
        session.execute(text("""
            CREATE TABLE checklists (
                id INT AUTO_INCREMENT PRIMARY KEY,
                confluence_page_id VARCHAR(64) NOT NULL UNIQUE,
                title VARCHAR(512) NOT NULL,
                description TEXT NULL,
                additional_content TEXT NULL,
                url VARCHAR(1024) NOT NULL,
                space_key VARCHAR(64) NOT NULL,
                section_id INT NOT NULL,
                subcategory VARCHAR(255) NULL,
                content_hash CHAR(64) NOT NULL,
                version INT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                
                INDEX idx_checklists_confluence_id (confluence_page_id),
                INDEX idx_checklists_section (section_id),
                INDEX idx_checklists_space (space_key),
                INDEX idx_checklists_subcategory (subcategory),
                INDEX idx_checklists_hash (content_hash),
                FOREIGN KEY (section_id) REFERENCES qa_sections(id) ON DELETE CASCADE
            )
        """))
        logger.info("✅ Створено таблицю checklists")
        
        # Створюємо configs
        session.execute(text("""
            CREATE TABLE configs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                url VARCHAR(1024) NULL,
                description TEXT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                
                INDEX idx_configs_name (name)
            )
        """))
        logger.info("✅ Створено таблицю configs")
        
        # Створюємо testcases БЕЗ subcategory
        session.execute(text("""
            CREATE TABLE testcases (
                id INT AUTO_INCREMENT PRIMARY KEY,
                checklist_id INT NOT NULL,
                step TEXT NOT NULL,
                expected_result TEXT NOT NULL,
                screenshot VARCHAR(1024) NULL,
                priority ENUM('LOWEST', 'LOW', 'MEDIUM', 'HIGH', 'HIGHEST', 'CRITICAL') NULL,
                test_group ENUM('GENERAL', 'CUSTOM') NULL,
                functionality VARCHAR(255) NULL,
                order_index INT NOT NULL DEFAULT 0,
                config_id INT NULL,
                qa_auto_coverage VARCHAR(255) NULL,
                embedding LONGTEXT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                
                INDEX idx_testcases_checklist (checklist_id),
                INDEX idx_testcases_test_group (test_group),
                INDEX idx_testcases_functionality (functionality),
                INDEX idx_testcases_priority (priority),
                INDEX idx_testcases_config (config_id),
                INDEX idx_testcases_order (checklist_id, order_index),
                FOREIGN KEY (checklist_id) REFERENCES checklists(id) ON DELETE CASCADE,
                FOREIGN KEY (config_id) REFERENCES configs(id) ON DELETE SET NULL
            )
        """))
        logger.info("✅ Створено таблицю testcases")
        
        # Створюємо checklist_configs
        session.execute(text("""
            CREATE TABLE checklist_configs (
                checklist_id INT NOT NULL,
                config_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                PRIMARY KEY (checklist_id, config_id),
                FOREIGN KEY (checklist_id) REFERENCES checklists(id) ON DELETE CASCADE,
                FOREIGN KEY (config_id) REFERENCES configs(id) ON DELETE CASCADE
            )
        """))
        logger.info("✅ Створено таблицю checklist_configs")
        
        # Створюємо ingestion_jobs
        session.execute(text("""
            CREATE TABLE ingestion_jobs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMP NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'running',
                details TEXT NULL,
                documents_processed INT DEFAULT 0,
                chunks_created INT DEFAULT 0,
                features_created INT DEFAULT 0,
                
                INDEX idx_ingestion_jobs_status (status),
                INDEX idx_ingestion_jobs_started (started_at)
            )
        """))
        logger.info("✅ Створено таблицю ingestion_jobs")
        
        # 3. Додаємо тестові дані
        logger.info("📝 Додаємо тестові дані...")
        
        # Додаємо тестові секції
        session.execute(text("""
            INSERT INTO qa_sections (confluence_page_id, title, description, url, space_key) VALUES 
            ('43624449', 'Checklist WEB', 'Web application testing checklists', 'https://confluence.togethernetworks.com/pages/43624449', 'QMT'),
            ('117706559', 'Checklist MOB', 'Mobile application testing checklists', 'https://confluence.togethernetworks.com/pages/117706559', 'QMT'),
            ('340830206', 'Payment Page', 'Payment functionality testing', 'https://confluence.togethernetworks.com/pages/340830206', 'QMT')
        """))
        logger.info("✅ Додано тестові секції")
        
        # Додаємо тестові конфіги
        session.execute(text("""
            INSERT INTO configs (name, url, description) VALUES 
            ('billingHistoryConfig', 'https://my.platformphoenix.com/search/showConfigs?fileName=%2Fbilling%2Fhistory.yaml', 'Billing history configuration'),
            ('paymentConfig', 'https://my.platformphoenix.com/search/showConfigs?fileName=%2Fpayment%2Fconfig.yaml', 'Payment processing configuration'),
            ('authConfig', 'https://my.platformphoenix.com/search/showConfigs?fileName=%2Fauth%2Fconfig.yaml', 'Authentication configuration')
        """))
        logger.info("✅ Додано тестові конфіги")
        
        # Додаємо тестові чеклісти з subcategory
        session.execute(text("""
            INSERT INTO checklists (confluence_page_id, title, description, url, space_key, section_id, subcategory, content_hash, version) VALUES 
            ('billing_history_123', 'WEB: Billing History', 'Testing billing history functionality', 'https://confluence.togethernetworks.com/pages/billing_history_123', 'QMT', 1, 'Billing Management', SHA2('billing history content', 256), 1),
            ('search_456', 'WEB: Search', 'Testing search functionality', 'https://confluence.togethernetworks.com/pages/search_456', 'QMT', 1, 'Search & Navigation', SHA2('search content', 256), 1),
            ('payment_789', 'WEB: Payment', 'Testing payment functionality', 'https://confluence.togethernetworks.com/pages/payment_789', 'QMT', 1, 'Payment Processing', SHA2('payment content', 256), 1)
        """))
        logger.info("✅ Додано тестові чеклісти")
        
        session.commit()
        logger.info("🎉 Повна переініціалізація бази даних успішно завершена!")
        
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Помилка під час переініціалізації: {e}")
        raise
    finally:
        session.close()
        qa_repo.close()

if __name__ == "__main__":
    reinit_database()
