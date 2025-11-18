#!/bin/bash
# Мониторинг прогресса Qdrant миграции

echo "🔍 МОНИТОРИНГ QDRANT МИГРАЦИИ"
echo "======================================"
echo ""

while true; do
    clear
    echo "🕐 $(date '+%H:%M:%S')"
    echo "======================================"
    echo ""

    # Последние 30 строк лога
    if [ -f qdrant_migration_FULL.log ]; then
        echo "📋 ПОСЛЕДНИЕ СТРОКИ ЛОГА:"
        tail -30 qdrant_migration_FULL.log
        echo ""
        echo "======================================"

        # Статистика парсинга
        echo "📊 СТАТИСТИКА ПАРСИНГА:"
        grep -E "(FAQ parsed|Lessons parsed|Corrections parsed|Questions parsed|Brainwrites parsed)" qdrant_migration_FULL.log | tail -5
        echo ""

        # Прогресс загрузки
        echo "📤 ПРОГРЕСС ЗАГРУЗКИ:"
        grep -E "Batch \d+/\d+ uploaded" qdrant_migration_FULL.log | tail -1
        echo ""

        # Финальная статистика (если завершено)
        if grep -q "Migration completed" qdrant_migration_FULL.log; then
            echo "✅ МИГРАЦИЯ ЗАВЕРШЕНА!"
            echo ""
            grep -A 10 "MIGRATION STATISTICS" qdrant_migration_FULL.log
            break
        fi
    else
        echo "⏳ Ожидание старта миграции..."
    fi

    sleep 10
done
