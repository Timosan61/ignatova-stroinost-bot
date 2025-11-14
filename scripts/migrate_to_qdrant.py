#!/usr/bin/env python3
"""
Migrate Knowledge Base to Qdrant

Скрипт миграции всей базы знаний курса "Всепрощающая" в Qdrant Vector Database.

Процесс:
1. Парсинг всех файлов базы знаний (FAQ, уроки, техники, корректировки)
2. Создание Qdrant collection (если не существует)
3. Генерация embeddings через sentence-transformers
4. Batch upload entities в Qdrant
5. Checkpoint system для resumable loading

Usage:
    python3 scripts/migrate_to_qdrant.py --batch-size 50 --reset
"""

import os
import sys
import json
import asyncio
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Добавить корень в PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from dotenv import load_dotenv
load_dotenv()

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance, VectorParams, PointStruct,
        CreateCollection
    )
    from sentence_transformers import SentenceTransformer
    QDRANT_AVAILABLE = True
except ImportError:
    print("❌ ERROR: qdrant-client or sentence-transformers not installed")
    print("Install: pip install qdrant-client sentence-transformers")
    sys.exit(1)

from bot.config import QDRANT_URL, QDRANT_API_KEY, QDRANT_COLLECTION, EMBEDDING_MODEL
from bot.models.knowledge_entities import (
    CourseLesson, FAQEntry, BrainwriteTechnique,
    StudentQuestion, CuratorCorrection, BrainwriteExample
)

