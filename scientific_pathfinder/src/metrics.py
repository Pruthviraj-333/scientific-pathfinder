"""
Basic in-memory API metrics collection.
No external dependencies required.
"""

import time
from collections import defaultdict
from typing import Dict


class APIMetrics:
    """Collects basic API metrics in memory."""

    def __init__(self):
        self.start_time = time.time()
        self.total_requests = 0
        self.total_errors = 0
        self.active_websockets = 0
        self.active_sessions = 0
        self.requests_by_endpoint: Dict[str, int] = defaultdict(int)
        self._response_times: list = []

    def record_request(self, endpoint: str, duration_ms: float, is_error: bool = False):
        self.total_requests += 1
        self.requests_by_endpoint[endpoint] += 1
        self._response_times.append(duration_ms)
        # Keep only last 1000 response times
        if len(self._response_times) > 1000:
            self._response_times = self._response_times[-1000:]
        if is_error:
            self.total_errors += 1

    @property
    def uptime_seconds(self) -> float:
        return time.time() - self.start_time

    @property
    def avg_response_time_ms(self) -> float:
        if not self._response_times:
            return 0.0
        return sum(self._response_times) / len(self._response_times)

    def to_dict(self) -> dict:
        return {
            "uptime_seconds": round(self.uptime_seconds, 1),
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "active_websockets": self.active_websockets,
            "active_sessions": self.active_sessions,
            "requests_by_endpoint": dict(self.requests_by_endpoint),
            "avg_response_time_ms": round(self.avg_response_time_ms, 2),
        }


metrics = APIMetrics()
