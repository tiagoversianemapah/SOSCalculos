from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.db import Base, configurar_sessao
from app.main import app
from app.models.enums import FonteIndice
from app.models.indice_serie_valor import IndiceSerieValor


@pytest.fixture()
def engine():
    # StaticPool: cada conexão nova a "sqlite:///:memory:" abre um banco
    # separado por padrão — precisa forçar todas as conexões (a do
    # setup e as das requisições via get_db) a compartilhar a mesma.
    eng = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(eng)
    configurar_sessao(eng)
    return eng


@pytest.fixture()
def client(engine):
    with TestClient(app) as c:
        yield c


def _gravar_indice(engine, indice, competencia, variacao):
    with Session(engine) as s:
        s.add(
            IndiceSerieValor(
                indice=indice, competencia=competencia, variacao_percentual=variacao, fonte=FonteIndice.MANUAL
            )
        )
        s.commit()


def _criar_processo(client, **overrides):
    payload = {
        "numero_processo": "0001234-56.2024.8.09.0001",
        "requerente": "Fulano",
        "requerido": "Beltrano",
        "comarca": "Goiania",
        "vara": "1a Vara Civel",
        "data_calculo": "2024-03-31",
        "correcao_segmentos_default": [
            {"ordem": 1, "indice": "ipca", "data_inicio": "2024-01-01", "data_fim": None}
        ],
        "juros_segmentos_default": [],
    }
    payload.update(overrides)
    resp = client.post("/api/v1/processos", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_fluxo_completo_processo_parcela_pagamento_acessorio_calculo(client, engine):
    processo = _criar_processo(client)
    processo_id = processo["id"]
    assert len(processo["correcao_segmentos_default"]) == 1

    resp = client.post(
        f"/api/v1/processos/{processo_id}/parcelas",
        json={
            "vencimento": "2024-01-01",
            "historico": "Diferenca salarial",
            "valor_bruto": "1000.00",
        },
    )
    assert resp.status_code == 201, resp.text
    parcela = resp.json()
    parcela_id = parcela["id"]
    assert parcela["valor_bruto"] == "1000.00"
    assert parcela["valor_apurado"] is None

    resp = client.post(
        f"/api/v1/parcelas/{parcela_id}/pagamentos",
        json={"data": "2024-02-15", "valor": "200.00", "tipo": "pagamento"},
    )
    assert resp.status_code == 201, resp.text

    resp = client.post(
        f"/api/v1/processos/{processo_id}/acessorios",
        json={
            "tipo": "honorarios_sucumbencia",
            "percentual": "0.10",
            "base_calculo": "total_liquido_parcelas",
        },
    )
    assert resp.status_code == 201, resp.text

    for indice, competencia, variacao in [
        ("ipca", date(2024, 1, 1), "0.01"),
        ("ipca", date(2024, 2, 1), "0.01"),
        ("ipca", date(2024, 3, 1), "0.01"),
    ]:
        _gravar_indice(engine, indice, competencia, Decimal(variacao))

    resp = client.post(f"/api/v1/processos/{processo_id}/calcular")
    assert resp.status_code == 200, resp.text
    resultado = resp.json()

    # 1000*1.01=1010 -200=810 *1.01=818.10 *1.01=826.281 -> 826.28
    assert resultado["parcelas"][0]["valor_apurado"] == "826.28"
    assert len(resultado["parcelas"][0]["memoria"]) == 3
    assert resultado["acessorios"][0]["valor_apurado"] == "82.63"
    assert resultado["total_geral"] == "908.91"

    # o preview NÃO persiste memoria_calculo nem altera valor_apurado da parcela
    resp = client.get(f"/api/v1/processos/{processo_id}/parcelas")
    assert resp.json()[0]["valor_apurado"] is None


def test_deducao_data_calculo_subtrai_valor_flat_do_total(client, engine):
    """Dedução com atualizacao_tipo=data_calculo não passa pela linha do
    tempo (mesmo efeito de data_evento=None no Acessorio) — o valor é
    subtraído direto do total geral do processo."""
    processo = _criar_processo(client, configura_deducoes=True)
    processo_id = processo["id"]

    resp = client.post(
        f"/api/v1/processos/{processo_id}/parcelas",
        json={"vencimento": "2024-01-01", "historico": "Verba", "valor_bruto": "1000.00"},
    )
    assert resp.status_code == 201, resp.text

    resp = client.post(
        f"/api/v1/processos/{processo_id}/deducoes",
        json={
            "tipo": "pagamento",
            "historico": "dedução de teste",
            "data_inicial": "2024-02-01",
            "valor": "300.00",
            "atualizacao_tipo": "data_calculo",
        },
    )
    assert resp.status_code == 201, resp.text

    _gravar_indice(engine, "ipca", date(2024, 1, 1), Decimal("0"))

    resp = client.post(f"/api/v1/processos/{processo_id}/calcular")
    assert resp.status_code == 200, resp.text
    resultado = resp.json()

    assert len(resultado["deducoes"]) == 1
    assert resultado["deducoes"][0]["valor_apurado"] == "300.00"
    assert resultado["total_geral"] == "700.00"


def test_processo_inexistente_devolve_404(client):
    resp = client.get("/api/v1/processos/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_valor_monetario_como_float_e_rejeitado(client):
    resp = client.post(
        "/api/v1/processos",
        json={
            "numero_processo": "1", "requerente": "A", "requerido": "B",
            "comarca": "C", "vara": "D", "data_calculo": "2024-01-01",
        },
    )
    processo_id = resp.json()["id"]

    resp = client.post(
        f"/api/v1/processos/{processo_id}/parcelas",
        json={"vencimento": "2024-01-01", "historico": "x", "valor_bruto": 1000.50},
    )
    assert resp.status_code == 422


def test_acessorio_sem_percentual_nem_valor_fixo_e_rejeitado(client):
    processo = _criar_processo(client)
    resp = client.post(
        f"/api/v1/processos/{processo['id']}/acessorios",
        json={"tipo": "multa", "base_calculo": "total_liquido_parcelas"},
    )
    assert resp.status_code == 422


def test_selic_substitutiva_sobreposta_a_correcao_vira_422(client, engine):
    processo = _criar_processo(
        client,
        correcao_segmentos_default=[
            {"ordem": 1, "indice": "ipca", "data_inicio": "2024-01-01", "data_fim": None}
        ],
        juros_segmentos_default=[
            {"ordem": 1, "tipo_taxa": "selic_substitutiva", "data_inicio": "2024-01-01", "data_fim": None}
        ],
    )
    client.post(
        f"/api/v1/processos/{processo['id']}/parcelas",
        json={"vencimento": "2024-01-01", "historico": "x", "valor_bruto": "1000.00"},
    )

    resp = client.post(f"/api/v1/processos/{processo['id']}/calcular")
    assert resp.status_code == 422
    assert "Selic substitutiva" in resp.json()["detail"]


def test_parada_com_data_fim_antes_de_inicio_e_rejeitada(client):
    processo = _criar_processo(client)
    resp = client.post(
        f"/api/v1/processos/{processo['id']}/paradas",
        json={"data_inicio": "2024-02-01", "data_fim": "2024-01-01", "motivo": "x"},
    )
    assert resp.status_code == 422


def test_deletar_processo_remove_parcelas_em_cascata(client):
    processo = _criar_processo(client)
    resp = client.post(
        f"/api/v1/processos/{processo['id']}/parcelas",
        json={"vencimento": "2024-01-01", "historico": "x", "valor_bruto": "1000.00"},
    )
    parcela_id = resp.json()["id"]

    resp = client.delete(f"/api/v1/processos/{processo['id']}")
    assert resp.status_code == 204

    resp = client.put(f"/api/v1/parcelas/{parcela_id}", json={
        "vencimento": "2024-01-01", "historico": "y", "valor_bruto": "1.00",
    })
    assert resp.status_code == 404


def test_emitir_gera_pdf_persiste_execucao_e_atualiza_valor_apurado(client, engine):
    processo = _criar_processo(client)
    processo_id = processo["id"]

    resp = client.post(
        f"/api/v1/processos/{processo_id}/parcelas",
        json={"vencimento": "2024-01-01", "historico": "Diferenca salarial", "valor_bruto": "1000.00"},
    )
    parcela_id = resp.json()["id"]

    for indice, competencia, variacao in [
        ("ipca", date(2024, 1, 1), "0.01"),
        ("ipca", date(2024, 2, 1), "0.01"),
        ("ipca", date(2024, 3, 1), "0.01"),
    ]:
        _gravar_indice(engine, indice, competencia, Decimal(variacao))

    resp = client.post(f"/api/v1/processos/{processo_id}/emitir")
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF-")
    execucao_id = resp.headers["x-calculo-execucao-id"]

    # o cache de valor_apurado da parcela foi atualizado pela emissão
    resp = client.get(f"/api/v1/processos/{processo_id}/parcelas")
    assert resp.json()[0]["id"] == parcela_id
    assert resp.json()[0]["valor_apurado"] == "1030.30"

    # GET /execucoes/{id}/pdf regenera sem recalcular, mesmo hash
    resp2 = client.get(f"/api/v1/execucoes/{execucao_id}/pdf")
    assert resp2.status_code == 200
    assert resp2.content.startswith(b"%PDF-")


def test_execucao_inexistente_devolve_404(client):
    resp = client.get("/api/v1/execucoes/00000000-0000-0000-0000-000000000000/pdf")
    assert resp.status_code == 404
