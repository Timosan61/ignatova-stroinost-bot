"""
Knowledge Search Service

Гибридный поиск по базе знаний курса "Всепрощающая" используя:
- Graphiti semantic search (векторный поиск)
- Neo4j full-text search (keyword matching)
- Graph traversal (поиск по relationships)
- Fallback к локальным файлам если Graphiti недоступен

Architecture:
    User Query → Query Routing → Hybrid Search → Ranked Results → LLM Context
"""

import os
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from enum import Enum

from bot.services.falkordb_service import get_falkordb_service  # FalkorDB (496x faster than Neo4j!)
from bot.services.qdrant_service import get_qdrant_service
from bot.config import GRAPHITI_ENABLED, USE_QDRANT

logger = logging.getLogger(__name__)


class SearchStrategy(str, Enum):
    """Стратегии поиска"""
    SEMANTIC = "semantic"      # Векторный поиск (embeddings)
    FULLTEXT = "fulltext"      # Keyword matching (BM25)
    GRAPH = "graph"            # Graph traversal (relationships)
    HYBRID = "hybrid"          # Комбинация всех методов
    FALLBACK = "fallback"      # Локальные файлы (когда Graphiti недоступен)


class SearchResult:
    """Результат поиска"""

    def __init__(
        self,
        content: str,
        source: str,
        relevance_score: float,
        metadata: Optional[Dict[str, Any]] = None,
        search_type: str = "unknown"
    ):
        self.content = content
        self.source = source
        self.relevance_score = relevance_score
        self.metadata = metadata or {}
        self.search_type = search_type

    def to_dict(self) -> Dict[str, Any]:
        """Конвертировать в dict"""
        return {
            "content": self.content,
            "source": self.source,
            "relevance_score": self.relevance_score,
            "metadata": self.metadata,
            "search_type": self.search_type
        }

    def __repr__(self):
        return f"SearchResult(source={self.source}, score={self.relevance_score:.2f}, type={self.search_type})"


