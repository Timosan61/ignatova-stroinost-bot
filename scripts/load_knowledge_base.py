#!/usr/bin/env python3
"""
Скрипт для загрузки базы знаний продаж в Zep Knowledge Graph.
Разбивает большой файл на семантические чанки и загружает их в Zep.
"""

import os
import re
import json
import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime
from dataclasses import dataclass

# Добавляем путь к проекту
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from zep_cloud.client import AsyncZep

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class KnowledgeChunk:
    """Структура для чанка знаний"""
    content: str
    title: str
    category: str
    source: str
    metadata: Dict[str, Any]

class KnowledgeBaseLoader:
    """Класс для загрузки базы знаний в Zep"""
    
    def __init__(self, zep_api_key: str):
        self.zep_client = AsyncZep(api_key=zep_api_key)
        self.project_id = "sales-knowledge-base"
        
    def split_markdown_by_sections(self, content: str) -> List[KnowledgeChunk]:
        """Разбивает markdown файл на семантические чанки по секциям"""
        chunks = []
        
        # Паттерны для разных типов секций
        patterns = {
            'training': r'## Тренинг.*?call_(\d+)_(summary|FAQ)\.md',
            'section': r'## (.+?)(?=\n\n|\n##|\nfollowed by another section|\Z)',
            'call_section': r'# (.+?)(?=\n##|\n#|\Z)',
            'faq': r'(\d+)\) \*\*(.+?)\*\* — (.+?)(?=\n\d+\)|\n##|\n#|\Z)',
            'script': r'### (.+?)(?=\n###|\n##|\n#|\Z)'
        }
        
        # Разбиваем по главным секциям (## заголовки)
        main_sections = re.split(r'\n(?=## )', content)
        
        for section in main_sections:
            if not section.strip():
                continue
                
            # Определяем тип секции и извлекаем метаданные
            chunk = self._process_section(section)
            if chunk:
                chunks.append(chunk)
        
        logger.info(f"Создано {len(chunks)} чанков из базы знаний")
        return chunks
    
    def _process_section(self, section: str) -> KnowledgeChunk:
        """Обрабатывает отдельную секцию и создаёт чанк"""
        lines = section.strip().split('\n')
        
        if not lines:
            return None
            
        # Извлекаем заголовок (первая строка)
        title = lines[0].strip('# ').strip()
        
        # Определяем категорию по содержимому
        category = self._determine_category(section)
        source = self._extract_source(section)
        
        # Ограничиваем размер чанка (примерно 1000 токенов = 4000 символов)
        max_chars = 3500
        content = section
        if len(content) > max_chars:
            # Обрезаем по предложениям, чтобы сохранить смысл
            sentences = re.split(r'(?<=[.!?])\s+', content)
            truncated = ""
            for sentence in sentences:
                if len(truncated + sentence) > max_chars:
                    break
                truncated += sentence + " "
            content = truncated.strip()
        
        # Создаём метаданные
        metadata = {
            'word_count': len(content.split()),
            'char_count': len(content),
            'created_at': datetime.now().isoformat(),
            'contains_scripts': 'скрипт' in content.lower() or 'шаблон' in content.lower(),
            'contains_objections': 'возражени' in content.lower(),
            'contains_faq': 'FAQ' in section or 'вопрос' in content.lower(),
        }
        
        return KnowledgeChunk(
            content=content,
            title=title,
            category=category,
            source=source,
            metadata=metadata
        )
    
    def _determine_category(self, section: str) -> str:
        """Определяет категорию чанка по содержимому"""
        section_lower = section.lower()
        
        if 'call_' in section_lower and 'summary' in section_lower:
            return 'training_summary'
        elif 'call_' in section_lower and 'faq' in section_lower:
            return 'training_faq'
        elif 'скрипт' in section_lower or 'шаблон' in section_lower:
            return 'scripts'
        elif 'возражени' in section_lower:
            return 'objections'
        elif 'faq' in section_lower or 'вопрос' in section_lower:
            return 'faq'
        elif 'техник' in section_lower or 'метод' in section_lower:
            return 'techniques'
        elif 'продаж' in section_lower or 'продав' in section_lower:
            return 'sales_methodology'
        else:
            return 'general'
    
    def _extract_source(self, section: str) -> str:
        """Извлекает источник (номер call'а) из секции"""
        match = re.search(r'call_(\d+)', section)
        if match:
            return f"call_{match.group(1)}"
        return "general"
    
    async def upload_to_zep(self, chunks: List[KnowledgeChunk]) -> bool:
        """Загружает чанки в Zep Knowledge Graph"""
        try:
            logger.info(f"Начинаем загрузку {len(chunks)} чанков в Zep...")
            
            # Загружаем каждый чанк как документ
            for i, chunk in enumerate(chunks):
                try:
                    # Подготавливаем данные для Zep
                    document_data = {
                        "content": chunk.content,
                        "metadata": {
                            "title": chunk.title,
                            "category": chunk.category,
                            "source": chunk.source,
                            "chunk_id": i + 1,
                            **chunk.metadata
                        }
                    }
                    
                    # Создаём сессию для каждого типа контента
                    session_id = f"knowledge_{chunk.category}_{chunk.source}_{i}"
                    
                    # Добавляем как данные графа знаний
                    # В Zep v2 используется add_data метод для Knowledge Graph
                    await self.zep_client.graph.add(
                        session_id=session_id,
                        data=json.dumps(document_data)
                    )
                    
                    logger.info(f"✅ Загружен чанк {i+1}/{len(chunks)}: {chunk.title[:50]}...")
                    
                    # Небольшая пауза чтобы не перегружать API
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка загрузки чанка {i+1}: {e}")
                    continue
            
            logger.info("🎉 Загрузка базы знаний в Zep завершена!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка загрузки в Zep: {e}")
            return False
    
    async def test_search(self, query: str) -> List[Dict]:
        """Тестирует поиск в загруженной базе знаний"""
        try:
            # Используем поиск по графу знаний
            results = await self.zep_client.graph.search(
                query=query,
                limit=5
            )
            
            logger.info(f"🔍 Найдено {len(results)} результатов для запроса: '{query}'")
            return results
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска: {e}")
            return []

