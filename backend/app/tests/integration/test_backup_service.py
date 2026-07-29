from datetime import date

import pytest

from app import models  # noqa: F401  (registra os modelos em Base.metadata)
from app.core.db import Base, configurar_sessao, criar_engine, get_db
from app.models.processo import Processo
from app.services import backup_service
from app.services.backup_service import BackupInvalidoError, exportar_backup, restaurar_backup


@pytest.fixture()
def banco_temporario(tmp_path, monkeypatch):
    caminho = tmp_path / "dados.db"
    # backup_service importa `caminho_banco` diretamente (from ... import
    # caminho_banco), então precisa remendar a referência local dele, não
    # o atributo no módulo de origem (app.core.config).
    monkeypatch.setattr(backup_service, "caminho_banco", lambda: caminho)

    engine = criar_engine(caminho)
    Base.metadata.create_all(engine)
    configurar_sessao(engine)
    return caminho


def _criar_processo(numero: str) -> None:
    db = next(get_db())
    db.add(
        Processo(
            numero_processo=numero, requerente="A", requerido="B",
            comarca="C", vara="D", data_calculo=date(2024, 1, 1),
        )
    )
    db.commit()
    db.close()


def test_exportar_devolve_bytes_sqlite_validos(banco_temporario):
    _criar_processo("0001")

    conteudo = exportar_backup()

    assert conteudo.startswith(b"SQLite format 3\x00")
    assert len(conteudo) > 0


def test_restaurar_rejeita_arquivo_que_nao_e_sqlite(banco_temporario):
    with pytest.raises(BackupInvalidoError):
        restaurar_backup(b"isso claramente nao e um banco sqlite")


def test_exportar_e_restaurar_preserva_os_dados(banco_temporario):
    _criar_processo("processo-original")
    backup = exportar_backup()

    # simula perda de dados: cria outro processo depois do backup
    _criar_processo("processo-depois-do-backup")
    db = next(get_db())
    assert db.query(Processo).count() == 2
    db.close()

    restaurar_backup(backup)

    db = next(get_db())
    numeros = [p.numero_processo for p in db.query(Processo).all()]
    db.close()
    assert numeros == ["processo-original"]


def test_restaurar_deixa_sessao_funcional_depois(banco_temporario):
    _criar_processo("antes")
    backup = exportar_backup()
    restaurar_backup(backup)

    # a sessão precisa continuar funcionando (engine trocado com sucesso)
    _criar_processo("depois-de-restaurar")
    db = next(get_db())
    numeros = sorted(p.numero_processo for p in db.query(Processo).all())
    db.close()
    assert numeros == ["antes", "depois-de-restaurar"]
