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
from typing import List, Dict, Any
from datetime import datetime
import logging

try:
    from tqdm import tqdm
except ImportError:
    print("⚠️ tqdm not installed. Install: pip install tqdm")
    sys.exit(1)

# Add root to PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from bot.services.graphiti_service import get_graphiti_service
from bot.models.knowledge_entities import (
    FAQEntry,
    CourseLesson,
    CuratorCorrection,
    StudentQuestion,
    BrainwriteExample,
    create_episode_metadata
)

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class GraphitiLoader:
    """Загрузчик базы знаний в Graphiti"""

    def __init__(self, parsed_dir: Path, checkpoint_file: Path):
        self.parsed_dir = parsed_dir
        self.checkpoint_file = checkpoint_file
        self.graphiti_service = get_graphiti_service()

        self.loaded_ids = set()
        self.stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0
        }

        # Загрузить checkpoint
        self.load_checkpoint()

    def load_checkpoint(self):
        """Загрузить checkpoint (какие entities уже загружены)"""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, 'r') as f:
                data = json.load(f)
                self.loaded_ids = set(data.get("loaded_ids", []))
                logger.info(f"📂 Checkpoint loaded: {len(self.loaded_ids)} entities already loaded")

    def save_checkpoint(self):
        """Сохранить checkpoint"""
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.checkpoint_file, 'w') as f:
            json.dump({
                "loaded_ids": list(self.loaded_ids),
                "timestamp": datetime.utcnow().isoformat(),
                "stats": self.stats
            }, f, indent=2)

    async def load_entity(self, entity: Any, entity_id: str, max_retries: int = 3) -> bool:
        """
        Загрузить один entity в Graphiti

        Args:
            entity: Pydantic entity
            entity_id: Уникальный ID
            max_retries: Количество попыток

        Returns:
            True if success, False otherwise
        """
        # Проверить если уже загружен
        if entity_id in self.loaded_ids:
            self.stats["skipped"] += 1
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
                    self.loaded_ids.add(entity_id)
                    self.stats["success"] += 1
                    return True
                else:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff
                    else:
                        logger.error(f"❌ Failed to load {entity_id}: {result}")
                        self.stats["failed"] += 1
                        return False

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"⚠️ Retry {attempt + 1}/{max_retries} for {entity_id}: {e}")
                    await asyncio.sleep(1 * (attempt + 1))
                else:
                    logger.error(f"❌ Failed {entity_id} after {max_retries} attempts: {e}")
                    self.stats["failed"] += 1
                    return False

        return False

    async def load_batch(self, entities: List[Any], entity_type: str, batch_size: int = 50):
        """
        Загрузить batch of entities

        Args:
            entities: List of parsed entities
            entity_type: Type name (для логов)
            batch_size: Размер batch
        """
        logger.info(f"\n📦 Loading {len(entities)} {entity_type} entities...")

        # Progress bar
        pbar = tqdm(total=len(entities), desc=f"Loading {entity_type}")

        for i in range(0, len(entities), batch_size):
            batch = entities[i:i + batch_size]

            # Параллельная загрузка в batch
            tasks = []
            for idx, entity in enumerate(batch):
                entity_id = f"{entity_type}_{i + idx}"
                tasks.append(self.load_entity(entity, entity_id))

            # Ждем завершения всех tasks в batch
            await asyncio.gather(*tasks)

            # Update progress
            pbar.update(len(batch))

            # Сохранить checkpoint каждые N batches
            if (i // batch_size) % 5 == 0:
                self.save_checkpoint()

        pbar.close()

        # Финальный checkpoint
        self.save_checkpoint()

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
            # Tier 3: Questions + Brainwrites
            logger.info("\n💬 TIER 3: Loading Questions + Brainwrites")

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

            # Brainwrite Examples
            brainwrites_file = self.parsed_dir / "parsed_brainwrites.json"
            if brainwrites_file.exists():
                with open(brainwrites_file, 'r', encoding='utf-8') as f:
                    brainwrites_data = json.load(f)

                entities = [BrainwriteExample(**item) for item in brainwrites_data]
                self.stats["total"] += len(entities)
                await self.load_batch(entities, "Brainwrite", batch_size)
            else:
                logger.warning(f"⚠️ Brainwrites file not found: {brainwrites_file}")

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
    parser.add_argument("--reset-checkpoint", action="store_true", help="Reset checkpoint (start from scratch)")

    args = parser.parse_args()

    # Paths
    parsed_dir = root_dir / "data" / "parsed_kb"
    checkpoint_file = root_dir / "data" / "graphiti_checkpoint.json"

    # Check parsed data exists
    if not parsed_dir.exists():
        logger.error(f"❌ Parsed data not found: {parsed_dir}")
        logger.info("\n💡 Run parser first: python scripts/parse_knowledge_base.py")
        return

    # Reset checkpoint if requested
    if args.reset_checkpoint and checkpoint_file.exists():
        checkpoint_file.unlink()
        logger.info("🗑️ Checkpoint reset")

    # Initialize loader
    loader = GraphitiLoader(parsed_dir, checkpoint_file)

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
