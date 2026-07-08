from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, func, select

from app.auth import get_current_user
from app.db import get_session
from app.models import User
from app.templating import templates

router = APIRouter()


@router.get("/login")
def login_form(request: Request, next: str = "/predictions", user: User | None = Depends(get_current_user)):
    if user is not None:
        return RedirectResponse(url=next, status_code=303)

    return templates.TemplateResponse(request, "login.html", {"next": next, "error": None, "user": None})


@router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(...),
    next: str = Form("/predictions"),
    session: Session = Depends(get_session),
):
    name = username.strip()
    if not name:
        return templates.TemplateResponse(
            request, "login.html", {"next": next, "error": "Enter a username.", "user": None}
        )

    # Case-insensitive lookup so "Ulysse" and "ulysse" recover the same account instead
    # of silently creating a second, empty one.
    user = session.exec(select(User).where(func.lower(User.name) == name.lower())).first()
    if user is None:
        user = User(name=name)
        session.add(user)
        session.commit()
        session.refresh(user)

    request.session["user_id"] = user.id
    return RedirectResponse(url=next, status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)
