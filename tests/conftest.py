"""Shared pytest fixtures for the SEO Content Factory test suite."""
import os
import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_placeholder")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_test_placeholder")

TEST_API_KEY = "test-api-key-garcar-ci"


@pytest.fixture
def client():
    from src.app import app, _api_keys
    app.config["TESTING"] = True

    # Inject a valid test API key so @require_api_key passes in all tests
    _api_keys[TEST_API_KEY] = {
        "customer_id": "cus_test",
        "plan": "agency",          # unlimited — no rate-limit interference
        "daily_count": 0,
        "count_date": None,
    }

    with app.test_client() as c:
        yield c

    # Clean up after each test
    _api_keys.pop(TEST_API_KEY, None)
