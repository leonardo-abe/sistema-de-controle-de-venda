from app.vendas.router.router_clientes import router as router_clientes
from app.vendas.router.router_dashboard import router as router_dashboard
from app.vendas.router.router_import import router as router_import
from app.vendas.router.router_pedidos import router as router_pedidos
from app.vendas.router.router_produtos import router as router_produtos

__all__ = ["router_clientes", "router_dashboard", "router_import", "router_pedidos", "router_produtos"]
