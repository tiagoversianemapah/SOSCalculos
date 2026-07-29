from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.db import Base
from app.engine.types import Indice
from app.models.indice_serie_valor import IndiceSerieValor
from app.services.indices.atualizador import atualizar_indice, atualizar_todos
from app.services.indices.bcb_sgs import IndiceOfflineError


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _serie_ipca_fake(codigo, data_inicial, data_final):
    assert codigo == 433
    return [
        (date(2024, 1, 1), Decimal("0.42")),
        (date(2024, 2, 1), Decimal("0.83")),
        (date(2024, 3, 1), Decimal("0.16")),
    ]


def test_primeira_atualizacao_grava_serie_como_fracao(db):
    gravados = atualizar_indice(db, Indice.IPCA, date(2024, 4, 1), buscar_serie_fn=_serie_ipca_fake)
    assert gravados == 3

    linhas = db.execute(
        select(IndiceSerieValor).where(IndiceSerieValor.indice == Indice.IPCA).order_by(IndiceSerieValor.competencia)
    ).scalars().all()
    assert [l.competencia for l in linhas] == [date(2024, 1, 1), date(2024, 2, 1), date(2024, 3, 1)]
    assert linhas[0].variacao_percentual == Decimal("0.42") / Decimal(100)
    assert linhas[1].variacao_percentual == Decimal("0.83") / Decimal(100)


def test_busca_so_o_delta_faltante(db):
    chamadas = []

    def fake(codigo, data_inicial, data_final):
        chamadas.append((data_inicial, data_final))
        return _serie_ipca_fake(codigo, data_inicial, data_final)

    atualizar_indice(db, Indice.IPCA, date(2024, 4, 1), buscar_serie_fn=fake)

    def fake_delta(codigo, data_inicial, data_final):
        chamadas.append((data_inicial, data_final))
        return [(date(2024, 4, 1), Decimal("0.38"))]

    gravados = atualizar_indice(db, Indice.IPCA, date(2024, 5, 1), buscar_serie_fn=fake_delta)
    assert gravados == 1
    # a segunda busca deveria ter pedido a partir de maio (competência seguinte à última gravada)
    assert chamadas[1][0] == date(2024, 4, 1)


def test_chamada_repetida_sem_mudanca_nao_grava_nada_novo(db):
    atualizar_indice(db, Indice.IPCA, date(2024, 4, 1), buscar_serie_fn=_serie_ipca_fake)
    total_antes = db.execute(select(IndiceSerieValor)).scalars().all()

    # nada de novo pra buscar (já está tudo até a competência atual) -> 0 gravados
    gravados = atualizar_indice(db, Indice.IPCA, date(2024, 4, 1), buscar_serie_fn=_serie_ipca_fake)
    assert gravados == 0
    assert db.execute(select(IndiceSerieValor)).scalars().all() == total_antes


def test_republicacao_retroativa_nunca_faz_update_usa_superseded_por(db, monkeypatch):
    atualizar_indice(db, Indice.IPCA, date(2024, 2, 1), buscar_serie_fn=lambda *a: [(date(2024, 1, 1), Decimal("0.42"))])

    original = db.execute(select(IndiceSerieValor).where(IndiceSerieValor.indice == Indice.IPCA)).scalar_one()
    assert original.superseded_por is None

    # BCB republica janeiro/2024 com valor revisado — força reprocessar a
    # mesma competência simulando que o "próximo a buscar" ainda não avançou
    def fake_revisado(codigo, data_inicial, data_final):
        return [(date(2024, 1, 1), Decimal("0.50"))]

    monkeypatch.setattr(
        "app.services.indices.atualizador._proxima_competencia_a_buscar",
        lambda db_, indice: date(2024, 1, 1),
    )
    gravados = atualizar_indice(db, Indice.IPCA, date(2024, 2, 1), buscar_serie_fn=fake_revisado)

    assert gravados == 1
    db.refresh(original)
    assert original.superseded_por is not None

    ativo = db.execute(
        select(IndiceSerieValor).where(
            IndiceSerieValor.indice == Indice.IPCA, IndiceSerieValor.superseded_por.is_(None)
        )
    ).scalar_one()
    assert ativo.variacao_percentual == Decimal("0.50") / Decimal(100)
    assert ativo.id != original.id


def test_serie_de_nivel_absoluto_calcula_variacao_mes_a_mes(db):
    def fake_ptax(codigo, data_inicial, data_final):
        assert codigo == 1
        return [
            (date(2023, 12, 29), Decimal("4.8500")),
            (date(2024, 1, 5), Decimal("4.9000")),
            (date(2024, 1, 31), Decimal("5.0000")),
            (date(2024, 2, 15), Decimal("5.1000")),
            (date(2024, 2, 29), Decimal("5.2000")),
        ]

    gravados = atualizar_indice(db, Indice.PTAX, date(2024, 3, 1), buscar_serie_fn=fake_ptax)
    assert gravados == 2

    linhas = {
        l.competencia: l.variacao_percentual
        for l in db.execute(select(IndiceSerieValor).where(IndiceSerieValor.indice == Indice.PTAX)).scalars()
    }
    assert linhas[date(2024, 1, 1)] == (Decimal("5.0000") - Decimal("4.8500")) / Decimal("4.8500")
    assert linhas[date(2024, 2, 1)] == (Decimal("5.2000") - Decimal("5.0000")) / Decimal("5.0000")


def test_serie_diaria_aniversario_usa_so_a_linha_do_dia_1(db):
    def fake_tr(codigo, data_inicial, data_final):
        assert codigo == 226
        return [
            (date(2024, 1, 1), Decimal("0.0100")),  # taxa calendário de janeiro — a única que importa
            (date(2024, 1, 2), Decimal("0.0200")),  # janela de aniversário 02/01→02/02, descartar
            (date(2024, 1, 15), Decimal("0.0300")),  # idem, descartar
            (date(2024, 2, 1), Decimal("0.0150")),
            (date(2024, 2, 20), Decimal("0.0400")),  # descartar
        ]

    gravados = atualizar_indice(db, Indice.TR, date(2024, 3, 1), buscar_serie_fn=fake_tr)
    assert gravados == 2

    linhas = {
        l.competencia: l.variacao_percentual
        for l in db.execute(select(IndiceSerieValor).where(IndiceSerieValor.indice == Indice.TR)).scalars()
    }
    assert linhas[date(2024, 1, 1)] == Decimal("0.0100") / Decimal(100)
    assert linhas[date(2024, 2, 1)] == Decimal("0.0150") / Decimal(100)


def test_indice_sem_codigo_mapeado_levanta_value_error(db):
    with pytest.raises(ValueError):
        atualizar_indice(db, Indice.SALARIO_MINIMO, date(2024, 1, 1), buscar_serie_fn=lambda *a: [])


def test_atualizar_todos_marca_offline_sem_abortar_os_outros(db):
    def fake(codigo, data_inicial, data_final):
        if codigo == 433:  # IPCA
            raise IndiceOfflineError("sem rede")
        return [(date(2024, 1, 1), Decimal("1.0"))]

    resultado = atualizar_todos(db, date(2024, 2, 1), buscar_serie_fn=fake)
    assert resultado[Indice.IPCA] == "offline"
    assert resultado[Indice.INPC] == 1
