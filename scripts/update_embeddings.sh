#!/bin/bash
# Скрипт для оновлення embeddings тесткейсів

# Переходимо в директорію проекту
cd "$(dirname "$0")/.."

# Активуємо віртуальне середовище якщо воно існує
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Запускаємо Python скрипт з передачею всіх аргументів
python scripts/update_embeddings.py "$@"
