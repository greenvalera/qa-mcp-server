#!/usr/bin/env python3
"""
Скрипт для міграції поля subcategory з таблиці testcases до таблиці checklists.
Цей скрипт видаляє поле subcategory з testcases та додає його до checklists.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.data.qa_repository import QARepository
from app.models.qa_models import TestCase, Checklist
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_subcategory():
    """Виконує міграцію поля subcategory."""
    
    qa_repo = QARepository()
    session = qa_repo.get_session()
    
    try:
        logger.info("🚀 Починаємо міграцію поля subcategory...")
        
        # 1. Перевіряємо, чи існує поле subcategory в testcases
        logger.info("📋 Перевіряємо структуру таблиці testcases...")
        result = session.execute(text("SHOW COLUMNS FROM testcases LIKE 'subcategory'"))
        has_subcategory_in_testcases = result.fetchone() is not None
        
        if has_subcategory_in_testcases:
            logger.info("✅ Поле subcategory знайдено в таблиці testcases")
            
            # 2. Перевіряємо, чи існує поле subcategory в checklists
            logger.info("📋 Перевіряємо структуру таблиці checklists...")
            result = session.execute(text("SHOW COLUMNS FROM checklists LIKE 'subcategory'"))
            has_subcategory_in_checklists = result.fetchone() is not None
            
            if not has_subcategory_in_checklists:
                logger.info("⚠️ Поле subcategory не знайдено в таблиці checklists")
                logger.info("🔧 Додаємо поле subcategory до таблиці checklists...")
                
                # Додаємо поле subcategory до checklists
                session.execute(text("""
                    ALTER TABLE checklists 
                    ADD COLUMN subcategory VARCHAR(255) NULL 
                    COMMENT 'Subcategory from parent page hierarchy'
                """))
                
                # Додаємо індекс
                session.execute(text("""
                    ALTER TABLE checklists 
                    ADD INDEX idx_checklists_subcategory (subcategory)
                """))
                
                logger.info("✅ Поле subcategory додано до таблиці checklists")
            
            # 3. Переносимо дані subcategory з testcases до checklists
            logger.info("🔄 Переносимо дані subcategory з testcases до checklists...")
            
            # Отримуємо унікальні значення subcategory з testcases
            result = session.execute(text("""
                SELECT DISTINCT checklist_id, subcategory 
                FROM testcases 
                WHERE subcategory IS NOT NULL AND subcategory != ''
            """))
            
            migrated_count = 0
            for row in result:
                checklist_id, subcategory = row
                
                # Оновлюємо checklist з subcategory
                session.execute(text("""
                    UPDATE checklists 
                    SET subcategory = :subcategory 
                    WHERE id = :checklist_id
                """), {"subcategory": subcategory, "checklist_id": checklist_id})
                
                migrated_count += 1
            
            logger.info(f"✅ Перенесено {migrated_count} записів subcategory")
            
            # 4. Видаляємо поле subcategory з testcases
            logger.info("🗑️ Видаляємо поле subcategory з таблиці testcases...")
            
            # Видаляємо індекс
            session.execute(text("DROP INDEX IF EXISTS idx_testcases_subcategory ON testcases"))
            
            # Видаляємо поле
            session.execute(text("ALTER TABLE testcases DROP COLUMN subcategory"))
            
            logger.info("✅ Поле subcategory видалено з таблиці testcases")
            
        else:
            logger.info("ℹ️ Поле subcategory не знайдено в таблиці testcases - міграція не потрібна")
        
        # 5. Перевіряємо результат
        logger.info("🔍 Перевіряємо результат міграції...")
        
        # Перевіряємо checklists
        result = session.execute(text("SHOW COLUMNS FROM checklists LIKE 'subcategory'"))
        if result.fetchone():
            logger.info("✅ Поле subcategory присутнє в таблиці checklists")
        else:
            logger.error("❌ Поле subcategory відсутнє в таблиці checklists")
        
        # Перевіряємо testcases
        result = session.execute(text("SHOW COLUMNS FROM testcases LIKE 'subcategory'"))
        if not result.fetchone():
            logger.info("✅ Поле subcategory відсутнє в таблиці testcases")
        else:
            logger.error("❌ Поле subcategory все ще присутнє в таблиці testcases")
        
        session.commit()
        logger.info("🎉 Міграція успішно завершена!")
        
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Помилка під час міграції: {e}")
        raise
    finally:
        session.close()
        qa_repo.close()

if __name__ == "__main__":
    migrate_subcategory()
