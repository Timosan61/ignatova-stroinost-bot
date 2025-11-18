"""
Supabase Vector Store Service

Сервис для работы с Supabase pgvector.
Обеспечивает семантический поиск через OpenAI embeddings.

Architecture:
- Supabase: PostgreSQL + pgvector extension
- OpenAI: text-embedding-3-small (1536D vectors)
- RPC functions: match_documents для similarity search

Usage:
    from bot.services.supabase_service import get_supabase_service

    service = get_supabase_service()
    results = await service.search_semantic(
        query="как делать мозгоритмы?",
        limit=10,
        entity_type="lesson"
    )
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio

# Use requests instead of Supabase SDK (SDK doesn't support new key format sb_secret_...)
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logging.warning("⚠️ requests not installed. Install: pip install requests")

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("⚠️ openai SDK not installed. Install: pip install openai")

from bot.config import (
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY,
    SUPABASE_TABLE,
    OPENAI_API_KEY,
    OPENAI_EMBEDDING_MODEL,
    USE_SUPABASE
)

logger = logging.getLogger(__name__)


class SupabaseService:
    """Сервис для работы с Supabase pgvector"""

    def __init__(self):
        """Инициализация Supabase REST API client"""
        self.enabled = USE_SUPABASE and REQUESTS_AVAILABLE and OPENAI_AVAILABLE
        self.openai_client: Optional[OpenAI] = None
        self.table_name = SUPABASE_TABLE
        self.embedding_model = OPENAI_EMBEDDING_MODEL

        # REST API setup
        self.api_url = None
        self.headers = None

        if not self.enabled:
            if not REQUESTS_AVAILABLE:
                logger.warning("⚠️ Supabase service disabled: requests not installed")
            elif not OPENAI_AVAILABLE:
                logger.warning("⚠️ Supabase service disabled: openai SDK not installed")
            else:
                logger.warning("⚠️ Supabase service disabled (USE_SUPABASE=false)")
            return

        try:
            # Проверка credentials
            if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
                logger.error("❌ Supabase credentials not configured (SUPABASE_URL/SUPABASE_SERVICE_KEY)")
                self.enabled = False
                return

            if not OPENAI_API_KEY:
                logger.error("❌ OpenAI API key not configured (required for embeddings)")
                self.enabled = False
                return

            # Настройка REST API (вместо SDK - новый формат ключей sb_secret_...)
            self.api_url = f"{SUPABASE_URL}/rest/v1"
            self.headers = {
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=representation"  # Для получения данных в ответе
            }
            logger.info(f"✅ Supabase REST API configured: {SUPABASE_URL}")

            # Инициализация OpenAI client ОТЛОЖЕНА (lazy initialization)
            # Клиент будет создан при первом использовании, чтобы использовать актуальный API key
            self.openai_client = None
            logger.info(f"✅ OpenAI client will be initialized on first use: {self.embedding_model}")

            # Проверка подключения к таблице
            try:
                response = requests.get(
                    f"{self.api_url}/{self.table_name}",
                    headers=self.headers,
                    params={"select": "id", "limit": 1}
                )
                response.raise_for_status()
                logger.info(f"✅ Supabase table '{self.table_name}' accessible")
            except Exception as table_error:
                logger.warning(f"⚠️ Supabase table '{self.table_name}' not found or empty: {table_error}")
                logger.warning("   Run SQL setup script to create the table")

            self.enabled = True

        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase service: {e}")
            logger.exception("Full traceback:")
            self.enabled = False

    def _generate_embedding(self, text: str) -> List[float]:
        """
        Генерация embedding через OpenAI API

        Args:
            text: Текст для векторизации

        Returns:
            Embedding vector (1536D для text-embedding-3-small)

        Raises:
            Exception: Если генерация embedding не удалась
        """
        # Lazy initialization: создать OpenAI client при первом использовании
        # Это гарантирует что мы используем актуальный OPENAI_API_KEY из environment
        if not self.openai_client:
            import os
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY not found in environment")
            self.openai_client = OpenAI(api_key=api_key)
            logger.info(f"✅ OpenAI client initialized (lazy): API key ending in ...{api_key[-4:]}")

        try:
            response = self.openai_client.embeddings.create(
                input=text,
                model=self.embedding_model
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"❌ Failed to generate embedding: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья Supabase service"""
        if not self.enabled:
            return {
                "service": "supabase",
                "status": "disabled",
                "enabled": False,
                "url": SUPABASE_URL or "not configured",
                "table": self.table_name
            }

        try:
            # Проверка подключения через REST API
            response = requests.get(
                f"{self.api_url}/{self.table_name}",
                headers=self.headers,
                params={"select": "id", "limit": 1}
            )
            response.raise_for_status()

            # Подсчет entities через REST API (используем Prefer: count=exact)
            count_headers = {**self.headers, "Prefer": "count=exact"}
            count_response = requests.get(
                f"{self.api_url}/{self.table_name}",
                headers=count_headers,
                params={"select": "id"}
            )
            count_response.raise_for_status()

            # Получаем count из Content-Range header
            content_range = count_response.headers.get("Content-Range", "")
            total_count = 0
            if content_range:
                # Format: "0-9/100" → extract 100
                parts = content_range.split("/")
                if len(parts) == 2:
                    total_count = int(parts[1])

            return {
                "service": "supabase",
                "status": "healthy",
                "enabled": True,
                "url": SUPABASE_URL,
                "table": self.table_name,
                "total_entities": total_count,
                "embedding_model": self.embedding_model
            }
        except Exception as e:
            logger.error(f"❌ Supabase health check failed: {e}")
            return {
                "service": "supabase",
                "status": "unhealthy",
                "enabled": True,
                "url": SUPABASE_URL,
                "table": self.table_name,
                "error": str(e)
            }

    async def search_semantic(
        self,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.5,
        entity_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Семантический поиск через pgvector

        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов
            score_threshold: Минимальный порог similarity (0.0-1.0)
            entity_type: Фильтр по типу entity (lesson, faq, correction, question, brainwrite)

        Returns:
            List of search results:
            [
                {
                    "id": str,
                    "score": float,
                    "entity_type": str,
                    "title": str,
                    "content": str,
                    "metadata": dict
                },
                ...
            ]
        """
        if not self.enabled or not self.api_url:
            logger.warning("⚠️ Supabase service not available")
            return []

        try:
            # Генерируем embedding для запроса
            query_embedding = self._generate_embedding(query)

            # Вызываем RPC function через REST API
            rpc_url = f"{SUPABASE_URL}/rest/v1/rpc/match_documents"

            rpc_params = {
                "query_embedding": query_embedding,
                "match_threshold": score_threshold,
                "match_count": limit
            }

            # Добавляем entity_type фильтр если указан
            if entity_type:
                rpc_params["filter_entity_type"] = entity_type
            else:
                rpc_params["filter_entity_type"] = None

            # POST request для RPC
            response = requests.post(
                rpc_url,
                headers=self.headers,
                json=rpc_params
            )
            response.raise_for_status()

            # Парсим результаты
            data = response.json()

            # Форматируем результаты
            results = []
            for row in data:
                results.append({
                    "id": str(row.get("id")),
                    "score": row.get("similarity", 0.0),
                    "entity_type": row.get("entity_type", "unknown"),
                    "title": row.get("title", ""),
                    "content": row.get("content", ""),
                    "metadata": row.get("metadata", {})
                })

            logger.info(
                f"🔍 Supabase semantic search: query='{query[:50]}...', "
                f"found={len(results)}, entity_type={entity_type or 'all'}"
            )
            return results

        except Exception as e:
            logger.error(f"❌ Supabase semantic search failed: {e}")
            logger.exception("Full traceback:")
            return []

    async def add_entity(
        self,
        entity_id: str,
        content: str,
        entity_type: str,
        title: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Добавить entity в Supabase

        Args:
            entity_id: Уникальный ID entity
            content: Содержимое для векторизации
            entity_type: Тип entity (lesson, faq, correction, question, brainwrite)
            title: Заголовок
            metadata: Дополнительные метаданные

        Returns:
            (success: bool, error_message: Optional[str])
        """
        if not self.enabled or not self.api_url:
            return False, "Supabase service not available"

        try:
            # Генерируем embedding
            embedding = self._generate_embedding(content)

            # Подготавливаем данные
            data = {
                "id": entity_id,
                "entity_type": entity_type,
                "title": title,
                "content": content,
                "metadata": metadata or {},
                "embedding": embedding,
                "created_at": datetime.utcnow().isoformat()
            }

            # Upsert через REST API (используем Prefer: resolution=merge-duplicates)
            upsert_headers = {**self.headers, "Prefer": "resolution=merge-duplicates"}
            response = requests.post(
                f"{self.api_url}/{self.table_name}",
                headers=upsert_headers,
                json=data
            )
            response.raise_for_status()

            logger.info(f"✅ Added entity to Supabase: id={entity_id}, type={entity_type}")
            return True, None

        except Exception as e:
            error_msg = f"Failed to add entity to Supabase: {e}"
            logger.error(f"❌ {error_msg}")
            logger.exception("Full traceback:")
            return False, error_msg

    async def get_stats(self) -> Dict[str, Any]:
        """Получить статистику таблицы"""
        if not self.enabled or not self.api_url:
            return {
                "error": "Supabase service not enabled",
                "enabled": False
            }

        try:
            # Общее количество через REST API
            count_headers = {**self.headers, "Prefer": "count=exact"}
            count_response = requests.get(
                f"{self.api_url}/{self.table_name}",
                headers=count_headers,
                params={"select": "id"}
            )
            count_response.raise_for_status()

            # Получаем count из Content-Range header
            content_range = count_response.headers.get("Content-Range", "")
            total = 0
            if content_range:
                parts = content_range.split("/")
                if len(parts) == 2:
                    total = int(parts[1])

            # По типам (отдельные запросы для каждого типа)
            stats_by_type = {}
            for entity_type in ["lesson", "faq", "correction", "question", "brainwrite"]:
                try:
                    type_response = requests.get(
                        f"{self.api_url}/{self.table_name}",
                        headers=count_headers,
                        params={"select": "id", "entity_type": f"eq.{entity_type}"}
                    )
                    type_response.raise_for_status()

                    type_content_range = type_response.headers.get("Content-Range", "")
                    if type_content_range:
                        parts = type_content_range.split("/")
                        if len(parts) == 2:
                            type_count = int(parts[1])
                            if type_count > 0:
                                stats_by_type[entity_type] = type_count
                except Exception as type_error:
                    logger.warning(f"Failed to get count for {entity_type}: {type_error}")

            return {
                "table": self.table_name,
                "total_entities": total,
                "by_type": stats_by_type,
                "embedding_model": self.embedding_model,
                "embedding_dimensions": 1536  # text-embedding-3-small
            }

        except Exception as e:
            logger.error(f"❌ Failed to get Supabase stats: {e}")
            return {
                "error": str(e),
                "enabled": True
            }


# Singleton instance
_supabase_service_instance = None


def get_supabase_service() -> SupabaseService:
    """Получить singleton instance SupabaseService"""
    global _supabase_service_instance
    if _supabase_service_instance is None:
        _supabase_service_instance = SupabaseService()
    return _supabase_service_instance
