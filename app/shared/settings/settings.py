from decouple import config


class Settings:
    app_secret_key: str = config("APP_SECRET_KEY")
    database_url: str = config("APP_DATABASE_URL", default="sqlite:///./data/app.db")

    admin_email: str = config("ADMIN_EMAIL")
    admin_password: str = config("ADMIN_PASSWORD")
    admin_name: str = config("ADMIN_NAME", default="Administrador")

    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = config("JWT_EXPIRE_MINUTES", default=720, cast=int)

    session_cookie_name: str = "access_token"

    docs_user: str = config("DOCS_USER", default="admin")
    docs_password: str = config("DOCS_PASSWORD", default="troque-esta-senha")


settings = Settings()
