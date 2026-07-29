import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Date, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.engine.types import BaseCalculoAcessorio

from .base import TimestampMixin, UUIDPk
from .enums import TipoAcessorio
from .tipos import DecimalText

if TYPE_CHECKING:
    from .processo import Processo
    from .segmento import CorrecaoSegmento, JurosSegmento


class Acessorio(UUIDPk, TimestampMixin, Base):
    __tablename__ = "acessorio"
    __table_args__ = (
        CheckConstraint(
            "(percentual IS NOT NULL AND valor_fixo IS NULL AND valor_diario IS NULL AND salario_minimo_quantidade IS NULL AND valor_mensal IS NULL) OR "
            "(percentual IS NULL AND valor_fixo IS NOT NULL AND valor_diario IS NULL AND salario_minimo_quantidade IS NULL AND valor_mensal IS NULL) OR "
            "(percentual IS NULL AND valor_fixo IS NULL AND valor_diario IS NOT NULL AND salario_minimo_quantidade IS NULL AND valor_mensal IS NULL) OR "
            "(percentual IS NULL AND valor_fixo IS NULL AND valor_diario IS NULL AND salario_minimo_quantidade IS NOT NULL AND valor_mensal IS NULL) OR "
            "(percentual IS NULL AND valor_fixo IS NULL AND valor_diario IS NULL AND salario_minimo_quantidade IS NULL AND valor_mensal IS NOT NULL)",
            name="ck_acessorio_percentual_xor_valor_fixo",
        ),
        CheckConstraint(
            "base_calculo <> 'saldo_remanescente_em_data_evento' OR data_evento IS NOT NULL",
            name="ck_acessorio_data_evento_obrigatoria_para_saldo_remanescente",
        ),
    )

    processo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("processo.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tipo: Mapped[TipoAcessorio] = mapped_column(
        Enum(TipoAcessorio, name="tipo_acessorio"), nullable=False
    )
    # Campo "Histórico" do passo 3 (paridade SOSCálculos) — texto livre
    # identificando a linha (ex.: "honorários de execução"), distinto de
    # `fonte_criterio` (de onde veio o percentual/valor no processo).
    historico: Mapped[str | None] = mapped_column(String, nullable=True)
    percentual: Mapped[Decimal | None] = mapped_column(DecimalText(9, 6), nullable=True)
    valor_fixo: Mapped[Decimal | None] = mapped_column(DecimalText(18, 2), nullable=True)
    base_calculo: Mapped[BaseCalculoAcessorio] = mapped_column(
        Enum(BaseCalculoAcessorio, name="base_calculo_acessorio"), nullable=False
    )
    data_evento: Mapped[date | None] = mapped_column(Date, nullable=True)
    fonte_criterio: Mapped[str | None] = mapped_column(String, nullable=True)

    # Multa "Diária (Data final)" — valor por dia e a data de início do
    # acúmulo; `data_evento` acima funciona como a "Data Fim" nesse modo
    # (confirmado com cálculo real do SOSCálculos, seção 3.9/motor).
    valor_diario: Mapped[Decimal | None] = mapped_column(DecimalText(18, 2), nullable=True)
    data_inicio_acumulo: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Multa "Diária (Competência)" — mesmos campos de "Diária (Data
    # final)" acima, mas quebra em sub-linhas por mês civil, cada uma
    # corrigida a partir do seu próprio início (confirmado com cálculo
    # real, seção 3.9/motor). Só tem efeito quando valor_diario preenchido.
    diaria_por_competencia: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Multa "Salário Mínimo" — quantidade de salários mínimos vigentes em
    # `data_evento` (aqui rotulada "Data Salário Mínimo" na UI); a camada
    # de serviço resolve o valor absoluto (cadastro manual, mesma tabela
    # `salario_minimo_valor` do botão "Salário Mínimo" do passo 2) e
    # multiplica pela quantidade antes de rodar a linha do tempo de
    # correção/juros — o motor nunca lida com "salário mínimo" como
    # conceito, só recebe um valor_fixo já resolvido.
    salario_minimo_quantidade: Mapped[Decimal | None] = mapped_column(DecimalText(9, 4), nullable=True)

    # Multa "Mensal" — valor fixo lançado uma vez por mês vencido entre
    # data_inicio_acumulo e data_evento (confirmado com cálculo real,
    # seção 3.9/motor — ver `_marcos_mensais` em app/engine/acessorios.py).
    valor_mensal: Mapped[Decimal | None] = mapped_column(DecimalText(18, 2), nullable=True)

    # "Tabela de C.M." / "Juros de Mora" do passo 3, modo "Valor
    # Monetário" (paridade SOSCálculos) — só fazem sentido quando
    # `base_calculo = valor_fixo_absoluto` e `data_evento` preenchida;
    # mesmo padrão default/override já usado em Parcela (seção 4).
    usa_correcao_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    usa_juros_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    processo: Mapped["Processo"] = relationship(back_populates="acessorios")
    correcao_segmentos_override: Mapped[list["CorrecaoSegmento"]] = relationship(
        back_populates="acessorio",
        cascade="all, delete-orphan",
        primaryjoin="and_(Acessorio.id==CorrecaoSegmento.acessorio_id)",
    )
    juros_segmentos_override: Mapped[list["JurosSegmento"]] = relationship(
        back_populates="acessorio",
        cascade="all, delete-orphan",
        primaryjoin="and_(Acessorio.id==JurosSegmento.acessorio_id)",
    )
