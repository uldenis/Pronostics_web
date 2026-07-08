from fastapi import APIRouter, Depends, Request

from app.auth import get_current_user
from app.models import User
from app.templating import templates

router = APIRouter()


@router.get("/")
def home(request: Request, user: User | None = Depends(get_current_user)):
    return templates.TemplateResponse(request, "home.html", {"user": user})
