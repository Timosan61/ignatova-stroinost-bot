#!/usr/bin/env python3
"""
Debug script to check entity_type in Qdrant search results
"""

import os
import sys
from pathlib import Path

# Добавить корень в PYTHONPATH
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

# Установить environment variables
os.environ['QDRANT_URL'] = 'https://33d94c1b-cc7f-4b71-82cc-dcee289122f0.eu-central-1-0.aws.cloud.qdrant.io:6333'
os.environ['QDRANT_API_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.UTJlYE3KsxYq-NCTexIE035VcMuZ5KiTAf79ezuMYgg'
os.environ['QDRANT_COLLECTION'] = 'course_knowledge'
os.environ['USE_QDRANT'] = 'true'

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

print("=" * 80)
print("🔍 ТЕСТ ENTITY_TYPE В QDRANT")
print("=" * 80)
print()

# Подключение к Qdrant
client = QdrantClient(
    url=os.environ['QDRANT_URL'],
    api_key=os.environ['QDRANT_API_KEY'],
    timeout=30
)

# Получить несколько точек с entity_type=question
print("📊 Получаем 3 точки с entity_type='question'...")
print()

try:
    # Scroll через фильтр
    scroll_result = client.scroll(
        collection_name='course_knowledge',
        scroll_filter=Filter(
            must=[
                FieldCondition(
                    key="entity_type",
                    match=MatchValue(value="question")
                )
            ]
        ),
        limit=3,
        with_payload=True,
        with_vectors=False
    )

    points = scroll_result[0]  # (points, next_offset)

    print(f"✅ Найдено: {len(points)} точек")
    print()

    for idx, point in enumerate(points, 1):
        print(f"{'='*60}")
        print(f"ТОЧКА #{idx}")
        print(f"{'='*60}")
        print(f"ID: {point.id}")
        print()

        if point.payload:
            print(f"PAYLOAD KEYS: {list(point.payload.keys())}")
            print()

            # Детально проверяем entity_type
            if 'entity_type' in point.payload:
                entity_type_value = point.payload['entity_type']
                print(f"✅ entity_type НАЙДЕН:")
                print(f"   Значение: '{entity_type_value}'")
                print(f"   Тип: {type(entity_type_value).__name__}")
            else:
                print(f"❌ entity_type НЕ НАЙДЕН в payload!")

            print()

            # Показать другие ключевые поля
            for key in ['title', 'content', 'category', 'source']:
                if key in point.payload:
                    value = point.payload[key]
                    if isinstance(value, str) and len(value) > 100:
                        value = value[:100] + "..."
                    print(f"   {key}: {value}")

            print()
        else:
            print("❌ PAYLOAD ПУСТОЙ!")

        print()

    print("="*80)
    print("✅ ТЕСТ ЗАВЕРШЁН")
    print("="*80)

except Exception as e:
    print(f"❌ ОШИБКА: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
