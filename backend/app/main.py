"""Monta o FastAPI: routers de `api/v1/` sob o prefixo `/api/v1`
(seção 4.5), e serve o build estático do frontend (Vite) como fallback
de rota `/` → `index.html` (seção 6.1)."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.v1 import acessorios, calculo, deducoes, paradas, parcelas, processos, sistema
from app.core.config import diretorio_frontend_dist

_FRONTEND_DIST = diretorio_frontend_dist()


def criar_app() -> FastAPI:
    app = FastAPI(title="Cálculo Judicial")

    for router in (
        processos.router,
        parcelas.router,
        acessorios.router,
        deducoes.router,
        paradas.router,
        calculo.router,
        sistema.router,
    ):
        app.include_router(router, prefix="/api/v1")

    if _FRONTEND_DIST.is_dir():
        app.mount("/", StaticFiles(directory=_FRONTEND_DIST, html=True), name="frontend")

    return app


app = criar_app()
