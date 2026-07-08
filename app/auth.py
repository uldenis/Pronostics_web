from fastapi import Depends, Request
from sqlmodel import Session

from app.db import get_session
from app.models import User


class NotAuthenticated(Exception):
    """Raised by require_user; caught by the handler registered in app/main.py to redirect to /login."""


def get_current_user(request: Request, session: Session = Depends(get_session)) -> User | None:
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    return session.get(User, user_id)


def require_user(user: User | None = Depends(get_current_user)) -> User:
    if user is None:
        raise NotAuthenticated()
    return user
