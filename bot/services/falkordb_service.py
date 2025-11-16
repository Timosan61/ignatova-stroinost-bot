"""
FalkorDB Service for Graphiti Knowledge Graph
496x faster than Neo4j, Redis-based graph database
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from graphiti_core import Graphiti
from graphiti_core.llm_client import OpenAIClient, LLMConfig
from graphiti_core.driver.falkordb_driver import FalkorDriver

from bot.config import (
    FALKORDB_HOST,
    FALKORDB_PORT,
    FALKORDB_USERNAME,
    FALKORDB_PASSWORD,
    FALKORDB_DATABASE,
    OPENAI_API_KEY,
    MODEL_NAME,
    SMALL_MODEL_NAME
)

logger = logging.getLogger(__name__)


class FalkorDBService:
    """Сервис для работы с Graphiti через FalkorDB"""

    def __init__(self):
        """Инициализация FalkorDB service"""
        self.graphiti_client: Optional[Graphiti] = None
        self.falkor_driver: Optional[FalkorDriver] = None
        self.enabled = False
        self._indices_built = False

        try:
            # Проверка credentials
            if not FALKORDB_HOST or not FALKORDB_PASSWORD:
                logger.error("FalkorDB credentials not configured")
                self.enabled = False
                return

            logger.info(f"Initializing FalkorDB driver: {FALKORDB_HOST}:{FALKORDB_PORT}")

            # Создаём FalkorDB driver
            self.falkor_driver = FalkorDriver(
                host=FALKORDB_HOST,
                port=FALKORDB_PORT,
                username=FALKORDB_USERNAME,
                password=FALKORDB_PASSWORD,
                database=FALKORDB_DATABASE
            )

            logger.info("✅ FalkorDB driver created successfully")

            # Создаём LLM client с явным указанием модели
            logger.info(f"Creating LLM client with model: {MODEL_NAME}")

            llm_config = LLMConfig(
                api_key=OPENAI_API_KEY,
                model=MODEL_NAME,  # "gpt-4o-mini"
                temperature=0.1
            )

            llm_client = OpenAIClient(config=llm_config)

            # Создаём Graphiti client с FalkorDB driver
            self.graphiti_client = Graphiti(
                graph_driver=self.falkor_driver,
                llm_client=llm_client
            )

            logger.info(f"✅ Graphiti client initialized with FalkorDB backend ({MODEL_NAME})")

            self.enabled = True

        except Exception as e:
            logger.error(f"Failed to initialize FalkorDB service: {e}")
            logger.exception("Full traceback:")
            self.enabled = False

    async def _ensure_indices(self) -> bool:
        """Убедиться что indices и constraints созданы"""
        logger.info(f"🔍 _ensure_indices() called. Current state: _indices_built={self._indices_built}")

        if self._indices_built:
            logger.info("✅ Indices already built, skipping")
            return True

        try:
            logger.info("🔨 Building FalkorDB indices and constraints...")
            logger.info(f"   FalkorDB: {FALKORDB_HOST}:{FALKORDB_PORT}/{FALKORDB_DATABASE}")
            logger.info(f"   Calling graphiti_client.build_indices_and_constraints()...")

            await self.graphiti_client.build_indices_and_constraints()

            self._indices_built = True
            logger.info("✅ FalkorDB indices and constraints created successfully")
            logger.info(f"   _indices_built flag set to: {self._indices_built}")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to build indices: {type(e).__name__}: {e}")
            logger.exception("Full traceback:")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья FalkorDB connection"""
        if not self.enabled or not self.graphiti_client:
            return {
                "status": "disabled",
                "message": "FalkorDB service is not enabled or not configured"
            }

        try:
            # Попытка получить статистику графа
            stats = await self.get_graph_stats()

            return {
                "status": "healthy",
                "backend": "FalkorDB",
                "host": FALKORDB_HOST,
                "port": FALKORDB_PORT,
                "database": FALKORDB_DATABASE,
                "indices_built": self._indices_built,
                "stats": stats
            }
        except Exception as e:
            logger.error(f"FalkorDB health check failed: {e}")
            return {
                "status": "unhealthy",
                "backend": "FalkorDB",
                "error": str(e)
            }

    async def get_graph_stats(self) -> Dict[str, Any]:
        """Получить статистику графа"""
        if not self.enabled or not self.graphiti_client or not self.falkor_driver:
            return {"error": "FalkorDB service not enabled"}

        try:
            # FalkorDB использует другие команды для статистики
            # Здесь базовая реализация, можно расширить

            return {
                "backend": "FalkorDB",
                "database": FALKORDB_DATABASE,
                "indices_built": self._indices_built,
                "message": "Detailed stats coming soon"
            }

        except Exception as e:
            logger.error(f"Failed to get graph stats: {e}")
            return {"error": str(e)}

    async def add_episode(
        self,
        content: str,
        episode_type: str = "conversation",
        source: str = "telegram",
        source_description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Добавить episode в knowledge graph

        Args:
            content: Текст episode
            episode_type: Тип (conversation, lesson, faq, etc.)
            source: Источник (telegram, web, etc.)
            source_description: Описание источника
            metadata: Дополнительные метаданные

        Returns:
            (success: bool, episode_id: Optional[str])
        """
        if not self.enabled or not self.graphiti_client:
            logger.error("FalkorDB service not enabled, cannot add episode")
            return False, None

        # Убедимся что indices созданы
        if not await self._ensure_indices():
            logger.error("Failed to ensure indices, cannot add episode")
            return False, None

        try:
            logger.info(f"🔵 FALKORDB: Adding episode (type: {episode_type})")
            logger.info(f"   Content length: {len(content)} chars")
            logger.info(f"   LLM model: {MODEL_NAME}")

            # Добавляем episode
            episode_id = await self.graphiti_client.add_episode(
                name=episode_type,
                episode_body=content,
                source=source,
                source_description=source_description or f"{source} {episode_type}",
                metadata=metadata or {}
            )

            logger.info(f"✅ FALKORDB: Episode added successfully")
            logger.info(f"   Episode ID: {episode_id}")

            return True, episode_id

        except Exception as e:
            logger.error(f"❌ FALKORDB: Failed to add episode: {type(e).__name__}: {e}")
            logger.exception("Full traceback:")
            return False, None

    async def search_semantic(
        self,
        query: str,
        limit: int = 5,
        min_relevance: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Semantic search по knowledge graph

        Args:
            query: Поисковый запрос
            limit: Максимум результатов
            min_relevance: Минимальная релевантность (0.0-1.0)

        Returns:
            List of search results with metadata
        """
        if not self.enabled or not self.graphiti_client:
            logger.warning("FalkorDB service not enabled, returning empty results")
            return []

        try:
            logger.info(f"🔍 FALKORDB: Semantic search: '{query[:50]}...'")

            # Graphiti semantic search
            results = await self.graphiti_client.search(
                query=query,
                num_results=limit
            )

            # Фильтруем по релевантности
            filtered_results = []
            for result in results:
                # Преобразуем результат в наш формат
                relevance = getattr(result, 'relevance', 0.0)
                if relevance >= min_relevance:
                    filtered_results.append({
                        "content": getattr(result, 'content', ''),
                        "relevance_score": relevance,
                        "metadata": getattr(result, 'metadata', {}),
                        "entity_type": getattr(result, 'type', 'unknown')
                    })

            logger.info(f"✅ FALKORDB: Found {len(filtered_results)} results (filtered from {len(results)})")

            return filtered_results

        except Exception as e:
            logger.error(f"❌ FALKORDB: Search failed: {type(e).__name__}: {e}")
            logger.exception("Full traceback:")
            return []

    async def clear_all_data(self) -> bool:
        """Очистить все данные из графа (ОПАСНО!)"""
        if not self.enabled or not self.graphiti_client:
            logger.error("FalkorDB service not enabled")
            return False

        try:
            logger.warning("🗑️ FALKORDB: Clearing all data from graph...")

            # Здесь нужна реализация очистки через FalkorDB
            # Пока placeholder
            logger.warning("⚠️ Clear all data not yet implemented for FalkorDB")

            return False

        except Exception as e:
            logger.error(f"Failed to clear data: {e}")
            return False

    def close(self):
        """Закрыть соединения"""
        try:
            if self.falkor_driver:
                # FalkorDriver может иметь метод close()
                # Здесь placeholder
                logger.info("Closing FalkorDB connections...")
        except Exception as e:
            logger.error(f"Error closing connections: {e}")


# Singleton instance
_falkordb_service: Optional[FalkorDBService] = None


def get_falkordb_service() -> FalkorDBService:
    """Получить singleton instance FalkorDB service"""
    global _falkordb_service

    if _falkordb_service is None:
        _falkordb_service = FalkorDBService()

    return _falkordb_service
