#!/usr/bin/env python3
"""
Скрипт для оновлення embeddings тесткейсів.
Використовується для підготовки даних для семантичного пошуку.
"""

import sys
import os
import click
import time
from typing import Dict, Any

# Додаємо корінь проекту до Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.data.qa_repository import QARepository
from app.ai.embedder import OpenAIEmbedder


class EmbeddingUpdater:
    """Клас для оновлення embeddings тесткейсів."""
    
    def __init__(self):
        """Ініціалізація."""
        self.qa_repo = QARepository()
        self.embedder = OpenAIEmbedder()
        
    def check_connection(self) -> bool:
        """Перевіряє з'єднання з OpenAI API."""
        click.echo("🔍 Перевірка з'єднання з OpenAI API...")
        
        try:
            # Тестуємо з'єднання
            test_embedding = self.embedder.embed_text("test connection")
            if test_embedding:
                click.echo("✅ З'єднання з OpenAI API успішне")
                return True
            else:
                click.echo("❌ Не вдалося отримати embedding від OpenAI API")
                return False
        except Exception as e:
            click.echo(f"❌ Помилка з'єднання з OpenAI API: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Отримує статистику по embeddings."""
        session = self.qa_repo.get_session()
        try:
            from sqlalchemy import func
            from app.models.qa_models import TestCase
            
            total_testcases = session.query(TestCase).count()
            testcases_with_embeddings = session.query(TestCase).filter(
                TestCase.embedding.isnot(None)
            ).count()
            testcases_without_embeddings = total_testcases - testcases_with_embeddings
            
            return {
                'total': total_testcases,
                'with_embeddings': testcases_with_embeddings,
                'without_embeddings': testcases_without_embeddings,
                'percentage': (testcases_with_embeddings / total_testcases * 100) if total_testcases > 0 else 0
            }
        finally:
            session.close()
    
    def update_embeddings(self, batch_size: int = 50, dry_run: bool = False) -> Dict[str, Any]:
        """Оновлює embeddings для тесткейсів."""
        click.echo(f"🚀 Початок оновлення embeddings...")
        click.echo(f"📊 Розмір батчу: {batch_size}")
        
        if dry_run:
            click.echo("🔍 DRY RUN - нічого не буде змінено")
        
        # Отримуємо статистику
        stats = self.get_statistics()
        click.echo(f"📈 Статистика:")
        click.echo(f"   • Всього тесткейсів: {stats['total']}")
        click.echo(f"   • З embeddings: {stats['with_embeddings']} ({stats['percentage']:.1f}%)")
        click.echo(f"   • Без embeddings: {stats['without_embeddings']}")
        
        if stats['without_embeddings'] == 0:
            click.echo("✅ Всі тесткейси вже мають embeddings!")
            return {
                'success': True,
                'message': 'All testcases already have embeddings',
                'total': 0,
                'updated': 0
            }
        
        if dry_run:
            click.echo(f"🔍 DRY RUN: Було б оновлено {stats['without_embeddings']} тесткейсів")
            return {
                'success': True,
                'message': f'DRY RUN: Would update {stats["without_embeddings"]} testcases',
                'total': stats['without_embeddings'],
                'updated': 0
            }
        
        # Підтвердження
        if not click.confirm(f"❓ Продовжити оновлення {stats['without_embeddings']} тесткейсів?"):
            click.echo("❌ Операцію скасовано")
            return {'success': False, 'message': 'Cancelled by user'}
        
        # Виконуємо оновлення
        start_time = time.time()
        result = self.qa_repo.update_all_embeddings(batch_size=batch_size)
        end_time = time.time()
        
        # Виводимо результати
        if result['success']:
            click.echo("✅ Оновлення embeddings завершено успішно!")
            click.echo(f"📊 Результати:")
            click.echo(f"   • Всього оброблено: {result['total']}")
            click.echo(f"   • Успішно оновлено: {result['updated']}")
            if result.get('failed', 0) > 0:
                click.echo(f"   • Помилок: {result['failed']}")
            click.echo(f"⏱️  Час виконання: {end_time - start_time:.1f} секунд")
        else:
            click.echo(f"❌ Помилка оновлення: {result.get('error', 'Unknown error')}")
        
        return result
    
    def close(self):
        """Закриває з'єднання."""
        self.qa_repo.close()


@click.command()
@click.option('--batch-size', '-b', default=50, help='Розмір батчу для обробки (1-100)')
@click.option('--dry-run', '-d', is_flag=True, help='Тільки показати що буде зроблено, не виконувати')
@click.option('--stats-only', '-s', is_flag=True, help='Тільки показати статистику')
@click.option('--check-connection', '-c', is_flag=True, help='Тільки перевірити з\'єднання з OpenAI')
def main(batch_size: int, dry_run: bool, stats_only: bool, check_connection: bool):
    """Скрипт для оновлення embeddings тесткейсів."""
    
    click.echo("🔧 QA Embeddings Updater")
    click.echo("=" * 50)
    
    # Валідація параметрів
    if batch_size < 1 or batch_size > 100:
        click.echo("❌ Помилка: batch_size повинен бути від 1 до 100")
        sys.exit(1)
    
    updater = EmbeddingUpdater()
    
    try:
        # Перевірка з'єднання
        if check_connection:
            success = updater.check_connection()
            sys.exit(0 if success else 1)
        
        # Показ статистики
        if stats_only:
            stats = updater.get_statistics()
            click.echo("📊 Статистика embeddings:")
            click.echo(f"   • Всього тесткейсів: {stats['total']}")
            click.echo(f"   • З embeddings: {stats['with_embeddings']} ({stats['percentage']:.1f}%)")
            click.echo(f"   • Без embeddings: {stats['without_embeddings']}")
            sys.exit(0)
        
        # Перевіряємо з'єднання перед початком
        if not updater.check_connection():
            click.echo("❌ Неможливо продовжити без з'єднання з OpenAI API")
            sys.exit(1)
        
        # Оновлюємо embeddings
        result = updater.update_embeddings(batch_size=batch_size, dry_run=dry_run)
        
        if result['success']:
            click.echo("🎉 Операція завершена успішно!")
            sys.exit(0)
        else:
            click.echo("💥 Операція завершилася з помилкою!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        click.echo("\n⏹️  Операцію перервано користувачем")
        sys.exit(1)
    except Exception as e:
        click.echo(f"💥 Неочікувана помилка: {e}")
        sys.exit(1)
    finally:
        updater.close()


if __name__ == '__main__':
    main()
