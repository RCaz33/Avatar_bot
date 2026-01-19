from collections import defaultdict
from datetime import datetime, timedelta

# Rate limiter class
class RateLimiter:
    def __init__(self, max_requests=10, window_minutes=60):
        self.max_requests = max_requests
        self.window = timedelta(minutes=window_minutes)
        self.requests = defaultdict(list)
    
    def is_allowed(self, identifier):
        now = datetime.now()
        # Clean old requests
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if now - req_time < self.window
        ]
        
        if len(self.requests[identifier]) < self.max_requests:
            self.requests[identifier].append(now)
            return True
        return False
    
    def get_remaining(self, identifier):
        now = datetime.now()
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if now - req_time < self.window
        ]
        return self.max_requests - len(self.requests[identifier])
