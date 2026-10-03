from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse

from app.auth.router.dependencies import get_auth_service
from app.auth.service.service_auth import ServiceAuth
from app.shared.settings import settings
from app.shared.templates import templates

router = APIRouter(tags=["auth"])


@router.get("/login")
def login_page(request: Request):
    if request.cookies.get(settings.session_cookie_name):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login")
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    service: ServiceAuth = Depends(get_auth_service),
):
    try:
        token = service.login(email=email, password=password)
    except Exception as exc:
        detail = getattr(exc, "detail", "Falha ao autenticar")
        return templates.TemplateResponse(request, "login.html", {"error": detail}, status_code=401)

    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.jwt_expire_minutes * 60,
    )
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(settings.session_cookie_name)
    return response
