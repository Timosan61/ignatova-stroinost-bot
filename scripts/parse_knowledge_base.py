#!/usr/bin/env python3
"""
Knowledge Base Parser

Парсинг всех файлов базы знаний курса "Всепрощающая" в structured entities.

Поддерживаемые форматы:
- Markdown (.md) - уроки, FAQ, примеры
- JSON (.json) - корректировки, вопросы, мозгоритмы

Output: List of Pydantic entities готовых для загрузки в Graphiti
"""

import re
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

# Добавить корень в PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from bot.models.knowledge_entities import (
    CourseLesson,
    LessonCategory,
    BrainwriteTechnique,
    StudentQuestion,
    CuratorCorrection,
    BrainwriteExample,
    FAQEntry,
    GlossaryEntry
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class KnowledgeBaseParser:
    """Парсер базы знаний"""

    def __init__(self, kb_dir: Path):
        """
        Args:
            kb_dir: Путь к папке KNOWLEDGE_BASE
        """
        self.kb_dir = kb_dir
        self.parsed_entities = []

    # ==================== FAQ PARSER ====================

    def parse_faq(self, file_path: Path) -> List[FAQEntry]:
        """
        Парсинг FAQ_EXTENDED.md

        Returns:
            List of FAQEntry entities
        """
        logger.info(f"Parsing FAQ from {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        faq_entries = []

        # Паттерн для вопросов: **В1.1.1: Текст вопроса?**
        question_pattern = r'\*\*В([\d.]+):\s*(.+?)\?\*\*'

        # Найти все вопросы
        questions = list(re.finditer(question_pattern, content))

        for i, q_match in enumerate(questions):
            question_id = f"FAQ_{q_match.group(1)}"
            question_text = q_match.group(2).strip() + "?"

            # Найти ответ (между текущим вопросом и следующим)
            answer_start = q_match.end()
            answer_end = questions[i + 1].start() if i + 1 < len(questions) else len(content)

            answer_section = content[answer_start:answer_end]

            # Извлечь текст ответа (после **Ответ:**)
            answer_match = re.search(r'\*\*Ответ:\*\*\s*(.+)', answer_section, re.DOTALL)
            if not answer_match:
                logger.warning(f"No answer found for question {question_id}")
                continue

            answer_text = answer_match.group(1).strip()

            # Очистить ответ от следующего вопроса
            next_q_in_answer = re.search(r'\*\*В\d', answer_text)
            if next_q_in_answer:
                answer_text = answer_text[:next_q_in_answer.start()].strip()

            # Определить категорию по разделу
            category = self._extract_faq_category(content, q_match.start())

            # Извлечь ключевые слова
            keywords = self._extract_keywords(question_text + " " + answer_text)

            faq_entry = FAQEntry(
                faq_id=question_id,
                question=question_text,
                answer=answer_text[:5000],  # Ограничение для safety
                category=category,
                frequency=None,  # Можно добавить ранжирование позже
                keywords=keywords,
                source_file=str(file_path.name)
            )

            faq_entries.append(faq_entry)

        logger.info(f"Parsed {len(faq_entries)} FAQ entries")
        return faq_entries

    def _extract_faq_category(self, content: str, position: int) -> str:
        """Извлечь категорию FAQ по позиции вопроса"""
        # Найти ближайший заголовок раздела перед вопросом
        section_headers = list(re.finditer(r'### 📚 РАЗДЕЛ \d+: (.+)', content))

        for header in reversed(section_headers):
            if header.start() < position:
                return header.group(1).strip()

        return "Общее"

    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Извлечь ключевые слова из текста (простая эвристика)"""
        # Удалить пунктуацию и лишние символы
        clean_text = re.sub(r'[^\w\s]', ' ', text.lower())

        # Стоп-слова (расширить при необходимости)
        stop_words = {
            'это', 'есть', 'был', 'была', 'были', 'быть', 'для', 'как',
            'что', 'чтобы', 'или', 'если', 'когда', 'где', 'через', 'под'
        }

        # Подсчет частоты слов (длина > 4 символов)
        words = [w for w in clean_text.split() if len(w) > 4 and w not in stop_words]
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1

        # Топ N ключевых слов
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:max_keywords]]

    # ==================== LESSONS PARSER ====================

    def parse_lessons(self, file_path: Path, chunk_size: int = 1000) -> List[CourseLesson]:
        """
        Парсинг KNOWLEDGE_BASE_FULL.md

        Args:
            file_path: Путь к файлу с уроками
            chunk_size: Размер chunk в словах (для разбивки больших уроков)

        Returns:
            List of CourseLesson entities
        """
        logger.info(f"Parsing lessons from {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        lessons = []

        # Паттерн для уроков: # УРОК N: НАЗВАНИЕ
        lesson_pattern = r'<a id="урок-(\d+)"></a>\s*\n+# УРОК (\d+): (.+?)\n'

        lesson_matches = list(re.finditer(lesson_pattern, content, re.IGNORECASE))

        for i, match in enumerate(lesson_matches):
            lesson_num = int(match.group(1))
            title = match.group(3).strip()

            # Извлечь содержание урока (до следующего урока)
            content_start = match.end()
            content_end = lesson_matches[i + 1].start() if i + 1 < len(lesson_matches) else len(content)

            lesson_content = content[content_start:content_end].strip()

            # Определить категорию по ключевым словам в названии
            category = self._categorize_lesson(title)

            # Извлечь краткое резюме (если есть раздел КРАТКОЕ РЕЗЮМЕ)
            summary = self._extract_lesson_summary(lesson_content)

            # Извлечь ключевые концепты
            key_concepts = self._extract_key_concepts(lesson_content)

            # Разбить на chunks если урок слишком большой
            lesson_chunks = self._chunk_text(lesson_content, chunk_size)

            for chunk_idx, chunk_text in enumerate(lesson_chunks):
                lesson = CourseLesson(
                    lesson_number=lesson_num,
                    title=title,
                    category=category,
                    content=chunk_text,
                    summary=summary if chunk_idx == 0 else None,
                    key_concepts=key_concepts if chunk_idx == 0 else [],
                    related_techniques=[],  # TODO: извлечь из содержания
                    source_file=str(file_path.name),
                    chunk_index=chunk_idx if len(lesson_chunks) > 1 else None,
                    total_chunks=len(lesson_chunks) if len(lesson_chunks) > 1 else None
                )

                lessons.append(lesson)

        logger.info(f"Parsed {len(lessons)} lesson chunks from {len(lesson_matches)} lessons")
        return lessons

    def _categorize_lesson(self, title: str) -> LessonCategory:
        """Определить категорию урока по названию"""
        title_lower = title.lower()

        # Ключевые слова для категорий
        if any(word in title_lower for word in ['техника', 'метод', 'способ']):
            return LessonCategory.TECHNIQUE

        if any(word in title_lower for word in ['практика', 'упражнение', 'задание']):
            return LessonCategory.PRACTICE

        if any(word in title_lower for word in ['основа', 'введение', 'настраиваемся']):
            return LessonCategory.FOUNDATION

        if any(word in title_lower for word in ['теория', 'понимание', 'концепция']):
            return LessonCategory.THEORY

        return LessonCategory.OTHER

    def _extract_lesson_summary(self, content: str, max_length: int = 1000) -> Optional[str]:
        """Извлечь краткое резюме урока"""
        # Паттерн: ## 📌 КРАТКОЕ РЕЗЮМЕ
        summary_match = re.search(
            r'## 📌 КРАТКОЕ РЕЗЮМЕ\s*\n+(.+?)(?=\n##|\Z)',
            content,
            re.DOTALL
        )

        if summary_match:
            summary = summary_match.group(1).strip()
            return summary[:max_length]

        # Альтернатива: первый параграф
        first_paragraph = content.split('\n\n')[0]
        if len(first_paragraph) > 50:
            return first_paragraph[:max_length]

        return None

    def _extract_key_concepts(self, content: str) -> List[str]:
        """Извлечь ключевые концепты из урока"""
        concepts = []

        # Поиск списков с маркерами (- или *)
        list_items = re.findall(r'^\s*[•\-\*]\s*(.+)$', content, re.MULTILINE)

        # Фильтровать короткие и информативные
        for item in list_items:
            clean_item = re.sub(r'\*\*(.+?)\*\*', r'\1', item)  # Убрать **bold**
            clean_item = clean_item.strip()

            if 10 < len(clean_item) < 200:
                concepts.append(clean_item)

        return concepts[:10]  # Топ 10

    def _chunk_text(self, text: str, chunk_size: int = 1000) -> List[str]:
        """
        Разбить текст на chunks по размеру (в словах)

        Args:
            text: Исходный текст
            chunk_size: Размер chunk в словах

        Returns:
            List of text chunks
        """
        words = text.split()

        if len(words) <= chunk_size:
            return [text]

        chunks = []
        for i in range(0, len(words), chunk_size):
            chunk_words = words[i:i + chunk_size]
            chunks.append(' '.join(chunk_words))

        return chunks

    # ==================== CORRECTIONS PARSER ====================

    def parse_corrections(self, file_path: Path) -> List[CuratorCorrection]:
        """
        Парсинг curator_corrections_ALL.json

        Returns:
            List of CuratorCorrection entities
        """
        logger.info(f"Parsing corrections from {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        corrections_data = data.get('all_corrections', [])
        corrections = []

        for idx, corr_data in enumerate(corrections_data):
            text = corr_data.get('text', '')
            author = corr_data.get('author', 'Куратор')
            chat = corr_data.get('chat', '')

            # Извлечь тип ошибки и корректировку из текста
            error_type, student_text, correction, explanation = self._parse_correction_text(text)

            if not student_text or not correction:
                # Если не удалось распарсить структуру, сохранить как есть
                correction_entity = CuratorCorrection(
                    correction_id=f"CORR_{idx + 1}",
                    error_type="Общая корректировка",
                    student_text=text[:500],
                    correction=text,
                    explanation=None,
                    related_technique=None,
                    related_lesson=None,
                    curator_name=author,
                    source_file=str(file_path.name)
                )
            else:
                correction_entity = CuratorCorrection(
                    correction_id=f"CORR_{idx + 1}",
                    error_type=error_type,
                    student_text=student_text,
                    correction=correction,
                    explanation=explanation,
                    related_technique=None,  # TODO: извлечь из текста
                    related_lesson=None,     # TODO: извлечь из текста
                    curator_name=author,
                    source_file=str(file_path.name)
                )

            corrections.append(correction_entity)

        logger.info(f"Parsed {len(corrections)} corrections")
        return corrections

    def parse_questions(self, file_path: Path, sample_limit: int = 500) -> List[StudentQuestion]:
        """
        Парсинг student_questions_ALL.json

        Args:
            file_path: Путь к JSON файлу
            sample_limit: Максимальное количество вопросов (из-за большого объема - 2636)

        Returns:
            List of StudentQuestion entities
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            total_questions = data.get("total_questions", 0)
            logger.info(f"Parsing student questions... Total available: {total_questions}, sampling: {sample_limit}")

            questions = []
            by_category = data.get("by_category", {})

            # Равномерная выборка из всех категорий
            categories = list(by_category.keys())

            # Если sample_limit=None → загружаем ВСЕ вопросы
            if sample_limit is None:
                per_category = None  # Без ограничений
            else:
                per_category = sample_limit // len(categories) if categories else 0

            for category, category_questions in by_category.items():
                # Берем только первые N вопросов из каждой категории
                # (если per_category=None, то [:None] вернёт все вопросы)
                sampled = category_questions[:per_category]

                for q_data in sampled:
                    try:
                        question = StudentQuestion(
                            question_id=f"q_{len(questions)+1}",
                            question_text=q_data.get("text", "")[:2000],
                            category=category,
                            curator_answer="[Ответ куратора в процессе обработки]"  # Placeholder
                        )
                        questions.append(question)
                    except Exception as e:
                        logger.warning(f"Failed to parse question: {e}")
                        continue

            logger.info(f"✅ Parsed {len(questions)} student questions from {len(categories)} categories")
            return questions

        except Exception as e:
            logger.error(f"Failed to parse student questions from {file_path}: {e}")
            return []

    def parse_brainwrites(self, file_path: Path, sample_limit: int = 200) -> List[BrainwriteExample]:
        """
        Парсинг student_brainwrites_SAMPLE.json

        Args:
            file_path: Путь к JSON файлу
            sample_limit: Максимальное количество примеров

        Returns:
            List of BrainwriteExample entities
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            total_brainwrites = data.get("total_brainwrites", 0)
            logger.info(f"Parsing brainwrites... Total available: {total_brainwrites}, sampling: {sample_limit}")

            brainwrites = []
            categories_data = data.get("categories", {})

            # Равномерная выборка из категорий
            categories = list(categories_data.keys())
            per_category = sample_limit // len(categories) if categories else 0

            for category_name, category_data in categories_data.items():
                examples = category_data.get("examples", [])
                sampled = examples[:per_category]

                for ex_data in sampled:
                    try:
                        # Определяем качество по длине (длинные = более детальные)
                        text = ex_data.get("text", "")
                        length = len(text)

                        if length > 3000:
                            quality = "excellent"
                        elif length > 1500:
                            quality = "good"
                        else:
                            quality = "average"

                        brainwrite = BrainwriteExample(
                            brainwrite_id=f"bw_{len(brainwrites)+1}",
                            text=text[:3000],  # Ограничим длину
                            student_name=ex_data.get("author", "Unknown"),
                            technique_used=category_name,
                            quality_rating=quality
                        )
                        brainwrites.append(brainwrite)
                    except Exception as e:
                        logger.warning(f"Failed to parse brainwrite: {e}")
                        continue

            logger.info(f"✅ Parsed {len(brainwrites)} brainwrite examples from {len(categories)} categories")
            return brainwrites

        except Exception as e:
            logger.error(f"Failed to parse brainwrites from {file_path}: {e}")
            return []

    def _parse_correction_text(self, text: str) -> Tuple[str, str, str, Optional[str]]:
        """
        Извлечь структурированную информацию из текста корректировки

        Returns:
            (error_type, student_text, correction, explanation)
        """
        # Паттерны для различных типов корректировок
        patterns = {
            "структура": r'соблюдайте.*?структуру',
            "вопрос 5": r'допишите.*?ответ на 5 вопрос',
            "рекомендация": r'рекомендую.*?прописать',
            "дополнение": r'можем дополнить',
        }

        error_type = "Общая корректировка"
        for err_type, pattern in patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                error_type = err_type.capitalize()
                break

        # Упрощенная логика: весь текст = корректировка
        return error_type, "", text, None

    # ==================== GLOSSARY PARSER ====================

    def parse_glossary(self, file_path: Path) -> List[GlossaryEntry]:
        """
        Парсинг терминов из секций КЛЮЧЕВЫЕ ТЕРМИНЫ И ПОНЯТИЯ

        Args:
            file_path: Путь к KNOWLEDGE_BASE_FULL.md

        Returns:
            List of GlossaryEntry entities
        """
        logger.info(f"Parsing glossary from {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        glossary_entries = []

        # Паттерн для секций с терминами
        section_pattern = r'(?:##?\s*)?📚\s*(?:\*\*)?КЛЮЧЕВЫЕ ТЕРМИНЫИ ПОНЯТИЯ(?:\*\*)?:?\s*\n((?:- \*\*[^*]+\*\*:[^\n]+\n?)+)'

        # Альтернативный паттерн для вариаций
        alt_section_pattern = r'📚\s*(?:\*\*)?КЛЮЧЕВЫЕ ТЕРМИНЫ(?:\*\*)?:?\s*\n((?:- \*\*[^*]+\*\*:[^\n]+\n?)+)'

        # Паттерн для отдельных терминов
        term_pattern = r'- \*\*([^*]+)\*\*:\s*(.+)'

        # Найти все секции с терминами
        sections = list(re.finditer(section_pattern, content, re.IGNORECASE))
        sections.extend(list(re.finditer(alt_section_pattern, content, re.IGNORECASE)))

        # Если паттерны не сработали, ищем термины напрямую
        if not sections:
            logger.info("Using direct term search (no sections found)")
            # Найти все термины в формате - **Термин**: описание
            all_terms = re.findall(term_pattern, content)

            for idx, (term, definition) in enumerate(all_terms):
                term = term.strip()
                definition = definition.strip()

                if len(definition) < 10:
                    continue

                entry = GlossaryEntry(
                    term_id=f"glossary_{idx}",
                    term=term,
                    definition=definition,
                    lesson_number=None,
                    keywords=self._extract_keywords(f"{term} {definition}"),
                    source_file=str(file_path.name)
                )
                glossary_entries.append(entry)
        else:
            # Парсить термины из найденных секций
            term_idx = 0
            for section_match in sections:
                section_content = section_match.group(1) if section_match.lastindex else section_match.group(0)

                # Определить номер урока по позиции в файле
                lesson_number = self._find_lesson_number(content, section_match.start())

                # Извлечь термины из секции
                terms = re.findall(term_pattern, section_content)

                for term, definition in terms:
                    term = term.strip()
                    definition = definition.strip()

                    if len(definition) < 10:
                        continue

                    entry = GlossaryEntry(
                        term_id=f"glossary_{term_idx}",
                        term=term,
                        definition=definition,
                        lesson_number=lesson_number,
                        keywords=self._extract_keywords(f"{term} {definition}"),
                        source_file=str(file_path.name)
                    )
                    glossary_entries.append(entry)
                    term_idx += 1

        # Удалить дубликаты по термину
        seen_terms = set()
        unique_entries = []
        for entry in glossary_entries:
            if entry.term.lower() not in seen_terms:
                seen_terms.add(entry.term.lower())
                unique_entries.append(entry)

        logger.info(f"Parsed {len(unique_entries)} unique glossary terms")
        return unique_entries

    def _find_lesson_number(self, content: str, position: int) -> Optional[int]:
        """Найти номер урока по позиции в файле"""
        # Ищем последний заголовок урока перед позицией
        lesson_pattern = r'# УРОК (\d+):'
        matches = list(re.finditer(lesson_pattern, content[:position]))
        if matches:
            return int(matches[-1].group(1))
        return None

    # ==================== MAIN PARSING ====================

    def parse_all(self) -> Dict[str, List[Any]]:
        """
        Парсинг всей базы знаний

        Returns:
            Dict с parsed entities по типам
        """
        logger.info(f"Starting full knowledge base parsing from {self.kb_dir}")

        results = {
            "faq": [],
            "lessons": [],
            "corrections": [],
            "questions": [],
            "brainwrites": [],
            "glossary": []
        }

        # 1. Parse FAQ
        faq_file = self.kb_dir / "FAQ_EXTENDED.md"
        if faq_file.exists():
            results["faq"] = self.parse_faq(faq_file)
        else:
            logger.warning(f"FAQ file not found: {faq_file}")

        # 2. Parse Lessons
        lessons_file = self.kb_dir / "KNOWLEDGE_BASE_FULL.md"
        if lessons_file.exists():
            results["lessons"] = self.parse_lessons(lessons_file, chunk_size=800)
        else:
            logger.warning(f"Lessons file not found: {lessons_file}")

        # 3. Parse Corrections
        corrections_file = self.kb_dir / "curator_corrections_ALL.json"
        if corrections_file.exists():
            results["corrections"] = self.parse_corrections(corrections_file)
        else:
            logger.warning(f"Corrections file not found: {corrections_file}")

        # 4. Parse Student Questions
        questions_file = self.kb_dir / "student_questions_ALL.json"
        if questions_file.exists():
            results["questions"] = self.parse_questions(questions_file, sample_limit=500)
        else:
            logger.warning(f"Questions file not found: {questions_file}")

        # 5. Parse Brainwrite Examples
        brainwrites_file = self.kb_dir / "student_brainwrites_SAMPLE.json"
        if brainwrites_file.exists():
            results["brainwrites"] = self.parse_brainwrites(brainwrites_file, sample_limit=200)
        else:
            logger.warning(f"Brainwrites file not found: {brainwrites_file}")

        # 6. Parse Glossary Terms
        glossary_file = self.kb_dir / "KNOWLEDGE_BASE_FULL.md"
        if glossary_file.exists():
            results["glossary"] = self.parse_glossary(glossary_file)
        else:
            logger.warning(f"Glossary source file not found: {glossary_file}")

        # Summary
        total_entities = sum(len(v) for v in results.values())
        logger.info(f"\n{'=' * 60}")
        logger.info(f"PARSING COMPLETE: {total_entities} total entities")
        logger.info(f"  FAQ entries: {len(results['faq'])}")
        logger.info(f"  Lesson chunks: {len(results['lessons'])}")
        logger.info(f"  Corrections: {len(results['corrections'])}")
        logger.info(f"  Questions: {len(results['questions'])}")
        logger.info(f"  Brainwrites: {len(results['brainwrites'])}")
        logger.info(f"  Glossary terms: {len(results['glossary'])}")
        logger.info(f"{'=' * 60}\n")

        return results

    def save_parsed_data(self, results: Dict[str, List[Any]], output_dir: Path):
        """
        Сохранить parsed entities в JSON файлы

        Args:
            results: Dict с parsed entities
            output_dir: Папка для сохранения
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        for entity_type, entities in results.items():
            if not entities:
                continue

            output_file = output_dir / f"parsed_{entity_type}.json"

            # Конвертировать Pydantic models в dict
            entities_data = [e.model_dump() for e in entities]

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(entities_data, f, ensure_ascii=False, indent=2, default=str)

            logger.info(f"Saved {len(entities)} {entity_type} to {output_file}")


def main():
    """Main function"""
    kb_dir = Path(__file__).parent.parent / "KNOWLEDGE_BASE"

    if not kb_dir.exists():
        logger.error(f"Knowledge base directory not found: {kb_dir}")
        return

    parser = KnowledgeBaseParser(kb_dir)

    # Parse all
    results = parser.parse_all()

    # Save parsed data
    output_dir = Path(__file__).parent.parent / "data" / "parsed_kb"
    parser.save_parsed_data(results, output_dir)

    logger.info("✅ Parsing complete! Parsed data saved to data/parsed_kb/")


if __name__ == "__main__":
    main()
