#!/usr/bin/env python3
"""
Migrate Knowledge Base to Supabase

Скрипт миграции всей базы знаний курса "Всепрощающая" в Supabase pgvector.

Процесс:
1. Парсинг всех файлов базы знаний (FAQ, уроки, техники, корректировки)
2. Генерация embeddings через OpenAI API (text-embedding-3-small)
3. Batch upload entities в Supabase
4. Progress tracking и error handling

Usage:
    python3 scripts/migrate_to_supabase.py --batch-size 20 --reset
    python3 scripts/migrate_to_supabase.py --dry-run  # Тестовый прогон без загрузки
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
import time

# Добавить корень в PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from dotenv import load_dotenv
load_dotenv()

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    print("❌ ERROR: requests not installed")
    print("Install: pip install requests")
    sys.exit(1)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    print("❌ ERROR: openai SDK not installed")
    print("Install: pip install openai")
    sys.exit(1)

from bot.config import (
    SUPABASE_URL, SUPABASE_SERVICE_KEY, SUPABASE_TABLE,
    OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL
)

# Import parser
from parse_knowledge_base import KnowledgeBaseParser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SupabaseMigration:
    """Миграция базы знаний в Supabase"""

    def __init__(
        self,
        kb_dir: Path,
        batch_size: int = 20,  # Меньше из-за OpenAI rate limits
        dry_run: bool = False
    ):
        """
        Args:
            kb_dir: Путь к папке KNOWLEDGE_BASE
            batch_size: Размер batch для upload
            dry_run: Если True, не загружать данные (только парсинг)
        """
        self.kb_dir = kb_dir
        self.batch_size = batch_size
        self.dry_run = dry_run

        # Инициализация Supabase REST API
        if not dry_run:
            if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
                raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY required")

            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY required for embeddings")

            # Настройка REST API вместо SDK
            self.api_url = f"{SUPABASE_URL}/rest/v1"
            self.headers = {
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal"
            }
            logger.info(f"✅ Supabase REST API configured: {SUPABASE_URL}")

            # Инициализация OpenAI client (для embeddings)
            self.openai = OpenAI(api_key=OPENAI_API_KEY)
            logger.info(f"✅ OpenAI client initialized: {OPENAI_EMBEDDING_MODEL}")
        else:
            logger.info("🔵 DRY RUN MODE: Данные не будут загружены")

        # Установить атрибуты для всех режимов (включая dry-run)
        self.table_name = SUPABASE_TABLE
        self.embedding_model = OPENAI_EMBEDDING_MODEL

        # Статистика
        self.stats = {
            "total_entities": 0,
            "uploaded_entities": 0,
            "failed_entities": 0,
            "by_type": {},
            "total_tokens": 0,  # Для расчёта стоимости
            "total_cost_usd": 0.0
        }

    def _generate_embedding(self, text: str) -> List[float]:
        """Генерация embedding через OpenAI"""
        if self.dry_run:
            # В dry-run режиме возвращаем пустой вектор
            return [0.0] * 1536

        try:
            response = self.openai.embeddings.create(
                input=text,
                model=self.embedding_model
            )

            # Считаем токены для статистики
            tokens_used = response.usage.total_tokens
            self.stats["total_tokens"] += tokens_used

            # Стоимость для text-embedding-3-small: $0.00002 за 1K tokens
            cost = (tokens_used / 1000) * 0.00002
            self.stats["total_cost_usd"] += cost

            return response.data[0].embedding

        except Exception as e:
            logger.error(f"❌ Failed to generate embedding: {e}")
            raise

    def _parse_all_entities(self) -> List[Dict[str, Any]]:
        """
        Парсинг всех entities из базы знаний

        Returns:
            List of entities в формате:
            [
                {
                    "id": "faq_0",
                    "entity_type": "faq",
                    "title": "...",
                    "content": "...",
                    "metadata": {...}
                },
                ...
            ]
        """
        parser = KnowledgeBaseParser(self.kb_dir)
        all_entities = []

        # 1. Parse FAQ
        faq_file = self.kb_dir / "FAQ_EXTENDED.md"
        if faq_file.exists():
            logger.info("📖 Parsing FAQ...")
            faq_entries = parser.parse_faq(faq_file)
            for idx, faq in enumerate(faq_entries):
                entity = {
                    "id": f"faq_{idx}",  # String ID для Supabase
                    "entity_type": "faq",
                    "title": faq.question[:100],
                    "content": faq.to_episode_content(),
                    "metadata": {
                        "category": faq.category,
                        "keywords": faq.keywords,
                        "frequency": faq.frequency
                    }
                }
                all_entities.append(entity)

            logger.info(f"✅ FAQ parsed: {len(faq_entries)} entries")

        # 2. Parse Lessons
        kb_file = self.kb_dir / "KNOWLEDGE_BASE_FULL.md"
        if kb_file.exists():
            logger.info("📖 Parsing Lessons...")
            lessons = parser.parse_lessons(kb_file)
            for idx, lesson in enumerate(lessons):
                entity = {
                    "id": f"lesson_{idx}",
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

            logger.info(f"✅ Lessons parsed: {len(lessons)} chunks")

        # 3. Parse Curator Corrections
        corrections_file = self.kb_dir / "curator_corrections_ALL.json"
        if corrections_file.exists():
            logger.info("📖 Parsing Curator Corrections...")
            corrections = parser.parse_corrections(corrections_file)
            for idx, correction in enumerate(corrections):
                entity = {
                    "id": f"correction_{idx}",
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

            logger.info(f"✅ Curator Corrections parsed: {len(corrections)} entries")

        # 4. Parse Student Questions (ВСЕ 2,635 вопросов!)
        questions_file = self.kb_dir / "student_questions_ALL.json"
        if questions_file.exists():
            logger.info("📖 Parsing Student Questions (ALL questions)...")
            questions = parser.parse_questions(questions_file, sample_limit=None)
            for idx, question in enumerate(questions):
                entity = {
                    "id": f"question_{idx}",
                    "entity_type": "question",
                    "title": question.question_text[:100] if question.question_text else f"Question {idx}",
                    "content": question.to_episode_content(),
                    "metadata": {
                        "category": question.category,
                        "lesson_reference": question.lesson_reference,
                        "student_name": question.student_name
                    }
                }
                all_entities.append(entity)

            logger.info(f"✅ Student Questions parsed: {len(questions)} questions")

        # 5. Parse Brainwrite Examples
        brainwrites_file = self.kb_dir / "student_brainwrites_SAMPLE.json"
        if brainwrites_file.exists():
            logger.info("📖 Parsing Brainwrite Examples...")
            brainwrites = parser.parse_brainwrites(brainwrites_file)
            for idx, brainwrite in enumerate(brainwrites):
                entity = {
                    "id": f"brainwrite_{idx}",
                    "entity_type": "brainwrite",
                    "title": brainwrite.text[:100] if brainwrite.text else f"Brainwrite {idx}",
                    "content": brainwrite.to_episode_content(),
                    "metadata": {
                        "student_name": brainwrite.student_name,
                        "lesson_number": brainwrite.lesson_number,
                        "technique_used": brainwrite.technique_used,
                        "quality_rating": brainwrite.quality_rating
                    }
                }
                all_entities.append(entity)

            logger.info(f"✅ Brainwrite Examples parsed: {len(brainwrites)} examples")

        # 6. Parse Glossary Terms
        glossary_file = self.kb_dir / "KNOWLEDGE_BASE_FULL.md"
        if glossary_file.exists():
            logger.info("📖 Parsing Glossary Terms...")
            glossary_terms = parser.parse_glossary(glossary_file)
            for idx, term in enumerate(glossary_terms):
                entity = {
                    "id": f"glossary_{idx}",
                    "entity_type": "glossary",
                    "title": term.term,
                    "content": f"{term.term}: {term.definition}",
                    "metadata": {
                        "lesson_number": term.lesson_number,
                        "keywords": term.keywords
                    }
                }
                all_entities.append(entity)

            logger.info(f"✅ Glossary Terms parsed: {len(glossary_terms)} terms")

        logger.info(f"📊 Total entities parsed: {len(all_entities)}")
        return all_entities

    def _upload_batch(self, entities: List[Dict[str, Any]]) -> int:
        """
        Upload batch с embeddings

        Returns:
            Количество успешно загруженных entities
        """
        if self.dry_run:
            return len(entities)

        rows = []

        for entity in entities:
            try:
                # Генерируем embedding
                embedding = self._generate_embedding(entity["content"])

                # Подготавливаем row
                row = {
                    "id": entity["id"],
                    "entity_type": entity["entity_type"],
                    "title": entity["title"],
                    "content": entity["content"],
                    "metadata": entity["metadata"],
                    "embedding": embedding,
                    "created_at": datetime.utcnow().isoformat()
                }
                rows.append(row)

                # Rate limit: небольшая задержка между embeddings
                time.sleep(0.05)  # 50ms delay

            except Exception as e:
                logger.error(f"❌ Failed to process entity {entity['id']}: {e}")
                self.stats["failed_entities"] += 1
                continue

        if not rows:
            return 0

        # Batch insert в Supabase через REST API
        try:
            response = requests.post(
                f"{self.api_url}/{self.table_name}",
                headers=self.headers,
                json=rows
            )
            response.raise_for_status()

            uploaded_count = len(rows)
            self.stats["uploaded_entities"] += uploaded_count

            # Статистика по типам
            for entity in entities:
                entity_type = entity["entity_type"]
                self.stats["by_type"][entity_type] = self.stats["by_type"].get(entity_type, 0) + 1

            return uploaded_count

        except Exception as e:
            logger.error(f"❌ Batch upload failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"   Response: {e.response.text}")
            self.stats["failed_entities"] += len(rows)
            return 0

    async def migrate(self, reset: bool = False):
        """Запустить миграцию"""
        start_time = time.time()

        logger.info("🚀 Starting Supabase migration...")
        logger.info(f"   Batch size: {self.batch_size}")
        logger.info(f"   Embedding model: {self.embedding_model}")
        logger.info(f"   Dry run: {self.dry_run}")

        # Парсинг entities
        logger.info("")
        logger.info("=" * 60)
        logger.info("STEP 1: Parsing Knowledge Base")
        logger.info("=" * 60)
        all_entities = self._parse_all_entities()
        self.stats["total_entities"] = len(all_entities)

        if self.dry_run:
            logger.info("")
            logger.info("🔵 DRY RUN COMPLETE - Данные НЕ загружены")
            logger.info(f"   Total entities: {len(all_entities)}")
            for entity_type in ["faq", "lesson", "correction", "question", "brainwrite"]:
                count = len([e for e in all_entities if e["entity_type"] == entity_type])
                if count > 0:
                    logger.info(f"   - {entity_type}: {count}")
            return

        # Upload batches
        logger.info("")
        logger.info("=" * 60)
        logger.info("STEP 2: Uploading to Supabase")
        logger.info("=" * 60)

        total_batches = (len(all_entities) + self.batch_size - 1) // self.batch_size

        for i in range(0, len(all_entities), self.batch_size):
            batch = all_entities[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1

            logger.info(
                f"📤 Batch {batch_num}/{total_batches}: "
                f"Uploading {len(batch)} entities..."
            )

            uploaded = self._upload_batch(batch)

            logger.info(
                f"   ✅ Uploaded: {uploaded}/{len(batch)} | "
                f"Progress: {self.stats['uploaded_entities']}/{self.stats['total_entities']} | "
                f"Tokens: {self.stats['total_tokens']:,} | "
                f"Cost: ${self.stats['total_cost_usd']:.4f}"
            )

        # Итоговая статистика
        elapsed_time = time.time() - start_time

        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ MIGRATION COMPLETE!")
        logger.info("=" * 60)
        logger.info(f"Total entities: {self.stats['total_entities']}")
        logger.info(f"Uploaded: {self.stats['uploaded_entities']}")
        logger.info(f"Failed: {self.stats['failed_entities']}")
        logger.info("")
        logger.info("By type:")
        for entity_type, count in sorted(self.stats['by_type'].items()):
            logger.info(f"  - {entity_type}: {count}")
        logger.info("")
        logger.info(f"OpenAI API usage:")
        logger.info(f"  - Total tokens: {self.stats['total_tokens']:,}")
        logger.info(f"  - Total cost: ${self.stats['total_cost_usd']:.4f}")
        logger.info("")
        logger.info(f"Time elapsed: {elapsed_time:.1f}s ({elapsed_time/60:.1f}m)")
        logger.info("=" * 60)


async def main():
    parser = argparse.ArgumentParser(description="Migrate Knowledge Base to Supabase")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=20,
        help="Batch size for uploads (default: 20)"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset collection (drop and recreate)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse knowledge base without uploading (для тестирования)"
    )
    args = parser.parse_args()

    kb_dir = Path(__file__).parent.parent / "KNOWLEDGE_BASE"

    if not kb_dir.exists():
        print(f"❌ ERROR: Knowledge base directory not found: {kb_dir}")
        sys.exit(1)

    migration = SupabaseMigration(
        kb_dir=kb_dir,
        batch_size=args.batch_size,
        dry_run=args.dry_run
    )

    await migration.migrate(reset=args.reset)


if __name__ == "__main__":
    asyncio.run(main())
