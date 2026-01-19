import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent.restrict_usage import RateLimiter


@pytest.fixture
def limiter():
    """Create a RateLimiter instance for testing."""
    return RateLimiter(max_requests=5, window_minutes=60)


def test_first_request_allowed(limiter):
    """First request should always be allowed."""
    assert limiter.is_allowed("test_ip") is True


def test_requests_within_limit(limiter):
    """All requests within limit should be allowed."""
    for _ in range(5):
        assert limiter.is_allowed("test_ip") is True


def test_request_exceeds_limit(limiter):
    """Request exceeding limit should be blocked."""
    for _ in range(5):
        limiter.is_allowed("test_ip")
    assert limiter.is_allowed("test_ip") is False


def test_different_identifiers_separate(limiter):
    """Different identifiers should have separate limits."""
    for _ in range(5):
        limiter.is_allowed("ip1")
    assert limiter.is_allowed("ip1") is False
    assert limiter.is_allowed("ip2") is True


def test_get_remaining(limiter):
    """get_remaining should return correct count."""
    assert limiter.get_remaining("test_ip") == 5
    limiter.is_allowed("test_ip")
    assert limiter.get_remaining("test_ip") == 4
    for _ in range(4):
        limiter.is_allowed("test_ip")
    assert limiter.get_remaining("test_ip") == 0


def test_old_requests_cleaned(limiter):
    """Old requests outside window should be cleaned."""
    fixed_time = datetime(2024, 1, 1, 12, 0, 0)
    
    with patch('agent.restrict_usage.datetime') as mock_datetime:
        mock_datetime.now.return_value = fixed_time
        
        for _ in range(5):
            limiter.is_allowed("test_ip")
        
        assert limiter.is_allowed("test_ip") is False
        
        # Move time forward past the window
        mock_datetime.now.return_value = fixed_time + timedelta(minutes=61)
        
        assert limiter.is_allowed("test_ip") is True
        assert limiter.get_remaining("test_ip") == 4


def test_multiple_identifiers_tracking(limiter):
    """Multiple identifiers should be tracked independently."""
    limiter.is_allowed("user1")
    limiter.is_allowed("user1")
    limiter.is_allowed("user2")
    
    assert limiter.get_remaining("user1") == 3
    assert limiter.get_remaining("user2") == 4
    assert limiter.get_remaining("user3") == 5