class KnowledgeSearchService:
    """
    Сервис гибридного поиска по базе знаний

    Features:
    - Automatic query routing (определение оптимальной стратегии)
    - Hybrid search (semantic + fulltext + graph)
    - Result ranking and deduplication
    - Fallback to local files
    - Context formatting for LLM
    """

    def __init__(self):
        # Инициализация обеих систем
        self.falkordb_service = get_falkordb_service()  # FalkorDB (496x faster!)
        self.qdrant_service = get_qdrant_service()

        # Определение какую систему использовать
        self.use_qdrant = USE_QDRANT
        self.graphiti_enabled = GRAPHITI_ENABLED and self.falkordb_service.enabled
        self.qdrant_enabled = USE_QDRANT and self.qdrant_service.enabled

        # Paths для fallback
        self.kb_dir = Path(__file__).parent.parent.parent / "KNOWLEDGE_BASE"

        # Логирование активной системы
        if self.use_qdrant and self.qdrant_enabled:
            logger.info("🔵 KnowledgeSearchService initialized (Using: QDRANT)")
        elif self.graphiti_enabled:
            logger.info("🟢 KnowledgeSearchService initialized (Using: GRAPHITI)")
        else:
            logger.info("⚪ KnowledgeSearchService initialized (Using: FALLBACK - local files)")

    async def search(
        self,
        query: str,
        strategy: SearchStrategy = SearchStrategy.HYBRID,
        limit: int = 5,
        min_relevance: float = 0.6
    ) -> List[SearchResult]:
        """
        Поиск по базе знаний

        Args:
            query: Поисковый запрос
            strategy: Стратегия поиска
            limit: Максимальное количество результатов
            min_relevance: Минимальный порог relevance (0-1)

        Returns:
            List of SearchResult sorted by relevance
        """
        logger.info(f"Search query: '{query}' (strategy: {strategy}, limit: {limit})")

        # Определить какую систему использовать
        if self.use_qdrant and self.qdrant_enabled:
            # Использовать Qdrant
            logger.info("🔵 Using Qdrant for search")
            if strategy == SearchStrategy.GRAPH:
                # Qdrant не поддерживает graph traversal - fallback на semantic
                logger.warning("Qdrant doesn't support graph traversal, using semantic search instead")
                strategy = SearchStrategy.SEMANTIC
        elif self.graphiti_enabled:
            # Использовать Graphiti
            logger.info("🟢 Using Graphiti for search")
        else:
            # Fallback к локальным файлам
            logger.warning("Both Qdrant and Graphiti disabled, using fallback to local files")
            return await self._search_fallback(query, limit)

        # Выполнить поиск по стратегии
        if strategy == SearchStrategy.SEMANTIC:
            results = await self._search_semantic(query, limit, min_relevance)
        elif strategy == SearchStrategy.FULLTEXT:
            results = await self._search_fulltext(query, limit, min_relevance)
        elif strategy == SearchStrategy.GRAPH:
            results = await self._search_graph(query, limit, min_relevance)
        elif strategy == SearchStrategy.HYBRID:
            results = await self._search_hybrid(query, limit, min_relevance)
        else:
            logger.error(f"Unknown strategy: {strategy}")
            results = []

        logger.info(f"Search returned {len(results)} results")
        return results

    async def _search_semantic(
        self,
        query: str,
        limit: int,
        min_relevance: float
    ) -> List[SearchResult]:
        """
        Семантический поиск через Qdrant или Graphiti

        Приоритизация entity types для мозгоритмов:
        1. Lessons (boost 1.5x) - методология мозгоритмов
        2. Corrections (boost 1.2x) - стиль и примеры фраз
        3. FAQ - ответы на вопросы
        4. Brainwrites ИСКЛЮЧЕНЫ из основного поиска (могут содержать ошибки)
        """
        try:
            # Переключение между Qdrant и Graphiti
            if self.use_qdrant and self.qdrant_enabled:
                # Многоступенчатый поиск с приоритизацией
                all_results = []

                # ЭТАП 1: Поиск в УРОКАХ (highest priority)
                logger.info(f"🔍 Этап 1: Поиск в уроках (lessons)...")
                lesson_results = await self.qdrant_service.search_semantic(
                    query=query,
                    limit=limit,
                    score_threshold=min_relevance,
                    entity_type="lesson"  # Фильтр по типу!
                )

                for r in lesson_results:
                    # Score boost для уроков
                    boosted_score = r.get("score", 0.0) * 1.5
                    metadata = {**r.get("metadata", {}), "entity_type": r.get("entity_type", "lesson")}
                    result = SearchResult(
                        content=r.get("content", ""),
                        source=f"qdrant_{r.get('entity_type', 'lesson')}",
                        relevance_score=boosted_score,
                        metadata=metadata,
                        search_type="semantic_qdrant_prioritized"
                    )
                    all_results.append(result)

                logger.info(f"  ✅ Найдено {len(lesson_results)} lessons (boosted score 1.5x)")

                # ЭТАП 2: Поиск в КОРРЕКТИРОВКАХ КУРАТОРА (medium priority)
                logger.info(f"🔍 Этап 2: Поиск в корректировках куратора (corrections)...")
                correction_results = await self.qdrant_service.search_semantic(
                    query=query,
                    limit=limit,
                    score_threshold=min_relevance,
                    entity_type="correction"
                )

                for r in correction_results:
                    # Score boost для корректировок
                    boosted_score = r.get("score", 0.0) * 1.2
                    metadata = {**r.get("metadata", {}), "entity_type": r.get("entity_type", "correction")}
                    result = SearchResult(
                        content=r.get("content", ""),
                        source=f"qdrant_{r.get('entity_type', 'correction')}",
                        relevance_score=boosted_score,
                        metadata=metadata,
                        search_type="semantic_qdrant_prioritized"
                    )
                    all_results.append(result)

                logger.info(f"  ✅ Найдено {len(correction_results)} corrections (boosted score 1.2x)")

                # ЭТАП 3: Поиск в FAQ (если недостаточно уроков и корректировок)
                if len(all_results) < limit:
                    logger.info(f"🔍 Этап 3: Поиск в FAQ...")
                    faq_results = await self.qdrant_service.search_semantic(
                        query=query,
                        limit=limit - len(all_results),
                        score_threshold=min_relevance,
                        entity_type="faq"
                    )

                    for r in faq_results:
                        metadata = {**r.get("metadata", {}), "entity_type": r.get("entity_type", "faq")}
                        result = SearchResult(
                            content=r.get("content", ""),
                            source=f"qdrant_{r.get('entity_type', 'faq')}",
                            relevance_score=r.get("score", 0.0),
                            metadata=metadata,
                            search_type="semantic_qdrant_prioritized"
                        )
                        all_results.append(result)

                    logger.info(f"  ✅ Найдено {len(faq_results)} FAQ")

                # NOTE: Brainwrites ИСКЛЮЧЕНЫ из основного поиска!
                # Они используются ТОЛЬКО если явно запрошены отдельным методом
                logger.info(f"⚠️ Brainwrites исключены из основного поиска (могут содержать ошибки)")

                # Сортируем по boosted relevance score
                all_results.sort(key=lambda x: x.relevance_score, reverse=True)

                # Возвращаем top N результатов
                final_results = all_results[:limit]
                logger.info(f"📊 Итого найдено: {len(final_results)} результатов (lessons: {len(lesson_results)}, corrections: {len(correction_results)})")

                return final_results

            else:
                # Поиск через FalkorDB (Graphiti backend)
                graphiti_results = await self.falkordb_service.search_semantic(
                    query=query,
                    limit=limit,
                    min_relevance=min_relevance  # Note: параметр переименован
                )

                results = []
                for r in graphiti_results:
                    result = SearchResult(
                        content=r.get("content", ""),
                        source=r.get("source", "knowledge_base"),
                        relevance_score=r.get("similarity", 0.0),
                        metadata=r.get("metadata", {}),
                        search_type="semantic_graphiti"
                    )
                    results.append(result)

                return results

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            logger.exception("Full traceback:")
            return []

    async def _search_fulltext(
        self,
        query: str,
        limit: int,
        min_relevance: float
    ) -> List[SearchResult]:
        """Full-text search через Neo4j"""
        # TODO: Реализовать после создания fulltext index в Neo4j
        logger.warning("Fulltext search not implemented yet")
        return []

    async def _search_graph(
        self,
        query: str,
        limit: int,
        min_relevance: float
    ) -> List[SearchResult]:
        """Graph traversal search"""
        # TODO: Реализовать после загрузки relationships
        logger.warning("Graph search not implemented yet")
        return []

    async def _search_hybrid(
        self,
        query: str,
        limit: int,
        min_relevance: float
    ) -> List[SearchResult]:
        """
        Гибридный поиск (комбинация semantic + fulltext + graph)

        Для Qdrant: multi-stage search с entity_type приоритизацией
        - Приоритизация: lessons (1.5x) > corrections (1.2x) > FAQ (1.0x)
        - Brainwrites и questions ИСКЛЮЧЕНЫ из основного поиска

        Для Graphiti: комбинация semantic + fulltext + graph

        Веса:
        - Semantic: 1.0 (высший приоритет)
        - Fulltext: 0.8
        - Graph: 0.6
        """
        # Переключение между Qdrant и Graphiti
        if self.use_qdrant and self.qdrant_enabled:
            # Qdrant multi-stage search с приоритизацией
            try:
                all_results = []

                # ЭТАП 1: Поиск в УРОКАХ (highest priority)
                logger.info(f"🔍 Hybrid: Этап 1 - Поиск в уроках (lessons)...")
                lesson_results = await self.qdrant_service.search_semantic(
                    query=query,
                    limit=limit,
                    score_threshold=min_relevance,
                    entity_type="lesson"
                )

                for r in lesson_results:
                    boosted_score = r.get("score", 0.0) * 1.5
                    metadata = {**r.get("metadata", {}), "entity_type": r.get("entity_type", "lesson")}
                    result = SearchResult(
                        content=r.get("content", ""),
                        source=f"qdrant_{r.get('entity_type', 'lesson')}",
                        relevance_score=boosted_score,
                        metadata=metadata,
                        search_type="hybrid_qdrant_prioritized"
                    )
                    all_results.append(result)

                logger.info(f"  ✅ Найдено {len(lesson_results)} lessons (boosted 1.5x)")

                # ЭТАП 2: Поиск в КОРРЕКТИРОВКАХ КУРАТОРА (medium priority)
                logger.info(f"🔍 Hybrid: Этап 2 - Поиск в корректировках (corrections)...")
                correction_results = await self.qdrant_service.search_semantic(
                    query=query,
                    limit=limit,
                    score_threshold=min_relevance,
                    entity_type="correction"
                )

                for r in correction_results:
                    boosted_score = r.get("score", 0.0) * 1.2
                    metadata = {**r.get("metadata", {}), "entity_type": r.get("entity_type", "correction")}
                    result = SearchResult(
                        content=r.get("content", ""),
                        source=f"qdrant_{r.get('entity_type', 'correction')}",
                        relevance_score=boosted_score,
                        metadata=metadata,
                        search_type="hybrid_qdrant_prioritized"
                    )
                    all_results.append(result)

                logger.info(f"  ✅ Найдено {len(correction_results)} corrections (boosted 1.2x)")

                # ЭТАП 3: Поиск в FAQ (если ещё нужно результатов)
                if len(all_results) < limit:
                    logger.info(f"🔍 Hybrid: Этап 3 - Поиск в FAQ...")
                    faq_results = await self.qdrant_service.search_semantic(
                        query=query,
                        limit=limit - len(all_results),
                        score_threshold=min_relevance,
                        entity_type="faq"
                    )

                    for r in faq_results:
                        metadata = {**r.get("metadata", {}), "entity_type": r.get("entity_type", "faq")}
                        result = SearchResult(
                            content=r.get("content", ""),
                            source=f"qdrant_{r.get('entity_type', 'faq')}",
                            relevance_score=r.get("score", 0.0),
                            metadata=metadata,
                            search_type="hybrid_qdrant_prioritized"
                        )
                        all_results.append(result)

                    logger.info(f"  ✅ Найдено {len(faq_results)} FAQ")

                # NOTE: Brainwrites и questions ИСКЛЮЧЕНЫ из основного поиска!
                logger.info(f"⚠️ Hybrid: Brainwrites и questions исключены (могут содержать ошибки)")

                # Сортировка по relevance score (уже с учётом boost)
                all_results.sort(key=lambda x: x.relevance_score, reverse=True)

                return all_results[:limit]

            except Exception as e:
                logger.error(f"Qdrant hybrid search failed: {e}")
                return []

        else:
            # Graphiti hybrid search (semantic + fulltext + graph)
            all_results = []

            # 1. Semantic search
            semantic_results = await self._search_semantic(query, limit * 2, min_relevance)
            for r in semantic_results:
                r.relevance_score *= 1.0  # Вес semantic
            all_results.extend(semantic_results)

            # 2. Fulltext search (когда реализуется для Graphiti)
            # fulltext_results = await self._search_fulltext(query, limit, min_relevance)
            # for r in fulltext_results:
            #     r.relevance_score *= 0.8
            # all_results.extend(fulltext_results)

            # 3. Graph search (когда реализуется для Graphiti)
            # graph_results = await self._search_graph(query, limit, min_relevance)
            # for r in graph_results:
            #     r.relevance_score *= 0.6
            # all_results.extend(graph_results)

            # Deduplicate (по content hash)
            unique_results = self._deduplicate_results(all_results)

            # Sort by relevance
            unique_results.sort(key=lambda x: x.relevance_score, reverse=True)

            return unique_results[:limit]

    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Удалить дубликаты результатов"""
        seen = set()
        unique = []

        for result in results:
            content_hash = hash(result.content[:200])  # Первые 200 символов
            if content_hash not in seen:
                seen.add(content_hash)
                unique.append(result)

        return unique

    async def _search_fallback(self, query: str, limit: int) -> List[SearchResult]:
        """
        Fallback поиск по локальным файлам (когда Graphiti недоступен)

        Простой keyword matching в markdown файлах
        """
        logger.info("Using fallback search (local files)")
        results = []

        # Поиск в FAQ
        faq_file = self.kb_dir / "FAQ_EXTENDED.md"
        if faq_file.exists():
            faq_results = self._search_in_file(faq_file, query, "FAQ")
            results.extend(faq_results[:limit // 2])

        # Поиск в уроках
        lessons_file = self.kb_dir / "KNOWLEDGE_BASE_FULL.md"
        if lessons_file.exists():
            lesson_results = self._search_in_file(lessons_file, query, "Lessons")
            results.extend(lesson_results[:limit // 2])

        # Sort by relevance
        results.sort(key=lambda x: x.relevance_score, reverse=True)

        return results[:limit]

    def _search_in_file(
        self,
        file_path: Path,
        query: str,
        source: str
    ) -> List[SearchResult]:
        """
        Простой keyword поиск в файле

        Args:
            file_path: Путь к файлу
            query: Поисковый запрос
            source: Источник (для metadata)

        Returns:
            List of SearchResult
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Разбить на секции (по заголовкам ##)
            sections = re.split(r'\n## ', content)

            results = []
            query_lower = query.lower()
            query_words = set(query_lower.split())

            for section in sections:
                section_lower = section.lower()

                # Подсчитать совпадения ключевых слов
                matches = sum(1 for word in query_words if word in section_lower)

                if matches > 0:
                    # Relevance = matches / total query words
                    relevance = matches / len(query_words) if query_words else 0

                    # Извлечь заголовок секции
                    section_title = section.split('\n')[0] if section else "Unknown"

                    # Ограничить размер content
                    section_content = section[:1500] + "..." if len(section) > 1500 else section

                    result = SearchResult(
                        content=section_content,
                        source=f"{source}: {section_title}",
                        relevance_score=relevance,
                        metadata={"file": str(file_path.name)},
                        search_type="fallback"
                    )
                    results.append(result)

            # Sort by relevance
            results.sort(key=lambda x: x.relevance_score, reverse=True)

            return results

        except Exception as e:
            logger.error(f"Failed to search in {file_path}: {e}")
            return []

    def route_query(self, query: str) -> SearchStrategy:
        """
        Определить оптимальную стратегию поиска для запроса

        Rules:
        - "урок N" или "lesson N" → FULLTEXT (точное совпадение)
        - "что такое", "как понять" → SEMANTIC (концептуальный поиск)
        - "похожие примеры", "связанные техники" → GRAPH (relationships)
        - Default → HYBRID (комбинация всех методов)

        Args:
            query: Поисковый запрос

        Returns:
            Рекомендуемая SearchStrategy
        """
        query_lower = query.lower()

        # Точные номера уроков
        if re.search(r'урок\s+\d+|lesson\s+\d+', query_lower):
            logger.info(f"🎯 Выбрана стратегия FULLTEXT (найден паттерн 'урок N' в запросе)")
            return SearchStrategy.FULLTEXT

        # Концептуальные вопросы
        if any(word in query_lower for word in ["что такое", "как понять", "объясни", "в чем смысл"]):
            logger.info(f"🎯 Выбрана стратегия SEMANTIC (концептуальный вопрос)")
            return SearchStrategy.SEMANTIC

        # Поиск связей
        if any(word in query_lower for word in ["похожие", "связанные", "смежные", "related"]):
            logger.info(f"🎯 Выбрана стратегия GRAPH (поиск связей)")
            return SearchStrategy.GRAPH

        # Default: hybrid
        logger.info(f"🎯 Выбрана стратегия HYBRID (default - комбинированный поиск)")
        return SearchStrategy.HYBRID

    def format_context_for_llm(
        self,
        results: List[SearchResult],
        max_length: int = 3000
    ) -> str:
        """
        Форматировать результаты поиска в контекст для LLM

        Args:
            results: Результаты поиска
            max_length: Максимальная длина контекста (в символах)

        Returns:
            Formatted context string
        """
        if not results:
            return "Релевантная информация не найдена в базе знаний."

        context_parts = ["Найденная информация из базы знаний:\n"]
        current_length = len(context_parts[0])

        for i, result in enumerate(results, 1):
            # Заголовок результата
            header = f"\n📚 Источник {i}: {result.source} (relevance: {result.relevance_score:.2f})\n"

            # Контент (ограничить если нужно)
            content = result.content

            # Проверить лимит
            if current_length + len(header) + len(content) > max_length:
                # Обрезать последний результат
                remaining = max_length - current_length - len(header)
                if remaining > 100:
                    content = content[:remaining] + "..."
                    context_parts.append(header + content)
                break
            else:
                context_parts.append(header + content)
                current_length += len(header) + len(content)

        return "\n".join(context_parts)


# Singleton instance
_knowledge_search_service = None

def get_knowledge_search_service() -> KnowledgeSearchService:
    """
    Получить singleton instance Knowledge Search Service

    Returns:
        KnowledgeSearchService instance
    """
    global _knowledge_search_service
    if _knowledge_search_service is None:
        _knowledge_search_service = KnowledgeSearchService()
    return _knowledge_search_service
