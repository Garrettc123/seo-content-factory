"""Tests for the Stripe billing module."""
import os
import pytest
from unittest.mock import patch, MagicMock

from src.billing import (
    PLANS,
    create_checkout_session,
    get_subscription,
    list_active_subscriptions,
    monthly_revenue,
    _subscriptions,
)


def test_plans_structure():
    assert set(PLANS.keys()) == {"starter", "pro", "agency"}
    assert PLANS["starter"]["price_usd"] == 149
    assert PLANS["starter"]["posts_per_day"] == 20
    assert PLANS["pro"]["price_usd"] == 399
    assert PLANS["pro"]["posts_per_day"] == 50
    assert PLANS["agency"]["price_usd"] == 999
    assert PLANS["agency"]["posts_per_day"] is None  # unlimited


def test_create_checkout_session_invalid_plan():
    with pytest.raises(ValueError, match="Unknown plan"):
        create_checkout_session("invalid", "http://ok", "http://cancel")


def test_create_checkout_session_no_stripe_key():
    with patch.dict(os.environ, {"STRIPE_SECRET_KEY": "", "STRIPE_PRICE_PRO": "price_xyz"}):
        with pytest.raises(RuntimeError, match="STRIPE_SECRET_KEY"):
            create_checkout_session("pro", "http://ok", "http://cancel")


def test_create_checkout_session_no_price_id():
    with patch.dict(os.environ, {
        "STRIPE_SECRET_KEY": "sk_test_key",
        "STRIPE_PRICE_PRO": "",
    }):
        with pytest.raises(RuntimeError, match="STRIPE_PRICE_PRO"):
            create_checkout_session("pro", "http://ok", "http://cancel")


def test_create_checkout_session_success():
    mock_session = MagicMock()
    mock_session.url = "https://checkout.stripe.com/pay/cs_test_abc"
    mock_session.id = "cs_test_abc"

    with patch.dict(os.environ, {
        "STRIPE_SECRET_KEY": "sk_test_key",
        "STRIPE_PRICE_PRO": "price_pro_test",
    }):
        with patch("stripe.checkout.Session.create", return_value=mock_session):
            result = create_checkout_session("pro", "http://ok", "http://cancel")

    assert result["checkout_url"] == mock_session.url
    assert result["session_id"] == mock_session.id


def test_get_subscription_none():
    assert get_subscription("nonexistent") is None


def test_list_active_subscriptions_empty():
    _subscriptions.clear()
    assert list_active_subscriptions() == {}


def test_monthly_revenue_empty():
    _subscriptions.clear()
    assert monthly_revenue() == 0.0


def test_monthly_revenue_with_subscriptions():
    _subscriptions.clear()
    _subscriptions["cus_starter"] = {"plan": "starter", "status": "active"}
    _subscriptions["cus_pro"] = {"plan": "pro", "status": "active"}
    _subscriptions["cus_agency"] = {"plan": "agency", "status": "active"}
    _subscriptions["cus_canceled"] = {"plan": "starter", "status": "canceled"}

    rev = monthly_revenue()
    assert rev == 149 + 399 + 999  # starter + pro + agency (not the canceled one)
    _subscriptions.clear()
