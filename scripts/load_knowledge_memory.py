#!/usr/bin/env python3
"""
Альтернативный подход: загрузка базы знаний через Memory API вместо Knowledge Graph.
Создаём виртуальные диалоги с категориями знаний.
"""

import os
import re
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
from zep_cloud.types import Message

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

class KnowledgeMemoryLoader:
    """Класс для загрузки базы знаний в Zep Memory как диалоги"""
    
    def __init__(self, zep_api_key: str):
        self.zep_client = AsyncZep(api_key=zep_api_key)
        
    def split_markdown_by_sections(self, content: str) -> List[KnowledgeChunk]:
        """Разбивает markdown файл на семантические чанки по секциям"""
        chunks = []
        
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
        
        # Ограничиваем размер чанка (примерно 1500 символов для Memory)
        max_chars = 1500
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
    
    async def upload_to_zep_memory(self, chunks: List[KnowledgeChunk]) -> bool:
        """Загружает чанки в Zep Memory как диалоги"""
        try:
            logger.info(f"Начинаем загрузку {len(chunks)} чанков в Zep Memory...")
            
            # Группируем чанки по категориям для создания тематических сессий
            categories = {}
            for chunk in chunks:
                if chunk.category not in categories:
                    categories[chunk.category] = []
                categories[chunk.category].append(chunk)
            
            # Загружаем каждую категорию, разбивая на подсессии по 12 чанков (24 сообщения + система = 25 < 30)
            total_loaded = 0
            max_chunks_per_session = 12
            
            for category, category_chunks in categories.items():
                try:
                    # Разбиваем большие категории на подсессии
                    chunk_batches = [category_chunks[i:i + max_chunks_per_session] 
                                   for i in range(0, len(category_chunks), max_chunks_per_session)]
                    
                    for batch_idx, batch_chunks in enumerate(chunk_batches):
                        try:
                            session_id = f"knowledge_{category}_session_{batch_idx + 1}"
                            
                            # Создаём диалог для этой подсессии
                            messages = []
                            
                            # Добавляем вступительное сообщение
                            intro_message = Message(
                                role="system",
                                role_type="system",
                                content=f"База знаний [{category.upper()}] часть {batch_idx + 1}. Чанков в этой части: {len(batch_chunks)}"
                            )
                            messages.append(intro_message)
                            
                            # Добавляем каждый чанк как пару вопрос-ответ
                            for chunk in batch_chunks:
                                # Создаём вопрос на основе заголовка
                                question_content = f"Расскажи про: {chunk.title}"
                                question = Message(
                                    role="user",
                                    role_type="user", 
                                    content=question_content
                                )
                                
                                # Создаём ответ с содержимым чанка
                                answer_content = f"[{chunk.category.upper()}] {chunk.title}\n\n{chunk.content}\n\nИсточник: {chunk.source}"
                                answer = Message(
                                    role="assistant",
                                    role_type="assistant",
                                    content=answer_content
                                )
                                
                                messages.extend([question, answer])
                            
                            # Загружаем подсессию
                            await self.zep_client.memory.add(session_id=session_id, messages=messages)
                            
                            total_loaded += len(batch_chunks)
                            logger.info(f"✅ Загружена подсессия '{category}' часть {batch_idx + 1}: {len(batch_chunks)} чанков")
                            
                            # Небольшая пауза между подсессиями
                            await asyncio.sleep(0.2)
                        
                        except Exception as e:
                            logger.error(f"❌ Ошибка загрузки подсессии '{category}' часть {batch_idx + 1}: {e}")
                            continue
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка загрузки категории '{category}': {e}")
                    continue
            
            logger.info(f"🎉 Загрузка завершена! Загружено {total_loaded} чанков в Zep Memory")
            return True
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка загрузки в Zep Memory: {e}")
            return False
    
    async def test_memory_search(self, query: str, limit: int = 3) -> List[str]:
        """Тестирует поиск в загруженной памяти"""
        try:
            # Ищем по всем категориям знаний включая подсессии
            results = []
            
            categories = [
                'training_summary', 'training_faq', 'scripts', 'objections', 
                'faq', 'techniques', 'sales_methodology', 'general'
            ]
            
            for category in categories:
                # Ищем во всех подсессиях этой категории
                for session_part in range(1, 20):  # Максимум 20 подсессий на категорию
                    try:
                        session_id = f"knowledge_{category}_session_{session_part}"
                        memory = await self.zep_client.memory.search(
                            session_id=session_id,
                            query=query,
                            limit=2  # Ограничиваем по 2 результата с подсессии
                        )
                        
                        if memory and hasattr(memory, 'results') and memory.results:
                            for result in memory.results[:2]:  # Берём максимум 2 результата
                                if hasattr(result, 'message') and result.message:
                                    results.append(result.message.content)
                                elif hasattr(result, 'content'):
                                    results.append(result.content)
                        
                    except Exception as e:
                        # Если сессии не существует, прерываем поиск по этой категории
                        if "404" in str(e):
                            break
                        logger.debug(f"Поиск в подсессии {session_id} не дал результатов: {e}")
                        continue
            
            logger.info(f"🔍 Найдено {len(results)} результатов для запроса: '{query}'")
            return results[:limit]  # Возвращаем только нужное количество
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска в памяти: {e}")
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
    loader = KnowledgeMemoryLoader(zep_api_key)
    
    # Разбиваем на чанки
    chunks = loader.split_markdown_by_sections(content)
    
    # Выводим статистику
    logger.info(f"📈 Статистика чанков:")
    categories = {}
    for chunk in chunks:
        categories[chunk.category] = categories.get(chunk.category, 0) + 1
    
    for category, count in categories.items():
        logger.info(f"  {category}: {count} чанков")
    
    # Загружаем в Zep Memory
    success = await loader.upload_to_zep_memory(chunks)
    
    if success:
        # Тестируем поиск
        logger.info("\n🧪 Тестируем поиск в памяти...")
        
        test_queries = [
            "как работать с возражениями",
            "скрипты для старой базы",
            "диагностика психотипа",
            "марафоны похудения цена"
        ]
        
        for query in test_queries:
            results = await loader.test_memory_search(query, limit=2)
            logger.info(f"  '{query}': {len(results)} результатов")
            if results:
                logger.info(f"    Превью: {results[0][:100]}...")

if __name__ == "__main__":
    asyncio.run(main())