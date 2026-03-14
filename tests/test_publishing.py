"""Tests for the WordPress and Ghost publishing connectors."""
import pytest
from unittest.mock import patch, MagicMock

import requests

from src.publishing import publish_to_wordpress, publish_to_ghost, _ghost_jwt


# ---------------------------------------------------------------------------
# WordPress tests
# ---------------------------------------------------------------------------

def test_publish_to_wordpress_success():
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "id": 101,
        "link": "https://myblog.com/my-post",
        "status": "publish",
    }
    mock_response.raise_for_status = MagicMock()

    article = {"title": "Test Post", "content": "Hello world", "meta_description": "A test"}
    with patch("src.publishing.requests.post", return_value=mock_response):
        result = publish_to_wordpress(article, "https://myblog.com", "admin", "app_pass")

    assert result["platform"] == "wordpress"
    assert result["post_id"] == 101
    assert result["link"] == "https://myblog.com/my-post"
    assert result["status"] == "publish"


def test_publish_to_wordpress_failure():
    with patch("src.publishing.requests.post", side_effect=requests.exceptions.ConnectionError("timeout")):
        with pytest.raises(RuntimeError, match="WordPress publish failed"):
            publish_to_wordpress(
                {"title": "T", "content": "C"},
                "https://myblog.com",
                "admin",
                "pass",
            )


def test_publish_to_wordpress_http_error():
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("403 Forbidden")

    with patch("src.publishing.requests.post", return_value=mock_response):
        with pytest.raises(RuntimeError, match="WordPress publish failed"):
            publish_to_wordpress(
                {"title": "T", "content": "C"},
                "https://myblog.com",
                "admin",
                "wrong_pass",
            )


# ---------------------------------------------------------------------------
# Ghost tests
# ---------------------------------------------------------------------------

def test_ghost_jwt_format():
    # key_secret must be valid hex (32 hex chars = 16 bytes)
    key_id = "abc123"
    key_secret = "deadbeef01234567deadbeef01234567"
    token = _ghost_jwt(key_id, key_secret)
    parts = token.split(".")
    assert len(parts) == 3  # header.payload.signature


def test_publish_to_ghost_success():
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "posts": [
            {
                "id": "ghost-post-id-1",
                "url": "https://myghost.io/test-post",
                "status": "published",
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()

    article = {"title": "Ghost Test", "content": "<p>Body</p>", "meta_description": "A ghost post"}
    with patch("src.publishing.requests.post", return_value=mock_response):
        result = publish_to_ghost(
            article,
            "https://myghost.io",
            "abc123:deadbeef01234567deadbeef01234567",
        )

    assert result["platform"] == "ghost"
    assert result["post_id"] == "ghost-post-id-1"
    assert result["link"] == "https://myghost.io/test-post"


def test_publish_to_ghost_failure():
    with patch("src.publishing.requests.post", side_effect=requests.exceptions.ConnectionError("timeout")):
        with pytest.raises(RuntimeError, match="Ghost publish failed"):
            publish_to_ghost(
                {"title": "T", "content": "C"},
                "https://myghost.io",
                "abc123:deadbeef01234567deadbeef01234567",
            )
