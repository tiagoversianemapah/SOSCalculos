import httpx
import pytest

from app.services import versao


class _RespostaFake:
    def __init__(self, tag: str, status: int = 200):
        self._tag = tag
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("erro", request=None, response=self)

    def json(self):
        return {"tag_name": self._tag}


def test_versao_publicada_maior_devolve_a_tag(monkeypatch):
    monkeypatch.setattr(versao, "APP_VERSION", "1.0.0")
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _RespostaFake("v1.2.0"))

    assert versao.verificar_versao_nova() == "v1.2.0"


def test_versao_publicada_igual_ou_menor_devolve_none(monkeypatch):
    monkeypatch.setattr(versao, "APP_VERSION", "1.2.0")
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _RespostaFake("v1.2.0"))
    assert versao.verificar_versao_nova() is None

    monkeypatch.setattr(httpx, "get", lambda *a, **k: _RespostaFake("v1.0.0"))
    assert versao.verificar_versao_nova() is None


def test_falha_de_rede_devolve_none_sem_levantar(monkeypatch):
    def _levanta(*a, **k):
        raise httpx.ConnectError("sem rede")

    monkeypatch.setattr(httpx, "get", _levanta)
    assert versao.verificar_versao_nova() is None


def test_resposta_sem_tag_valida_devolve_none(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _RespostaFake("release-sem-semver"))
    assert versao.verificar_versao_nova() is None


def test_checar_e_armazenar_atualiza_cache(monkeypatch):
    monkeypatch.setattr(versao, "APP_VERSION", "1.0.0")
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _RespostaFake("v9.9.9"))

    versao.checar_e_armazenar()

    assert versao.versao_nova_disponivel() == "v9.9.9"
