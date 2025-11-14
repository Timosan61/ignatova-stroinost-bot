"""
Qdrant Vector Database Service

Сервис для работы с Qdrant vector database.
Обеспечивает семантический поиск и гибридный поиск
по базе знаний курса "Всепрощающая".

Architecture:
- Qdrant Cloud: Vector database backend
- sentence-transformers: Генерация embeddings (all-MiniLM-L6-v2)
- Hybrid search: Vector + Full-text search
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance, VectorParams, PointStruct,
        Filter, FieldCondition, MatchValue,
        SearchRequest, QueryResponse, ScoredPoint
    )
    from sentence_transformers import SentenceTransformer
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    logging.warning("Qdrant or sentence-transformers not installed. Vector search disabled.")

from bot.config import (
    QDRANT_URL,
    QDRANT_API_KEY,
    QDRANT_COLLECTION,
    EMBEDDING_MODEL,
    USE_QDRANT
)

logger = logging.getLogger(__name__)


class QdrantService:
    """
    Сервис для работы с Qdrant vector database

    Features:
    - Semantic search (векторный поиск по embeddings)
    - Full-text search (keyword matching через payload)
    - Hybrid search (комбинация vector + filters)
    - Fast retrieval (HNSW algorithm, оптимизирован для speed)
    """

    def __init__(self):
        """Инициализация Qdrant client"""
        self.enabled = USE_QDRANT and QDRANT_AVAILABLE
        self.client = None
        self.encoder = None
        self.collection_name = QDRANT_COLLECTION

        if not self.enabled:
            logger.warning("Qdrant service disabled (check USE_QDRANT and dependencies)")
            return

        try:
            # Инициализация Qdrant client
            if QDRANT_URL and QDRANT_API_KEY:
                self.client = QdrantClient(
                    url=QDRANT_URL,
                    api_key=QDRANT_API_KEY,
                    timeout=30
                )
                logger.info(f"Qdrant client initialized: {QDRANT_URL}")
            else:
                logger.error("Qdrant credentials not configured (QDRANT_URL/QDRANT_API_KEY)")
                self.enabled = False
                return

            # Инициализация sentence transformer для embeddings
            logger.info(f"Loading sentence transformer model: {EMBEDDING_MODEL}")
            self.encoder = SentenceTransformer(EMBEDDING_MODEL)
            logger.info(f"✅ Sentence transformer loaded: {EMBEDDING_MODEL}")

            # Проверка подключения
            try:
                collections = self.client.get_collections()
                logger.info(f"✅ Qdrant connected. Collections: {[c.name for c in collections.collections]}")
            except Exception as e:
                logger.error(f"Failed to connect to Qdrant: {e}")
                self.enabled = False
                return

            logger.info(f"✅ Qdrant service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Qdrant service: {e}")
            logger.exception("Full traceback:")
            self.enabled = False

    async def health_check(self) -> Dict[str, Any]:
        """
        Проверка здоровья Qdrant service

        Returns:
            Dict с информацией о статусе:
            {
                "service": "qdrant",
                "status": "healthy" | "unhealthy",
                "enabled": bool,
                "url": str,
                "collection": str,
                "error": str (optional)
            }
        """
        if not self.enabled:
            return {
                "service": "qdrant",
                "status": "disabled",
                "enabled": False,
                "url": QDRANT_URL or "not configured",
                "collection": self.collection_name
            }

        try:
            # Проверка подключения
            collections = self.client.get_collections()
            collection_exists = any(c.name == self.collection_name for c in collections.collections)

            return {
                "service": "qdrant",
                "status": "healthy",
                "enabled": True,
                "url": QDRANT_URL,
                "collection": self.collection_name,
                "collection_exists": collection_exists
            }
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return {
                "service": "qdrant",
                "status": "unhealthy",
                "enabled": True,
                "url": QDRANT_URL,
                "collection": self.collection_name,
                "error": str(e)
            }

    async def get_stats(self) -> Dict[str, Any]:
        """
        Получить статистику Qdrant collection

        Returns:
            Dict со статистикой:
            {
                "collection": str,
                "points_count": int,
                "indexed_vectors_count": int,
                "vectors_count": int,
                "status": str
            }
        """
        if not self.enabled or not self.client:
            return {
                "error": "Qdrant service not enabled or not initialized",
                "enabled": self.enabled
            }

        try:
            # Получаем информацию о коллекции
            collection_info = self.client.get_collection(self.collection_name)

            return {
                "collection": self.collection_name,
                "points_count": collection_info.points_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "vectors_count": collection_info.vectors_count,
                "status": collection_info.status
            }
        except Exception as e:
            logger.error(f"Failed to get Qdrant stats: {e}")
            return {
                "error": str(e),
                "collection": self.collection_name
            }

    async def search_semantic(
        self,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.5,
        entity_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Семантический поиск (векторный поиск по embeddings)

        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов
            score_threshold: Минимальный порог релевантности (0.0-1.0)
            entity_type: Фильтр по типу entity (lesson, faq, technique и т.д.)

        Returns:
            List результатов поиска:
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
        if not self.enabled or not self.client or not self.encoder:
            logger.warning("Qdrant service not available for search")
            return []

        try:
            # Генерируем embedding для запроса
            query_vector = self.encoder.encode(query).tolist()

            # Создаём фильтр если указан entity_type
            search_filter = None
            if entity_type:
                search_filter = Filter(
                    must=[
                        FieldCondition(
                            key="entity_type",
                            match=MatchValue(value=entity_type)
                        )
                    ]
                )

            # Выполняем поиск
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=search_filter
            )

            # Форматируем результаты
            results = []
            for hit in search_result:
                result = {
                    "id": str(hit.id),
                    "score": hit.score,
                    "entity_type": hit.payload.get("entity_type", "unknown"),
                    "title": hit.payload.get("title", ""),
                    "content": hit.payload.get("content", ""),
                    "metadata": hit.payload.get("metadata", {})
                }
                results.append(result)

            logger.info(f"🔍 Qdrant semantic search: query='{query[:50]}', found={len(results)}")
            return results

        except Exception as e:
            logger.error(f"Qdrant semantic search failed: {e}")
            logger.exception("Full traceback:")
            return []

    async def search_hybrid(
        self,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Гибридный поиск (векторный + фильтры)

        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов
            score_threshold: Минимальный порог релевантности
            filters: Дополнительные фильтры:
                {
                    "entity_type": "lesson",
                    "category": "forgiveness",
                    "lesson_number": 5
                }

        Returns:
            List результатов поиска (формат как в search_semantic)
        """
        if not self.enabled or not self.client or not self.encoder:
            logger.warning("Qdrant service not available for hybrid search")
            return []

        try:
            # Генерируем embedding для запроса
            query_vector = self.encoder.encode(query).tolist()

            # Создаём фильтр из filters dict
            search_filter = None
            if filters:
                filter_conditions = []
                for key, value in filters.items():
                    filter_conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        )
                    )

                if filter_conditions:
                    search_filter = Filter(must=filter_conditions)

            # Выполняем поиск
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=search_filter
            )

            # Форматируем результаты
            results = []
            for hit in search_result:
                result = {
                    "id": str(hit.id),
                    "score": hit.score,
                    "entity_type": hit.payload.get("entity_type", "unknown"),
                    "title": hit.payload.get("title", ""),
                    "content": hit.payload.get("content", ""),
                    "metadata": hit.payload.get("metadata", {})
                }
                results.append(result)

            logger.info(f"🔍 Qdrant hybrid search: query='{query[:50]}', filters={filters}, found={len(results)}")
            return results

        except Exception as e:
            logger.error(f"Qdrant hybrid search failed: {e}")
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
        Добавить entity в Qdrant

        Args:
            entity_id: Уникальный ID entity
            content: Текстовое содержимое (будет векторизовано)
            entity_type: Тип entity (lesson, faq, technique и т.д.)
            title: Заголовок entity
            metadata: Дополнительные метаданные

        Returns:
            Tuple (success: bool, error_message: Optional[str])
        """
        if not self.enabled or not self.client or not self.encoder:
            return False, "Qdrant service not available"

        try:
            # Генерируем embedding
            vector = self.encoder.encode(content).tolist()

            # Подготавливаем payload
            payload = {
                "entity_type": entity_type,
                "title": title,
                "content": content,
                "metadata": metadata or {},
                "created_at": datetime.utcnow().isoformat()
            }

            # Добавляем point в коллекцию
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=entity_id,
                        vector=vector,
                        payload=payload
                    )
                ]
            )

            logger.info(f"✅ Added entity to Qdrant: id={entity_id}, type={entity_type}")
            return True, None

        except Exception as e:
            error_msg = f"Failed to add entity to Qdrant: {e}"
            logger.error(error_msg)
            logger.exception("Full traceback:")
            return False, error_msg


# Singleton instance
_qdrant_service_instance = None


def get_qdrant_service() -> QdrantService:
    """Получить singleton instance QdrantService"""
    global _qdrant_service_instance
    if _qdrant_service_instance is None:
        _qdrant_service_instance = QdrantService()
    return _qdrant_service_instance
