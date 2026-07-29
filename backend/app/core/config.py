"""Constantes de configuração do app desktop (seção 6.1).

Fonte única da versão do app — tanto o empacotamento (PyInstaller)
quanto `GET /app/status` (seção 4.5/9) leem daqui.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_VERSION = "0.1.0"
GITHUB_REPO = "tiago/calculo-judicial"  # usado na checagem de versão nova (seção 9)


def diretorio_dados() -> Path:
    """`%APPDATA%\\CalculoJudicial\\` — nunca grava no diretório de instalação."""
    base = os.environ.get("APPDATA") or str(Path.home())
    caminho = Path(base) / "CalculoJudicial"
    caminho.mkdir(parents=True, exist_ok=True)
    return caminho


def caminho_banco() -> Path:
    return diretorio_dados() / "dados.db"


def diretorio_base_recursos() -> Path:
    """Raiz de onde ler recursos empacotados dentro de `backend/`
    (banco semente, alembic) — o diretório `backend/` em dev, ou a pasta
    temporária que o PyInstaller extrai (`sys._MEIPASS`) quando rodando
    como executável congelado (seção 6.1/`packaging/app.spec`). No
    executável, `app.spec` achata tudo (inclusive `frontend/dist`) numa
    raiz só — mas em dev, `frontend/` é irmã de `backend/`, não filha
    (ver `diretorio_frontend_dist` abaixo, que trata essa diferença)."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS"))  # noqa: B009 — só existe quando frozen
    return Path(__file__).resolve().parents[2]


def diretorio_frontend_dist() -> Path:
    """`frontend/dist` — em dev fica um nível acima de `backend/`
    (projeto/frontend/dist); no executável, `app.spec` embute como
    `frontend/dist` dentro da mesma raiz que `diretorio_base_recursos`."""
    base = diretorio_base_recursos()
    if getattr(sys, "frozen", False):
        return base / "frontend" / "dist"
    return base.parent / "frontend" / "dist"
