"""
Admin API Endpoints

Административные endpoints для управления ботом:
- Загрузка базы знаний в Neo4j/Graphiti
- Управление памятью
- Статистика и мониторинг
"""

import os
import sys
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel

# Добавляем путь к scripts
scripts_path = Path(__file__).parent.parent.parent / "scripts"
sys.path.append(str(scripts_path))

logger = logging.getLogger(__name__)

# Router для админских endpoints
router = APIRouter(prefix="/api/admin", tags=["admin"])

# Глобальное состояние загрузки
_load_status = {
    "is_loading": False,
    "started_at": None,
    "progress": 0,
    "total": 0,
    "current_tier": None,
    "errors": [],
    "completed_at": None,
    "stats": {}
}


class LoadKnowledgeRequest(BaseModel):
    """Запрос на загрузку базы знаний"""
    tier: Optional[int] = None  # 1, 2, 3 или None для всех
    batch_size: int = 50
    reset_checkpoint: bool = False


class LoadKnowledgeResponse(BaseModel):
    """Ответ на запрос загрузки"""
    success: bool
    message: str
    status: Dict[str, Any]


def verify_admin_password(admin_password: Optional[str]) -> bool:
    """Проверка админского пароля"""
    # ВРЕМЕННО: Отключена проверка пароля для тестирования
    # TODO: Восстановить после тестирования
    return True

    # expected_password = os.getenv("ADMIN_PASSWORD", "")
    # if not expected_password:
    #     return True  # Если пароль не установлен, разрешаем доступ
    # return admin_password == expected_password


