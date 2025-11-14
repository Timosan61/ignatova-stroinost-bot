#!/usr/bin/env python3
"""
Graphiti Knowledge Loader

Загрузка parsed knowledge base entities в Neo4j через Graphiti.

Features:
- Batch loading с прогрессом (tqdm)
- Checkpoints для возобновления
- Error handling и retry logic
- Приоритетная загрузка (Tier 1 → Tier 3)
- Статистика загрузки

Usage:
    python scripts/load_knowledge_to_graphiti.py [--tier 1|2|3] [--batch-size 50]
"""

import os
import sys
import json
import asyncio
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

try:
    from tqdm import tqdm
except ImportError:
    print("⚠️ tqdm not installed. Install: pip install tqdm")
    sys.exit(1)

try:
    from neo4j.exceptions import ServiceUnavailable, ClientError
except ImportError:
    # Fallback если neo4j не установлен (не должно произойти)
    ServiceUnavailable = Exception
    ClientError = Exception

# Add root to PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from bot.services.graphiti_service import get_graphiti_service
from bot.services.graphiti_checkpoint_service import get_checkpoint_service
from bot.models.knowledge_entities import (
    FAQEntry,
    CourseLesson,
    CuratorCorrection,
    StudentQuestion,
    create_episode_metadata
)

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class GraphitiLoader:
    """Загрузчик базы знаний в Graphiti с MySQL checkpoint"""

    def __init__(self, parsed_dir: Path, tier: Optional[int] = None, batch_number: int = 0):
        self.parsed_dir = parsed_dir
        self.tier = tier
        self.batch_number = batch_number
        self.graphiti_service = get_graphiti_service()
        self.checkpoint_service = get_checkpoint_service()

        self.stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0
        }

        # Загрузить checkpoint statistics из MySQL
        checkpoint_stats = self.checkpoint_service.get_stats()
        logger.info(f"📂 MySQL Checkpoint loaded: {checkpoint_stats['total']} entities already loaded")
        if checkpoint_stats['by_type']:
            for entity_type, count in checkpoint_stats['by_type'].items():
                logger.info(f"   - {entity_type}: {count}")

    async def load_entity(self, entity: Any, entity_id: str, entity_type: str, max_retries: int = 10) -> bool:
        """
        Загрузить один entity в Graphiti с двойной проверкой дубликатов

        Args:
            entity: Pydantic entity
            entity_id: Уникальный ID
            entity_type: Тип entity (для checkpoint)
            max_retries: Количество попыток (увеличено до 10 для Neo4j token refresh)

        Returns:
            True if success, False otherwise
        """
        # ДВОЙНАЯ ПРОВЕРКА ДУБЛИКАТОВ:
        # 1. Проверить MySQL checkpoint (быстро)
        if self.checkpoint_service.is_loaded(entity_id):
            self.stats["skipped"] += 1
            return True

        # 2. Проверить Neo4j (резервная проверка, на случай если checkpoint потерян)
        entity_exists = await self.graphiti_service.entity_exists(entity_id)
        if entity_exists:
            # Entity есть в Neo4j но нет в checkpoint - добавим в checkpoint
            self.checkpoint_service.mark_loaded(
                entity_id=entity_id,
                entity_type=entity_type,
                tier=self.tier,
                batch_number=self.batch_number
            )
            self.stats["skipped"] += 1
            logger.debug(f"Entity {entity_id} found in Neo4j but not in checkpoint - updated checkpoint")
            return True

        # Конвертировать в Episode content
        content = entity.to_episode_content()
        metadata = create_episode_metadata(entity)

        # Попытки загрузки с retry
        for attempt in range(max_retries):
            try:
                success, result = await self.graphiti_service.add_episode(
                    content=content,
                    episode_type=entity.entity_type.value,
                    metadata=metadata,
                    source_description=f"{entity.entity_type.value} from knowledge base"
                )

                if success:
                    # Сохранить в MySQL checkpoint
                    self.checkpoint_service.mark_loaded(
                        entity_id=entity_id,
                        entity_type=entity_type,
                        episode_id=result,
                        tier=self.tier,
                        batch_number=self.batch_number
                    )
                    self.stats["success"] += 1
                    return True
                else:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff
                    else:
                        logger.error(f"❌ Failed to load {entity_id}: {result}")
                        self.stats["failed"] += 1
                        return False

            except ServiceUnavailable as e:
                # Neo4j токен истёк или временно недоступен (обновление токена)
                if attempt < max_retries - 1:
                    backoff_seconds = min(10 + (attempt * 2), 30)  # 10s, 12s, 14s ... до 30s
                    logger.warning(f"⚠️ Neo4j unavailable (token refresh?), retry {attempt + 1}/{max_retries} for {entity_id} after {backoff_seconds}s")
                    await asyncio.sleep(backoff_seconds)
                else:
                    logger.error(f"❌ Neo4j unavailable for {entity_id} after {max_retries} attempts: {e}")
                    self.stats["failed"] += 1
                    return False

            except ClientError as e:
                # Neo4j query error - не retry, это скорее всего проблема с данными
                logger.error(f"❌ Neo4j client error for {entity_id}: {e}")
                self.stats["failed"] += 1
                return False

            except Exception as e:
                # Другие ошибки - retry с exponential backoff
                if attempt < max_retries - 1:
                    backoff_seconds = 2 * (attempt + 1)  # 2s, 4s, 6s, 8s ...
                    logger.warning(f"⚠️ Retry {attempt + 1}/{max_retries} for {entity_id} after {backoff_seconds}s: {type(e).__name__}: {e}")
                    await asyncio.sleep(backoff_seconds)
                else:
                    logger.error(f"❌ Failed {entity_id} after {max_retries} attempts: {type(e).__name__}: {e}")
                    self.stats["failed"] += 1
                    return False

        return False

    async def load_batch(self, entities: List[Any], entity_type: str, batch_size: int = 50):
        """
        Загрузить batch of entities

        Args:
            entities: List of parsed entities
            entity_type: Type name (для логов и checkpoint)
            batch_size: Размер batch
        """
        logger.info(f"\n📦 Loading {len(entities)} {entity_type} entities...")

        # Progress bar
        pbar = tqdm(total=len(entities), desc=f"Loading {entity_type}")

        for i in range(0, len(entities), batch_size):
            batch = entities[i:i + batch_size]
            batch_num = i // batch_size
            self.batch_number = batch_num

            # Параллельная загрузка в batch
            tasks = []
            for idx, entity in enumerate(batch):
                entity_id = f"{entity_type}_{i + idx}"
                # Передаём entity_type для checkpoint
                tasks.append(self.load_entity(entity, entity_id, entity_type))

            # Ждем завершения всех tasks в batch
            await asyncio.gather(*tasks)

            # Update progress
            pbar.update(len(batch))

            # MySQL checkpoint сохраняется автоматически в load_entity()
            logger.debug(f"Batch {batch_num} completed ({i + len(batch)}/{len(entities)})")

        pbar.close()

        logger.info(f"✅ Finished loading {entity_type}: {self.stats['success']} success, {self.stats['skipped']} skipped, {self.stats['failed']} failed")

    async def load_tier(self, tier: int, batch_size: int = 50):
        """
        Загрузить определенный tier базы знаний

        Tier 1: FAQ (высший приоритет)
        Tier 2: Lessons + Corrections
        Tier 3: Questions + Brainwrites (TODO)

        Args:
            tier: Номер tier (1-3)
            batch_size: Размер batch
        """
        if tier == 1:
            # Tier 1: FAQ - самые важные и частые вопросы
            logger.info("\n🎯 TIER 1: Loading FAQ (TOP priority)")

            faq_file = self.parsed_dir / "parsed_faq.json"
            if faq_file.exists():
                with open(faq_file, 'r', encoding='utf-8') as f:
                    faq_data = json.load(f)

                entities = [FAQEntry(**item) for item in faq_data]
                self.stats["total"] += len(entities)
                await self.load_batch(entities, "FAQ", batch_size)
            else:
                logger.warning(f"⚠️ FAQ file not found: {faq_file}")

        elif tier == 2:
            # Tier 2: Lessons + Corrections
            logger.info("\n📚 TIER 2: Loading Lessons + Corrections")

            # Lessons
            lessons_file = self.parsed_dir / "parsed_lessons.json"
            if lessons_file.exists():
                with open(lessons_file, 'r', encoding='utf-8') as f:
                    lessons_data = json.load(f)

                entities = [CourseLesson(**item) for item in lessons_data]
                self.stats["total"] += len(entities)
                await self.load_batch(entities, "Lesson", batch_size)
            else:
                logger.warning(f"⚠️ Lessons file not found: {lessons_file}")

            # Corrections
            corrections_file = self.parsed_dir / "parsed_corrections.json"
            if corrections_file.exists():
                with open(corrections_file, 'r', encoding='utf-8') as f:
                    corrections_data = json.load(f)

                entities = [CuratorCorrection(**item) for item in corrections_data]
                self.stats["total"] += len(entities)
                await self.load_batch(entities, "Correction", batch_size)
            else:
                logger.warning(f"⚠️ Corrections file not found: {corrections_file}")

        elif tier == 3:
            # Tier 3: Questions only (Brainwrites excluded)
            logger.info("\n💬 TIER 3: Loading Questions")

            # Student Questions
            questions_file = self.parsed_dir / "parsed_questions.json"
            if questions_file.exists():
                with open(questions_file, 'r', encoding='utf-8') as f:
                    questions_data = json.load(f)

                entities = [StudentQuestion(**item) for item in questions_data]
                self.stats["total"] += len(entities)
                await self.load_batch(entities, "Question", batch_size)
            else:
                logger.warning(f"⚠️ Questions file not found: {questions_file}")

            # Note: Brainwrite Examples excluded - student examples may not follow exact methodology

        else:
            logger.error(f"❌ Invalid tier: {tier}. Must be 1, 2, or 3")

    async def load_all(self, batch_size: int = 50):
        """Загрузить всю базу знаний (все tiers)"""
        logger.info("🚀 Loading ALL knowledge base tiers...")

        for tier in [1, 2, 3]:  # Все 3 тира
            await self.load_tier(tier, batch_size)

        logger.info("\n✅ All tiers loaded!")

    def print_stats(self):
        """Вывести статистику загрузки"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 LOADING STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Total entities: {self.stats['total']}")
        logger.info(f"Successfully loaded: {self.stats['success']} ({self.stats['success'] / max(1, self.stats['total']) * 100:.1f}%)")
        logger.info(f"Failed: {self.stats['failed']}")
        logger.info(f"Skipped (already loaded): {self.stats['skipped']}")
        logger.info("=" * 60)


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Load knowledge base to Graphiti")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3], help="Load specific tier (1=FAQ, 2=Lessons+Corrections, 3=Questions+Brainwrites)")
    parser.add_argument("--all", action="store_true", help="Load all tiers")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size (default: 50)")
    parser.add_argument("--reset-checkpoint", action="store_true", help="Reset MySQL checkpoint (start from scratch)")

    args = parser.parse_args()

    # Paths
    parsed_dir = root_dir / "data" / "parsed_kb"

    # Check parsed data exists
    if not parsed_dir.exists():
        logger.error(f"❌ Parsed data not found: {parsed_dir}")
        logger.info("\n💡 Run parser first: python scripts/parse_knowledge_base.py")
        return

    # Reset checkpoint if requested
    if args.reset_checkpoint:
        checkpoint_service = get_checkpoint_service()
        if checkpoint_service.clear_all():
            logger.info("🗑️ MySQL checkpoint reset - all entries cleared")
        else:
            logger.warning("⚠️ Failed to reset checkpoint (database might be disabled)")

    # Initialize loader with tier (will be updated for each tier)
    loader = GraphitiLoader(parsed_dir, tier=args.tier)

    # Check Graphiti service
    if not loader.graphiti_service.enabled:
        logger.error("❌ Graphiti service not enabled!")
        logger.info("\n💡 Setup Neo4j first:")
        logger.info("   1. Create Neo4j Aura instance (https://neo4j.com/cloud/aura/)")
        logger.info("   2. Add to .env:")
        logger.info("      NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io")
        logger.info("      NEO4J_PASSWORD=your_password")
        logger.info("      GRAPHITI_ENABLED=true")
        logger.info("   3. Test connection: python scripts/test_neo4j_connection.py")
        return

    # Load knowledge
    if args.tier:
        await loader.load_tier(args.tier, args.batch_size)
    elif args.all:
        await loader.load_all(args.batch_size)
    else:
        # Default: load Tier 1 (FAQ) only
        logger.info("💡 No tier specified, loading Tier 1 (FAQ) by default")
        logger.info("   Use --all to load all tiers, or --tier N to load specific tier")
        await loader.load_tier(1, args.batch_size)

    # Print stats
    loader.print_stats()

    # Final checkpoint
    loader.save_checkpoint()
    logger.info(f"\n💾 Checkpoint saved: {checkpoint_file}")


if __name__ == "__main__":
    asyncio.run(main())
