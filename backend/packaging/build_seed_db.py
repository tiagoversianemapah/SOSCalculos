"""Gera o banco semente `dados.db` embarcado no executável (seção 5/6.1).

Uso: `python packaging/build_seed_db.py [caminho_saida]`

Roda uma vez, no momento do build (não no computador do usuário): cria
um SQLite vazio, aplica as migrações do Alembic programaticamente e
baixa a série histórica completa de cada índice do BCB SGS. Assim o
primeiro uso do app não depende de baixar décadas de série — a
checagem na abertura (seção 5, `atualizador.py`) só precisa preencher o
delta desde o build até hoje.
"""
from __future__ import annotations

import os
import sys
from datetime import date
from functools import partial
from pathlib import Path

RAIZ_BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_BACKEND))

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402

from app.core.db import configurar_sessao, criar_engine, get_db  # noqa: E402
from app.services.indices.atualizador import atualizar_todos  # noqa: E402
from app.services.indices.bcb_sgs import buscar_serie  # noqa: E402

# Download único do histórico completo (décadas, séries diárias com
# milhares de pontos) — precisa de mais tempo que o timeout padrão de
# 10s usado na checagem incremental em runtime (seção 6.1).
_TIMEOUT_BUILD_SEGUNDOS = 60.0


def gerar_banco_semente(caminho_saida: Path) -> None:
    if caminho_saida.exists():
        caminho_saida.unlink()
    caminho_saida.parent.mkdir(parents=True, exist_ok=True)

    os.environ["DATABASE_URL"] = f"sqlite:///{caminho_saida}"
    alembic_cfg = Config(str(RAIZ_BACKEND / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")

    engine = criar_engine(caminho_saida)
    configurar_sessao(engine)
    db = next(get_db())
    try:
        print("Baixando séries históricas do BCB SGS...")
        buscar_com_timeout_longo = partial(buscar_serie, timeout=_TIMEOUT_BUILD_SEGUNDOS)
        resultado = atualizar_todos(db, date.today(), buscar_serie_fn=buscar_com_timeout_longo)
        for indice, status in sorted(resultado.items(), key=lambda item: item[0].value):
            print(f"  {indice.value}: {status}")
    finally:
        db.close()

    print(f"Banco semente gerado em {caminho_saida}")


if __name__ == "__main__":
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ_BACKEND / "packaging" / "dados_semente.db"
    gerar_banco_semente(destino)
