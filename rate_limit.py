import math
from collections import defaultdict, deque
from threading import Lock
from time import monotonic


class InMemoryRateLimiter:
    """
    基于固定时间窗口的内存限流器。
    """

    def __init__(
        self,
        max_requests: int,
        window_seconds: int,
    ):
        if max_requests <= 0:
            raise ValueError(
                "max_requests 必须大于 0"
            )

        if window_seconds <= 0:
            raise ValueError(
                "window_seconds 必须大于 0"
            )

        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> tuple[bool, int]:
        """
        返回：

        True, 0
            当前请求允许通过。

        False, retry_after
            当前请求被限制，retry_after 表示建议等待秒数。
        """
        now = monotonic()
        window_start = now - self.window_seconds

        with self._lock:
            request_times = self._requests[key]

            while (
                request_times
                and request_times[0] <= window_start
            ):
                request_times.popleft()

            if len(request_times) >= self.max_requests:
                retry_after = math.ceil(
                    self.window_seconds
                    - (now - request_times[0])
                )

                return False, max(1, retry_after)

            request_times.append(now)

        return True, 0