# Import parser
from parse_knowledge_base import KnowledgeBaseParser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class QdrantMigration:
    """Миграция базы знаний в Qdrant"""

    def __init__(
        self,
        kb_dir: Path,
        batch_size: int = 50,
        checkpoint_file: Optional[Path] = None
    ):
        """
        Args:
            kb_dir: Путь к папке KNOWLEDGE_BASE
            batch_size: Размер batch для upload
            checkpoint_file: Файл для сохранения прогресса
        """
        self.kb_dir = kb_dir
        self.batch_size = batch_size
        self.checkpoint_file = checkpoint_file or (kb_dir / "qdrant_migration_checkpoint.json")

        # Инициализация Qdrant client
        if not QDRANT_URL or not QDRANT_API_KEY:
            raise ValueError("QDRANT_URL and QDRANT_API_KEY must be configured")

        self.client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            timeout=60
        )
        logger.info(f"✅ Qdrant client connected: {QDRANT_URL}")

        # Инициализация sentence transformer
        logger.info(f"Loading sentence transformer: {EMBEDDING_MODEL}")
        self.encoder = SentenceTransformer(EMBEDDING_MODEL)
        logger.info(f"✅ Sentence transformer loaded: {EMBEDDING_MODEL}")

        # Статистика
        self.stats = {
            "total_entities": 0,
            "uploaded_entities": 0,
            "failed_entities": 0,
            "by_type": {}
        }

    def _load_checkpoint(self) -> Dict[str, Any]:
        """Загрузить checkpoint (если существует)"""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint = json.load(f)
                logger.info(f"📥 Checkpoint loaded: {checkpoint['uploaded_entities']} entities already uploaded")
                return checkpoint
        return {"uploaded_ids": [], "uploaded_entities": 0}

    def _save_checkpoint(self):
        """Сохранить checkpoint"""
        checkpoint = {
            "uploaded_ids": list(self.uploaded_ids),
            "uploaded_entities": self.stats["uploaded_entities"],
            "timestamp": datetime.utcnow().isoformat()
        }
        with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint, f, indent=2, ensure_ascii=False)
        logger.info(f"💾 Checkpoint saved: {self.stats['uploaded_entities']} entities")

    def _ensure_collection(self):
        """Создать collection если не существует"""
        collections = self.client.get_collections()
        collection_names = [c.name for c in collections.collections]

        if QDRANT_COLLECTION in collection_names:
            logger.info(f"✅ Collection '{QDRANT_COLLECTION}' already exists")
            return

        logger.info(f"Creating collection: {QDRANT_COLLECTION}")

        # Получаем размер вектора из модели
        test_vector = self.encoder.encode("test").tolist()
        vector_size = len(test_vector)

        self.client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE
            )
        )
        logger.info(f"✅ Collection '{QDRANT_COLLECTION}' created (vector_size={vector_size})")

    def _parse_all_entities(self) -> List[Dict[str, Any]]:
        """
        Парсинг всех entities из базы знаний

        Returns:
            List of entities в формате:
            [
                {
                    "id": "lesson_1_chunk_0",
                    "entity_type": "lesson",
                    "title": "Урок 1: Введение",
                    "content": "...",
                    "metadata": {...}
                },
                ...
            ]
        """
        parser = KnowledgeBaseParser(self.kb_dir)

        all_entities = []
        entity_id = 0

        # 1. Parse FAQ
        faq_file = self.kb_dir / "FAQ_EXTENDED.md"
        if faq_file.exists():
            logger.info("📖 Parsing FAQ...")
            faq_entries = parser.parse_faq(faq_file)
            for faq in faq_entries:
                entity = {
                    "id": f"faq_{entity_id}",
                    "entity_type": "faq",
                    "title": faq.question[:100],  # Первые 100 символов вопроса
                    "content": faq.to_episode_content(),
                    "metadata": {
                        "category": faq.category,
                        "keywords": faq.keywords,
                        "frequency": faq.frequency
                    }
                }
                all_entities.append(entity)
                entity_id += 1

            logger.info(f"✅ FAQ parsed: {len(faq_entries)} entries")

        # 2. Parse Lessons
        kb_file = self.kb_dir / "KNOWLEDGE_BASE_FULL.md"
        if kb_file.exists():
            logger.info("📖 Parsing Lessons...")
            lessons = parser.parse_lessons(kb_file)
            for lesson in lessons:
                entity = {
                    "id": f"lesson_{lesson.lesson_number}_chunk_{lesson.chunk_index or 0}",
                    "entity_type": "lesson",
                    "title": lesson.title,
                    "content": lesson.to_episode_content(),
                    "metadata": {
                        "lesson_number": lesson.lesson_number,
                        "category": lesson.category.value,
                        "chunk_index": lesson.chunk_index,
                        "total_chunks": lesson.total_chunks,
                        "key_concepts": lesson.key_concepts
                    }
                }
                all_entities.append(entity)
                entity_id += 1

            logger.info(f"✅ Lessons parsed: {len(lessons)} chunks")

        # 3. Parse Curator Corrections
        corrections_file = self.kb_dir / "curator_corrections_ALL.json"
        if corrections_file.exists():
            logger.info("📖 Parsing Curator Corrections...")
            corrections = parser.parse_corrections(corrections_file)
            for correction in corrections:
                entity = {
                    "id": f"correction_{entity_id}",
                    "entity_type": "correction",
                    "title": correction.student_text[:100] if correction.student_text else correction.error_type,
                    "content": correction.to_episode_content(),
                    "metadata": {
                        "error_type": correction.error_type,
                        "related_technique": correction.related_technique,
                        "related_lesson": correction.related_lesson,
                        "curator_name": correction.curator_name,
                        "student_name": correction.student_name,
                        "has_explanation": bool(correction.explanation)
                    }
                }
                all_entities.append(entity)
                entity_id += 1

            logger.info(f"✅ Curator Corrections parsed: {len(corrections)} entries")

        logger.info(f"📊 Total entities parsed: {len(all_entities)}")
        return all_entities

    def _upload_batch(self, entities: List[Dict[str, Any]]):
        """
        Upload batch of entities to Qdrant

        Args:
            entities: List of entities to upload
        """
        points = []

        for entity in entities:
            # Генерируем embedding для content
            vector = self.encoder.encode(entity["content"]).tolist()

            # Создаём payload
            payload = {
                "entity_type": entity["entity_type"],
                "title": entity["title"],
                "content": entity["content"],
                "metadata": entity["metadata"],
                "created_at": datetime.utcnow().isoformat()
            }

            # Создаём point
            point = PointStruct(
                id=entity["id"],
                vector=vector,
                payload=payload
            )
            points.append(point)

        # Upload batch
        self.client.upsert(
            collection_name=QDRANT_COLLECTION,
            points=points
        )

        self.stats["uploaded_entities"] += len(points)

        # Обновляем uploaded_ids
        for entity in entities:
            self.uploaded_ids.add(entity["id"])

    async def migrate(self, reset: bool = False):
        """
        Запустить миграцию

        Args:
            reset: Если True - удалить checkpoint и начать с нуля
        """
        logger.info("🚀 Starting Qdrant migration...")

        # Удалить checkpoint если reset
        if reset and self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
            logger.info("🗑️ Checkpoint deleted (reset=True)")

        # Создать collection
        self._ensure_collection()

        # Загрузить checkpoint
        checkpoint = self._load_checkpoint()
        self.uploaded_ids = set(checkpoint.get("uploaded_ids", []))
        self.stats["uploaded_entities"] = checkpoint.get("uploaded_entities", 0)

        # Парсинг всех entities
        logger.info("📖 Parsing knowledge base...")
        all_entities = self._parse_all_entities()
        self.stats["total_entities"] = len(all_entities)

        # Фильтруем уже загруженные entities
        entities_to_upload = [e for e in all_entities if e["id"] not in self.uploaded_ids]

        if not entities_to_upload:
            logger.info("✅ All entities already uploaded!")
            self._print_stats()
            return

        logger.info(f"📤 Uploading {len(entities_to_upload)} entities (batch_size={self.batch_size})...")

        # Upload batches
        for i in range(0, len(entities_to_upload), self.batch_size):
            batch = entities_to_upload[i:i + self.batch_size]

            try:
                self._upload_batch(batch)

                # Обновляем статистику по типам
                for entity in batch:
                    entity_type = entity["entity_type"]
                    self.stats["by_type"][entity_type] = self.stats["by_type"].get(entity_type, 0) + 1

                # Сохраняем checkpoint после каждого batch
                self._save_checkpoint()

                logger.info(
                    f"✅ Batch {i // self.batch_size + 1}/{(len(entities_to_upload) - 1) // self.batch_size + 1} "
                    f"uploaded ({self.stats['uploaded_entities']}/{self.stats['total_entities']})"
                )

            except Exception as e:
                logger.error(f"❌ Failed to upload batch: {e}")
                logger.exception("Full traceback:")
                self.stats["failed_entities"] += len(batch)

        logger.info("✅ Migration completed!")
        self._print_stats()

    def _print_stats(self):
        """Вывести финальную статистику"""
        logger.info("=" * 60)
        logger.info("📊 MIGRATION STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Total entities:    {self.stats['total_entities']}")
        logger.info(f"Uploaded:          {self.stats['uploaded_entities']}")
        logger.info(f"Failed:            {self.stats['failed_entities']}")
        logger.info("")
        logger.info("By entity type:")
        for entity_type, count in self.stats["by_type"].items():
            logger.info(f"  - {entity_type:15s} {count:4d}")
        logger.info("=" * 60)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Migrate knowledge base to Qdrant")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Batch size for upload (default: 50)"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset checkpoint and start from scratch"
    )
    parser.add_argument(
        "--kb-dir",
        type=Path,
        default=root_dir / "KNOWLEDGE_BASE",
        help="Path to KNOWLEDGE_BASE directory"
    )

    args = parser.parse_args()

    # Проверка что kb_dir существует
    if not args.kb_dir.exists():
        logger.error(f"❌ KNOWLEDGE_BASE directory not found: {args.kb_dir}")
        sys.exit(1)

    # Запуск миграции
    migration = QdrantMigration(
        kb_dir=args.kb_dir,
        batch_size=args.batch_size
    )

    asyncio.run(migration.migrate(reset=args.reset))


if __name__ == "__main__":
    main()