async def main():
    """Основная функция"""
    # Проверяем наличие API ключа
    zep_api_key = os.getenv('ZEP_API_KEY')
    if not zep_api_key:
        logger.error("❌ ZEP_API_KEY не найден в переменных окружения!")
        return
    
    # Путь к файлу с базой знаний
    knowledge_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        'Sales_Assistant_Master_Instruction_CONTENT_ONLY.md'
    )
    
    if not os.path.exists(knowledge_file):
        logger.error(f"❌ Файл базы знаний не найден: {knowledge_file}")
        return
    
    # Читаем файл
    logger.info(f"📖 Читаем базу знаний из {knowledge_file}")
    with open(knowledge_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    logger.info(f"📊 Размер файла: {len(content)} символов")
    
    # Создаём загрузчик
    loader = KnowledgeBaseLoader(zep_api_key)
    
    # Разбиваем на чанки
    chunks = loader.split_markdown_by_sections(content)
    
    # Выводим статистику
    logger.info(f"📈 Статистика чанков:")
    categories = {}
    for chunk in chunks:
        categories[chunk.category] = categories.get(chunk.category, 0) + 1
    
    for category, count in categories.items():
        logger.info(f"  {category}: {count} чанков")
    
    # Загружаем в Zep
    success = await loader.upload_to_zep(chunks)
    
    if success:
        # Тестируем поиск
        logger.info("\n🧪 Тестируем поиск в базе знаний...")
        
        test_queries = [
            "как работать с возражениями",
            "скрипты для старой базы",
            "диагностика психотипа",
            "марафоны похудения цена"
        ]
        
        for query in test_queries:
            results = await loader.test_search(query)
            logger.info(f"  '{query}': {len(results)} результатов")

if __name__ == "__main__":
    asyncio.run(main())