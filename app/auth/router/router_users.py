from typing import Any

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse

from app.auth.dto.user_dto import UserCreateSchema, UserSchema, UserUpdateSchema
from app.auth.router.dependencies import get_user_service
from app.auth.service.service_user import ServiceUser
from app.shared.security.security import require_admin
from app.shared.templates import templates

router = APIRouter(prefix="/usuarios", tags=["usuarios"], dependencies=[Depends(require_admin)])


@router.get("")
def users_page(
    request: Request,
    service: ServiceUser = Depends(get_user_service),
    current_user: dict[str, Any] = Depends(require_admin),
):
    users = service.list_users()
    return templates.TemplateResponse(
        request,
        "usuarios.html",
        {"users": users, "current_user": current_user, "error": None},
    )


@router.post("")
def create_user(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    service: ServiceUser = Depends(get_user_service),
    current_user: dict[str, Any] = Depends(require_admin),
):
    try:
        data = UserCreateSchema(name=name, email=email, password=password, role=role)
        service.create_user(data)
    except Exception as exc:
        users = service.list_users()
        detail = getattr(exc, "detail", str(exc))
        return templates.TemplateResponse(
            request,
            "usuarios.html",
            {"users": users, "current_user": current_user, "error": detail},
            status_code=400,
        )
    return RedirectResponse(url="/usuarios", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{user_id}/toggle-ativo")
def toggle_active(
    user_id: int,
    is_active: bool = Form(...),
    service: ServiceUser = Depends(get_user_service),
):
    service.update_user(user_id, UserUpdateSchema(is_active=is_active))
    return RedirectResponse(url="/usuarios", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{user_id}/excluir")
def delete_user(
    user_id: int,
    service: ServiceUser = Depends(get_user_service),
    current_user: dict[str, Any] = Depends(require_admin),
):
    service.delete_user(user_id, current_user_id=int(current_user["sub"]))
    return RedirectResponse(url="/usuarios", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/api", response_model=list[UserSchema])
def list_users_api(service: ServiceUser = Depends(get_user_service)):
    return service.list_users()
