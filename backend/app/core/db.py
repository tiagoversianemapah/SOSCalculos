"""Engine SQLAlchemy + session factory (seção 6.1).

Não cria o engine no import do módulo — quem inicializa explicitamente
é o entrypoint (`app/desktop.py`, seção 6.1) ou os testes, cada um com
o caminho de banco apropriado ao seu contexto. Isso evita efeito
colateral de tocar `%APPDATA%` só por importar `app.models`.
"""
from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def criar_engine(caminho_banco: str | Path) -> Engine:
    engine = create_engine(f"sqlite:///{caminho_banco}", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _pragmas_sqlite(dbapi_connection, connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    return engine


_SessionLocal: sessionmaker[Session] | None = None
_engine_atual: Engine | None = None


def configurar_sessao(engine: Engine) -> None:
    global _SessionLocal, _engine_atual
    _SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    _engine_atual = engine


def engine_atual() -> Engine:
    """Usado por `restaurar_backup` (seção 9): precisa fechar todas as
    conexões abertas do arquivo antigo antes de substituí-lo."""
    if _engine_atual is None:
        raise RuntimeError("Sessão de banco não configurada — chame configurar_sessao(engine) no startup")
    return _engine_atual


def get_db() -> Generator[Session, None, None]:
    if _SessionLocal is None:
        raise RuntimeError(
            "Sessão de banco não configurada — chame configurar_sessao(engine) no startup"
        )
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
