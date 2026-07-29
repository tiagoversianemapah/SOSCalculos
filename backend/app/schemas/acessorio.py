from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from app.engine.types import BaseCalculoAcessorio
from app.models.enums import TipoAcessorio

from .segmento import CorrecaoSegmentoIn, CorrecaoSegmentoOut, JurosSegmentoIn, JurosSegmentoOut
from .tipos import DecimalStr


class AcessorioCreate(BaseModel):
    tipo: TipoAcessorio
    historico: Optional[str] = None
    percentual: Optional[DecimalStr] = None
    valor_fixo: Optional[DecimalStr] = None
    base_calculo: BaseCalculoAcessorio
    data_evento: Optional[date] = None
    fonte_criterio: Optional[str] = None
    # Multa "Diária (Data final)" — quando preenchido, substitui
    # valor_fixo (total = valor_diario × dias entre data_inicio_acumulo
    # e data_evento, ver app/engine/acessorios.py).
    valor_diario: Optional[DecimalStr] = None
    data_inicio_acumulo: Optional[date] = None
    # Multa "Diária (Competência)" — mesmos campos acima, mas quebra por
    # mês civil (ver app/engine/acessorios.py). Só válido com valor_diario.
    diaria_por_competencia: bool = False
    # Multa "Salário Mínimo" — quantidade × valor vigente em data_evento
    # (aqui rotulada "Data Salário Mínimo"); substitui valor_fixo, a
    # camada de serviço resolve o valor absoluto antes do motor.
    salario_minimo_quantidade: Optional[DecimalStr] = None
    # Multa "Mensal" — um lançamento de valor_mensal por mês vencido
    # entre data_inicio_acumulo e data_evento (ver app/engine/acessorios.py).
    valor_mensal: Optional[DecimalStr] = None
    # Só fazem sentido (e só são persistidos) quando base_calculo =
    # valor_fixo_absoluto — "Tabela de C.M." / "Juros de Mora" do modo
    # "Valor Monetário" (passo 3, paridade SOSCálculos).
    usa_correcao_default: bool = True
    usa_juros_default: bool = True
    correcao_segmentos_override: list[CorrecaoSegmentoIn] = []
    juros_segmentos_override: list[JurosSegmentoIn] = []

    @model_validator(mode="after")
    def _validar_regras_de_base(self) -> "AcessorioCreate":
        if self.valor_diario is not None:
            if self.base_calculo is not BaseCalculoAcessorio.VALOR_FIXO_ABSOLUTO:
                raise ValueError("valor_diario só se aplica quando base_calculo = valor_fixo_absoluto")
            if self.data_inicio_acumulo is None or self.data_evento is None:
                raise ValueError(
                    "data_inicio_acumulo e data_evento são obrigatórias quando valor_diario é informado"
                )
        elif self.salario_minimo_quantidade is not None:
            if self.base_calculo is not BaseCalculoAcessorio.VALOR_FIXO_ABSOLUTO:
                raise ValueError("salario_minimo_quantidade só se aplica quando base_calculo = valor_fixo_absoluto")
            if self.data_evento is None:
                raise ValueError(
                    "data_evento (Data Salário Mínimo) é obrigatória quando salario_minimo_quantidade é informado"
                )
        elif self.valor_mensal is not None:
            if self.base_calculo is not BaseCalculoAcessorio.VALOR_FIXO_ABSOLUTO:
                raise ValueError("valor_mensal só se aplica quando base_calculo = valor_fixo_absoluto")
            if self.data_inicio_acumulo is None or self.data_evento is None:
                raise ValueError(
                    "data_inicio_acumulo e data_evento são obrigatórias quando valor_mensal é informado"
                )
        elif self.base_calculo is BaseCalculoAcessorio.VALOR_FIXO_ABSOLUTO:
            if self.valor_fixo is None:
                raise ValueError("valor_fixo é obrigatório quando base_calculo = valor_fixo_absoluto")
        elif self.percentual is None:
            raise ValueError("percentual é obrigatório quando base_calculo != valor_fixo_absoluto")
        if self.diaria_por_competencia and self.valor_diario is None:
            raise ValueError("diaria_por_competencia só se aplica quando valor_diario é informado")
        if (
            self.base_calculo is BaseCalculoAcessorio.SALDO_REMANESCENTE_EM_DATA_EVENTO
            and self.data_evento is None
        ):
            raise ValueError(
                "data_evento é obrigatória quando base_calculo = saldo_remanescente_em_data_evento"
            )
        return self


class AcessorioUpdate(AcessorioCreate):
    pass


class AcessorioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tipo: TipoAcessorio
    historico: Optional[str] = None
    percentual: Optional[DecimalStr] = None
    valor_fixo: Optional[DecimalStr] = None
    base_calculo: BaseCalculoAcessorio
    data_evento: Optional[date] = None
    fonte_criterio: Optional[str] = None
    valor_diario: Optional[DecimalStr] = None
    data_inicio_acumulo: Optional[date] = None
    diaria_por_competencia: bool = False
    salario_minimo_quantidade: Optional[DecimalStr] = None
    valor_mensal: Optional[DecimalStr] = None
    usa_correcao_default: bool
    usa_juros_default: bool
    correcao_segmentos_override: list[CorrecaoSegmentoOut] = []
    juros_segmentos_override: list[JurosSegmentoOut] = []
