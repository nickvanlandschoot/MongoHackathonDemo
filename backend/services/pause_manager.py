"""
Global pause manager for controlling all background processes.

This provides a centralized way to pause/resume all background operations
including watcher polls, AI analysis, and delta computation.
"""

from typing import Optional


class PauseManager:
    """
    Singleton manager for global pause state.

    When paused, all background processes should check is_paused() before
    starting new work. User-initiated operations should ignore pause state.
    """

    def __init__(self):
        self._is_paused = False

    def pause(self) -> None:
        """Pause all background processes."""
        self._is_paused = True
        print("[pause_manager] Background processes paused")

    def resume(self) -> None:
        """Resume all background processes."""
        self._is_paused = False
        print("[pause_manager] Background processes resumed")

    def is_paused(self) -> bool:
        """Check if background processes are paused."""
        return self._is_paused


# Global singleton instance
_pause_manager: Optional[PauseManager] = None


def get_pause_manager() -> PauseManager:
    """Get or create the global pause manager singleton."""
    global _pause_manager
    if _pause_manager is None:
        _pause_manager = PauseManager()
    return _pause_manager
