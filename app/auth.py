"""Minimal session-based auth for the operator UI (dashboard + event browser).

This is intentionally simple: a single seeded username/password from
Settings (env vars), checked in constant time, behind a signed session
cookie (Starlette's SessionMiddleware, keyed by SESSION_SECRET_KEY). A real
production deployment would put this behind a proper identity provider
(OAuth2/OIDC) instead -- this is enough to demonstrate the access-control
pattern without building a user-management system for a demo project.

The JSON API (/api/*) is left open, matching how most data platforms treat
read APIs vs. an internal operator console.
"""
from __future__ import annotations

import hmac
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import get_settings

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def is_authenticated(request: Request) -> bool:
    return bool(request.session.get("authenticated"))


def require_login(request: Request) -> Optional[RedirectResponse]:
    """Call at the top of a protected route; if it returns a Response,
    `return` it immediately instead of rendering the page.
    """
    if not is_authenticated(request):
        return RedirectResponse(url=f"/login?next={request.url.path}", status_code=303)
    return None


@router.get("/login")
def login_form(request: Request, error: Optional[str] = None, next: str = "/"):
    if is_authenticated(request):
        return RedirectResponse(url=next or "/", status_code=303)
    return templates.TemplateResponse(
        request=request, name="login.html", context={"error": error, "next": next}
    )


@router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
):
    settings = get_settings()
    valid = hmac.compare_digest(username, settings.dashboard_username) and hmac.compare_digest(
        password, settings.dashboard_password
    )
    if not valid:
        return RedirectResponse(url=f"/login?error=1&next={next}", status_code=303)

    request.session["authenticated"] = True
    request.session["username"] = username
    return RedirectResponse(url=next or "/", status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)
