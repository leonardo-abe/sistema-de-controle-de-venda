import os

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")


def static_url(path: str) -> str:
    """Monta a URL do asset estatico com a data de modificacao do arquivo
    como query string, para o navegador buscar a versao nova sempre que o
    arquivo mudar (evita servir JS/CSS antigo do cache)."""
    full_path = os.path.join("static", path)
    try:
        version = int(os.path.getmtime(full_path))
    except OSError:
        version = 0
    return f"/static/{path}?v={version}"


templates.env.globals["static_url"] = static_url
