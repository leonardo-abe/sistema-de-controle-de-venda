from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from starlette.status import HTTP_401_UNAUTHORIZED

from app.auth import router_auth, router_users
from app.auth.enum.role_permissions import RolePermissions
from app.auth.models import User
from app.infra.db.sqlite import Base, SessionLocal, engine
from app.shared.security.security import hash_password
from app.shared.settings import settings
from app.vendas import router_clientes, router_dashboard, router_import, router_pedidos, router_produtos
from app.vendas.models import ImportBatch, ItemVenda, Pagamento, Pedido, Produto  # noqa: F401


def seed_admin_user() -> None:
    with SessionLocal() as session:
        exists = session.query(User).filter(User.email == settings.admin_email).first()
        if exists is not None:
            return
        admin = User(
            name=settings.admin_name,
            email=settings.admin_email,
            hashed_password=hash_password(settings.admin_password),
            role=RolePermissions.ADMIN,
            is_active=True,
        )
        session.add(admin)
        session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_admin_user()
    yield


app = FastAPI(title="Deposito Baratao", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.exception_handler(HTTPException)
async def auth_redirect_handler(request: Request, exc: HTTPException):
    if exc.status_code == HTTP_401_UNAUTHORIZED and "application/json" not in request.headers.get("accept", ""):
        return RedirectResponse(url="/login")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.include_router(router_auth)
app.include_router(router_users)
app.include_router(router_import)
app.include_router(router_pedidos)
app.include_router(router_clientes)
app.include_router(router_produtos)
app.include_router(router_dashboard)
