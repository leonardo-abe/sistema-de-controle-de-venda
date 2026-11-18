import secrets
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.exceptions import HTTPException
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
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


app = FastAPI(title="Deposito Baratao", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

app.mount("/static", StaticFiles(directory="static"), name="static")

docs_basic_auth = HTTPBasic()


def verificar_docs_auth(credentials: HTTPBasicCredentials = Depends(docs_basic_auth)) -> None:
    usuario_ok = secrets.compare_digest(credentials.username, settings.docs_user)
    senha_ok = secrets.compare_digest(credentials.password, settings.docs_password)
    if not (usuario_ok and senha_ok):
        raise HTTPException(
            status_code=401,
            detail="Credenciais invalidas",
            headers={"WWW-Authenticate": "Basic"},
        )


@app.get("/openapi.json", include_in_schema=False)
async def openapi_json(_: None = Depends(verificar_docs_auth)):
    return JSONResponse(get_openapi(title=app.title, version="1.0.0", routes=app.routes))


@app.get("/docs", include_in_schema=False)
async def docs(_: None = Depends(verificar_docs_auth)):
    return get_swagger_ui_html(openapi_url="/openapi.json", title=f"{app.title} - Docs")


@app.get("/redoc", include_in_schema=False)
async def redoc(_: None = Depends(verificar_docs_auth)):
    return get_redoc_html(openapi_url="/openapi.json", title=f"{app.title} - ReDoc")


@app.exception_handler(HTTPException)
async def auth_redirect_handler(request: Request, exc: HTTPException):
    eh_desafio_basic = exc.headers and "WWW-Authenticate" in exc.headers
    if exc.status_code == HTTP_401_UNAUTHORIZED and eh_desafio_basic:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers)
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
