"""
Stripe billing integration.
Plans: Starter $149/mo (20 posts/day), Pro $399/mo (50 posts/day), Agency $999/mo (unlimited)
"""
import os
import logging
from typing import Dict, Optional

import stripe

logger = logging.getLogger(__name__)

PLANS: Dict[str, Dict] = {
    "starter": {
        "name": "Starter",
        "price_usd": 149,
        "posts_per_day": 20,
        "description": "20 posts/day – perfect for small blogs and startups",
        "price_id_env": "STRIPE_PRICE_STARTER",
    },
    "pro": {
        "name": "Pro",
        "price_usd": 399,
        "posts_per_day": 50,
        "description": "50 posts/day – scale your content marketing",
        "price_id_env": "STRIPE_PRICE_PRO",
    },
    "agency": {
        "name": "Agency",
        "price_usd": 999,
        "posts_per_day": None,
        "description": "Unlimited posts/day – for agencies managing many clients",
        "price_id_env": "STRIPE_PRICE_AGENCY",
    },
}

_subscriptions: Dict[str, Dict] = {}


def _stripe_key() -> str:
    key = os.getenv("STRIPE_SECRET_KEY", "")
    if not key:
        raise RuntimeError("STRIPE_SECRET_KEY environment variable not set")
    return key


def create_checkout_session(plan_key: str, success_url: str, cancel_url: str) -> Dict:
    if plan_key not in PLANS:
        raise ValueError(f"Unknown plan '{plan_key}'. Choose from: {list(PLANS)}")
    plan = PLANS[plan_key]
    price_id = os.getenv(plan["price_id_env"], "")
    if not price_id:
        raise RuntimeError(
            f"Stripe price ID not configured. Set {plan['price_id_env']} env var."
        )
    stripe.api_key = _stripe_key()
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"plan": plan_key},
    )
    return {"checkout_url": session.url, "session_id": session.id}


def handle_webhook(payload: bytes, sig_header: str) -> Dict:
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    stripe.api_key = _stripe_key()
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except stripe.error.SignatureVerificationError as e:
        raise ValueError(f"Invalid webhook signature: {e}") from e

    event_type = event["type"]
    result: Dict = {"received": True, "type": event_type}

    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        customer_id = session.get("customer")
        plan_key = session.get("metadata", {}).get("plan", "pro")
        subscription_id = session.get("subscription")
        _subscriptions[customer_id] = {
            "plan": plan_key,
            "subscription_id": subscription_id,
            "status": "active",
            "customer_id": customer_id,
        }
        # Return these so app.py can provision the API key
        result["customer_id"] = customer_id
        result["plan"] = plan_key
        logger.info("New subscription: customer=%s plan=%s", customer_id, plan_key)

    elif event_type in ("customer.subscription.deleted", "customer.subscription.updated"):
        sub = event["data"]["object"]
        customer_id = sub.get("customer")
        status = sub.get("status", "canceled")
        if customer_id in _subscriptions:
            _subscriptions[customer_id]["status"] = status
        logger.info("Subscription updated: customer=%s status=%s", customer_id, status)

    return result


def get_subscription(customer_id: str) -> Optional[Dict]:
    return _subscriptions.get(customer_id)


def list_active_subscriptions() -> Dict[str, Dict]:
    return {k: v for k, v in _subscriptions.items() if v.get("status") == "active"}


def monthly_revenue() -> float:
    total = 0.0
    for sub in list_active_subscriptions().values():
        plan = PLANS.get(sub.get("plan", ""), {})
        total += plan.get("price_usd", 0)
    return total
