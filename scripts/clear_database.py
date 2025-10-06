#!/usr/bin/env python3
"""Скрипт для очищення всіх даних з таблиць чеклістів та тесткейсів."""

import os
import sys
import click

# Add app to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.data.qa_repository import QARepository
from app.models.qa_models import Checklist, TestCase, Config, QASection, IngestionJob

def clear_database():
    """Очищає всі дані з таблиць чеклістів та тесткейсів."""
    qa_repo = QARepository()
    session = qa_repo.get_session()
    
    try:
        click.echo("🗑️ Починаємо очищення бази даних...")
        
        # Підрахунок записів перед видаленням
        testcases_count = session.query(TestCase).count()
        checklists_count = session.query(Checklist).count()
        configs_count = session.query(Config).count()
        sections_count = session.query(QASection).count()
        jobs_count = session.query(IngestionJob).count()
        
        click.echo(f"📊 Знайдено записів для видалення:")
        click.echo(f"  - Тесткейси: {testcases_count}")
        click.echo(f"  - Чеклісти: {checklists_count}")
        click.echo(f"  - Конфіги: {configs_count}")
        click.echo(f"  - Секції: {sections_count}")
        click.echo(f"  - Jobs: {jobs_count}")
        
        # Видалення в правильному порядку (з урахуванням foreign keys)
        click.echo("\n🗑️ Видаляємо тесткейси...")
        session.query(TestCase).delete()
        
        click.echo("🗑️ Видаляємо чеклісти...")
        session.query(Checklist).delete()
        
        click.echo("🗑️ Видаляємо конфіги...")
        session.query(Config).delete()
        
        click.echo("🗑️ Видаляємо секції...")
        session.query(QASection).delete()
        
        click.echo("🗑️ Видаляємо jobs...")
        session.query(IngestionJob).delete()
        
        # Підтверджуємо зміни
        session.commit()
        
        click.echo("\n✅ База даних успішно очищена!")
        
    except Exception as e:
        session.rollback()
        click.echo(f"❌ Помилка при очищенні бази даних: {e}")
        raise
    finally:
        session.close()
        qa_repo.close()

@click.command()
def main():
    """Очищає всі дані з таблиць чеклістів та тесткейсів."""
    if click.confirm("⚠️ Ви впевнені, що хочете видалити ВСІ дані з бази? Цю дію неможливо скасувати!"):
        clear_database()
    else:
        click.echo("❌ Операція скасована")

if __name__ == "__main__":
    main()
