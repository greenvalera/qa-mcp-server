# Конфігурація секцій

## sections.json

Файл `sections.json` містить конфігурацію базових секцій, які автоматично створюються при ініціалізації бази даних та використовуються для завантаження даних з Confluence.

### Структура файлу

```json
{
  "default_sections": [
    {
      "confluence_page_id": "43624449",
      "title": "Checklist WEB",
      "description": "Web application testing checklists",
      "url": "https://confluence.togethernetworks.com/spaces/QMT/pages/43624449/Checklist+WEB",
      "space_key": "QMT"
    }
  ]
}
```

### Поля секції

- `confluence_page_id` - ID сторінки в Confluence (унікальний ідентифікатор)
- `title` - Назва секції (відображається в MCP інструментах)
- `description` - Опис секції
- `url` - URL сторінки в Confluence
- `space_key` - Ключ простору в Confluence

### Як це працює

#### Ініціалізація бази даних

1. При першому запуску системи викликається `QARepository.create_tables()`
2. Після створення таблиць автоматично викликається `initialize_default_sections()`
3. Метод читає `sections.json` і створює секції в базі даних
4. При повторному запуску секції не дублюються

#### Завантаження даних з Confluence

1. `UnifiedConfluenceLoader` завантажує конфігурацію з `sections.json`
2. При завантаженні чеклістів, loader визначає секцію на основі:
   - ID батьківської сторінки в Confluence (якщо збігається з ID секції з конфігурації)
   - Назви батьківської сторінки (якщо збігається з назвою секції)
   - Першої доступної секції (якщо не знайдено збігів)
3. Якщо не передано `--page-ids` або `--use-config`, автоматично використовуються ID з `sections.json`

### Додавання нових секцій

Для додавання нової секції:

1. Відредагуйте `sections.json`
2. Додайте новий об'єкт в масив `default_sections`
3. Перезапустіть систему

### Приклад додавання секції

```json
{
  "default_sections": [
    {
      "confluence_page_id": "43624449",
      "title": "Checklist WEB",
      "description": "Web application testing checklists",
      "url": "https://confluence.togethernetworks.com/spaces/QMT/pages/43624449/Checklist+WEB",
      "space_key": "QMT"
    },
    {
      "confluence_page_id": "123456789",
      "title": "Checklist API",
      "description": "API testing checklists",
      "url": "https://confluence.togethernetworks.com/spaces/QMT/pages/123456789/Checklist+API",
      "space_key": "QMT"
    }
  ]
}
```

### Приклади використання

#### Завантаження з конфігурації (автоматично використовує ID з sections.json)

```bash
# Завантаження тільки в MySQL з автоматичним визначенням ID секцій
python3 scripts/confluence/unified_loader.py --mysql-only

# Завантаження з реальним API
python3 scripts/confluence/unified_loader.py --use-real-api --mysql-only
```

#### Завантаження конкретних сторінок

```bash
# Завантаження конкретних ID
python3 scripts/confluence/unified_loader.py --page-ids 43624449,117706559

# Завантаження з .env конфігурації
python3 scripts/confluence/unified_loader.py --use-config
```
