import pytest

import app.security as security


@pytest.fixture(autouse=True)
def _clear_rate_limiter():
    """Reset the in-memory rate-limit window between tests."""
    security._hits.clear()
    yield
    security._hits.clear()
