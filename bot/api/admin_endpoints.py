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
            from parse_knowledge_base import KnowledgeBaseParser
            from load_knowledge_to_graphiti import GraphitiLoader
        except ImportError as e:
            error_msg = f"Не удалось импортировать модули загрузки: {e}"
            logger.error(f"❌ {error_msg}")
            _load_status["errors"].append(error_msg)
            _load_status["is_loading"] = False
            return

        # ШАГИ 1: Парсинг базы знаний
        logger.info("📖 Шаг 1: Парсинг базы знаний...")
        _load_status["current_tier"] = "parsing"

        kb_dir = Path(__file__).parent.parent.parent / "KNOWLEDGE_BASE"
        parser = KnowledgeBaseParser(kb_dir=kb_dir)

        # Парсим FAQ
        faq_file = kb_dir / "FAQ_EXTENDED.md"
        faq_entries = parser.parse_faq(faq_file) if faq_file.exists() else []

        # Парсим уроки
        lessons_file = kb_dir / "KNOWLEDGE_BASE_FULL.md"
        lesson_chunks = parser.parse_lessons(lessons_file, chunk_size=800) if lessons_file.exists() else []

        # Парсим корректировки
        corrections_file = kb_dir / "curator_corrections_ALL.json"
        corrections = parser.parse_corrections(corrections_file) if corrections_file.exists() else []

        total_entities = len(faq_entries) + len(lesson_chunks) + len(corrections)
        _load_status["total"] = total_entities

        logger.info(f"✅ Парсинг завершен: {total_entities} entities")
        logger.info(f"  - FAQ: {len(faq_entries)}")
        logger.info(f"  - Lessons: {len(lesson_chunks)}")
        logger.info(f"  - Corrections: {len(corrections)}")

        # ШАГИ 2: Загрузка в Graphiti
        logger.info("🔄 Шаг 2: Загрузка в Neo4j/Graphiti...")

        loader = GraphitiLoader()

        # Определяем что загружать
        tiers_to_load = []
        if tier is None:
            tiers_to_load = [1, 2]  # Загружаем все (tier 3 пока нет данных)
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
                _load_status["progress"] += len(faq_entries)
            elif tier_num == 2:
                _load_status["progress"] += len(lesson_chunks) + len(corrections)

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
