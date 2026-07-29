import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Date, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.engine.types import Indice

from .base import UUIDPk
from .tipos import DecimalText

if TYPE_CHECKING:
    from .acessorio import Acessorio
    from .calculo_execucao import CalculoExecucao
    from .deducao import Deducao
    from .parcela import Parcela


class MemoriaCalculo(UUIDPk, Base):
    """Snapshot de auditoria — uma linha por mês por parcela OU por
    acessório com timeline própria (seção 2/3.1/3.9).

    `parcela_id`/`acessorio_id`: dono exclusivo, mesmo padrão de
    `correcao_segmento`/`juros_segmento` (CHECK abaixo) — um acessório
    com `data_evento` preenchida (seção 3.9) tem sua própria linha do
    tempo de correção/juros, e essas linhas precisam ficar auditáveis
    igual às de parcela para que `GET /execucoes/{id}/pdf` reconstrua um
    PDF já emitido sem recalcular (seção 4.5/8). Acessórios sem
    `data_evento` (base não depende de índice) ganham uma única linha
    sintética na competência da emissão — mantém o invariante "todo
    valor_apurado histórico é reconstruível a partir da última linha".

    Nada aqui é arredondado: os campos `Numeric` sem precisão/escala fixa
    guardam o valor com a precisão total que o motor produziu
    (`decimal.Decimal`, `getcontext().prec = 28`). Arredondamento só
    acontece na exibição (PDF) e no `valor_apurado` final.
    """

    __tablename__ = "memoria_calculo"
    __table_args__ = (
        CheckConstraint(
            "(parcela_id IS NOT NULL AND acessorio_id IS NULL AND deducao_id IS NULL) OR "
            "(parcela_id IS NULL AND acessorio_id IS NOT NULL AND deducao_id IS NULL) OR "
            "(parcela_id IS NULL AND acessorio_id IS NULL AND deducao_id IS NOT NULL)",
            name="ck_memoria_calculo_dono_exclusivo",
        ),
    )

    parcela_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("parcela.id", ondelete="CASCADE"), nullable=True, index=True
    )
    acessorio_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("acessorio.id", ondelete="CASCADE"), nullable=True, index=True
    )
    deducao_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("deducao.id", ondelete="CASCADE"), nullable=True, index=True
    )
    calculo_execucao_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("calculo_execucao.id", ondelete="CASCADE"), nullable=False, index=True
    )
    competencia: Mapped[date] = mapped_column(Date, nullable=False)
    saldo_inicio_mes: Mapped[Decimal] = mapped_column(DecimalText(), nullable=False)
    indice_aplicado: Mapped[Indice | None] = mapped_column(Enum(Indice, name="indice"), nullable=True)
    variacao_indice: Mapped[Decimal] = mapped_column(DecimalText(), nullable=False)
    saldo_corrigido: Mapped[Decimal] = mapped_column(DecimalText(), nullable=False)
    taxa_juros_aplicada: Mapped[Decimal] = mapped_column(DecimalText(), nullable=False)
    juros_mes: Mapped[Decimal] = mapped_column(DecimalText(), nullable=False)
    saldo_final_mes: Mapped[Decimal] = mapped_column(DecimalText(), nullable=False)
    parada_ativa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    parcela: Mapped["Parcela | None"] = relationship()
    acessorio: Mapped["Acessorio | None"] = relationship()
    deducao: Mapped["Deducao | None"] = relationship()
    calculo_execucao: Mapped["CalculoExecucao"] = relationship(back_populates="memoria_linhas")
