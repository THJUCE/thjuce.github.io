from .balance import router as balance_router
from .create_vps import router as create_router
from .servers import router as servers_router
from .start import router as start_router
from .tariffs import router as tariffs_router
from .topup import router as topup_router

__all__ = [
    "start_router",
    "balance_router",
    "servers_router",
    "create_router",
    "topup_router",
    "tariffs_router",
]
