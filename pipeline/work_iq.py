"""
work_iq.py — Microsoft Graph / Work IQ integration
Searches users by name, validates "next person" fields, enables
the original Feishu-style name→user_id→card routing workflow.
"""
from __future__ import annotations
import requests
from typing import Any

from config.config import TEAMS_APP_ID, TEAMS_APP_PASSWORD, TEAMS_APP_TENANT_ID

_GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def _get_graph_token() -> str | None:
    """Get a Microsoft Graph token using client credentials flow."""
    if not TEAMS_APP_ID or not TEAMS_APP_PASSWORD or not TEAMS_APP_TENANT_ID:
        return None

    token_url = f"https://login.microsoftonline.com/{TEAMS_APP_TENANT_ID}/oauth2/v2.0/token"
    try:
        resp = requests.post(token_url, data={
            "client_id": TEAMS_APP_ID,
            "client_secret": TEAMS_APP_PASSWORD,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        }, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("access_token")
        print(f"[work_iq] token failed: {resp.status_code} {resp.text[:200]}")
        return None
    except Exception as e:
        print(f"[work_iq] token error: {e}")
        return None


def search_users(name: str, top: int = 5) -> list[dict[str, Any]]:
    """Search Microsoft 365 users by display name or email.
    This is the Work IQ equivalent of Feishu's user lookup.

    Returns: [{"display_name":..., "email":..., "user_id":..., "department":..., "job_title":...}]
    """
    token = _get_graph_token()
    if not token:
        print("[work_iq] no Graph token — user search unavailable")
        return []

    try:
        resp = requests.get(
            f"{_GRAPH_BASE}/users",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "$filter": f"startswith(displayName,'{name}') or startswith(mail,'{name}')",
                "$select": "id,displayName,mail,userPrincipalName,department,jobTitle",
                "$top": top,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            users = resp.json().get("value", [])
            return [
                {
                    "display_name": u.get("displayName", ""),
                    "email": u.get("mail") or u.get("userPrincipalName", ""),
                    "user_id": u.get("id", ""),
                    "department": u.get("department", ""),
                    "job_title": u.get("jobTitle", ""),
                }
                for u in users
            ]
        print(f"[work_iq] search failed: {resp.status_code} {resp.text[:200]}")
        return []
    except Exception as e:
        print(f"[work_iq] search error: {e}")
        return []


def lookup_user(name: str) -> dict[str, Any] | None:
    """Look up a single user by name. Returns the first match or None."""
    users = search_users(name, top=1)
    return users[0] if users else None


def verify_next_person(name: str) -> str:
    """Verify that a name exists in the organization.
    Returns a confirmation message string.

    If the user is found: "✅ 张三 (zhangsan@contoso.com) — Engineering / Developer"
    If not found: "⚠️ 张三 — not found in directory, prompt manual routing"
    """
    user = lookup_user(name)
    if user:
        dept = user.get("department", "")
        title = user.get("job_title", "")
        extra = ""
        if dept or title:
            extra = f" — {dept}"
            if title:
                extra += f" / {title}"
        return f"✅ {user['display_name']} ({user['email']}){extra}"
    return f"⚠️ **{name}** — name not found in Work IQ. Please verify the spelling or enter the email."
