from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from app.auth import NotAuthenticated
from app.config import settings
from app.routes import auth, home, matches, predictions

app = FastAPI(title="Pronostic")

# Default session lifetime is 14 days - too short for a season-long pool. A year comfortably
# covers a full season; logging back in with the same username always works regardless.
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key, max_age=60 * 60 * 24 * 365)


@app.exception_handler(NotAuthenticated)
def handle_not_authenticated(request: Request, _exc: NotAuthenticated) -> RedirectResponse:
    next_path = request.url.path
    if request.url.query:
        next_path += f"?{request.url.query}"
    return RedirectResponse(url=f"/login?next={quote(next_path)}", status_code=303)


app.include_router(auth.router)
app.include_router(home.router)
app.include_router(matches.router)
app.include_router(predictions.router)
