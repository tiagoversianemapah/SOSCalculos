"""Cliente HTTP da API pública do BCB SGS (seção 5/6.1).

Pública, sem autenticação, sem custo. Timeout curto por padrão (10s,
conforme a seção 6.1): erro de rede ou timeout vira `IndiceOfflineError`,
tratado pelo chamador como "sem internet" — nunca deve travar a abertura
do app. `build_seed_db.py` (download único, do histórico completo, fora
da máquina do usuário) passa um timeout maior explicitamente — séries
diárias longas (ex.: PTAX) têm milhares de pontos por janela e podem não
responder em 10s.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

import httpx

TIMEOUT_SEGUNDOS_PADRAO = 10.0
_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"

# A API do BCB SGS rejeita (HTTP 406) janelas maiores que 10 anos para
# séries de periodicidade diária (ex.: PTAX, TR, Poupança) — mesmo
# quando o dado que nos interessa é mensal. Fatiar sempre evita o erro
# nas diárias; séries mensais de histórico longo (ex.: IPCA desde 2000)
# também acabam fatiadas, por isso `buscar_serie` deduplica por data.
_JANELA_MAX_DIAS = 3600


class IndiceOfflineError(Exception):
    """Falha de rede/timeout ao consultar o BCB SGS."""


def _buscar_janela(
    codigo: int, data_inicial: date, data_final: date, timeout: float
) -> list[tuple[date, Decimal]]:
    params = {
        "formato": "json",
        "dataInicial": data_inicial.strftime("%d/%m/%Y"),
        "dataFinal": data_final.strftime("%d/%m/%Y"),
    }
    try:
        resposta = httpx.get(_URL.format(codigo=codigo), params=params, timeout=timeout)
        resposta.raise_for_status()
        dados = resposta.json()
        return [
            (datetime.strptime(item["data"], "%d/%m/%Y").date(), Decimal(item["valor"]))
            for item in dados
        ]
    except httpx.HTTPError as exc:
        raise IndiceOfflineError(f"Falha ao consultar série BCB SGS {codigo}: {exc}") from exc
    except (json.JSONDecodeError, KeyError, ValueError, InvalidOperation) as exc:
        # resposta 200 mas corpo vazio/malformado (instabilidade do
        # serviço do BCB, não um erro de rede em si) — mesmo tratamento
        # de "offline": nunca travar o app por causa disso (seção 5).
        raise IndiceOfflineError(f"Resposta inválida do BCB SGS {codigo}: {exc}") from exc


def buscar_serie(
    codigo: int,
    data_inicial: date,
    data_final: date,
    timeout: float = TIMEOUT_SEGUNDOS_PADRAO,
) -> list[tuple[date, Decimal]]:
    """Devolve a lista (data, valor) bruta da série `codigo` no intervalo.

    `valor` é exatamente o que o BCB publica — pode ser uma variação
    percentual do mês (ex.: IPCA) ou um nível absoluto (ex.: PTAX);
    quem decide como interpretar é `mapeamento.py`/`atualizador.py`.
    Fatia automaticamente em janelas de até ~10 anos (ver `_JANELA_MAX_DIAS`).
    """
    por_data: dict[date, Decimal] = {}
    inicio_janela = data_inicial
    while inicio_janela <= data_final:
        fim_janela = min(data_final, inicio_janela + timedelta(days=_JANELA_MAX_DIAS))
        for d, v in _buscar_janela(codigo, inicio_janela, fim_janela, timeout):
            por_data[d] = v  # o BCB pode devolver a borda do mês em duas janelas — mantém 1 valor por data
        inicio_janela = fim_janela + timedelta(days=1)
    return sorted(por_data.items())
