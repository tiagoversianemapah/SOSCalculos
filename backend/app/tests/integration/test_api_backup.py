import pytest
from fastapi.testclient import TestClient

from app.core.db import Base, configurar_sessao, criar_engine
from app.main import app
from app.services import backup_service


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # backup/restaurar precisa de um arquivo real (não ":memory:") pra
    # fazer sentido — troca de engine + leitura de bytes do disco.
    caminho = tmp_path / "dados.db"
    monkeypatch.setattr(backup_service, "caminho_banco", lambda: caminho)

    engine = criar_engine(caminho)
    Base.metadata.create_all(engine)
    configurar_sessao(engine)
    with TestClient(app) as c:
        yield c


def test_exportar_backup_devolve_arquivo_sqlite(client):
    resp = client.post("/api/v1/processos", json={
        "numero_processo": "1", "requerente": "A", "requerido": "B",
        "comarca": "C", "vara": "D", "data_calculo": "2024-01-01",
    })
    assert resp.status_code == 201

    resp = client.post("/api/v1/backup/exportar")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/octet-stream"
    assert resp.content.startswith(b"SQLite format 3\x00")


def test_restaurar_backup_com_arquivo_invalido_devolve_422(client):
    resp = client.post(
        "/api/v1/backup/restaurar",
        files={"arquivo": ("nao-e-banco.db", b"conteudo invalido", "application/octet-stream")},
    )
    assert resp.status_code == 422


def test_exportar_e_restaurar_via_api_preserva_dados(client):
    client.post("/api/v1/processos", json={
        "numero_processo": "original", "requerente": "A", "requerido": "B",
        "comarca": "C", "vara": "D", "data_calculo": "2024-01-01",
    })
    backup = client.post("/api/v1/backup/exportar").content

    client.post("/api/v1/processos", json={
        "numero_processo": "depois-do-backup", "requerente": "A", "requerido": "B",
        "comarca": "C", "vara": "D", "data_calculo": "2024-01-01",
    })
    assert len(client.get("/api/v1/processos").json()) == 2

    resp = client.post(
        "/api/v1/backup/restaurar",
        files={"arquivo": ("backup.db", backup, "application/octet-stream")},
    )
    assert resp.status_code == 200

    processos = client.get("/api/v1/processos").json()
    assert [p["numero_processo"] for p in processos] == ["original"]
