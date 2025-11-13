"""
Graphiti Knowledge Graph Service

Сервис для работы с Graphiti knowledge graph на базе Neo4j.
Обеспечивает семантический поиск, graph traversal и temporal reasoning
по базе знаний курса "Всепрощающая".

Architecture:
- Graphiti: Temporal knowledge graph framework
- Neo4j: Graph database backend
- OpenAI Embeddings: Векторизация для semantic search
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio

try:
    from graphiti_core import Graphiti
    from graphiti_core.nodes import EpisodeType
    from neo4j import GraphDatabase, AsyncGraphDatabase
    GRAPHITI_AVAILABLE = True
except ImportError:
    GRAPHITI_AVAILABLE = False
    logging.warning("Graphiti or Neo4j not installed. Knowledge graph features disabled.")

from bot.config import (
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
    OPENAI_API_KEY,
    GRAPHITI_ENABLED
)

logger = logging.getLogger(__name__)


class GraphitiService:
    """
    Сервис для работы с Graphiti knowledge graph

    Features:
    - Semantic search (векторный поиск по embeddings)
    - Full-text search (BM25 algorithm)
    - Graph traversal (поиск по relationships)
    - Hybrid search (комбинация всех методов)
    - Temporal reasoning (когда информация была добавлена/актуальна)
    """

    def __init__(self):
        """Инициализация Graphiti client"""
        self.enabled = GRAPHITI_ENABLED and GRAPHITI_AVAILABLE
        self.graphiti_client = None
        self.neo4j_driver = None

        if not self.enabled:
            logger.warning("Graphiti service disabled (check GRAPHITI_ENABLED and dependencies)")
            return

        try:
            # Инициализация Neo4j driver для прямых запросов
            if NEO4J_URI and NEO4J_USER and NEO4J_PASSWORD:
                self.neo4j_driver = GraphDatabase.driver(
                    NEO4J_URI,
                    auth=(NEO4J_USER, NEO4J_PASSWORD)
                )
                logger.info(f"Neo4j driver initialized: {NEO4J_URI}")
            else:
                logger.error("Neo4j credentials not configured")
                self.enabled = False
                return

            # Инициализация Graphiti client
            self.graphiti_client = Graphiti(
                neo4j_uri=NEO4J_URI,
                neo4j_user=NEO4J_USER,
                neo4j_password=NEO4J_PASSWORD,
                openai_api_key=OPENAI_API_KEY
            )
            logger.info("Graphiti client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Graphiti service: {e}")
            self.enabled = False

    async def health_check(self) -> Dict[str, Any]:
        """
        Проверка состояния Graphiti service и Neo4j

        Returns:
            Dict с информацией о статусе подключения и статистике
        """
        if not self.enabled:
            return {
                "status": "disabled",
                "graphiti_available": GRAPHITI_AVAILABLE,
                "enabled": GRAPHITI_ENABLED
            }

        try:
            # Проверка Neo4j подключения
            with self.neo4j_driver.session() as session:
                result = session.run("RETURN 1 AS num")
                neo4j_connected = result.single()["num"] == 1

            # Статистика графа
            stats = await self.get_graph_stats()

            return {
                "status": "healthy",
                "neo4j_connected": neo4j_connected,
                "neo4j_uri": NEO4J_URI,
                **stats
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def get_graph_stats(self) -> Dict[str, int]:
        """
        Получить статистику knowledge graph

        Returns:
            Dict с количеством nodes, relationships, episodes
        """
        if not self.enabled:
            return {}

        try:
            with self.neo4j_driver.session() as session:
                # Количество nodes
                node_count = session.run("MATCH (n) RETURN count(n) AS count").single()["count"]

                # Количество relationships
                rel_count = session.run("MATCH ()-[r]->() RETURN count(r) AS count").single()["count"]

                # Количество episodes (если есть соответствующий label)
                episode_count = session.run(
                    "MATCH (n:Episode) RETURN count(n) AS count"
                ).single()["count"]

                return {
                    "total_nodes": node_count,
                    "total_relationships": rel_count,
                    "total_episodes": episode_count
                }
        except Exception as e:
            logger.error(f"Failed to get graph stats: {e}")
            return {}

    async def add_episode(
        self,
        content: str,
        episode_type: str = "message",
        metadata: Optional[Dict[str, Any]] = None,
        source_description: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Добавить episode в knowledge graph

        Args:
            content: Текстовое содержание episode
            episode_type: Тип episode (message, document, lesson, etc.)
            metadata: Дополнительные метаданные
            source_description: Описание источника

        Returns:
            (success, episode_id or error_message)
        """
        if not self.enabled:
            return False, "Graphiti service disabled"

        try:
            result = await self.graphiti_client.add_episode(
                name=f"{episode_type}_{datetime.utcnow().isoformat()}",
                episode_body=content,
                source_description=source_description or f"Episode type: {episode_type}",
                reference_time=datetime.utcnow(),
                metadata=metadata or {}
            )

            logger.info(f"Episode added successfully: {result}")
            return True, str(result)

        except Exception as e:
            logger.error(f"Failed to add episode: {e}")
            return False, str(e)

    async def search_semantic(
        self,
        query: str,
        limit: int = 5,
        min_similarity: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Семантический поиск по knowledge graph

        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов
            min_similarity: Минимальный порог similarity (0-1)

        Returns:
            List результатов с content, metadata, similarity score
        """
        if not self.enabled:
            return []

        try:
            results = await self.graphiti_client.search(
                query=query,
                limit=limit
            )

            # Фильтрация по similarity threshold
            filtered_results = [
                {
                    "content": r.content,
                    "metadata": r.metadata,
                    "similarity": r.similarity,
                    "source": r.source_description
                }
                for r in results
                if r.similarity >= min_similarity
            ]

            logger.info(f"Semantic search '{query}': {len(filtered_results)} results")
            return filtered_results

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    async def search_hybrid(
        self,
        query: str,
        limit: int = 5,
        use_semantic: bool = True,
        use_fulltext: bool = True,
        use_graph: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Гибридный поиск (комбинация semantic + fulltext + graph)

        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов
            use_semantic: Использовать semantic search
            use_fulltext: Использовать full-text search
            use_graph: Использовать graph traversal

        Returns:
            List результатов с ranking
        """
        if not self.enabled:
            return []

        all_results = []

        try:
            # 1. Semantic search
            if use_semantic:
                semantic_results = await self.search_semantic(query, limit=limit)
                for r in semantic_results:
                    r["search_type"] = "semantic"
                    r["rank_score"] = r.get("similarity", 0.0) * 1.0  # вес semantic
                all_results.extend(semantic_results)

            # 2. Full-text search (через Cypher query)
            if use_fulltext:
                fulltext_results = await self._search_fulltext(query, limit=limit)
                for r in fulltext_results:
                    r["search_type"] = "fulltext"
                    r["rank_score"] = r.get("relevance", 0.0) * 0.8  # вес fulltext
                all_results.extend(fulltext_results)

            # 3. Graph traversal (если включено)
            if use_graph:
                graph_results = await self._search_graph(query, limit=limit)
                for r in graph_results:
                    r["search_type"] = "graph"
                    r["rank_score"] = r.get("path_score", 0.0) * 0.6  # вес graph
                all_results.extend(graph_results)

            # Deduplicate и сортировка по rank_score
            seen = set()
            unique_results = []
            for r in sorted(all_results, key=lambda x: x.get("rank_score", 0), reverse=True):
                content_hash = hash(r.get("content", ""))
                if content_hash not in seen:
                    seen.add(content_hash)
                    unique_results.append(r)

            logger.info(f"Hybrid search '{query}': {len(unique_results)} unique results")
            return unique_results[:limit]

        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return []

    async def _search_fulltext(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Full-text search через Neo4j Cypher

        TODO: Реализовать после создания fulltext index в Neo4j
        """
        # Placeholder - будет реализовано после настройки fulltext index
        return []

    async def _search_graph(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Graph traversal search (поиск по relationships)

        TODO: Реализовать после определения relationship types
        """
        # Placeholder - будет реализовано после загрузки данных
        return []

    async def get_related_episodes(
        self,
        episode_id: str,
        relationship_types: Optional[List[str]] = None,
        max_depth: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Получить связанные episodes через graph relationships

        Args:
            episode_id: ID episode для поиска связанных
            relationship_types: Типы relationships (None = все типы)
            max_depth: Максимальная глубина traversal

        Returns:
            List связанных episodes
        """
        if not self.enabled:
            return []

        try:
            # TODO: Реализовать graph traversal через Cypher
            logger.info(f"Getting related episodes for {episode_id}")
            return []

        except Exception as e:
            logger.error(f"Failed to get related episodes: {e}")
            return []

    def close(self):
        """Закрыть подключения"""
        if self.neo4j_driver:
            self.neo4j_driver.close()
            logger.info("Neo4j driver closed")


# Singleton instance
_graphiti_service = None

def get_graphiti_service() -> GraphitiService:
    """
    Получить singleton instance Graphiti service

    Returns:
        GraphitiService instance
    """
    global _graphiti_service
    if _graphiti_service is None:
        _graphiti_service = GraphitiService()
    return _graphiti_service
