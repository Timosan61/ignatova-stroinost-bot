"""
SimpleFalkorDBService - Lightweight FalkorDB сервис без Graphiti
Прямые Cypher запросы к FalkorDB для максимальной совместимости
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from falkordb.asyncio import FalkorDB

from bot.config import (
    FALKORDB_HOST,
    FALKORDB_PORT,
    FALKORDB_USERNAME,
    FALKORDB_PASSWORD,
    FALKORDB_DATABASE
)

logger = logging.getLogger(__name__)


class SimpleFalkorDBService:
    """Простой сервис для работы с FalkorDB без Graphiti"""

    def __init__(self):
        """Инициализация FalkorDB service"""
        self.client: Optional[FalkorDB] = None
        self.graph = None
        self.enabled = False

        try:
            # Проверка credentials
            if not FALKORDB_HOST or not FALKORDB_PASSWORD:
                logger.error("FalkorDB credentials not configured")
                self.enabled = False
                return

            logger.info(f"Initializing SimpleFalkorDB: {FALKORDB_HOST}:{FALKORDB_PORT}")

            # Создаём FalkorDB клиент
            self.client = FalkorDB(
                host=FALKORDB_HOST,
                port=int(FALKORDB_PORT),
                password=FALKORDB_PASSWORD,
                username=FALKORDB_USERNAME,
                ssl=False  # Free tier не поддерживает TLS
            )

            # Выбираем граф
            self.graph = self.client.select_graph(FALKORDB_DATABASE)

            logger.info("✅ SimpleFalkorDB initialized successfully")
            self.enabled = True

        except Exception as e:
            logger.error(f"Failed to initialize SimpleFalkorDB: {e}")
            logger.exception("Full traceback:")
            self.enabled = False

    async def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья FalkorDB connection"""
        if not self.enabled or not self.client:
            return {
                "status": "disabled",
                "message": "SimpleFalkorDB service is not enabled"
            }

        try:
            # Простой запрос для проверки
            result = await self.graph.query("MATCH (n) RETURN COUNT(n) AS count LIMIT 1")
            count = result.result_set[0][0] if result.result_set else 0

            return {
                "status": "healthy",
                "backend": "FalkorDB (Simple)",
                "host": FALKORDB_HOST,
                "port": FALKORDB_PORT,
                "database": FALKORDB_DATABASE,
                "total_nodes": count
            }
        except Exception as e:
            logger.error(f"SimpleFalkorDB health check failed: {e}")
            return {
                "status": "unhealthy",
                "backend": "FalkorDB (Simple)",
                "error": str(e)
            }

    async def add_text(
        self,
        content: str,
        text_type: str = "knowledge",
        source: str = "telegram",
        metadata: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Добавить текст в граф

        Args:
            content: Текст
            text_type: Тип (knowledge, conversation, faq, etc.)
            source: Источник
            metadata: Метаданные

        Returns:
            (success: bool, node_id: Optional[str])
        """
        if not self.enabled or not self.graph:
            logger.error("SimpleFalkorDB not enabled")
            return False, None

        try:
            logger.info(f"🔵 SimpleFalkorDB: Adding text (type: {text_type})")

            # Создаём уникальный ID
            import uuid
            node_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat()

            # Простой Cypher запрос БЕЗ параметров (прямая подстановка)
            # Экранируем кавычки в content
            safe_content = content.replace("'", "\\'").replace('"', '\\"')
            safe_type = text_type.replace("'", "\\'")
            safe_source = source.replace("'", "\\'")

            cypher = f"""
            CREATE (n:Knowledge {{
                id: '{node_id}',
                content: '{safe_content}',
                type: '{safe_type}',
                source: '{safe_source}',
                created_at: '{timestamp}'
            }})
            RETURN n.id AS id
            """

            result = await self.graph.query(cypher)

            if result.result_set:
                created_id = result.result_set[0][0]
                logger.info(f"✅ SimpleFalkorDB: Text added (ID: {created_id})")
                return True, created_id
            else:
                logger.error("No result from CREATE query")
                return False, None

        except Exception as e:
            logger.error(f"❌ SimpleFalkorDB: Failed to add text: {e}")
            logger.exception("Full traceback:")
            return False, None

    async def search_fulltext(
        self,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Fulltext search по графу

        Args:
            query: Поисковый запрос
            limit: Максимум результатов

        Returns:
            List of search results
        """
        if not self.enabled or not self.graph:
            logger.warning("SimpleFalkorDB not enabled")
            return []

        try:
            logger.info(f"🔍 SimpleFalkorDB: Fulltext search: '{query[:50]}...'")

            # Экранируем query
            safe_query = query.replace("'", "\\'").replace('"', '\\"')

            # Fulltext search через toLower() CONTAINS (case-insensitive)
            cypher = f"""
            MATCH (n:Knowledge)
            WHERE toLower(n.content) CONTAINS toLower('{safe_query}')
            RETURN n.id AS id, n.content AS content, n.type AS type, n.source AS source, n.created_at AS created_at
            LIMIT {limit}
            """

            result = await self.graph.query(cypher)

            results = []
            for row in result.result_set:
                results.append({
                    "id": row[0],
                    "content": row[1],
                    "type": row[2],
                    "source": row[3],
                    "created_at": row[4],
                    "relevance_score": 0.8  # Примерная релевантность
                })

            logger.info(f"✅ SimpleFalkorDB: Found {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"❌ SimpleFalkorDB: Search failed: {e}")
            logger.exception("Full traceback:")
            return []

    async def get_stats(self) -> Dict[str, Any]:
        """Получить статистику графа"""
        if not self.enabled or not self.graph:
            return {"error": "SimpleFalkorDB not enabled"}

        try:
            # Подсчёт всех nodes
            result = await self.graph.query("MATCH (n) RETURN COUNT(n) AS count")
            total_nodes = result.result_set[0][0] if result.result_set else 0

            # Подсчёт по типам
            result = await self.graph.query("""
                MATCH (n:Knowledge)
                RETURN n.type AS type, COUNT(n) AS count
            """)

            by_type = {}
            for row in result.result_set:
                by_type[row[0]] = row[1]

            return {
                "backend": "FalkorDB (Simple)",
                "database": FALKORDB_DATABASE,
                "total_nodes": total_nodes,
                "by_type": by_type
            }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}

    def close(self):
        """Закрыть соединения"""
        try:
            if self.client:
                logger.info("Closing SimpleFalkorDB connections...")
                # FalkorDB client может не иметь close()
                self.client = None
        except Exception as e:
            logger.error(f"Error closing connections: {e}")


# Singleton instance
_simple_falkordb_service: Optional[SimpleFalkorDBService] = None


def get_simple_falkordb_service() -> SimpleFalkorDBService:
    """Получить singleton instance SimpleFalkorDB service"""
    global _simple_falkordb_service

    if _simple_falkordb_service is None:
        _simple_falkordb_service = SimpleFalkorDBService()

    return _simple_falkordb_service
