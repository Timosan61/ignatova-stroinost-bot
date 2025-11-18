# Gamma API - Полная документация

## Оглавление
1. [Введение](#введение)
2. [Доступ и цены](#доступ-и-цены)
3. [Аутентификация](#аутентификация)
4. [Основные концепции](#основные-концепции)
5. [API Endpoints](#api-endpoints)
6. [Параметры Generate API](#параметры-generate-api)
7. [Параметры Create from Template API](#параметры-create-from-template-api)
8. [Модели генерации изображений](#модели-генерации-изображений)
9. [Поддерживаемые языки](#поддерживаемые-языки)
10. [Коды ошибок](#коды-ошибок)
11. [Примеры использования](#примеры-использования)
12. [Best Practices](#best-practices)

---

## Введение

**Gamma API v1.0** — Generally Available (GA) с 5 ноября 2025 года.

Gamma API позволяет программно создавать:
- **Презентации** (presentations)
- **Документы** (documents)
- **Посты для соцсетей** (social media posts)
- **Веб-страницы** (webpages)

### Основные возможности
- ✅ Генерация контента на **60+ языках**
- ✅ **AI-генерация изображений** (20+ моделей)
- ✅ Кастомизация тем, тона, аудитории
- ✅ Экспорт в **PDF** и **PPTX**
- ✅ Интеграция с автоматизацией (Make, Zapier, N8N, Workato)

### Base URL
```
https://public-api.gamma.app/v1.0
```

---

## Доступ и цены

### Требования к подписке
API доступен для подписчиков:
- ✅ **Pro**
- ✅ **Ultra**
- ✅ **Teams**
- ✅ **Business**

### Получение API ключа
1. Войдите в свой аккаунт Gamma (Pro или выше)
2. Перейдите в **Settings and Members**
3. Откройте вкладку **API key**
4. Нажмите **Create API key**

### Модель оплаты: Кредиты
API использует **кредитную систему** вместо оплаты за запрос.

#### Стоимость в кредитах

**Генерация карточек:**
- 3-4 кредита за карточку

**Генерация изображений (зависит от модели):**
- **Basic модели** (Flux Fast, Imagen 3 Fast): ~2 кредита/изображение
- **Standard модели** (Flux Pro, Imagen 3): ~8-10 кредитов/изображение
- **Premium модели** (Imagen 4, Recraft, GPT Image): ~20-30 кредитов/изображение
- **Ultra модели** (только Ultra план): ~30-120 кредитов/изображение

#### Примеры стоимости
- **Презентация** (10 карточек + 5 изображений Basic): ~40-50 кредитов
- **Документ** (20 карточек + 15 изображений Premium): ~360-680 кредитов
- **Социальные посты** (30 карточек + 30 изображений Ultra): ~1290-3720 кредитов

#### Управление кредитами
При исчерпании кредитов:
1. **Обновить план** на более высокий уровень
2. **Докупить кредиты** вручную
3. **Включить автопополнение** (рекомендуется)

⚠️ **Внимание:** Стоимость в кредитах может изменяться. Проверяйте актуальные цены в Help Center.

---

## Аутентификация

### Формат API ключа
```
sk-gamma-xxxxxxxx
```

### HTTP Header
```http
X-API-KEY: sk-gamma-xxxxxxxx
```

⚠️ **Важно:** Используйте заголовок `X-API-KEY`, а **НЕ** `Authorization` или `Bearer`.

### Пример запроса
```bash
curl --request POST \
  --url https://public-api.gamma.app/v1.0/generations \
  --header 'Content-Type: application/json' \
  --header 'X-API-KEY: sk-gamma-xxxxxxxx' \
  --data '{
    "inputText": "Create a presentation about AI",
    "textMode": "generate"
  }'
```

### Ошибки аутентификации
- **401 Unauthorized**: Неверный API ключ или аккаунт не Pro/Ultra/Teams/Business

---

## Основные концепции

### Два типа API

| API | Назначение | Когда использовать |
|-----|-----------|-------------------|
| **Generate API** | Создание с нуля | Максимальная гибкость, без шаблона |
| **Create from Template API** | На основе шаблона | Есть готовый шаблон, нужно адаптировать контент |

### Форматы вывода
- `presentation` - Презентация (по умолчанию)
- `document` - Документ
- `social` - Пост для соцсетей
- `webpage` - Веб-страница

### Режимы обработки текста (textMode)
| Режим | Описание |
|-------|----------|
| `generate` | Переписывает и расширяет контент |
| `condense` | Сокращает длинный текст |
| `preserve` | Сохраняет текст как есть (с возможными структурными изменениями) |

### Источники изображений (imageOptions.source)
- `aiGenerated` - AI-генерация (DALL-E, Flux, Imagen, и др.)
- `pictographic` - Пиктограммы
- `unsplash` - Бесплатные фото Unsplash
- `giphy` - GIF анимации
- `webAllImages` - Все изображения из веба
- `webFreeToUse` - Бесплатные для использования
- `webFreeToUseCommercially` - Бесплатные для коммерческого использования
- `placeholder` - Placeholder изображения
- `noImages` - Без изображений

---

## API Endpoints

### 1. Generate API - Создание презентации с нуля

**Endpoint:**
```http
POST https://public-api.gamma.app/v1.0/generations
```

**Назначение:** Создание новой презентации без использования шаблона.

**Headers:**
```http
Content-Type: application/json
X-API-KEY: sk-gamma-xxxxxxxx
```

**Обязательные параметры:**
- `inputText` (string) - Контент для генерации (до 100,000 токенов / ~400,000 символов)
- `textMode` (string) - Режим обработки текста: `generate`, `condense`, или `preserve`

**Response:**
```json
{
  "generationId": "yyyyyyyyyy",
  "status": "processing",
  "createdAt": "2025-11-16T12:00:00Z"
}
```

---

### 2. Create from Template API - Создание на основе шаблона

**Endpoint:**
```http
POST https://public-api.gamma.app/v1.0/generations/from-template
```

**Статус:** ⚠️ **BETA** (функциональность и цены могут измениться)

**Назначение:** Создание контента на основе существующего шаблона Gamma.

**Обязательные параметры:**
- `gammaId` (string) - ID существующего шаблона Gamma
- `prompt` (string) - Описание контента (текст, URL изображений, инструкции)

**Пример:**
```bash
curl --request POST \
  --url https://public-api.gamma.app/v1.0/generations/from-template \
  --header 'Content-Type: application/json' \
  --header 'X-API-KEY: sk-gamma-xxxxxxxx' \
  --data '{
    "gammaId": "template-12345",
    "prompt": "Create a sales deck for our new product",
    "themeId": 32852
  }'
```

---

### 3. List Themes - Получить список тем

**Endpoint:**
```http
GET https://public-api.gamma.app/v1.0/themes
```

**Назначение:** Получить список доступных тем в вашем workspace.

**Headers:**
```http
X-API-KEY: sk-gamma-xxxxxxxx
```

**Response:**
```json
{
  "themes": [
    {
      "id": 32852,
      "name": "Modern Blue",
      "preview_url": "https://..."
    },
    {
      "id": 32461,
      "name": "Corporate Gray",
      "preview_url": "https://..."
    }
  ]
}
```

---

### 4. List Folders - Получить список папок

**Endpoint:**
```http
GET https://public-api.gamma.app/v1.0/folders
```

**Назначение:** Получить список доступных папок для организации.

**Headers:**
```http
X-API-KEY: sk-gamma-xxxxxxxx
```

**Response:**
```json
{
  "folders": [
    {
      "id": "folder-123",
      "name": "Marketing",
      "parent_id": null
    },
    {
      "id": "folder-456",
      "name": "Q1 2025",
      "parent_id": "folder-123"
    }
  ]
}
```

---

## Параметры Generate API

### Обязательные параметры

#### inputText (string, required)
Контент для генерации презентации.

**Ограничения:**
- Максимум: **100,000 токенов** (~400,000 символов)

**Возможности:**
- ✅ Markdown форматирование
- ✅ Вставка URL изображений
- ✅ Управление разрывами карточек: `\n---\n`

**Пример:**
```json
{
  "inputText": "# AI Revolution\n\nArtificial Intelligence is transforming industries.\n\n---\n\n## Key Benefits\n- Automation\n- Efficiency\n- Innovation"
}
```

---

#### textMode (string, required)
Режим обработки входного текста.

**Значения:**
- `generate` - Переписывает и расширяет контент (по умолчанию)
- `condense` - Сокращает длинный текст
- `preserve` - Сохраняет текст без изменений (с возможными структурными корректировками)

---

### Опциональные параметры верхнего уровня

#### format (string)
Тип создаваемого контента.

**Значения:**
- `presentation` (по умолчанию)
- `document`
- `social`
- `webpage`

---

#### themeId (integer)
ID темы для оформления.

**По умолчанию:** Тема workspace по умолчанию

**Как получить:** Используйте `GET /v1.0/themes`

**Пример:**
```json
{
  "themeId": 32852
}
```

---

#### numCards (integer)
Количество карточек для генерации.

**Диапазон:**
- **Pro план:** 1-60
- **Ultra план:** 1-75

**По умолчанию:** 10

---

#### cardSplit (string)
Метод разделения контента на карточки.

**Значения:**
- `auto` - Автоматическое разделение (по умолчанию)
- `inputTextBreaks` - Использовать `\n---\n` разделители из inputText

---

#### additionalInstructions (string)
Дополнительные инструкции для генерации.

**Ограничения:**
- 1-2000 символов

**Пример:**
```json
{
  "additionalInstructions": "Use bold colors and include data visualizations. Focus on startup audience."
}
```

---

#### folderIds (array of strings)
Массив ID папок для сохранения.

**Как получить:** Используйте `GET /v1.0/folders`

**Пример:**
```json
{
  "folderIds": ["folder-123", "folder-456"]
}
```

---

#### exportAs (string)
Формат экспорта после генерации.

**Значения:**
- `pdf` - Экспорт в PDF
- `pptx` - Экспорт в PowerPoint

**Пример:**
```json
{
  "exportAs": "pdf"
}
```

---

### Вложенные параметры: textOptions

Настройки генерации текста.

#### textOptions.amount (string)
Объем генерируемого текста.

**Значения:**
- `brief` - Краткий
- `medium` - Средний (по умолчанию)
- `detailed` - Детальный
- `extensive` - Обширный

---

#### textOptions.tone (string)
Тон/стиль текста.

**Ограничения:**
- 1-500 символов

**Примеры:**
- "Professional and formal"
- "Friendly and conversational"
- "Technical and precise"
- "Enthusiastic and motivating"

---

#### textOptions.audience (string)
Целевая аудитория.

**Ограничения:**
- 1-500 символов

**Примеры:**
- "C-level executives"
- "College students"
- "Healthcare professionals"
- "General public"

---

#### textOptions.language (string)
Язык генерации (ISO код).

**По умолчанию:** `en` (English US)

**Поддержка:** 77 языков (см. раздел [Поддерживаемые языки](#поддерживаемые-языки))

**Пример:**
```json
{
  "textOptions": {
    "amount": "detailed",
    "tone": "professional and inspiring",
    "audience": "startup founders and investors",
    "language": "en"
  }
}
```

---

### Вложенные параметры: imageOptions

Настройки генерации/выбора изображений.

#### imageOptions.source (string)
Источник изображений.

**Значения:**
- `aiGenerated` - AI генерация (по умолчанию)
- `pictographic` - Пиктограммы
- `unsplash` - Unsplash фото
- `giphy` - GIF анимации
- `webAllImages` - Все веб-изображения
- `webFreeToUse` - Бесплатные для использования
- `webFreeToUseCommercially` - Бесплатные для коммерческого использования
- `placeholder` - Placeholder
- `noImages` - Без изображений

---

#### imageOptions.model (string)
Модель AI для генерации изображений (только если `source: "aiGenerated"`).

**По умолчанию:** Автовыбор Gamma

**Доступные модели:** См. раздел [Модели генерации изображений](#модели-генерации-изображений)

**Пример:**
```json
{
  "imageOptions": {
    "source": "aiGenerated",
    "model": "imagen-4-pro"
  }
}
```

---

#### imageOptions.style (string)
Художественный стиль для AI-генерации.

**Ограничения:**
- 1-500 символов

**Примеры:**
- "minimalist and modern"
- "vibrant and colorful"
- "professional photography style"
- "hand-drawn illustrations"

**Рекомендация:** Всегда указывайте стиль для создания визуально согласованных изображений.

**Пример:**
```json
{
  "imageOptions": {
    "source": "aiGenerated",
    "model": "flux-1-pro",
    "style": "modern minimalist design with soft pastel colors"
  }
}
```

---

### Вложенные параметры: cardOptions

Настройки карточек презентации.

#### cardOptions.dimensions (string)
Соотношение сторон карточек.

**Варианты зависят от формата:**

**Presentation:**
- `16:9` (по умолчанию)
- `4:3`

**Document:**
- `A4 portrait` (по умолчанию)
- `A4 landscape`
- `Letter portrait`
- `Letter landscape`

**Social:**
- `1:1` (квадрат)
- `16:9` (широкий)
- `9:16` (вертикальный)

---

#### cardOptions.headerFooter (object)
Настройки колонтитулов.

**Доступные позиции:**
- `topLeft`
- `topCenter`
- `topRight`
- `bottomLeft`
- `bottomCenter`
- `bottomRight`

**Пример:**
```json
{
  "cardOptions": {
    "dimensions": "16:9",
    "headerFooter": {
      "bottomRight": "© 2025 Company Name",
      "bottomLeft": "Confidential"
    }
  }
}
```

---

### Вложенные параметры: sharingOptions

Настройки доступа к презентации.

**Уровни доступа:**
- `workspace` - Только workspace
- `external` - Внешний доступ по ссылке
- `email` - Доступ по email приглашению

**Пример:**
```json
{
  "sharingOptions": {
    "access": "external",
    "allowComments": true
  }
}
```

---

### Полный пример запроса Generate API

```json
{
  "inputText": "# AI Revolution in Healthcare\n\nArtificial Intelligence is transforming patient care.\n\n---\n\n## Key Applications\n- Diagnostic accuracy\n- Personalized treatment\n- Drug discovery\n\n---\n\n## Benefits\n- Improved outcomes\n- Cost reduction\n- Faster diagnoses",
  "textMode": "generate",
  "format": "presentation",
  "numCards": 15,
  "cardSplit": "inputTextBreaks",
  "themeId": 32852,
  "additionalInstructions": "Use medical imagery and professional tone. Include statistics where possible.",
  "textOptions": {
    "amount": "detailed",
    "tone": "professional and authoritative",
    "audience": "healthcare professionals and hospital administrators",
    "language": "en"
  },
  "imageOptions": {
    "source": "aiGenerated",
    "model": "imagen-4-pro",
    "style": "clean medical photography with soft blue tones"
  },
  "cardOptions": {
    "dimensions": "16:9",
    "headerFooter": {
      "bottomRight": "© 2025 HealthTech Inc.",
      "topRight": "Confidential"
    }
  },
  "folderIds": ["folder-123"],
  "exportAs": "pdf"
}
```

---

## Параметры Create from Template API

### Обязательные параметры

#### gammaId (string, required)
ID существующего шаблона Gamma.

**Как получить:**
1. Откройте шаблон в Gamma web app
2. ID находится в URL: `gamma.app/docs/{gammaId}`

---

#### prompt (string, required)
Описание контента для адаптации шаблона.

**Возможности:**
- ✅ Текстовое описание
- ✅ URL изображений
- ✅ Инструкции по использованию

**Пример:**
```json
{
  "gammaId": "abc123def456",
  "prompt": "Create a Q1 2025 sales review for our SaaS product. Include revenue growth, customer acquisition, and market expansion plans. Use professional tone."
}
```

---

### Опциональные параметры

**Create from Template API** поддерживает те же опциональные параметры, что и Generate API:
- `themeId`
- `imageOptions`
- `folderIds`
- `exportAs`
- и другие

---

## Модели генерации изображений

### Таблица доступных моделей

| Модель | Значение `imageOptions.model` | Кредиты/изображение | Доступность |
|--------|-------------------------------|---------------------|-------------|
| **BASIC TIER (2 кредита)** ||||
| Flux Fast 1.1 | `flux-1-quick` | 2 | Все планы |
| Flux Kontext Fast | `flux-kontext-fast` | 2 | Все планы |
| Imagen 3 Fast | `imagen-3-flash` | 2 | Все планы |
| Luma Photon Flash | `luma-photon-flash-1` | 2 | Все планы |
| **STANDARD TIER (8-15 кредитов)** ||||
| Flux Pro | `flux-1-pro` | 8 | Все планы |
| Imagen 3 | `imagen-3-pro` | 8 | Все планы |
| Ideogram 3 Turbo | `ideogram-v3-turbo` | 10 | Все планы |
| Luma Photon | `luma-photon-1` | 10 | Все планы |
| Leonardo Phoenix | `leonardo-phoenix` | 15 | Все планы |
| **PREMIUM TIER (20-33 кредита)** ||||
| Flux Kontext Pro | `flux-kontext-pro` | 20 | Все планы |
| Gemini 2.5 Flash | `gemini-2.5-flash-image` | 20 | Все планы |
| Ideogram 3 | `ideogram-v3` | 20 | Все планы |
| Imagen 4 | `imagen-4-pro` | 20 | Все планы |
| Recraft | `recraft-v3` | 20 | Все планы |
| GPT Image | `gpt-image-1-medium` | 30 | Все планы |
| Dall E 3 | `dall-e-3` | 33 | Все планы |
| **ULTRA TIER (30-120 кредитов)** ||||
| Flux Ultra | `flux-1-ultra` | 30 | **Только Ultra** |
| Imagen 4 Ultra | `imagen-4-ultra` | 30 | **Только Ultra** |
| Recraft Vector Illustration | `recraft-v3-svg` | 40 | **Только Ultra** |
| Flux Kontext Max | `flux-kontext-max` | 40 | **Только Ultra** |
| Ideogram 3.0 Quality | `ideogram-v3-quality` | 45 | **Только Ultra** |
| GPT Image Detailed | `gpt-image-1-high` | 120 | **Только Ultra** |

### Рекомендации по выбору модели

**Для презентаций (общий случай):**
- 🥇 `imagen-4-pro` - Лучшее соотношение качества и цены
- 🥈 `flux-1-pro` - Быстрая альтернатива

**Для минимальной стоимости:**
- `flux-1-quick` или `imagen-3-flash` - 2 кредита

**Для максимального качества (Ultra план):**
- `imagen-4-ultra` или `gpt-image-1-high`

**Для векторной графики (Ultra план):**
- `recraft-v3-svg` - SVG иллюстрации

---

## Поддерживаемые языки

**По умолчанию:** `en` (English US)

**Всего поддерживается:** 77 языковых вариантов

### Полный список кодов языков

```
af       - Afrikaans
sq       - Albanian
ar       - Arabic
ar-sa    - Arabic (Saudi Arabia)
bn       - Bengali
bs       - Bosnian
bg       - Bulgarian
ca       - Catalan
hr       - Croatian
cs       - Czech
da       - Danish
nl       - Dutch
en       - English (US)
en-gb    - English (UK)
en-in    - English (India)
et       - Estonian
fi       - Finnish
fr       - French
de       - German
el       - Greek
gu       - Gujarati
ha       - Hausa
he       - Hebrew
hi       - Hindi
hu       - Hungarian
is       - Icelandic
id       - Indonesian
it       - Italian
ja       - Japanese
ja-da    - Japanese (Dialect)
kn       - Kannada
kk       - Kazakh
ko       - Korean
lv       - Latvian
lt       - Lithuanian
mk       - Macedonian
ms       - Malay
ml       - Malayalam
mr       - Marathi
nb       - Norwegian Bokmål
fa       - Persian
pl       - Polish
pt-br    - Portuguese (Brazil)
pt-pt    - Portuguese (Portugal)
ro       - Romanian
ru       - Russian
sr       - Serbian
zh-cn    - Simplified Chinese
sl       - Slovenian
es       - Spanish
es-419   - Spanish (Latin America)
es-mx    - Spanish (Mexico)
es-es    - Spanish (Spain)
sw       - Swahili
sv       - Swedish
tl       - Tagalog
ta       - Tamil
te       - Telugu
th       - Thai
zh-tw    - Traditional Chinese
tr       - Turkish
uk       - Ukrainian
ur       - Urdu
uz       - Uzbek
vi       - Vietnamese
cy       - Welsh
yo       - Yoruba
```

### Пример использования

```json
{
  "textOptions": {
    "language": "ru"
  }
}
```

---

## Коды ошибок

### Таблица HTTP ошибок

| Код | Сообщение | Проблема | Решение |
|-----|-----------|----------|---------|
| **400** | Input validation errors | Некорректные параметры запроса | Проверьте все параметры согласно документации |
| **401** | Invalid API key | API ключ неверный или аккаунт не Pro+ | Проверьте ключ и уровень подписки |
| **403** | Forbidden / No credits left | Закончились кредиты | Купите кредиты или обновите план |
| **404** | Generation ID not found | ID генерации не существует | Проверьте правильность generationId |
| **422** | Failed to generate text | Генерация вернула пустой результат | Уточните инструкции и параметры |
| **429** | Too many requests | Превышен rate limit | Подождите перед повторной попыткой, используйте exponential backoff |
| **500** | An error occurred while generating | Внутренняя ошибка сервера | Свяжитесь с поддержкой, предоставьте `x-request-id` header |
| **502** | Bad gateway | Временная проблема gateway | Повторите запрос через несколько секунд |

### Обработка ошибок

#### Пример response с ошибкой

```json
{
  "error": {
    "code": 403,
    "message": "No credits left",
    "details": "Your account has 0 credits remaining. Please purchase additional credits or upgrade your plan."
  }
}
```

#### Рекомендации

1. **401 Unauthorized:**
   - Проверьте формат API ключа: `sk-gamma-xxxxxxxx`
   - Убедитесь, что используете `X-API-KEY` header
   - Проверьте уровень подписки (Pro/Ultra/Teams/Business)

2. **403 Forbidden:**
   - Проверьте баланс кредитов в dashboard
   - Включите автопополнение кредитов

3. **429 Too Many Requests:**
   - Реализуйте exponential backoff
   - Используйте очередь запросов

4. **500/502 Server Errors:**
   - Сохраните `x-request-id` из response headers
   - Повторите запрос через 5-10 секунд
   - Свяжитесь с поддержкой при повторении проблемы

---

## Примеры использования

### Пример 1: Минимальный запрос (презентация)

```bash
curl --request POST \
  --url https://public-api.gamma.app/v1.0/generations \
  --header 'Content-Type: application/json' \
  --header 'X-API-KEY: sk-gamma-xxxxxxxx' \
  --data '{
    "inputText": "Create a presentation about sustainable energy solutions",
    "textMode": "generate"
  }'
```

**Response:**
```json
{
  "generationId": "gen_abc123",
  "status": "processing",
  "createdAt": "2025-11-16T12:00:00Z",
  "estimatedCompletionTime": "2025-11-16T12:02:00Z"
}
```

---

### Пример 2: Презентация с AI изображениями и темой

```bash
curl --request POST \
  --url https://public-api.gamma.app/v1.0/generations \
  --header 'Content-Type: application/json' \
  --header 'X-API-KEY: sk-gamma-xxxxxxxx' \
  --data '{
    "inputText": "# Quarterly Sales Report\n\nQ1 2025 Performance Review\n\n---\n\n## Revenue Growth\n- Total revenue: $2.5M\n- YoY growth: 35%\n- New customers: 150\n\n---\n\n## Market Expansion\n- Entered 3 new markets\n- Partnerships: 12 strategic deals\n- Team growth: 25 new hires",
    "textMode": "preserve",
    "format": "presentation",
    "numCards": 12,
    "cardSplit": "inputTextBreaks",
    "themeId": 32852,
    "textOptions": {
      "amount": "medium",
      "tone": "professional and confident",
      "audience": "C-level executives and board members",
      "language": "en"
    },
    "imageOptions": {
      "source": "aiGenerated",
      "model": "imagen-4-pro",
      "style": "modern corporate design with blue and green accents"
    },
    "exportAs": "pdf"
  }'
```

---

### Пример 3: Документ на русском языке

```bash
curl --request POST \
  --url https://public-api.gamma.app/v1.0/generations \
  --header 'Content-Type: application/json' \
  --header 'X-API-KEY: sk-gamma-xxxxxxxx' \
  --data '{
    "inputText": "Руководство по внедрению AI в компании. Включить разделы: стратегия, технологии, обучение персонала, измерение результатов.",
    "textMode": "generate",
    "format": "document",
    "numCards": 25,
    "textOptions": {
      "amount": "extensive",
      "tone": "профессиональный и практичный",
      "audience": "руководители IT-отделов",
      "language": "ru"
    },
    "imageOptions": {
      "source": "pictographic",
      "style": "minimalist icons in blue color scheme"
    },
    "cardOptions": {
      "dimensions": "A4 portrait"
    }
  }'
```

---

### Пример 4: Соцсети с GIF анимациями

```bash
curl --request POST \
  --url https://public-api.gamma.app/v1.0/generations \
  --header 'Content-Type: application/json' \
  --header 'X-API-KEY: sk-gamma-xxxxxxxx' \
  --data '{
    "inputText": "Launch announcement for our new mobile app. Highlight: speed, simplicity, security.",
    "textMode": "generate",
    "format": "social",
    "numCards": 5,
    "textOptions": {
      "amount": "brief",
      "tone": "energetic and exciting",
      "audience": "tech-savvy millennials",
      "language": "en"
    },
    "imageOptions": {
      "source": "giphy"
    },
    "cardOptions": {
      "dimensions": "1:1"
    }
  }'
```

---

### Пример 5: Создание на основе шаблона

```bash
curl --request POST \
  --url https://public-api.gamma.app/v1.0/generations/from-template \
  --header 'Content-Type: application/json' \
  --header 'X-API-KEY: sk-gamma-xxxxxxxx' \
  --data '{
    "gammaId": "template_xyz789",
    "prompt": "Adapt this template for a product launch presentation. Product: SmartHome Hub. Features: voice control, energy savings, easy setup. Target: homeowners aged 30-50.",
    "imageOptions": {
      "source": "aiGenerated",
      "model": "flux-1-pro",
      "style": "modern home interior photography"
    }
  }'
```

---

### Пример 6: Python SDK (unofficial)

```python
import requests
import json

class GammaAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://public-api.gamma.app/v1.0"
        self.headers = {
            "Content-Type": "application/json",
            "X-API-KEY": api_key
        }

    def generate(self, input_text, text_mode="generate", **kwargs):
        """Создать презентацию через Generate API"""
        payload = {
            "inputText": input_text,
            "textMode": text_mode,
            **kwargs
        }

        response = requests.post(
            f"{self.base_url}/generations",
            headers=self.headers,
            json=payload
        )

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Error {response.status_code}: {response.text}")

    def get_status(self, generation_id):
        """Получить статус генерации"""
        response = requests.get(
            f"{self.base_url}/generations/{generation_id}",
            headers=self.headers
        )
        return response.json()

    def list_themes(self):
        """Получить список тем"""
        response = requests.get(
            f"{self.base_url}/themes",
            headers=self.headers
        )
        return response.json()

# Использование
gamma = GammaAPI("sk-gamma-xxxxxxxx")

# Создать презентацию
result = gamma.generate(
    input_text="AI in Healthcare: Opportunities and Challenges",
    text_mode="generate",
    format="presentation",
    numCards=15,
    textOptions={
        "amount": "detailed",
        "language": "en"
    },
    imageOptions={
        "source": "aiGenerated",
        "model": "imagen-4-pro"
    }
)

print(f"Generation ID: {result['generationId']}")
print(f"Status: {result['status']}")

# Проверить статус
status = gamma.get_status(result['generationId'])
print(f"Current status: {status['status']}")
```

---

### Пример 7: Node.js

```javascript
const axios = require('axios');

class GammaAPI {
  constructor(apiKey) {
    this.apiKey = apiKey;
    this.baseURL = 'https://public-api.gamma.app/v1.0';
    this.headers = {
      'Content-Type': 'application/json',
      'X-API-KEY': apiKey
    };
  }

  async generate(inputText, textMode = 'generate', options = {}) {
    try {
      const response = await axios.post(
        `${this.baseURL}/generations`,
        {
          inputText,
          textMode,
          ...options
        },
        { headers: this.headers }
      );
      return response.data;
    } catch (error) {
      console.error('Generation error:', error.response?.data || error.message);
      throw error;
    }
  }

  async getStatus(generationId) {
    const response = await axios.get(
      `${this.baseURL}/generations/${generationId}`,
      { headers: this.headers }
    );
    return response.data;
  }

  async listThemes() {
    const response = await axios.get(
      `${this.baseURL}/themes`,
      { headers: this.headers }
    );
    return response.data;
  }
}

// Использование
const gamma = new GammaAPI('sk-gamma-xxxxxxxx');

(async () => {
  const result = await gamma.generate(
    'Product roadmap for 2025',
    'generate',
    {
      format: 'presentation',
      numCards: 10,
      textOptions: {
        amount: 'detailed',
        tone: 'strategic and forward-thinking',
        language: 'en'
      },
      imageOptions: {
        source: 'aiGenerated',
        model: 'flux-1-pro'
      }
    }
  );

  console.log('Generation ID:', result.generationId);
})();
```

---

## Best Practices

### 1. Оптимизация стоимости

#### Используйте Basic модели для большинства случаев
```json
{
  "imageOptions": {
    "source": "aiGenerated",
    "model": "flux-1-quick"  // 2 кредита вместо 20-120
  }
}
```

#### Ограничивайте количество карточек
```json
{
  "numCards": 10  // Вместо 60-75
}
```

#### Используйте бесплатные источники изображений
```json
{
  "imageOptions": {
    "source": "unsplash"  // Или "pictographic", "webFreeToUse"
  }
}
```

---

### 2. Качество контента

#### Используйте структурированный inputText с Markdown
```json
{
  "inputText": "# Main Title\n\n## Section 1\nContent...\n\n---\n\n## Section 2\nMore content..."
}
```

#### Всегда указывайте стиль изображений
```json
{
  "imageOptions": {
    "style": "modern minimalist photography with soft pastel colors"
  }
}
```

#### Определяйте аудиторию и тон
```json
{
  "textOptions": {
    "tone": "professional yet approachable",
    "audience": "mid-level managers in tech companies"
  }
}
```

---

### 3. Управление генерацией

#### Используйте preserve для точного контроля
```json
{
  "textMode": "preserve",  // Сохранит ваш текст как есть
  "cardSplit": "inputTextBreaks"  // Используйте \n---\n для разделения
}
```

#### Добавляйте дополнительные инструкции
```json
{
  "additionalInstructions": "Include data visualizations. Use bullet points for key takeaways. Add a call-to-action on the last slide."
}
```

---

### 4. Обработка ошибок

#### Реализуйте exponential backoff для 429/500/502
```python
import time

def generate_with_retry(gamma_api, input_text, max_retries=3):
    for attempt in range(max_retries):
        try:
            return gamma_api.generate(input_text)
        except Exception as e:
            if e.status_code in [429, 500, 502]:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                time.sleep(wait_time)
            else:
                raise
    raise Exception("Max retries exceeded")
```

#### Валидируйте параметры перед отправкой
```python
def validate_params(params):
    if 'inputText' not in params:
        raise ValueError("inputText is required")

    if len(params['inputText']) > 400000:
        raise ValueError("inputText exceeds 400,000 characters")

    if params.get('numCards', 10) > 60:  # Pro plan
        raise ValueError("numCards exceeds Pro plan limit of 60")
```

---

### 5. Интеграция с workflow

#### Асинхронная обработка
```python
import asyncio
import aiohttp

async def generate_multiple(presentations):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for pres in presentations:
            task = generate_async(session, pres)
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        return results
```

#### Кэширование тем и папок
```python
class GammaAPIWithCache(GammaAPI):
    def __init__(self, api_key):
        super().__init__(api_key)
        self._themes_cache = None
        self._folders_cache = None

    def list_themes(self, use_cache=True):
        if use_cache and self._themes_cache:
            return self._themes_cache

        themes = super().list_themes()
        self._themes_cache = themes
        return themes
```

---

### 6. Безопасность

#### Никогда не храните API ключи в коде
```python
# ❌ ПЛОХО
api_key = "sk-gamma-abc123"

# ✅ ХОРОШО
import os
api_key = os.getenv("GAMMA_API_KEY")
```

#### Используйте environment variables
```bash
export GAMMA_API_KEY="sk-gamma-xxxxxxxx"
```

#### Ограничивайте доступ через sharingOptions
```json
{
  "sharingOptions": {
    "access": "workspace",  // Только workspace
    "allowComments": false
  }
}
```

---

### 7. Мониторинг и логирование

#### Логируйте все запросы и ошибки
```python
import logging

logger = logging.getLogger(__name__)

def generate_with_logging(gamma_api, input_text):
    logger.info(f"Generating presentation: {input_text[:50]}...")

    try:
        result = gamma_api.generate(input_text)
        logger.info(f"Success! Generation ID: {result['generationId']}")
        return result
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise
```

#### Отслеживайте расход кредитов
```python
class GammaAPIWithTracking(GammaAPI):
    def __init__(self, api_key):
        super().__init__(api_key)
        self.total_credits_used = 0

    def generate(self, *args, **kwargs):
        result = super().generate(*args, **kwargs)

        # Расчет примерной стоимости
        num_cards = kwargs.get('numCards', 10)
        credits_estimate = num_cards * 3.5  # Средняя стоимость

        self.total_credits_used += credits_estimate
        logger.info(f"Estimated credits used: {credits_estimate}")

        return result
```

---

### 8. Локализация

#### Список языков для dropdown
```python
GAMMA_LANGUAGES = {
    'en': 'English (US)',
    'ru': 'Русский',
    'es': 'Español',
    'fr': 'Français',
    'de': 'Deutsch',
    'zh-cn': '简体中文',
    'ja': '日本語',
    # ... см. полный список выше
}
```

#### Автоопределение языка из контента
```python
from langdetect import detect

def generate_auto_language(gamma_api, input_text):
    detected_lang = detect(input_text)

    # Mapping langdetect codes to Gamma codes
    lang_map = {
        'en': 'en',
        'ru': 'ru',
        'es': 'es',
        'zh-cn': 'zh-cn',
        # ...
    }

    gamma_lang = lang_map.get(detected_lang, 'en')

    return gamma_api.generate(
        input_text,
        textOptions={'language': gamma_lang}
    )
```

---

## Changelog

### v1.0 (GA) - 5 ноября 2025
- ✅ General Availability релиз
- ✅ Поддержка 60+ языков
- ✅ 20+ моделей генерации изображений
- ✅ Generate API (стабильный)
- ✅ Create from Template API (beta)
- ✅ List Themes и List Folders endpoints
- ✅ Экспорт в PDF и PPTX

---

## Полезные ссылки

- **Официальная документация:** https://developers.gamma.app/docs/getting-started
- **API Reference:** https://developers.gamma.app/reference/generate-a-gamma
- **Help Center:** https://help.gamma.app/en/articles/11962420-does-gamma-have-an-api
- **Gamma Web App:** https://gamma.app
- **Поддержка:** support@gamma.app

---

## Заключение

Gamma API предоставляет мощные возможности для автоматизации создания презентаций, документов и другого контента. Основные преимущества:

✅ **Простота использования** - REST API с JSON
✅ **Гибкость** - Множество параметров настройки
✅ **Мультиязычность** - 60+ языков
✅ **AI-генерация** - 20+ моделей изображений
✅ **Экспорт** - PDF и PPTX
✅ **Интеграции** - Make, Zapier, N8N, Workato

Начните с минимальных запросов, постепенно добавляйте параметры для достижения желаемого результата. Используйте Best Practices для оптимизации стоимости и качества.

---

**Документация обновлена:** 16 ноября 2025
**Версия API:** v1.0 (GA)
**Автор:** Claude Code Assistant
