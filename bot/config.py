import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
ZEP_API_KEY = os.getenv('ZEP_API_KEY', '').strip()  # Strip whitespace and newlines
BOT_USERNAME = os.getenv('BOT_USERNAME')

# Neo4j & Graphiti Configuration
NEO4J_URI = os.getenv('NEO4J_URI', '')
# Поддержка обоих вариантов: NEO4J_USERNAME (Railway default) и NEO4J_USER
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

# Абсолютный путь к файлу инструкций
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTRUCTION_FILE = os.path.join(BASE_DIR, 'data', 'instruction.json')
OPENAI_MODEL = 'gpt-4o'
ANTHROPIC_MODEL = 'claude-3-5-sonnet-20241022'

# Настройки голосовых сообщений
VOICE_ENABLED = os.getenv('VOICE_ENABLED', 'false').lower() in ('true', '1', 'yes')
VOICE_LANGUAGE = 'ru'  # Язык по умолчанию для транскрипции
VOICE_MAX_DURATION = 600  # 10 минут максимальная длительность
VOICE_MAX_SIZE_MB = 25  # 25MB максимальный размер файла

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
    if NEO4J_URI and NEO4J_PASSWORD:
        print("✅ Graphiti Knowledge Graph включен (GRAPHITI_ENABLED=true, Neo4j configured)")
    else:
        print("⚠️ Graphiti включен, но Neo4j не настроен (NEO4J_URI/NEO4J_PASSWORD не заданы)")
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