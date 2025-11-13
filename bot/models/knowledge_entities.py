"""
Knowledge Base Entity Schemas

Pydantic модели для представления различных типов knowledge entities
из базы знаний курса "Всепрощающая".

Эти схемы используются для:
- Валидации данных при парсинге
- Создания structured entities в Graphiti
- Определения relationships между entities
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum


class EntityType(str, Enum):
    """Типы entities в knowledge graph"""
    LESSON = "lesson"
    TECHNIQUE = "technique"
    QUESTION = "question"
    CORRECTION = "correction"
    BRAINWRITE = "brainwrite"
    FAQ = "faq"
    EPISODE = "episode"


class LessonCategory(str, Enum):
    """Категории уроков курса"""
    FOUNDATION = "foundation"  # Основа
    TECHNIQUE = "technique"    # Техника
    PRACTICE = "practice"      # Практика
    THEORY = "theory"          # Теория
    OTHER = "other"


class CourseLesson(BaseModel):
    """
    Урок курса 'Всепрощающая'

    Представляет отдельный урок с его содержимым,
    ключевыми концептами и связями с техниками.
    """
    lesson_number: int = Field(..., ge=1, le=100, description="Номер урока (1-60)")
    title: str = Field(..., min_length=1, max_length=500, description="Название урока")
    category: LessonCategory = Field(default=LessonCategory.OTHER, description="Категория урока")

    content: str = Field(..., min_length=10, description="Полное содержание урока")
    summary: Optional[str] = Field(None, max_length=1000, description="Краткое резюме урока")

    key_concepts: List[str] = Field(default_factory=list, description="Ключевые концепты урока")
    related_techniques: List[str] = Field(default_factory=list, description="Связанные техники")

    # Metadata
    source_file: Optional[str] = Field(None, description="Исходный файл (для трассировки)")
    chunk_index: Optional[int] = Field(None, description="Индекс chunk (если урок разбит)")
    total_chunks: Optional[int] = Field(None, description="Всего chunks для этого урока")

    @validator('content')
    def content_not_empty(cls, v):
        """Проверка что content не пустой"""
        if not v or len(v.strip()) < 10:
            raise ValueError("Content must be at least 10 characters")
        return v.strip()

    @property
    def entity_type(self) -> EntityType:
        return EntityType.LESSON

    def to_episode_content(self) -> str:
        """
        Конвертировать в текст для Graphiti Episode

        Returns:
            Formatted text для semantic search
        """
        parts = [
            f"УРОК {self.lesson_number}: {self.title}",
            f"Категория: {self.category.value}",
            ""
        ]

        if self.summary:
            parts.append(f"Резюме: {self.summary}")
            parts.append("")

        parts.append(self.content)

        if self.key_concepts:
            parts.append("")
            parts.append("Ключевые концепты:")
            for concept in self.key_concepts:
                parts.append(f"- {concept}")

        if self.related_techniques:
            parts.append("")
            parts.append("Связанные техники:")
            for tech in self.related_techniques:
                parts.append(f"- {tech}")

        return "\n".join(parts)


class BrainwriteTechnique(BaseModel):
    """
    Техника мозгоритма

    Описание конкретной техники написания мозгоритмов
    с примерами и типичными ошибками.
    """
    name: str = Field(..., min_length=1, max_length=200, description="Название техники")
    description: str = Field(..., min_length=10, description="Описание техники")

    steps: List[str] = Field(default_factory=list, description="Шаги выполнения техники")
    common_mistakes: List[str] = Field(default_factory=list, description="Частые ошибки при использовании")
    examples: List[str] = Field(default_factory=list, description="Примеры применения техники")

    # Relationships
    required_lessons: List[int] = Field(default_factory=list, description="Необходимые уроки (номера)")
    related_techniques: List[str] = Field(default_factory=list, description="Связанные техники")

    # Metadata
    difficulty_level: Optional[str] = Field(None, description="Уровень сложности (easy/medium/hard)")
    source_file: Optional[str] = Field(None, description="Исходный файл")

    @property
    def entity_type(self) -> EntityType:
        return EntityType.TECHNIQUE

    def to_episode_content(self) -> str:
        """Конвертировать в текст для Graphiti Episode"""
        parts = [
            f"ТЕХНИКА: {self.name}",
            "",
            self.description,
            ""
        ]

        if self.steps:
            parts.append("Шаги выполнения:")
            for i, step in enumerate(self.steps, 1):
                parts.append(f"{i}. {step}")
            parts.append("")

        if self.common_mistakes:
            parts.append("Частые ошибки:")
            for mistake in self.common_mistakes:
                parts.append(f"⚠️ {mistake}")
            parts.append("")

        if self.examples:
            parts.append("Примеры:")
            for example in self.examples:
                parts.append(f"✅ {example}")

        return "\n".join(parts)


class StudentQuestion(BaseModel):
    """
    Вопрос ученицы

    Реальный вопрос от ученицы с ответом куратора.
    Используется для улучшения качества ответов бота.
    """
    question_id: Optional[str] = Field(None, description="Уникальный ID вопроса")
    question_text: str = Field(..., min_length=5, description="Текст вопроса")

    category: Optional[str] = Field(None, description="Категория вопроса")
    lesson_reference: Optional[int] = Field(None, ge=1, le=100, description="Ссылка на урок")

    curator_answer: str = Field(..., min_length=5, description="Ответ куратора")

    # Metadata
    student_name: Optional[str] = Field(None, description="Имя ученицы (если есть)")
    date_asked: Optional[datetime] = Field(None, description="Дата вопроса")
    source_file: Optional[str] = Field(None, description="Исходный файл")

    @property
    def entity_type(self) -> EntityType:
        return EntityType.QUESTION

    def to_episode_content(self) -> str:
        """Конвертировать в текст для Graphiti Episode"""
        parts = ["ВОПРОС УЧЕНИЦЫ"]

        if self.lesson_reference:
            parts.append(f"(по уроку {self.lesson_reference})")

        parts.extend([
            "",
            f"Вопрос: {self.question_text}",
            "",
            f"Ответ куратора: {self.curator_answer}"
        ])

        return "\n".join(parts)


class CuratorCorrection(BaseModel):
    """
    Корректировка куратора

    Реальная корректировка мозгоритма ученицы куратором.
    Содержит тип ошибки, оригинальный текст и исправление.
    """
    correction_id: Optional[str] = Field(None, description="Уникальный ID корректировки")

    error_type: str = Field(..., min_length=1, description="Тип ошибки")
    student_text: str = Field(..., min_length=5, description="Оригинальный текст ученицы")
    correction: str = Field(..., min_length=5, description="Исправленный текст")
    explanation: Optional[str] = Field(None, description="Объяснение корректировки")

    # Relationships
    related_technique: Optional[str] = Field(None, description="Связанная техника")
    related_lesson: Optional[int] = Field(None, ge=1, le=100, description="Связанный урок")

    # Metadata
    student_name: Optional[str] = Field(None, description="Имя ученицы")
    curator_name: Optional[str] = Field(None, description="Имя куратора")
    date_corrected: Optional[datetime] = Field(None, description="Дата корректировки")
    source_file: Optional[str] = Field(None, description="Исходный файл")

    @property
    def entity_type(self) -> EntityType:
        return EntityType.CORRECTION

    def to_episode_content(self) -> str:
        """Конвертировать в текст для Graphiti Episode"""
        parts = [
            f"КОРРЕКТИРОВКА: {self.error_type}",
            "",
            f"Оригинальный текст: {self.student_text}",
            "",
            f"Исправление: {self.correction}"
        ]

        if self.explanation:
            parts.extend(["", f"Объяснение: {self.explanation}"])

        return "\n".join(parts)


class BrainwriteExample(BaseModel):
    """
    Пример мозгоритма ученицы

    Реальный мозгоритм из student_brainwrites.json.
    Используется для поиска похожих примеров.
    """
    brainwrite_id: Optional[str] = Field(None, description="Уникальный ID мозгоритма")
    text: str = Field(..., min_length=10, description="Текст мозгоритма")

    # Metadata
    student_name: Optional[str] = Field(None, description="Имя ученицы")
    lesson_number: Optional[int] = Field(None, ge=1, le=100, description="Номер урока")
    technique_used: Optional[str] = Field(None, description="Использованная техника")
    quality_rating: Optional[str] = Field(None, description="Оценка качества (good/medium/poor)")
    date_created: Optional[datetime] = Field(None, description="Дата создания")
    source_file: Optional[str] = Field(None, description="Исходный файл")

    @property
    def entity_type(self) -> EntityType:
        return EntityType.BRAINWRITE

    def to_episode_content(self) -> str:
        """Конвертировать в текст для Graphiti Episode"""
        parts = ["ПРИМЕР МОЗГОРИТМА"]

        if self.lesson_number:
            parts.append(f"(Урок {self.lesson_number})")

        if self.technique_used:
            parts.append(f"Техника: {self.technique_used}")

        parts.extend(["", self.text])

        return "\n".join(parts)


class FAQEntry(BaseModel):
    """
    Запись из FAQ (TOP-100 вопросов)

    Часто задаваемый вопрос с готовым ответом.
    Высший приоритет при поиске.
    """
    faq_id: Optional[str] = Field(None, description="Уникальный ID FAQ")
    question: str = Field(..., min_length=5, description="Вопрос")
    answer: str = Field(..., min_length=10, description="Ответ")

    # Metadata
    category: Optional[str] = Field(None, description="Категория вопроса")
    frequency: Optional[int] = Field(None, ge=1, description="Частота вопроса (для ранжирования)")
    keywords: List[str] = Field(default_factory=list, description="Ключевые слова для поиска")
    source_file: Optional[str] = Field(None, description="Исходный файл")

    @property
    def entity_type(self) -> EntityType:
        return EntityType.FAQ

    def to_episode_content(self) -> str:
        """Конвертировать в текст для Graphiti Episode"""
        parts = [
            "FAQ (ЧАСТЫЙ ВОПРОС)",
            "",
            f"Q: {self.question}",
            "",
            f"A: {self.answer}"
        ]

        if self.keywords:
            parts.extend([
                "",
                f"Ключевые слова: {', '.join(self.keywords)}"
            ])

        return "\n".join(parts)


# Relationship Types для Graphiti
class RelationshipType(str, Enum):
    """Типы relationships между entities в knowledge graph"""

    # Lesson relationships
    LESSON_INCLUDES_TECHNIQUE = "includes_technique"
    LESSON_PREREQUISITE = "prerequisite_for"
    LESSON_FOLLOWS = "follows"

    # Technique relationships
    TECHNIQUE_REQUIRES_LESSON = "requires_lesson"
    TECHNIQUE_RELATED_TO = "related_to_technique"
    TECHNIQUE_BUILDS_ON = "builds_on"

    # Question relationships
    QUESTION_ABOUT_LESSON = "about_lesson"
    QUESTION_ABOUT_TECHNIQUE = "about_technique"
    QUESTION_SIMILAR_TO = "similar_to_question"

    # Correction relationships
    CORRECTION_FOR_TECHNIQUE = "corrects_technique"
    CORRECTION_FOR_LESSON = "corrects_lesson"
    CORRECTION_EXAMPLE_OF = "example_of_error"

    # Brainwrite relationships
    BRAINWRITE_USES_TECHNIQUE = "uses_technique"
    BRAINWRITE_FOR_LESSON = "for_lesson"
    BRAINWRITE_SIMILAR_TO = "similar_to_brainwrite"

    # FAQ relationships
    FAQ_ABOUT_LESSON = "faq_about_lesson"
    FAQ_ABOUT_TECHNIQUE = "faq_about_technique"


# Utility functions
def create_episode_metadata(entity: BaseModel) -> Dict[str, Any]:
    """
    Создать metadata dict для Graphiti Episode

    Args:
        entity: Любой entity с Pydantic schema

    Returns:
        Dict с metadata для Graphiti
    """
    base_metadata = {
        "entity_type": entity.entity_type.value,
        "source_file": getattr(entity, 'source_file', None),
        "created_at": datetime.utcnow().isoformat()
    }

    # Добавить специфичные поля в зависимости от типа
    if isinstance(entity, CourseLesson):
        base_metadata.update({
            "lesson_number": entity.lesson_number,
            "category": entity.category.value,
            "key_concepts": entity.key_concepts,
            "chunk_index": entity.chunk_index,
            "total_chunks": entity.total_chunks
        })

    elif isinstance(entity, BrainwriteTechnique):
        base_metadata.update({
            "technique_name": entity.name,
            "difficulty": entity.difficulty_level,
            "required_lessons": entity.required_lessons
        })

    elif isinstance(entity, StudentQuestion):
        base_metadata.update({
            "lesson_reference": entity.lesson_reference,
            "category": entity.category
        })

    elif isinstance(entity, CuratorCorrection):
        base_metadata.update({
            "error_type": entity.error_type,
            "related_lesson": entity.related_lesson,
            "related_technique": entity.related_technique
        })

    elif isinstance(entity, FAQEntry):
        base_metadata.update({
            "category": entity.category,
            "frequency": entity.frequency,
            "keywords": entity.keywords
        })

    # Удалить None значения
    return {k: v for k, v in base_metadata.items() if v is not None}
