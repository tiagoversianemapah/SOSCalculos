from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.db import Base
from app.engine.types import BaseCalculoAcessorio, Indice
from app.models.acessorio import Acessorio
from app.models.calculo_execucao import CalculoExecucao
from app.models.enums import FonteIndice, TipoAcessorio
from app.models.indice_serie_valor import IndiceSerieValor
from app.models.memoria_calculo import MemoriaCalculo
from app.models.parcela import Parcela
from app.models.processo import Processo
from app.models.segmento import CorrecaoSegmento
from app.models.enums import DonoTipo
from app.services.emissao_service import emitir_processo


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_emitir_persiste_execucao_memoria_e_atualiza_cache_da_parcela(db):
    processo = Processo(
        numero_processo="0001", requerente="A", requerido="B",
        comarca="C", vara="D", data_calculo=date(2024, 3, 31),
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

    acessorio_sem_evento = Acessorio(
        processo_id=processo.id, tipo=TipoAcessorio.HONORARIOS_SUCUMBENCIA,
        percentual=Decimal("0.10"), valor_fixo=None,
        base_calculo=BaseCalculoAcessorio.TOTAL_LIQUIDO_PARCELAS, data_evento=None,
    )
    acessorio_com_evento = Acessorio(
        processo_id=processo.id, tipo=TipoAcessorio.MULTA,
        percentual=Decimal("0.05"), valor_fixo=None,
        base_calculo=BaseCalculoAcessorio.TOTAL_LIQUIDO_PARCELAS, data_evento=date(2024, 1, 1),
    )
    db.add_all([acessorio_sem_evento, acessorio_com_evento])

    for mes, variacao in [(1, "0.01"), (2, "0.01"), (3, "0.01")]:
        db.add(
            IndiceSerieValor(
                indice=Indice.IPCA, competencia=date(2024, mes, 1),
                variacao_percentual=Decimal(variacao), fonte=FonteIndice.MANUAL,
            )
        )
    db.commit()
    db.refresh(processo)

    execucao = emitir_processo(db, processo, date(2024, 3, 31))

    assert isinstance(execucao, CalculoExecucao)
    assert execucao.processo_id == processo.id
    assert execucao.valor_total_apurado > Decimal("1000")

    db.refresh(parcela)
    assert parcela.valor_apurado is not None

    linhas_parcela = db.execute(
        select(MemoriaCalculo).where(MemoriaCalculo.parcela_id == parcela.id)
    ).scalars().all()
    assert len(linhas_parcela) == 3  # jan, fev, mar
    # saldo_final_mes guarda precisão total (não arredondada); valor_apurado
    # é o mesmo valor arredondado em 2 casas (seção 3.1) — não são iguais
    # em precisão, mas devem bater depois de arredondar.
    from decimal import ROUND_HALF_UP

    assert linhas_parcela[-1].saldo_final_mes.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) == parcela.valor_apurado

    # acessório sem data_evento -> 1 linha sintética
    linhas_sem_evento = db.execute(
        select(MemoriaCalculo).where(MemoriaCalculo.acessorio_id == acessorio_sem_evento.id)
    ).scalars().all()
    assert len(linhas_sem_evento) == 1
    assert linhas_sem_evento[0].indice_aplicado is None

    # acessório com data_evento -> linha por competência real (mesma janela da parcela)
    linhas_com_evento = db.execute(
        select(MemoriaCalculo).where(MemoriaCalculo.acessorio_id == acessorio_com_evento.id)
    ).scalars().all()
    assert len(linhas_com_evento) == 3
    assert linhas_com_evento[0].indice_aplicado == Indice.IPCA


def test_emitir_duas_vezes_cria_duas_execucoes_independentes(db):
    processo = Processo(
        numero_processo="0002", requerente="A", requerido="B",
        comarca="C", vara="D", data_calculo=date(2024, 2, 29),
    )
    db.add(processo)
    db.flush()
    db.add(
        Parcela(processo_id=processo.id, vencimento=date(2024, 1, 1), historico="x", valor_bruto=Decimal("500"))
    )
    db.commit()
    db.refresh(processo)

    execucao_1 = emitir_processo(db, processo, date(2024, 1, 31))
    execucao_2 = emitir_processo(db, processo, date(2024, 2, 29))

    assert execucao_1.id != execucao_2.id
    linhas_1 = db.execute(
        select(MemoriaCalculo).where(MemoriaCalculo.calculo_execucao_id == execucao_1.id)
    ).scalars().all()
    linhas_2 = db.execute(
        select(MemoriaCalculo).where(MemoriaCalculo.calculo_execucao_id == execucao_2.id)
    ).scalars().all()
    assert len(linhas_1) == 1  # só janeiro
    assert len(linhas_2) == 2  # janeiro e fevereiro
