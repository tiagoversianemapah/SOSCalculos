"""`deducao` (paridade SOSCálculos, passo "Deduções" — só existe quando
`Processo.configura_deducoes` é True). Cada dedução tem valor e data
próprios, e pode ter correção/juros próprios (mesmo padrão default/
override de Parcela e Acessorio) — o valor corrigido é subtraído do
total geral do processo (seção 3.9, `calculo_service.calcular_processo`),
reaproveitando `app/engine/acessorios.calcular_acessorio` (a mesma conta
de "valor base + correção a partir de uma data", só que subtraído em vez
de somado)."""
import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Date, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

from .base import TimestampMixin, UUIDPk
from .enums import TipoAtualizacaoDeducao, TipoDeducao
from .tipos import DecimalText

if TYPE_CHECKING:
    from .processo import Processo
    from .segmento import CorrecaoSegmento, JurosSegmento


class Deducao(UUIDPk, TimestampMixin, Base):
    __tablename__ = "deducao"
    __table_args__ = (
        CheckConstraint(
            "atualizacao_tipo NOT IN ('outra_data', 'data_levantamento') OR data_atualizacao IS NOT NULL",
            name="ck_deducao_data_atualizacao_obrigatoria",
        ),
    )

    processo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("processo.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tipo: Mapped[TipoDeducao] = mapped_column(Enum(TipoDeducao, name="tipo_deducao"), nullable=False)
    historico: Mapped[str | None] = mapped_column(String, nullable=True)
    data_inicial: Mapped[date] = mapped_column(Date, nullable=False)
    valor: Mapped[Decimal] = mapped_column(DecimalText(18, 2), nullable=False)
    atualizacao_tipo: Mapped[TipoAtualizacaoDeducao] = mapped_column(
        Enum(TipoAtualizacaoDeducao, name="tipo_atualizacao_deducao"),
        nullable=False,
        default=TipoAtualizacaoDeducao.DATA_INICIAL,
    )
    data_atualizacao: Mapped[date | None] = mapped_column(Date, nullable=True)
    fonte_criterio: Mapped[str | None] = mapped_column(String, nullable=True)

    usa_correcao_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    usa_juros_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    processo: Mapped["Processo"] = relationship(back_populates="deducoes")
    correcao_segmentos_override: Mapped[list["CorrecaoSegmento"]] = relationship(
        back_populates="deducao",
        cascade="all, delete-orphan",
        primaryjoin="and_(Deducao.id==CorrecaoSegmento.deducao_id)",
    )
    juros_segmentos_override: Mapped[list["JurosSegmento"]] = relationship(
        back_populates="deducao",
        cascade="all, delete-orphan",
        primaryjoin="and_(Deducao.id==JurosSegmento.deducao_id)",
    )
