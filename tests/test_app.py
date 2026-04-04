"""Tests for the main Flask application endpoints."""
from unittest.mock import patch


def test_index(client):
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["service"] == "SEO Content Factory"
    # Verify correct pricing tiers
    pricing = data["pricing"]
    assert "starter" in pricing
    assert "pro" in pricing
    assert "agency" in pricing
    assert "149" in pricing["starter"]
    assert "399" in pricing["pro"]
    assert "999" in pricing["agency"]


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "openai_configured" in data


def test_generate_missing_keyword(client):
    resp = client.post("/api/v1/generate", json={})
    assert resp.status_code == 400
    assert "seed_keyword" in resp.get_json()["error"]


def test_generate_article(client):
    mock_content = "# Python Guide\n\nThis is sample content."
    with patch("src.app.write_article", return_value=mock_content):
        resp = client.post(
            "/api/v1/generate",
            json={"seed_keyword": "python programming", "word_count": 1000},
        )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["title"] == "Python Programming: Complete Guide (2026)"
    assert data["content"] == mock_content
    assert "keywords" in data
    assert "seo_score" in data
    assert "meta_description" in data


def test_generate_updates_stats(client):
    mock_content = "# Test\n\nContent."
    with patch("src.app.write_article", return_value=mock_content):
        client.post("/api/v1/generate", json={"seed_keyword": "seo tips"})
    stats_resp = client.get("/api/v1/stats")
    stats = stats_resp.get_json()
    assert stats["articles_generated_today"] >= 1


def test_stats(client):
    resp = client.get("/api/v1/stats")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "articles_generated_today" in data
    assert "average_seo_score" in data
    assert "total_words_today" in data
    assert "revenue_today" in data


def test_dashboard(client):
    resp = client.get("/api/v1/dashboard")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "posts_generated_today" in data
    assert "average_seo_score" in data
    assert "active_subscriptions" in data
    assert "monthly_revenue_usd" in data
    assert "annual_run_rate_usd" in data
    assert "plans" in data
    plans = data["plans"]
    assert set(plans.keys()) == {"starter", "pro", "agency"}
    assert plans["starter"]["price_usd"] == 149
    assert plans["pro"]["price_usd"] == 399
    assert plans["agency"]["price_usd"] == 999


def test_subscribe_missing_plan(client):
    resp = client.post("/api/v1/subscribe", json={})
    assert resp.status_code == 400


def test_subscribe_invalid_plan(client):
    resp = client.post("/api/v1/subscribe", json={"plan": "enterprise"})
    assert resp.status_code in (400, 503)


def test_subscribe_no_stripe_key(client):
    import os
    with patch.dict(os.environ, {"STRIPE_SECRET_KEY": ""}):
        resp = client.post("/api/v1/subscribe", json={"plan": "pro"})
    assert resp.status_code in (400, 503)


def test_webhook_bad_signature(client):
    resp = client.post(
        "/api/v1/webhook",
        data=b'{"type":"checkout.session.completed"}',
        content_type="application/json",
        headers={"Stripe-Signature": "bad-sig"},
    )
    assert resp.status_code == 400


def test_publish_missing_article(client):
    resp = client.post("/api/v1/publish", json={"platform": "wordpress"})
    assert resp.status_code == 400


def test_publish_invalid_platform(client):
    resp = client.post(
        "/api/v1/publish",
        json={"article": {"title": "Test"}, "platform": "medium"},
    )
    assert resp.status_code == 400


def test_publish_wordpress_missing_credentials(client):
    import os
    with patch.dict(os.environ, {
        "WORDPRESS_URL": "", "WORDPRESS_USERNAME": "", "WORDPRESS_APP_PASSWORD": ""
    }):
        resp = client.post(
            "/api/v1/publish",
            json={"article": {"title": "Test", "content": "Body"}, "platform": "wordpress"},
        )
    assert resp.status_code == 400


def test_publish_ghost_missing_credentials(client):
    import os
    with patch.dict(os.environ, {"GHOST_URL": "", "GHOST_ADMIN_API_KEY": ""}):
        resp = client.post(
            "/api/v1/publish",
            json={"article": {"title": "Test", "content": "Body"}, "platform": "ghost"},
        )
    assert resp.status_code == 400


def test_publish_wordpress_success(client):
    mock_result = {"platform": "wordpress", "post_id": 42, "link": "https://blog.com/p/42", "status": "publish"}
    with patch("src.app.publish_to_wordpress", return_value=mock_result):
        resp = client.post(
            "/api/v1/publish",
            json={
                "article": {"title": "T", "content": "C"},
                "platform": "wordpress",
                "wp_url": "https://blog.com",
                "wp_username": "admin",
                "wp_app_password": "pass",
            },
        )
    assert resp.status_code == 200
    assert resp.get_json()["post_id"] == 42


def test_publish_ghost_success(client):
    mock_result = {"platform": "ghost", "post_id": "abc", "link": "https://ghost.io/t", "status": "published"}
    with patch("src.app.publish_to_ghost", return_value=mock_result):
        resp = client.post(
            "/api/v1/publish",
            json={
                "article": {"title": "T", "content": "C"},
                "platform": "ghost",
                "ghost_url": "https://myghost.io",
                "ghost_admin_api_key": "abc123:defsecret0123456789abcdef01234567",
            },
        )
    assert resp.status_code == 200
    assert resp.get_json()["platform"] == "ghost"
