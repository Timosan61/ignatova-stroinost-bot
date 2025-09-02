# Scripts для работы с базой знаний

Скрипты для интеграции базы знаний продаж с Zep Knowledge Graph.

## Структура

### `load_knowledge_base.py`
Загружает базу знаний продаж в Zep Knowledge Graph.

**Что делает:**
- Читает файл `Sales_Assistant_Master_Instruction_CONTENT_ONLY.md`
- Разбивает на семантические чанки по темам
- Добавляет метаданные (категория, источник, etc.)
- Загружает в Zep Knowledge Graph

**Использование:**
```bash
# Убедитесь что ZEP_API_KEY установлен в .env
python scripts/load_knowledge_base.py
```

### `test_knowledge_search.py`
Тестирует поиск в загруженной базе знаний.

**Что делает:**
- Проверяет подключение к Zep
- Выполняет тестовые поисковые запросы
- Показывает найденные результаты
- Тестирует полную генерацию ответа с контекстом

**Использование:**
```bash
python scripts/test_knowledge_search.py
```

## Требования

1. **ZEP_API_KEY** в переменных окружения
2. Файл `Sales_Assistant_Master_Instruction_CONTENT_ONLY.md` в корне проекта
3. Установленные зависимости: `pip install -r requirements.txt`

## Процесс интеграции

1. **Загрузка базы знаний:**
   ```bash
   python scripts/load_knowledge_base.py
   ```
   
2. **Проверка работы:**
   ```bash
   python scripts/test_knowledge_search.py
   ```

3. **Результат:**
   - База знаний доступна боту для семантического поиска
   - Бот может находить релевантную информацию по любым вопросам
   - Ответы основаны на актуальных методологиях продаж

## Лимиты Zep Cloud

- **Бесплатный план:** 2.5MB Graph Data/месяц
- **Наша база:** ~0.25MB (10% от лимита)
- **Запас:** Можно загрузить в 10 раз больше данных

## Категории в базе знаний

- `training_summary` - Конспекты тренингов
- `training_faq` - FAQ по тренингам  
- `scripts` - Готовые скрипты и шаблоны
- `objections` - Работа с возражениями
- `techniques` - Техники продаж
- `sales_methodology` - Методологии продаж
- `general` - Общая информация