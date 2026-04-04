"""Shared pytest fixtures for the SEO Content Factory test suite."""
import os
import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_placeholder")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_test_placeholder")


@pytest.fixture
def client():
    from src.app import app
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c
