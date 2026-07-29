"""`correcao_segmento` e `juros_segmento` (seção 2).

O "dono" de um segmento é o processo (default), uma parcela (override),
um acessório (override) ou uma dedução (override) — nunca mais de um. Em
vez de uma FK genérica `dono_id` sem integridade referencial real,
usamos quatro colunas FK nullable com um CHECK garantindo que exatamente
uma esteja preenchida — mesmo padrão já usado em `parada_extraordinaria`.
`dono_tipo` fica como coluna derivada e indexável para filtros, mas a
integridade de fato vem do CHECK + das FKs reais.
"""
import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Date, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.engine.types import Indice, TipoTaxaJuros

from .base import TimestampMixin, UUIDPk
from .enums import DonoTipo, TipoVencimento
from .tipos import DecimalText

if TYPE_CHECKING:
    from .acessorio import Acessorio
    from .deducao import Deducao
    from .parcela import Parcela
    from .processo import Processo

# "Dono" pode ser o processo (default), uma parcela (override, passo 2),
# um acessório (override, passo 3 — honorário/multa "Valor Monetário"
# com Tabela de C.M./Juros de Mora próprios) ou uma dedução (override,
# passo "Deduções" — paridade SOSCálculos) — exatamente um dos quatro.
_DONO_CHECK = (
    "(processo_id IS NOT NULL AND parcela_id IS NULL AND acessorio_id IS NULL AND deducao_id IS NULL) OR "
    "(processo_id IS NULL AND parcela_id IS NOT NULL AND acessorio_id IS NULL AND deducao_id IS NULL) OR "
    "(processo_id IS NULL AND parcela_id IS NULL AND acessorio_id IS NOT NULL AND deducao_id IS NULL) OR "
    "(processo_id IS NULL AND parcela_id IS NULL AND acessorio_id IS NULL AND deducao_id IS NOT NULL)"
)


class CorrecaoSegmento(UUIDPk, TimestampMixin, Base):
    __tablename__ = "correcao_segmento"
    __table_args__ = (CheckConstraint(_DONO_CHECK, name="ck_correcao_segmento_dono_exclusivo"),)

    dono_tipo: Mapped[DonoTipo] = mapped_column(Enum(DonoTipo, name="dono_tipo"), nullable=False)
    processo_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("processo.id", ondelete="CASCADE"), nullable=True, index=True
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
    ordem: Mapped[int] = mapped_column(nullable=False)
    indice: Mapped[Indice] = mapped_column(Enum(Indice, name="indice"), nullable=False)
    tribunal_codigo: Mapped[str | None] = mapped_column(String, nullable=True)
    data_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    data_fim: Mapped[date | None] = mapped_column(Date, nullable=True)
    # De onde veio o critério (ex.: "sentença, fls. 312") — quadro de
    # premissas do PDF, seções 0/8.
    fonte_criterio: Mapped[str | None] = mapped_column(String, nullable=True)
    # Qual data-âncora do processo preencheu `data_inicio` (campo
    # "Vencimento da C.M." do passo 1) — só metadado de exibição, não
    # afeta o motor.
    vencimento_tipo: Mapped[TipoVencimento] = mapped_column(
        Enum(TipoVencimento, name="tipo_vencimento"), nullable=False, default=TipoVencimento.DO_VENCIMENTO
    )
    # Campo "Deflação (índices negativos)" — True ("Com deflação",
    # padrão) deixa a variação negativa reduzir o saldo; False ("Sem
    # deflação") zera a variação negativa naquele mês (seção 3, motor).
    permite_deflacao: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Campo "Compor com Selic" — quando True, a camada de serviço gera
    # automaticamente um segmento de juros SELIC_SUBSTITUTIVA cobrindo o
    # mesmo período deste segmento (e este vira "sem correção" nesse
    # período), reaproveitando a regra que a Selic substitui correção e
    # juros ao mesmo tempo (seção 3.4). O preset "Tema 1368/STJ" do passo
    # 1 é só um atalho que preenche data_inicio=01/2003, data_fim=07/2024
    # e marca este campo True.
    compor_com_selic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    processo: Mapped["Processo | None"] = relationship(
        back_populates="correcao_segmentos_default", foreign_keys=[processo_id]
    )
    parcela: Mapped["Parcela | None"] = relationship(
        back_populates="correcao_segmentos_override", foreign_keys=[parcela_id]
    )
    acessorio: Mapped["Acessorio | None"] = relationship(
        back_populates="correcao_segmentos_override", foreign_keys=[acessorio_id]
    )
    deducao: Mapped["Deducao | None"] = relationship(
        back_populates="correcao_segmentos_override", foreign_keys=[deducao_id]
    )


class JurosSegmento(UUIDPk, TimestampMixin, Base):
    __tablename__ = "juros_segmento"
    __table_args__ = (
        CheckConstraint(_DONO_CHECK, name="ck_juros_segmento_dono_exclusivo"),
        CheckConstraint(
            "tipo_taxa <> 'percentual_fixo_mensal' OR taxa_valor IS NOT NULL",
            name="ck_juros_segmento_taxa_valor_obrigatorio",
        ),
    )

    dono_tipo: Mapped[DonoTipo] = mapped_column(Enum(DonoTipo, name="dono_tipo"), nullable=False)
    processo_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("processo.id", ondelete="CASCADE"), nullable=True, index=True
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
    ordem: Mapped[int] = mapped_column(nullable=False)
    tipo_taxa: Mapped[TipoTaxaJuros] = mapped_column(
        Enum(TipoTaxaJuros, name="tipo_taxa_juros"), nullable=False
    )
    taxa_valor: Mapped[Decimal | None] = mapped_column(DecimalText(9, 6), nullable=True)
    data_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    data_fim: Mapped[date | None] = mapped_column(Date, nullable=True)
    fonte_criterio: Mapped[str | None] = mapped_column(String, nullable=True)
    # Campo "Tipo Vencimento Juros" do passo 1 — mesmo metadado de
    # exibição que `CorrecaoSegmento.vencimento_tipo`.
    vencimento_tipo: Mapped[TipoVencimento] = mapped_column(
        Enum(TipoVencimento, name="tipo_vencimento"), nullable=False, default=TipoVencimento.DO_VENCIMENTO
    )

    processo: Mapped["Processo | None"] = relationship(
        back_populates="juros_segmentos_default", foreign_keys=[processo_id]
    )
    parcela: Mapped["Parcela | None"] = relationship(
        back_populates="juros_segmentos_override", foreign_keys=[parcela_id]
    )
    acessorio: Mapped["Acessorio | None"] = relationship(
        back_populates="juros_segmentos_override", foreign_keys=[acessorio_id]
    )
    deducao: Mapped["Deducao | None"] = relationship(
        back_populates="juros_segmentos_override", foreign_keys=[deducao_id]
    )
