"""
Валидатор ответов бота-куратора
Проверяет правильность форматирования ответов перед отправкой
"""

import re
import logging

logger = logging.getLogger(__name__)


class ResponseValidator:
    """Валидатор ответов бота"""

    @staticmethod
    def validate(response: str, student_name: str | None = None) -> dict:
        """
        Валидирует ответ бота

        Args:
            response: Текст ответа
            student_name: Имя ученицы (если известно)

        Returns:
            dict: {
                "valid": bool,
                "warnings": List[str],
                "errors": List[str]
            }
        """
        errors = []
        warnings = []

        # ===== 1. ПРОВЕРКА PLACEHOLDER [Имя] =====
        if "[Имя]" in response or "[имя]" in response:
            errors.append("❌ Используется placeholder [Имя] вместо реального имени!")

        if "{имя_ученицы}" in response or "{Имя}" in response:
            errors.append("❌ Используется placeholder {имя_ученицы} вместо реального имени!")

        # ===== 2. ПРОВЕРКА НАЛИЧИЯ РЕАЛЬНОГО ИМЕНИ =====
        if student_name:
            # Проверить что имя есть в начале ответа
            if not response.startswith(student_name):
                # Может быть имя есть в середине (менее вероятно)
                if student_name not in response:
                    warnings.append(f"⚠️ Имя '{student_name}' не найдено в ответе!")

        # ===== 3. ПРОВЕРКА ПУНКТУАЦИИ "если бы я хотя бы" =====
        if "если бы я хотя бы" in response.lower():
            # Найти все строки с "если бы я хотя бы"
            lines = response.split('\n')
            if_lines = []

            for i, line in enumerate(lines):
                if line.strip().lower().startswith('- если бы я хотя бы'):
                    if_lines.append((i, line))

            if if_lines:
                # Проверить пунктуацию
                for idx, (line_num, line) in enumerate(if_lines):
                    is_last = (idx == len(if_lines) - 1)

                    # Проверить формат (дефис, пробел, маленькая буква)
                    if not re.match(r'^- если бы я хотя бы', line.strip()):
                        warnings.append(
                            f"⚠️ Строка {line_num}: неправильный формат "
                            f"(должно быть: '- если бы я хотя бы')"
                        )

                    # Проверить пунктуацию
                    if is_last:
                        # Последний пункт должен заканчиваться точкой
                        if not line.strip().endswith('.'):
                            errors.append(
                                f"❌ Строка {line_num}: последний пункт должен "
                                f"заканчиваться ТОЧКОЙ (.)"
                            )
                    else:
                        # Промежуточные пункты должны заканчиваться точкой с запятой
                        if not line.strip().endswith(';'):
                            errors.append(
                                f"❌ Строка {line_num}: промежуточный пункт должен "
                                f"заканчиваться ТОЧКОЙ С ЗАПЯТОЙ (;)"
                            )

                    # Проверить что начинается с маленькой буквы
                    match = re.search(r'если бы я хотя бы\s+([а-яА-ЯёЁ])', line)
                    if match:
                        first_letter = match.group(1)
                        if first_letter.isupper():
                            warnings.append(
                                f"⚠️ Строка {line_num}: после 'если бы я хотя бы' "
                                f"должна быть МАЛЕНЬКАЯ буква"
                            )

        # ===== 4. ПРОВЕРКА НАЛИЧИЯ ЦВЕТОЧНОГО ЭМОДЗИ =====
        flower_emojis = ['🌷', '🌹', '🌻', '🌸', '🌼']
        has_flower = any(emoji in response for emoji in flower_emojis)

        if not has_flower:
            warnings.append("⚠️ Нет цветочного эмодзи (🌷🌹🌻🌸🌼)")

        # ===== 5. ИТОГОВАЯ ВАЛИДНОСТЬ =====
        is_valid = len(errors) == 0

        result = {
            "valid": is_valid,
            "warnings": warnings,
            "errors": errors
        }

        # Логирование
        if errors:
            logger.error(f"🚫 Валидация ответа провалилась: {errors}")
        if warnings:
            logger.warning(f"⚠️ Предупреждения при валидации: {warnings}")

        return result

    @staticmethod
    def log_validation_result(result: dict, response: str):
        """Логирует результат валидации"""
        if not result["valid"]:
            logger.error("=" * 60)
            logger.error("❌ ОТВЕТ НЕ ПРОШЁЛ ВАЛИДАЦИЮ")
            logger.error("=" * 60)

            for error in result["errors"]:
                logger.error(f"  {error}")

            if result["warnings"]:
                logger.warning("\nПредупреждения:")
                for warning in result["warnings"]:
                    logger.warning(f"  {warning}")

            logger.error("\nПроблемный ответ:")
            logger.error(response)
            logger.error("=" * 60)

        elif result["warnings"]:
            logger.warning("⚠️ Ответ прошёл валидацию с предупреждениями:")
            for warning in result["warnings"]:
                logger.warning(f"  {warning}")


def validate_response(response: str, student_name: str | None = None) -> dict:
    """
    Shortcut функция для валидации ответа

    Args:
        response: Текст ответа
        student_name: Имя ученицы (если известно)

    Returns:
        dict: Результат валидации
    """
    validator = ResponseValidator()
    result = validator.validate(response, student_name)
    validator.log_validation_result(result, response)
    return result
