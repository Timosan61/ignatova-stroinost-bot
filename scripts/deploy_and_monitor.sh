#!/bin/bash

# Deploy and Monitor Script
# Автоматизирует git push + проверку Railway deployment

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Deploy and Monitor Script${NC}\n"

# Проверка наличия изменений
if [[ -z $(git status -s) ]]; then
    echo -e "${YELLOW}⚠️  Нет изменений для коммита${NC}"
    exit 0
fi

# Показать изменения
echo -e "${BLUE}📝 Изменения:${NC}"
git status -s
echo ""

# Запросить сообщение коммита
if [ -z "$1" ]; then
    echo -e "${YELLOW}Введите сообщение коммита:${NC}"
    read -r commit_message
else
    commit_message="$1"
fi

if [ -z "$commit_message" ]; then
    echo -e "${RED}❌ Сообщение коммита не может быть пустым${NC}"
    exit 1
fi

# Добавить изменения
echo -e "${BLUE}📦 Добавление файлов...${NC}"
git add .

# Создать коммит
echo -e "${BLUE}💾 Создание коммита...${NC}"
git commit -m "$commit_message

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push на GitHub
echo -e "${BLUE}⬆️  Отправка на GitHub...${NC}"
git push origin main

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Ошибка при push на GitHub${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Push успешен!${NC}\n"

# Подождать запуска deployment
echo -e "${YELLOW}⏳ Ожидание запуска Railway deployment (90 секунд)...${NC}"
for i in {90..1}; do
    printf "\r   Осталось: %02d секунд" $i
    sleep 1
done
echo -e "\n"

# Проверить статус deployment
echo -e "${BLUE}🔍 Проверка статуса deployment:${NC}\n"
python3 scripts/railway_monitor.py info

# Спросить о мониторинге
echo -e "\n${YELLOW}Запустить мониторинг в реальном времени? (y/n)${NC}"
read -r response

if [[ "$response" =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}🔍 Запуск мониторинга (Ctrl+C для выхода)...${NC}\n"
    python3 scripts/railway_monitor.py monitor
else
    echo -e "${GREEN}✅ Готово!${NC}"
fi
