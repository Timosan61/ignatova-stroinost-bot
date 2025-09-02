import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
ZEP_API_KEY = os.getenv('ZEP_API_KEY', '')
BOT_USERNAME = os.getenv('BOT_USERNAME')

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