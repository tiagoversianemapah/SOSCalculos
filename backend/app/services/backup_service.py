"""Backup/restauração do `dados.db` (seção 9) — a única proteção contra
perda de disco, já que o app é local e não há servidor nem sincronização.
"""
from __future__ import annotations

from pathlib import Path

from app.core.config import caminho_banco
from app.core.db import configurar_sessao, criar_engine, engine_atual

_ASSINATURA_SQLITE = b"SQLite format 3\x00"


class BackupInvalidoError(Exception):
    """O arquivo enviado para restaurar não parece ser um SQLite válido."""


def exportar_backup() -> bytes:
    """Devolve os bytes atuais do `dados.db`. Força um checkpoint do WAL
    antes de ler — com `journal_mode=WAL` (seção 6.1), transações
    recentes podem estar só no `-wal` e não no arquivo principal ainda;
    sem isso, um backup lido "a frio" perderia dados recém-commitados.
    """
    engine = engine_atual()
    with engine.begin() as conexao:
        conexao.exec_driver_sql("PRAGMA wal_checkpoint(TRUNCATE)")
    return caminho_banco().read_bytes()


def restaurar_backup(conteudo: bytes) -> None:
    """Substitui o `dados.db` pelo conteúdo enviado.

    Fecha todas as conexões do banco atual antes de trocar o arquivo
    (no Windows não dá para sobrescrever um arquivo com handle aberto) e
    reabre a sessão depois, apontando pro arquivo novo — nunca deixa a
    aplicação com uma sessão presa no arquivo antigo.
    """
    if not conteudo.startswith(_ASSINATURA_SQLITE):
        raise BackupInvalidoError("o arquivo enviado não parece ser um backup válido (.db)")

    caminho = caminho_banco()
    engine_atual().dispose()

    caminho_temporario = Path(str(caminho) + ".restaurando")
    caminho_temporario.write_bytes(conteudo)
    caminho_temporario.replace(caminho)  # troca atômica no mesmo volume

    # sidecars do WAL do banco antigo não fazem sentido pro arquivo novo
    for sufixo in ("-wal", "-shm"):
        sidecar = Path(str(caminho) + sufixo)
        if sidecar.exists():
            sidecar.unlink()

    configurar_sessao(criar_engine(caminho))
