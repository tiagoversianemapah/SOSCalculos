from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.engine.types import BaseCalculoAcessorio, Indice, TipoTaxaJuros
from app.models.acessorio import Acessorio
from app.models.enums import DonoTipo, FonteIndice, TipoAcessorio, TipoPagamentoParcial
from app.models.indice_serie_valor import IndiceSerieValor
from app.models.pagamento_parcial import PagamentoParcial
from app.models.parcela import Parcela
from app.models.processo import Processo
from app.models.segmento import CorrecaoSegmento
from app.services.calculo_service import calcular_processo


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _gravar_indice(db, indice, competencia, variacao):
    db.add(
        IndiceSerieValor(
            indice=indice, competencia=competencia, variacao_percentual=variacao, fonte=FonteIndice.MANUAL
        )
    )


def test_calcula_processo_com_parcela_pagamento_e_acessorio(db):
    processo = Processo(
        numero_processo="0001", requerente="Fulano", requerido="Beltrano",
        comarca="Goiania", vara="1a Vara", data_calculo=date(2024, 3, 31),
    )
    db.add(processo)
    db.flush()

    db.add(
        CorrecaoSegmento(
            processo_id=processo.id, dono_tipo=DonoTipo.PROCESSO_DEFAULT,
            ordem=1, indice=Indice.IPCA, data_inicio=date(2024, 1, 1), data_fim=None,
        )
    )

    parcela = Parcela(
        processo_id=processo.id, vencimento=date(2024, 1, 1), historico="teste",
        valor_bruto=Decimal("1000"),
    )
    db.add(parcela)
    db.flush()
    db.add(
        PagamentoParcial(
            parcela_id=parcela.id, data=date(2024, 2, 15), valor=Decimal("200"),
            tipo=TipoPagamentoParcial.PAGAMENTO,
        )
    )

    acessorio = Acessorio(
        processo_id=processo.id, tipo=TipoAcessorio.HONORARIOS_SUCUMBENCIA,
        percentual=Decimal("0.10"), valor_fixo=None,
        base_calculo=BaseCalculoAcessorio.TOTAL_LIQUIDO_PARCELAS, data_evento=None,
    )
    db.add(acessorio)

    _gravar_indice(db, Indice.IPCA, date(2024, 1, 1), Decimal("0.01"))
    _gravar_indice(db, Indice.IPCA, date(2024, 2, 1), Decimal("0.01"))
    _gravar_indice(db, Indice.IPCA, date(2024, 3, 1), Decimal("0.01"))
    db.commit()

    db.refresh(processo)
    resultado = calcular_processo(db, processo, date(2024, 3, 31))

    # 1000*1.01=1010 -200=810 *1.01=818.10 *1.01=826.281 -> 826.28
    assert resultado.resultados_parcelas[parcela.id].valor_apurado == Decimal("826.28")
    assert resultado.resultados_acessorios[acessorio.id].valor_apurado == Decimal("82.63")  # 826.28*0.10 arredondado
    assert resultado.total_geral == Decimal("908.91")  # 826.28 + 82.63


def test_calcula_parcela_com_override_de_juros(db):
    """Parcela com usa_juros_default=False usa os próprios segmentos de
    juros, ignorando o default do processo."""
    processo = Processo(
        numero_processo="0002", requerente="A", requerido="B",
        comarca="C", vara="D", data_calculo=date(2024, 2, 29),
    )
    db.add(processo)
    db.flush()

    parcela = Parcela(
        processo_id=processo.id, vencimento=date(2024, 1, 1), historico="override",
        valor_bruto=Decimal("1000"), usa_juros_default=False,
    )
    db.add(parcela)
    db.flush()

    from app.models.segmento import JurosSegmento

    db.add(
        JurosSegmento(
            parcela_id=parcela.id, dono_tipo=DonoTipo.PARCELA_OVERRIDE,
            ordem=1, tipo_taxa=TipoTaxaJuros.PERCENTUAL_FIXO_MENSAL,
            taxa_valor=Decimal("0.01"), data_inicio=date(2024, 1, 1), data_fim=None,
        )
    )
    db.commit()
    db.refresh(processo)

    resultado = calcular_processo(db, processo, date(2024, 2, 29))

    # 2024 é bissexto, então 29/02 é o último dia do mês (fator_dias=1
    # nos dois meses) — sem correção, juros de 1% ao mês: 1000+10+10=1020.00
    assert resultado.resultados_parcelas[parcela.id].valor_apurado == Decimal("1020.00")


def test_compor_com_selic_gera_juros_selic_substitutiva_automaticamente(db):
    """Campo 'Compor com Selic' (paridade SOSCálculos): marcar True no
    segmento de correção deve produzir o mesmo resultado que configurar
    manualmente um segmento de juros SELIC_SUBSTITUTIVA cobrindo o mesmo
    período (sem precisar o usuário duplicar a configuração)."""
    processo = Processo(
        requerente="A", requerido="B", data_calculo=date(2024, 3, 31),
    )
    db.add(processo)
    db.flush()

    db.add(
        CorrecaoSegmento(
            processo_id=processo.id, dono_tipo=DonoTipo.PROCESSO_DEFAULT,
            ordem=1, indice=Indice.IPCA, data_inicio=date(2024, 1, 1), data_fim=None,
            compor_com_selic=True,
        )
    )

    parcela = Parcela(
        processo_id=processo.id, vencimento=date(2024, 1, 1), historico="selic",
        valor_bruto=Decimal("1000"),
    )
    db.add(parcela)

    _gravar_indice(db, Indice.SELIC_SIMPLES, date(2024, 1, 1), Decimal("0.01"))
    _gravar_indice(db, Indice.SELIC_SIMPLES, date(2024, 2, 1), Decimal("0.01"))
    _gravar_indice(db, Indice.SELIC_SIMPLES, date(2024, 3, 1), Decimal("0.01"))
    db.commit()
    db.refresh(processo)

    resultado = calcular_processo(db, processo, date(2024, 3, 31))

    # equivalente a SELIC_SUBSTITUTIVA simples 1% a.m. compondo: essa
    # variação já não capitaliza (juros simples), mas a correção
    # substituída pela Selic aplica direto sobre o saldo (seção 3.4)
    assert resultado.resultados_parcelas[parcela.id].valor_apurado == Decimal("1030.30")
