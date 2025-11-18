"""
Мониторинг производительности и стоимости embeddings
Отслеживает latency, tokens, costs для OpenAI Embeddings API
"""

import time
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingMetrics:
    """Метрики производительности embeddings"""

    total_calls: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    latencies_ms: List[float] = field(default_factory=list)
    errors: int = 0
    start_time: float = field(default_factory=time.time)

    # Константы стоимости (OpenAI text-embedding-3-small)
    COST_PER_1K_TOKENS: float = 0.00002  # $0.00002 / 1K tokens

    def add_call(self, tokens: int, latency_ms: float, error: bool = False):
        """Добавить метрику вызова embeddings API"""
        self.total_calls += 1
        self.total_tokens += tokens
        self.latencies_ms.append(latency_ms)

        if error:
            self.errors += 1
        else:
            # Стоимость только для успешных вызовов
            cost = (tokens / 1000.0) * self.COST_PER_1K_TOKENS
            self.total_cost_usd += cost

    @property
    def avg_latency_ms(self) -> float:
        """Средняя latency в миллисекундах"""
        if not self.latencies_ms:
            return 0.0
        return sum(self.latencies_ms) / len(self.latencies_ms)

    @property
    def p95_latency_ms(self) -> float:
        """95-й перцентиль latency (95% вызовов быстрее этого значения)"""
        if not self.latencies_ms:
            return 0.0
        sorted_latencies = sorted(self.latencies_ms)
        index = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[index] if index < len(sorted_latencies) else sorted_latencies[-1]

    @property
    def p99_latency_ms(self) -> float:
        """99-й перцентиль latency (99% вызовов быстрее этого значения)"""
        if not self.latencies_ms:
            return 0.0
        sorted_latencies = sorted(self.latencies_ms)
        index = int(len(sorted_latencies) * 0.99)
        return sorted_latencies[index] if index < len(sorted_latencies) else sorted_latencies[-1]

    @property
    def max_latency_ms(self) -> float:
        """Максимальная latency"""
        return max(self.latencies_ms) if self.latencies_ms else 0.0

    @property
    def min_latency_ms(self) -> float:
        """Минимальная latency"""
        return min(self.latencies_ms) if self.latencies_ms else 0.0

    @property
    def uptime_seconds(self) -> float:
        """Время работы мониторинга в секундах"""
        return time.time() - self.start_time

    @property
    def error_rate(self) -> float:
        """Процент ошибок (0-100)"""
        if self.total_calls == 0:
            return 0.0
        return (self.errors / self.total_calls) * 100.0

    def get_summary(self) -> Dict[str, Any]:
        """Получить сводку метрик для API"""
        return {
            "total_calls": self.total_calls,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "errors": self.errors,
            "error_rate_percent": round(self.error_rate, 2),
            "latency": {
                "avg_ms": round(self.avg_latency_ms, 2),
                "p95_ms": round(self.p95_latency_ms, 2),
                "p99_ms": round(self.p99_latency_ms, 2),
                "min_ms": round(self.min_latency_ms, 2),
                "max_ms": round(self.max_latency_ms, 2)
            },
            "uptime_seconds": round(self.uptime_seconds, 1),
            "started_at": datetime.fromtimestamp(self.start_time).isoformat()
        }

    def reset(self):
        """Сбросить все метрики"""
        self.total_calls = 0
        self.total_tokens = 0
        self.total_cost_usd = 0.0
        self.latencies_ms = []
        self.errors = 0
        self.start_time = time.time()
        logger.info("🔄 Метрики embeddings сброшены")


# Singleton instance
_metrics_instance = None


def get_metrics() -> EmbeddingMetrics:
    """Получить глобальный экземпляр метрик"""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = EmbeddingMetrics()
        logger.info("📊 Инициализирован мониторинг embeddings")
    return _metrics_instance


def track_embedding_call(func):
    """
    Декоратор для автоматического отслеживания вызовов embeddings

    Usage:
        @track_embedding_call
        def generate_embedding(text: str) -> List[float]:
            ...
    """
    async def wrapper(*args, **kwargs):
        metrics = get_metrics()
        start_time = time.time()
        error_occurred = False

        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            error_occurred = True
            raise e
        finally:
            latency_ms = (time.time() - start_time) * 1000

            # Оценка токенов (примерно 1 токен = 4 символа для английского)
            # Для точного подсчета нужен tiktoken, но это увеличит зависимости
            text = args[1] if len(args) > 1 else kwargs.get('text', '')
            estimated_tokens = len(str(text)) // 4

            metrics.add_call(
                tokens=estimated_tokens,
                latency_ms=latency_ms,
                error=error_occurred
            )

    return wrapper
