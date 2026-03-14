"""
Publishing connectors for WordPress (REST API) and Ghost (Admin API).
"""
import hashlib
import hmac
import logging
import time
from typing import Dict

import requests

logger = logging.getLogger(__name__)

# Timeout for HTTP requests to external CMS endpoints
_REQUEST_TIMEOUT = 30


def publish_to_wordpress(
    article: Dict,
    wp_url: str,
    wp_username: str,
    wp_app_password: str,
    status: str = "publish",
) -> Dict:
    """
    Publish an article to a WordPress site using the WP REST API.

    Args:
        article: dict with keys title, content, meta_description
        wp_url: base URL of the WordPress site, e.g. "https://myblog.com"
        wp_username: WordPress username
        wp_app_password: WordPress Application Password (generated in WP admin)
        status: "publish" or "draft"

    Returns:
        dict with post id, link, and status
    """
    endpoint = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts"
    payload = {
        "title": article.get("title", ""),
        "content": article.get("content", ""),
        "excerpt": article.get("meta_description", ""),
        "status": status,
    }
    try:
        resp = requests.post(
            endpoint,
            json=payload,
            auth=(wp_username, wp_app_password),
            timeout=_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "platform": "wordpress",
            "post_id": data.get("id"),
            "link": data.get("link"),
            "status": data.get("status"),
        }
    except requests.exceptions.RequestException as e:
        logger.error("WordPress publish failed: %s", e)
        raise RuntimeError(f"WordPress publish failed: {e}") from e


def publish_to_ghost(
    article: Dict,
    ghost_url: str,
    ghost_admin_api_key: str,
    status: str = "published",
) -> Dict:
    """
    Publish an article to a Ghost site using the Ghost Admin API.

    Args:
        article: dict with keys title, content (HTML), meta_description
        ghost_url: base URL of the Ghost site, e.g. "https://myblog.ghost.io"
        ghost_admin_api_key: Ghost Admin API key (format: "id:secret")
        status: "published" or "draft"

    Returns:
        dict with post id, url, and status
    """
    # Generate JWT for Ghost Admin API v3+
    key_id, key_secret = ghost_admin_api_key.split(":")
    jwt_token = _ghost_jwt(key_id, key_secret)

    endpoint = f"{ghost_url.rstrip('/')}/ghost/api/admin/posts/"
    headers = {
        "Authorization": f"Ghost {jwt_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "posts": [
            {
                "title": article.get("title", ""),
                "html": article.get("content", ""),
                "custom_excerpt": article.get("meta_description", ""),
                "status": status,
            }
        ]
    }
    try:
        resp = requests.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        post = resp.json()["posts"][0]
        return {
            "platform": "ghost",
            "post_id": post.get("id"),
            "link": post.get("url"),
            "status": post.get("status"),
        }
    except requests.exceptions.RequestException as e:
        logger.error("Ghost publish failed: %s", e)
        raise RuntimeError(f"Ghost publish failed: {e}") from e


def _ghost_jwt(key_id: str, key_secret: str) -> str:
    """Generate a short-lived HS256 JWT for the Ghost Admin API."""
    import base64
    import json

    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT", "kid": key_id}
    payload = {"iat": now, "exp": now + 300, "aud": "/admin/"}

    def _b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    header_enc = _b64url(json.dumps(header, separators=(",", ":")).encode())
    payload_enc = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_enc}.{payload_enc}".encode()
    secret_bytes = bytes.fromhex(key_secret)
    sig = hmac.new(secret_bytes, signing_input, hashlib.sha256).digest()
    return f"{header_enc}.{payload_enc}.{_b64url(sig)}"
