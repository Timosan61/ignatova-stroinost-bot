import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
ZEP_API_KEY = os.getenv('ZEP_API_KEY', '').strip()  # Strip whitespace and newlines
BOT_USERNAME = os.getenv('BOT_USERNAME')

# FalkorDB & Graphiti Configuration (496x faster than Neo4j!)
FALKORDB_HOST = os.getenv('FALKORDB_HOST', 'localhost')
FALKORDB_PORT = int(os.getenv('FALKORDB_PORT', '6379'))
FALKORDB_USERNAME = os.getenv('FALKORDB_USERNAME', 'falkordb')  # Default username для FalkorDB Cloud
FALKORDB_PASSWORD = os.getenv('FALKORDB_PASSWORD', '')
FALKORDB_DATABASE = os.getenv('FALKORDB_DATABASE', 'knowledge_graph')

# Legacy Neo4j support (deprecated, use FalkorDB instead)
NEO4J_URI = os.getenv('NEO4J_URI', '')
NEO4J_USER = os.getenv('NEO4J_USERNAME') or os.getenv('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', '')
GRAPHITI_ENABLED = os.getenv('GRAPHITI_ENABLED', 'false').lower() in ('true', '1', 'yes')

# Graphiti LLM Configuration (cost optimization - использовать GPT-4o-mini вместо GPT-4o)
# MODEL_NAME - основная модель для entity/relationship extraction
# SMALL_MODEL_NAME - модель для вспомогательных операций (deduplication, summarization)
MODEL_NAME = os.getenv('MODEL_NAME', 'gpt-4o-mini')
SMALL_MODEL_NAME = os.getenv('SMALL_MODEL_NAME', 'gpt-4o-mini')

# Qdrant Vector Database Configuration
QDRANT_URL = os.getenv('QDRANT_URL', '')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY', '')
QDRANT_COLLECTION = os.getenv('QDRANT_COLLECTION', 'course_knowledge')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
USE_QDRANT = os.getenv('USE_QDRANT', 'false').lower() in ('true', '1', 'yes')

# Supabase Vector Store Configuration
SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY', '')
SUPABASE_TABLE = os.getenv('SUPABASE_TABLE', 'course_knowledge')
OPENAI_EMBEDDING_MODEL = os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')
USE_SUPABASE = os.getenv('USE_SUPABASE', 'false').lower() in ('true', '1', 'yes')

# Knowledge Search Configuration
SEARCH_LIMIT = int(os.getenv('SEARCH_LIMIT', '10'))  # Количество результатов из базы знаний

# Абсолютный путь к файлу инструкций
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTRUCTION_FILE = os.path.join(BASE_DIR, 'data', 'instruction.json')

# OpenAI Model Configuration
# Поддерживает env переменную для гибкого переключения между моделями
# Default: GPT-5.1 (gpt-5.1-2025-11-13) - улучшенное reasoning для длинных диалогов
# Rollback: export OPENAI_MODEL=gpt-4o
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-5.1-2025-11-13')
ANTHROPIC_MODEL = 'claude-3-5-sonnet-20241022'

# Настройки голосовых сообщений
VOICE_ENABLED = os.getenv('VOICE_ENABLED', 'false').lower() in ('true', '1', 'yes')
VOICE_LANGUAGE = 'ru'  # Язык по умолчанию для транскрипции
VOICE_MAX_DURATION = 600  # 10 минут максимальная длительность
VOICE_MAX_SIZE_MB = 25  # 25MB максимальный размер файла

# Debug Configuration
DEBUG_INFO_ENABLED = os.getenv('DEBUG_INFO_ENABLED', 'false').lower() in ('true', '1', 'yes')

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
# Проверки API ключей (не критичные для запуска)
if not OPENAI_API_KEY:
    print("⚠️ OPENAI_API_KEY не найден в переменных окружения - голосовые сообщения будут отключены")
if not ANTHROPIC_API_KEY:
    print("⚠️ ANTHROPIC_API_KEY не найден в переменных окружения")
if not ZEP_API_KEY:
    print("⚠️ ZEP_API_KEY не найден в переменных окружения")

# Информация о статусе голосовых сообщений
if VOICE_ENABLED:
    if OPENAI_API_KEY:
        print("✅ Голосовые сообщения включены (VOICE_ENABLED=true, OpenAI API доступен)")
    else:
        print("⚠️ Голосовые сообщения включены, но OpenAI API недоступен")
else:
    print("❌ Голосовые сообщения отключены (VOICE_ENABLED=false)")

# Информация о статусе Graphiti Knowledge Graph
if GRAPHITI_ENABLED:
    if FALKORDB_HOST and FALKORDB_PASSWORD:
        print(f"✅ Graphiti Knowledge Graph включен (GRAPHITI_ENABLED=true, FalkorDB: {FALKORDB_HOST}:{FALKORDB_PORT})")
    elif NEO4J_URI and NEO4J_PASSWORD:
        print("⚠️ Graphiti включен с legacy Neo4j (рекомендуется переключиться на FalkorDB)")
    else:
        print("⚠️ Graphiti включен, но FalkorDB не настроен (FALKORDB_HOST/FALKORDB_PASSWORD не заданы)")
else:
    print("❌ Graphiti Knowledge Graph отключен (GRAPHITI_ENABLED=false)")

# Информация о статусе Qdrant Vector Database
if USE_QDRANT:
    if QDRANT_URL and QDRANT_API_KEY:
        print("🔵 Qdrant Vector Database включен (USE_QDRANT=true, Qdrant Cloud configured)")
    else:
        print("⚠️ Qdrant включен, но не настроен (QDRANT_URL/QDRANT_API_KEY не заданы)")
else:
    print("⚪ Qdrant Vector Database отключен (USE_QDRANT=false)")

# Информация о статусе Supabase Vector Store
if USE_SUPABASE:
    if SUPABASE_URL and SUPABASE_SERVICE_KEY and OPENAI_API_KEY:
        print("🟣 Supabase Vector Store включен (USE_SUPABASE=true, OpenAI embeddings ready)")
    elif not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("⚠️ Supabase включен, но не настроен (SUPABASE_URL/SUPABASE_SERVICE_KEY не заданы)")
    elif not OPENAI_API_KEY:
        print("⚠️ Supabase включен, но OpenAI API недоступен (требуется для embeddings)")
else:
    print("⚪ Supabase Vector Store отключен (USE_SUPABASE=false)")