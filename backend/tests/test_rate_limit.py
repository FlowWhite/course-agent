import unittest

from course_agent.rate_limit import InMemoryRateLimiter


class RateLimiterTests(unittest.TestCase):
    def test_limit_is_scoped_to_each_key(self):
        limiter = InMemoryRateLimiter(max_requests=1, window_seconds=60)

        self.assertEqual(limiter.check("client-a"), (True, 0))
        allowed, retry_after = limiter.check("client-a")
        self.assertFalse(allowed)
        self.assertGreaterEqual(retry_after, 1)
        self.assertEqual(limiter.check("client-b"), (True, 0))

    def test_invalid_configuration_is_rejected(self):
        with self.assertRaises(ValueError):
            InMemoryRateLimiter(max_requests=0, window_seconds=60)
        with self.assertRaises(ValueError):
            InMemoryRateLimiter(max_requests=1, window_seconds=0)


if __name__ == "__main__":
    unittest.main()