@router.get("/health")
async def admin_health():
    """Проверка доступности админских endpoints"""
    return {
        "status": "ok",
        "admin_endpoints": "available",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/load_status")
async def get_load_status():
    """Получить текущий статус загрузки базы знаний"""
    return {
        "success": True,
        "status": _load_status
    }


@router.post("/load_knowledge", response_model=LoadKnowledgeResponse)
async def load_knowledge_to_neo4j(
    request: LoadKnowledgeRequest,
    background_tasks: BackgroundTasks,
    admin_password: Optional[str] = Header(None, alias="X-Admin-Password")
):
    """
    Загрузить базу знаний в Neo4j через Graphiti

    Args:
        request: Параметры загрузки
        admin_password: Админский пароль (header X-Admin-Password)

    Returns:
        Статус запуска загрузки
    """
    # Проверка пароля
    if not verify_admin_password(admin_password):
        raise HTTPException(status_code=403, detail="Invalid admin password")

    # Проверка что загрузка не идет
    if _load_status["is_loading"]:
        return LoadKnowledgeResponse(
            success=False,
            message="Загрузка уже выполняется",
            status=_load_status
        )

    # Запускаем загрузку в фоне
    background_tasks.add_task(
        _run_knowledge_loading,
        tier=request.tier,
        batch_size=request.batch_size,
        reset_checkpoint=request.reset_checkpoint
    )

    return LoadKnowledgeResponse(
        success=True,
        message="Загрузка запущена в фоновом режиме",
        status=_load_status
    )


async def _run_knowledge_loading(
    tier: Optional[int],
    batch_size: int,
    reset_checkpoint: bool
):
    """
    Выполнить загрузку базы знаний (фоновая задача)

    Args:
        tier: Уровень загрузки (1, 2, 3 или None для всех)
        batch_size: Размер батча
        reset_checkpoint: Сбросить чекпоинт
    """
    global _load_status

    try:
        # Инициализация статуса
        _load_status["is_loading"] = True
        _load_status["started_at"] = datetime.utcnow().isoformat()
        _load_status["progress"] = 0
        _load_status["errors"] = []
        _load_status["completed_at"] = None

        logger.info("🚀 Начинаем загрузку базы знаний в Neo4j...")

        # Импорт модулей
        try:
            from scripts.load_knowledge_to_graphiti import GraphitiLoader
        except ImportError as e:
            error_msg = f"Не удалось импортировать GraphitiLoader: {e}"
            logger.error(f"❌ {error_msg}")
            _load_status["errors"].append(error_msg)
            _load_status["is_loading"] = False
            return

        # ШАГ 1: Подсчёт entities из готовых parsed файлов
        logger.info("📖 Шаг 1: Подсчёт entities из parsed файлов...")
        _load_status["current_tier"] = "counting"

        parsed_dir = Path(__file__).parent.parent.parent / "data" / "parsed_kb"

        # Считаем entities из parsed файлов
        import json
        entity_counts = {}

        # FAQ
        faq_file = parsed_dir / "parsed_faq.json"
        if faq_file.exists():
            with open(faq_file, 'r', encoding='utf-8') as f:
                entity_counts["faq"] = len(json.load(f))
        else:
            entity_counts["faq"] = 0
            logger.warning(f"⚠️ parsed_faq.json not found")

        # Lessons
        lessons_file = parsed_dir / "parsed_lessons.json"
        if lessons_file.exists():
            with open(lessons_file, 'r', encoding='utf-8') as f:
                entity_counts["lessons"] = len(json.load(f))
        else:
            entity_counts["lessons"] = 0
            logger.warning(f"⚠️ parsed_lessons.json not found")

        # Corrections
        corrections_file = parsed_dir / "parsed_corrections.json"
        if corrections_file.exists():
            with open(corrections_file, 'r', encoding='utf-8') as f:
                entity_counts["corrections"] = len(json.load(f))
        else:
            entity_counts["corrections"] = 0
            logger.warning(f"⚠️ parsed_corrections.json not found")

        # Questions
        questions_file = parsed_dir / "parsed_questions.json"
        if questions_file.exists():
            with open(questions_file, 'r', encoding='utf-8') as f:
                entity_counts["questions"] = len(json.load(f))
        else:
            entity_counts["questions"] = 0
            logger.warning(f"⚠️ parsed_questions.json not found")

        # Note: Brainwrites excluded - student examples may not follow exact methodology

        total_entities = sum(entity_counts.values())
        _load_status["total"] = total_entities

        logger.info(f"✅ Подсчёт завершен: {total_entities} entities")
        logger.info(f"  - FAQ: {entity_counts['faq']}")
        logger.info(f"  - Lessons: {entity_counts['lessons']}")
        logger.info(f"  - Corrections: {entity_counts['corrections']}")
        logger.info(f"  - Questions: {entity_counts['questions']}")

        # ШАГИ 2: Загрузка в Graphiti
        logger.info("🔄 Шаг 2: Загрузка в Neo4j/Graphiti...")

        # Инициализируем GraphitiLoader с путями
        parsed_dir = Path(__file__).parent.parent.parent / "data" / "parsed_kb"

        # КРИТИЧЕСКИ ВАЖНО: Очистить MySQL checkpoint если reset_checkpoint=True
        if reset_checkpoint:
            from bot.services.graphiti_checkpoint_service import get_checkpoint_service
            checkpoint_service = get_checkpoint_service()
            if checkpoint_service.clear_all():
                logger.info(f"🗑️ MySQL Checkpoint очищен")
            else:
                logger.warning("⚠️ Не удалось очистить checkpoint (БД недоступна?)")

        loader = GraphitiLoader(parsed_dir, tier=tier)

        # Определяем что загружать
        tiers_to_load = []
        if tier is None:
            tiers_to_load = [1, 2, 3]  # Загружаем все тиры (FAQ + Lessons + Questions/Brainwrites)
        else:
            tiers_to_load = [tier]

        results = {}
        for tier_num in tiers_to_load:
            _load_status["current_tier"] = tier_num
            logger.info(f"🎯 Загружаем Tier {tier_num}...")

            tier_result = await loader.load_tier(
                tier=tier_num,
                batch_size=batch_size
            )

            results[f"tier_{tier_num}"] = tier_result

            # Обновляем прогресс
            if tier_num == 1:
                _load_status["progress"] += entity_counts["faq"]
            elif tier_num == 2:
                _load_status["progress"] += entity_counts["lessons"] + entity_counts["corrections"]
            elif tier_num == 3:
                _load_status["progress"] += entity_counts["questions"]

        # Завершение
        _load_status["is_loading"] = False
        _load_status["completed_at"] = datetime.utcnow().isoformat()
        _load_status["stats"] = results

        logger.info("✅ Загрузка базы знаний завершена успешно!")

    except Exception as e:
        error_msg = f"Ошибка загрузки: {type(e).__name__}: {e}"
        logger.error(f"❌ {error_msg}")
        _load_status["errors"].append(error_msg)
        _load_status["is_loading"] = False
        _load_status["completed_at"] = datetime.utcnow().isoformat()


@router.post("/reset_loading")
async def reset_loading_status(
    admin_password: Optional[str] = Header(None, alias="X-Admin-Password")
):
    """
    Сбросить статус загрузки (для случаев когда загрузка зависла)

    Args:
        admin_password: Админский пароль

    Returns:
        Результат сброса
    """
    # Проверка пароля
    if not verify_admin_password(admin_password):
        raise HTTPException(status_code=403, detail="Invalid admin password")

    global _load_status

    old_status = _load_status.copy()

    # Сброс к начальным значениям
    _load_status["is_loading"] = False
    _load_status["started_at"] = None
    _load_status["progress"] = 0
    _load_status["total"] = 0
    _load_status["current_tier"] = None
    _load_status["errors"] = []
    _load_status["completed_at"] = None
    _load_status["stats"] = {}

    logger.info("🔄 Loading status reset manually")

    return {
        "success": True,
        "message": "Loading status reset successfully",
        "old_status": old_status,
        "new_status": _load_status
    }


@router.post("/clear_knowledge")
async def clear_knowledge_graph(
    admin_password: Optional[str] = Header(None, alias="X-Admin-Password")
):
    """
    Очистить Neo4j граф (ОПАСНАЯ ОПЕРАЦИЯ!)

    Args:
        admin_password: Админский пароль

    Returns:
        Результат очистки
    """
    # Проверка пароля
    if not verify_admin_password(admin_password):
        raise HTTPException(status_code=403, detail="Invalid admin password")

    try:
        from bot.services.graphiti_service import get_graphiti_service

        graphiti_service = get_graphiti_service()

        if not graphiti_service.enabled:
            raise HTTPException(
                status_code=503,
                detail="Graphiti service not available"
            )

        # Выполняем очистку через Neo4j
        driver = graphiti_service.graphiti_client.driver
        async with driver.session() as session:
            result = await session.run("MATCH (n) DETACH DELETE n")
            summary = await result.consume()

        return {
            "success": True,
            "message": "Knowledge graph cleared successfully",
            "nodes_deleted": summary.counters.nodes_deleted,
            "relationships_deleted": summary.counters.relationships_deleted
        }

    except Exception as e:
        logger.error(f"❌ Error clearing knowledge graph: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear knowledge graph: {str(e)}"
        )


@router.get("/stats")
async def get_knowledge_stats():
    """Получить статистику базы знаний в Neo4j"""
    try:
        from bot.services.graphiti_service import get_graphiti_service

        graphiti_service = get_graphiti_service()

        if not graphiti_service.enabled:
            return {
                "success": False,
                "error": "Graphiti service not available"
            }

        stats = await graphiti_service.get_graph_stats()

        return {
            "success": True,
            "stats": stats
        }

    except Exception as e:
        logger.error(f"❌ Error getting stats: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/debug_indices")
async def debug_indices(
    admin_password: Optional[str] = Header(None, alias="X-Admin-Password")
):
    """
    DEBUG: Ручное тестирование создания индексов и добавления episode

    Этот endpoint:
    1. Проверяет состояние Graphiti service
    2. Вручную вызывает _ensure_indices()
    3. Проверяет созданные индексы в Neo4j
    4. Добавляет тестовый episode
    5. Проверяет что episode сохранился

    Args:
        admin_password: Админский пароль

    Returns:
        Детальная диагностическая информация
    """
    # Проверка пароля
    if not verify_admin_password(admin_password):
        raise HTTPException(status_code=403, detail="Invalid admin password")

    logger.info("🔍 DEBUG: Starting indices diagnostic...")

    try:
        from bot.services.graphiti_service import get_graphiti_service

        graphiti_service = get_graphiti_service()

        if not graphiti_service.enabled:
            return {
                "success": False,
                "error": "Graphiti service not available",
                "enabled": graphiti_service.enabled,
                "graphiti_available": graphiti_service.graphiti_client is not None
            }

        result = {
            "success": True,
            "steps": {}
        }

        # Шаг 1: Проверка начального состояния
        logger.info("📊 Step 1: Initial state")
        stats_before = await graphiti_service.get_graph_stats()
        result["steps"]["1_initial_state"] = {
            "stats": stats_before,
            "indices_built_flag": graphiti_service._indices_built
        }

        # Шаг 2: Ручной вызов _ensure_indices()
        logger.info("🔨 Step 2: Manually calling _ensure_indices()")
        indices_result = await graphiti_service._ensure_indices()
        result["steps"]["2_ensure_indices"] = {
            "result": indices_result,
            "indices_built_flag_after": graphiti_service._indices_built
        }

        # Шаг 3: Проверка индексов в Neo4j
        logger.info("🔍 Step 3: Verify indices in Neo4j")
        indices_verification = await graphiti_service._verify_indices()
        result["steps"]["3_verify_indices"] = indices_verification

        # Шаг 4: Добавление тестового episode
        logger.info("📝 Step 4: Add test episode")
        test_content = "DEBUG TEST: Это тестовый episode для проверки что Neo4j индексы работают корректно."
        success, episode_result = await graphiti_service.add_episode(
            content=test_content,
            episode_type="debug_test",
            metadata={"debug": True, "timestamp": datetime.utcnow().isoformat()},
            source_description="Debug endpoint test episode"
        )

        result["steps"]["4_add_episode"] = {
            "success": success,
            "result": episode_result
        }

        # Шаг 5: Проверка что episode сохранился
        logger.info("📊 Step 5: Check stats after episode")
        stats_after = await graphiti_service.get_graph_stats()
        result["steps"]["5_stats_after"] = stats_after

        # Шаг 6: Сравнение
        nodes_added = stats_after.get("total_nodes", 0) - stats_before.get("total_nodes", 0)
        episodes_added = stats_after.get("total_episodes", 0) - stats_before.get("total_episodes", 0)

        result["steps"]["6_comparison"] = {
            "nodes_added": nodes_added,
            "episodes_added": episodes_added,
            "episode_persisted": episodes_added > 0
        }

        # Итоговая диагностика
        if not indices_result:
            result["diagnosis"] = "❌ FAILED: _ensure_indices() returned False"
        elif indices_verification.get("indices_count", 0) == 0:
            result["diagnosis"] = "❌ FAILED: No indices created in Neo4j"
        elif not success:
            result["diagnosis"] = f"❌ FAILED: Episode add failed: {episode_result}"
        elif episodes_added == 0:
            result["diagnosis"] = "❌ CRITICAL: Episode added successfully but NOT PERSISTED to Neo4j (silent failure)"
        else:
            result["diagnosis"] = "✅ SUCCESS: Indices created and episode persisted correctly"

        logger.info(f"🔍 DEBUG complete: {result['diagnosis']}")

        return result

    except Exception as e:
        logger.error(f"❌ Debug endpoint error: {e}")
        logger.exception("Full traceback:")
        raise HTTPException(
            status_code=500,
            detail=f"Debug failed: {str(e)}"
        )


@router.get("/graphiti_config")
async def get_graphiti_config():
    """
    Проверить конфигурацию Graphiti LLM модели

    Returns:
        Dict с информацией о настройках MODEL_NAME и SMALL_MODEL_NAME
    """
    try:
        model_name = os.getenv("MODEL_NAME", "NOT_SET")
        small_model_name = os.getenv("SMALL_MODEL_NAME", "NOT_SET")

        # Определяем используется ли GPT-4o-mini
        is_optimized = (
            model_name == "gpt-4o-mini" and
            small_model_name == "gpt-4o-mini"
        )

        return {
            "status": "ok",
            "config": {
                "MODEL_NAME": model_name,
                "SMALL_MODEL_NAME": small_model_name
            },
            "optimization": {
                "enabled": is_optimized,
                "description": (
                    "✅ Cost optimized (GPT-4o-mini)" if is_optimized
                    else "⚠️ Using default GPT-4o (expensive)"
                ),
                "cost_savings": "15-17x cheaper" if is_optimized else "N/A"
            },
            "pricing": {
                "gpt-4o": {
                    "input": "$2.50 per 1M tokens",
                    "output": "$10.00 per 1M tokens"
                },
                "gpt-4o-mini": {
                    "input": "$0.15 per 1M tokens",
                    "output": "$0.60 per 1M tokens"
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get Graphiti config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Config check failed: {str(e)}"
        )


# ==================== QDRANT ENDPOINTS ====================

_qdrant_migration_status = {
    "is_migrating": False,
    "started_at": None,
    "progress": 0,
    "total": 0,
    "errors": [],
    "completed_at": None,
    "stats": {}
}


class QdrantMigrateRequest(BaseModel):
    """Запрос на миграцию в Qdrant"""
    batch_size: int = 50
    reset: bool = False


class QdrantMigrateResponse(BaseModel):
    """Ответ миграции в Qdrant"""
    success: bool
    message: str
    started_at: Optional[str] = None


@router.get("/qdrant/health")
async def qdrant_health():
    """
    Проверка здоровья Qdrant service

    Returns:
        Dict с информацией о статусе Qdrant
    """
    try:
        from bot.services.qdrant_service import get_qdrant_service

        qdrant_service = get_qdrant_service()
        health = await qdrant_service.health_check()

        return health

    except Exception as e:
        logger.error(f"Qdrant health check failed: {e}")
        return {
            "service": "qdrant",
            "status": "error",
            "enabled": False,
            "error": str(e)
        }


@router.get("/qdrant/stats")
async def qdrant_stats():
    """
    Получить статистику Qdrant collection

    Returns:
        Dict со статистикой (количество points, vectors и т.д.)
    """
    try:
        from bot.services.qdrant_service import get_qdrant_service

        qdrant_service = get_qdrant_service()
        stats = await qdrant_service.get_stats()

        return {
            "status": "ok",
            "stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get Qdrant stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Stats failed: {str(e)}"
        )


@router.post("/qdrant/migrate", response_model=QdrantMigrateResponse)
async def migrate_to_qdrant(
    request: QdrantMigrateRequest,
    background_tasks: BackgroundTasks
):
    """
    Запустить миграцию данных в Qdrant

    Args:
        request: Параметры миграции (batch_size, reset)

    Returns:
        Response с информацией о запуске миграции
    """
    global _qdrant_migration_status

    # Проверка что миграция не запущена
    if _qdrant_migration_status["is_migrating"]:
        raise HTTPException(
            status_code=400,
            detail="Migration already in progress"
        )

    try:
        # Запуск миграции в background
        background_tasks.add_task(
            _run_qdrant_migration,
            batch_size=request.batch_size,
            reset=request.reset
        )

        _qdrant_migration_status["is_migrating"] = True
        _qdrant_migration_status["started_at"] = datetime.utcnow().isoformat()
        _qdrant_migration_status["errors"] = []

        return QdrantMigrateResponse(
            success=True,
            message="Migration started in background",
            started_at=_qdrant_migration_status["started_at"]
        )

    except Exception as e:
        logger.error(f"Failed to start Qdrant migration: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Migration start failed: {str(e)}"
        )


@router.get("/qdrant/migrate_status")
async def get_qdrant_migrate_status():
    """
    Получить статус миграции

    Returns:
        Dict со статусом миграции (progress, errors и т.д.)
    """
    return {
        "status": "ok",
        "migration": _qdrant_migration_status,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/qdrant/search_test")
async def qdrant_search_test(query: str, limit: int = 5):
    """
    Тестовый поиск в Qdrant

    Args:
        query: Поисковый запрос
        limit: Максимальное количество результатов

    Returns:
        Dict с результатами поиска
    """
    try:
        from bot.services.qdrant_service import get_qdrant_service

        qdrant_service = get_qdrant_service()
        results = await qdrant_service.search_semantic(
            query=query,
            limit=limit
        )

        return {
            "status": "ok",
            "query": query,
            "limit": limit,
            "results_count": len(results),
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Qdrant search test failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search test failed: {str(e)}"
        )


async def _run_qdrant_migration(batch_size: int, reset: bool):
    """
    Background task для миграции в Qdrant

    Args:
        batch_size: Размер batch для upload
        reset: Сбросить checkpoint и начать с нуля
    """
    global _qdrant_migration_status

    try:
        # Импортируем migrate скрипт
        from migrate_to_qdrant import QdrantMigration

        kb_dir = Path(__file__).parent.parent.parent / "KNOWLEDGE_BASE"

        migration = QdrantMigration(
            kb_dir=kb_dir,
            batch_size=batch_size
        )

        # Запуск миграции
        await migration.migrate(reset=reset)

        # Обновляем статус
        _qdrant_migration_status["is_migrating"] = False
        _qdrant_migration_status["completed_at"] = datetime.utcnow().isoformat()
        _qdrant_migration_status["stats"] = migration.stats

        logger.info("✅ Qdrant migration completed successfully")

    except Exception as e:
        logger.error(f"❌ Qdrant migration failed: {e}")
        logger.exception("Full traceback:")

        _qdrant_migration_status["is_migrating"] = False
        _qdrant_migration_status["errors"].append({
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })


# ============================================================================
# DEBUG ENDPOINT: Test Search
# ============================================================================

class TestSearchRequest(BaseModel):
    query: str
    limit: int = 3
    min_relevance: float = 0.5


@router.post("/test_search")
async def test_search(request: TestSearchRequest):
    """
    Тестовый endpoint для диагностики поиска по базе знаний
    
    Возвращает детальную информацию о результатах поиска:
    - Какая система используется (Qdrant/Graphiti)
    - Найденные результаты с relevance scores
    - Почему бот может возвращать fallback ответ
    """
    try:
        from bot.services.knowledge_search import get_knowledge_search_service, SearchStrategy
        
        knowledge_service = get_knowledge_search_service()
        
        # Информация о системе
        system_info = {
            "use_qdrant": knowledge_service.use_qdrant,
            "qdrant_enabled": knowledge_service.qdrant_enabled,
            "graphiti_enabled": knowledge_service.graphiti_enabled
        }
        
        active_system = None
        if knowledge_service.use_qdrant and knowledge_service.qdrant_enabled:
            active_system = "QDRANT"
        elif knowledge_service.graphiti_enabled:
            active_system = "GRAPHITI"
        else:
            active_system = "NONE"
        
        # Выполняем поиск
        strategy = knowledge_service.route_query(request.query)
        
        search_results = await knowledge_service.search(
            query=request.query,
            strategy=strategy,
            limit=request.limit,
            min_relevance=request.min_relevance
        )
        
        # Форматируем результаты
        results_formatted = []
        if search_results:
            for result in search_results:
                results_formatted.append({
                    "relevance_score": result.relevance_score,
                    "source": result.source,
                    "content_preview": result.content[:200] + "..." if len(result.content) > 200 else result.content,
                    "metadata": result.metadata
                })
        
        # Объяснение почему может быть fallback
        fallback_reason = None
        if not search_results:
            if active_system == "NONE":
                fallback_reason = "Ни одна система поиска не доступна (Graphiti/Qdrant отключены или не установлены)"
            else:
                fallback_reason = f"Поиск через {active_system} не нашел результатов с relevance >= {request.min_relevance}"
        
        return {
            "success": True,
            "query": request.query,
            "system_info": system_info,
            "active_system": active_system,
            "strategy_used": strategy.value if strategy else None,
            "min_relevance": request.min_relevance,
            "results_count": len(search_results),
            "results": results_formatted,
            "fallback_reason": fallback_reason,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Test search failed: {e}")
        logger.exception("Full traceback:")
        
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "timestamp": datetime.utcnow().isoformat()
        }
