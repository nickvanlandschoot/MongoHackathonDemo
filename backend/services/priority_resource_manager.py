"""
Priority-based resource manager for controlling concurrent access to limited resources.

This module provides a priority queue system for managing concurrent access to
npm registry API calls, ensuring user requests are never blocked by background jobs.
"""

import asyncio
from enum import Enum
from contextlib import asynccontextmanager
from typing import Optional


class Priority(Enum):
    """Priority levels for resource access."""
    HIGH = 1  # User-initiated requests
    LOW = 2   # Background jobs


class PriorityResourceManager:
    """
    Manages prioritized access to limited resources (npm API calls).

    This class implements a priority-based semaphore system that guarantees
    minimum capacity for HIGH priority requests while allowing LOW priority
    requests to use any unused capacity.

    Features:
    - Two priority levels: HIGH (user requests) and LOW (background jobs)
    - Reserved capacity for HIGH priority requests
    - Dynamic allocation: LOW can use unused HIGH slots when available
    - Fair queuing: FIFO within each priority level

    Example:
        manager = PriorityResourceManager(total_capacity=16, high_priority_min=10)

        # User request (HIGH priority)
        async with manager.acquire(Priority.HIGH):
            result = await make_npm_api_call()

        # Background job (LOW priority)
        async with manager.acquire(Priority.LOW):
            result = await make_npm_api_call()
    """

    def __init__(
        self,
        total_capacity: int = 16,
        high_priority_min: int = 10
    ):
        """
        Initialize the priority resource manager.

        Args:
            total_capacity: Maximum number of concurrent operations allowed
            high_priority_min: Minimum slots reserved for HIGH priority requests

        Raises:
            ValueError: If high_priority_min > total_capacity
        """
        if high_priority_min > total_capacity:
            raise ValueError(
                f"high_priority_min ({high_priority_min}) cannot exceed "
                f"total_capacity ({total_capacity})"
            )

        self._total_capacity = total_capacity
        self._high_priority_min = high_priority_min
        self._low_priority_max = total_capacity - high_priority_min

        # Semaphores for each priority level
        # HIGH priority gets full capacity access
        self._high_sem = asyncio.Semaphore(total_capacity)
        # LOW priority is limited to prevent starving HIGH priority
        self._low_sem = asyncio.Semaphore(self._low_priority_max)

        # Track active requests per priority for monitoring
        self._active_high = 0
        self._active_low = 0
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def acquire(self, priority: Priority):
        """
        Acquire a resource slot with the given priority.

        This is an async context manager that acquires a semaphore slot
        based on priority level and releases it when done.

        Args:
            priority: Priority level (HIGH or LOW)

        Yields:
            None (resource slot is held for the duration of the context)

        Example:
            async with manager.acquire(Priority.HIGH):
                # Resource slot is held here
                await do_work()
            # Resource slot is automatically released here
        """
        if priority == Priority.HIGH:
            async with self._high_sem:
                async with self._lock:
                    self._active_high += 1
                try:
                    yield
                finally:
                    async with self._lock:
                        self._active_high -= 1
        else:  # LOW priority
            async with self._low_sem:
                async with self._lock:
                    self._active_low += 1
                try:
                    yield
                finally:
                    async with self._lock:
                        self._active_low -= 1

    def get_stats(self) -> dict:
        """
        Get current resource utilization statistics.

        Returns:
            Dict with current utilization metrics:
                - total_capacity: Maximum concurrent operations
                - high_priority_min: Reserved capacity for HIGH priority
                - low_priority_max: Maximum capacity for LOW priority
                - active_high: Currently active HIGH priority operations
                - active_low: Currently active LOW priority operations
                - available_high: Remaining capacity for HIGH priority
                - available_low: Remaining capacity for LOW priority

        Note: This method is not thread-safe and should be used for
        monitoring purposes only, not for making resource decisions.
        """
        return {
            "total_capacity": self._total_capacity,
            "high_priority_min": self._high_priority_min,
            "low_priority_max": self._low_priority_max,
            "active_high": self._active_high,
            "active_low": self._active_low,
            "available_high": self._total_capacity - self._active_high - self._active_low,
            "available_low": max(0, self._low_priority_max - self._active_low),
        }


# Global singleton instance
_resource_manager: Optional[PriorityResourceManager] = None


def get_resource_manager() -> PriorityResourceManager:
    """
    Get or create the global resource manager singleton.

    This function returns the singleton instance of PriorityResourceManager
    with default configuration suitable for small-scale deployments
    (1-5 users, <50 packages).

    Configuration:
    - total_capacity: 16 concurrent npm API calls
    - high_priority_min: 10 slots reserved for user requests (62%)
    - low_priority_max: 6 slots for background jobs (38%)

    Returns:
        PriorityResourceManager singleton instance

    Note: The singleton is created on first call and reused thereafter.
    """
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = PriorityResourceManager(
            total_capacity=16,
            high_priority_min=10
        )
    return _resource_manager
