#!/usr/bin/env python3
"""
Миграция только glossary терминов в Supabase.
Не трогает существующие entities.
"""

import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Добавить корень в PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from supabase import create_client
from openai import OpenAI
from scripts.parse_knowledge_base import KnowledgeBaseParser

# Load environment
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    # Initialize clients
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not all([supabase_url, supabase_key, openai_key]):
        logger.error("Missing required environment variables")
        return

    supabase = create_client(supabase_url, supabase_key)
    openai_client = OpenAI(api_key=openai_key)

    # Parse glossary
    kb_dir = root_dir / "KNOWLEDGE_BASE"
    parser = KnowledgeBaseParser(kb_dir)
    glossary_file = kb_dir / "KNOWLEDGE_BASE_FULL.md"

    logger.info("📖 Parsing Glossary Terms...")
    glossary_terms = parser.parse_glossary(glossary_file)
    logger.info(f"✅ Found {len(glossary_terms)} terms")

    # Delete existing glossary entries
    logger.info("🗑️ Deleting existing glossary entries...")
    try:
        supabase.table("course_knowledge").delete().eq("entity_type", "glossary").execute()
        logger.info("✅ Existing glossary entries deleted")
    except Exception as e:
        logger.warning(f"⚠️ Could not delete existing entries: {e}")

    # Upload glossary terms
    logger.info("📤 Uploading glossary terms...")
    success_count = 0

    for idx, term in enumerate(glossary_terms):
        try:
            # Generate embedding
            content = f"{term.term}: {term.definition}"
            response = openai_client.embeddings.create(
                input=content,
                model="text-embedding-3-small"
            )
            embedding = response.data[0].embedding

            # Prepare row
            row = {
                "id": f"glossary_{idx}",
                "entity_type": "glossary",
                "title": term.term,
                "content": content,
                "metadata": {
                    "lesson_number": term.lesson_number,
                    "keywords": term.keywords
                },
                "embedding": embedding,
                "created_at": datetime.utcnow().isoformat()
            }

            # Upsert to Supabase
            supabase.table("course_knowledge").upsert(row).execute()
            success_count += 1

            if (idx + 1) % 10 == 0:
                logger.info(f"  Progress: {idx + 1}/{len(glossary_terms)}")

            # Rate limit
            time.sleep(0.05)

        except Exception as e:
            logger.error(f"❌ Failed to upload term '{term.term}': {e}")

    logger.info(f"\n{'=' * 60}")
    logger.info(f"✅ MIGRATION COMPLETE")
    logger.info(f"   Uploaded: {success_count}/{len(glossary_terms)} terms")
    logger.info(f"{'=' * 60}")


if __name__ == "__main__":
    main()
