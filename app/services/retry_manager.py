"""Retry manager with exponential backoff and circuit breaker."""

import time
from typing import Any, Callable
from enum import Enum
from dataclasses import dataclass
import structlog

logger = structlog.get_logger()


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class RetryPolicy:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True


@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: float = 0.0

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        return True

    def record_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning("circuit_breaker.opened", failures=self.failure_count)


class RetryManager:
    """Executes callables with retry logic and circuit breaker protection."""

    def __init__(self, policy: RetryPolicy = None, circuit: CircuitBreaker = None):
        self.policy = policy or RetryPolicy()
        self.circuit = circuit or CircuitBreaker()

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        import asyncio, random

        if not self.circuit.can_execute():
            raise RuntimeError("Circuit breaker is OPEN")

        last_error = None
        for attempt in range(self.policy.max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                self.circuit.record_success()
                return result
            except Exception as e:
                last_error = e
                self.circuit.record_failure()
                if attempt < self.policy.max_retries:
                    delay = min(
                        self.policy.base_delay * (self.policy.exponential_base ** attempt),
                        self.policy.max_delay,
                    )
                    if self.policy.jitter:
                        delay = delay * (0.5 + random.random())
                    logger.info("retry.attempt", attempt=attempt + 1, delay=round(delay, 2))
                    await asyncio.sleep(delay)
        raise last_error
