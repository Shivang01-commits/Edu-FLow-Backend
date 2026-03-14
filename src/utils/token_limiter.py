import time

class TokenAwareLimiter:

    def __init__(self, tokens_per_minute=8000):
        self.tokens_per_minute = tokens_per_minute
        self.tokens_used = 0
        self.window_start = time.time()

    def wait_if_needed(self, estimated_tokens):
        now = time.time()

        # reset window
        if now - self.window_start >= 60:
            self.tokens_used = 0
            self.window_start = now

        if self.tokens_used + estimated_tokens > self.tokens_per_minute:
            sleep_time = 60 - (now - self.window_start)

            if sleep_time > 0:
                print(f"Sleeping {sleep_time:.2f}s to respect rate limit")
                time.sleep(sleep_time)

            self.tokens_used = 0
            self.window_start = time.time()

    def update_usage(self, actual_tokens):
        self.tokens_used += actual_tokens