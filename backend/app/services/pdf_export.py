"""Renderiza a memória de cálculo persistida em PDF (seção 8) —
`reportlab`, decidido pelo teste de fumaça (seção 8/10, item 2).

Nunca recalcula: lê só o que `emissao_service.emitir_processo` já
gravou em `calculo_execucao`/`memoria_calculo`. O hash SHA-256 é
calculado sobre os dados persistidos (não sobre os bytes do PDF — isso
seria um problema do ovo e da galinha, já que o hash aparece dentro do
próprio PDF) na primeira geração e nunca recalculado depois — é isso
que prova, mais tarde, que o conteúdo gravado não mudou.
"""
from __future__ import annotations

import hashlib
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.calculo_execucao import CalculoExecucao
from app.models.indice_serie_valor import IndiceSerieValor
from app.models.memoria_calculo import MemoriaCalculo

DUAS_CASAS = Decimal("0.01")

_TIPOS_HONORARIOS = {"honorarios_sucumbencia", "honorarios_523_cpc", "honorarios_contratuais", "honorarios_execucao"}
_TIPOS_MULTA = {"multa", "multa_523_cpc"}


def _moeda(valor: Decimal) -> str:
    inteiro_str = f"{valor.quantize(DUAS_CASAS, rounding=ROUND_HALF_UP):,.2f}"
    return "R$ " + inteiro_str.replace(",", "_").replace(".", ",").replace("_", ".")


def _percentual(valor: Decimal) -> str:
    return f"{(valor * 100).quantize(Decimal('0.0001'))}".replace(".", ",") + "%"


def _competencia_str(d: date) -> str:
    return d.strftime("%m/%Y")


def _data_str(d: date | None) -> str:
    return d.strftime("%d/%m/%Y") if d else "—"


def calcular_hash_conteudo(execucao: CalculoExecucao) -> str:
    """Hash determinístico sobre os dados persistidos da execução —
    reproduz o mesmo valor sempre que chamado sobre os mesmos dados,
    seja na emissão original ou numa regeneração posterior."""
    linhas = sorted(
        execucao.memoria_linhas,
        key=lambda l: (str(l.parcela_id or ""), str(l.acessorio_id or ""), str(l.deducao_id or ""), l.competencia),
    )
    partes = [
        str(execucao.id),
        str(execucao.processo_id),
        execucao.data_calculo.isoformat(),
        str(execucao.valor_total_apurado),
    ]
    for linha in linhas:
        partes.append(
            "|".join(
                [
                    str(linha.parcela_id or ""),
                    str(linha.acessorio_id or ""),
                    str(linha.deducao_id or ""),
                    linha.competencia.isoformat(),
                    str(linha.saldo_inicio_mes),
                    linha.indice_aplicado.value if linha.indice_aplicado else "",
                    str(linha.variacao_indice),
                    str(linha.saldo_corrigido),
                    str(linha.taxa_juros_aplicada),
                    str(linha.juros_mes),
                    str(linha.saldo_final_mes),
                    str(linha.parada_ativa),
                ]
            )
        )
    return hashlib.sha256("\n".join(partes).encode("utf-8")).hexdigest()


def _competencia_limite_indices(db: Session) -> date | None:
    return db.execute(
        select(IndiceSerieValor.competencia)
        .where(IndiceSerieValor.superseded_por.is_(None))
        .order_by(IndiceSerieValor.competencia.desc())
        .limit(1)
    ).scalar_one_or_none()


def _estilo_tabela() -> TableStyle:
    return TableStyle(
        [
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]
    )


def _tabela(linhas: list[list[str]], repetir_cabecalho: bool = False) -> Table:
    tabela = Table(linhas, repeatRows=1 if repetir_cabecalho else 0)
    tabela.setStyle(_estilo_tabela())
    return tabela


def _tabela_memoria(linhas: list[MemoriaCalculo]) -> Table:
    dados = [["Competência", "Saldo início", "Índice", "Variação", "Saldo corrigido", "Taxa juros", "Juros mês", "Saldo final", "Parada"]]
    for linha in linhas:
        dados.append(
            [
                _competencia_str(linha.competencia),
                _moeda(linha.saldo_inicio_mes),
                linha.indice_aplicado.value if linha.indice_aplicado else "—",
                _percentual(linha.variacao_indice),
                _moeda(linha.saldo_corrigido),
                _percentual(linha.taxa_juros_aplicada),
                _moeda(linha.juros_mes),
                _moeda(linha.saldo_final_mes),
                "sim" if linha.parada_ativa else "não",
            ]
        )
    return _tabela(dados, repetir_cabecalho=True)


def _valor_final_por_acessorio(execucao: CalculoExecucao) -> dict:
    por_acessorio: dict = {}
    for linha in execucao.memoria_linhas:
        if linha.acessorio_id is None:
            continue
        atual = por_acessorio.get(linha.acessorio_id)
        if atual is None or linha.competencia > atual.competencia:
            por_acessorio[linha.acessorio_id] = linha
    return {acessorio_id: linha.saldo_final_mes for acessorio_id, linha in por_acessorio.items()}


def _valor_final_por_deducao(execucao: CalculoExecucao) -> dict:
    por_deducao: dict = {}
    for linha in execucao.memoria_linhas:
        if linha.deducao_id is None:
            continue
        atual = por_deducao.get(linha.deducao_id)
        if atual is None or linha.competencia > atual.competencia:
            por_deducao[linha.deducao_id] = linha
    return {deducao_id: linha.saldo_final_mes for deducao_id, linha in por_deducao.items()}


def calcular_totalizacao(execucao: CalculoExecucao) -> dict[str, Decimal]:
    """Totalização separada por natureza (seção 8, item 4) — pura,
    testável sem precisar renderizar o PDF.

    Correção NÃO pode ser "saldo_corrigido - saldo_inicio_mes" somado
    mês a mês: saldo_inicio já inclui os juros acumulados de meses
    anteriores (seção 3.3, dois acumuladores separados), então essa
    subtração mistura grandezas diferentes e pode até dar negativa por
    engano. A forma correta é isolar por diferença dos totais:
    principal - deduções + correção + juros = total apurado.
    """
    processo = execucao.processo
    principal = sum((p.valor_bruto for p in processo.parcelas), Decimal(0))
    deducoes_pagamentos = sum((pg.valor for p in processo.parcelas for pg in p.pagamentos), Decimal(0))
    valor_por_deducao = _valor_final_por_deducao(execucao)
    deducoes_passo4 = sum(valor_por_deducao.values(), Decimal(0))
    deducoes = deducoes_pagamentos + deducoes_passo4
    total_parcelas_apurado = sum((p.valor_apurado or Decimal(0) for p in processo.parcelas), Decimal(0))

    # juros_mes é sempre o juro daquele mês isolado — soma direta é segura.
    juros = Decimal(0)
    for linha in execucao.memoria_linhas:
        if linha.parcela_id is not None:
            juros += linha.juros_mes

    # A dedução do passo 4 (paridade SOSCálculos) é subtraída do total
    # geral do processo diretamente (`calculo_service.calcular_processo`),
    # não do total das parcelas — só `deducoes_pagamentos` (o abatimento
    # simples de `pagamento_parcial`) entra na identidade da correção.
    correcao = total_parcelas_apurado - principal + deducoes_pagamentos - juros

    valor_por_acessorio = _valor_final_por_acessorio(execucao)
    honorarios = Decimal(0)
    multas = Decimal(0)
    custas = Decimal(0)
    for acessorio in processo.acessorios:
        valor = valor_por_acessorio.get(acessorio.id, Decimal(0))
        if acessorio.tipo.value in _TIPOS_HONORARIOS:
            honorarios += valor
        elif acessorio.tipo.value in _TIPOS_MULTA:
            multas += valor
        elif acessorio.tipo.value == "custas_processuais":
            custas += valor

    return {
        "principal": principal,
        "correcao": correcao,
        "juros": juros,
        "honorarios": honorarios,
        "multas": multas,
        "custas": custas,
        "deducoes": deducoes,
        "total_geral": execucao.valor_total_apurado,
    }


def _tabela_totalizacao(execucao: CalculoExecucao) -> Table:
    t = calcular_totalizacao(execucao)
    linhas = [
        ["Principal original", _moeda(t["principal"])],
        ["Correção monetária", _moeda(t["correcao"])],
        ["Juros", _moeda(t["juros"])],
        ["Honorários", _moeda(t["honorarios"])],
        ["Multas", _moeda(t["multas"])],
        ["Custas processuais", _moeda(t["custas"])],
        ["(−) Deduções", "−" + _moeda(t["deducoes"])],
        ["Total geral", _moeda(t["total_geral"])],
    ]
    tabela = _tabela(linhas)
    tabela.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
            ]
        )
    )
    return tabela


def gerar_pdf(db: Session, execucao: CalculoExecucao) -> bytes:
    """Gera os bytes do PDF da execução. Na primeira chamada (emissão),
    calcula e grava `hash_conteudo`; em regenerações (`GET
    /execucoes/{id}/pdf`), reaproveita o hash já persistido — nunca
    recalcula em cima de índices que podem ter mudado depois.
    """
    if execucao.hash_conteudo is None:
        execucao.hash_conteudo = calcular_hash_conteudo(execucao)
        db.commit()
        db.refresh(execucao)

    processo = execucao.processo
    estilos = getSampleStyleSheet()
    elementos = []

    elementos.append(Paragraph(processo.titulo_calculo or "Memória de Cálculo Judicial", estilos["Title"]))
    identificacao = [
        ["Número do processo", processo.numero_processo or "—"],
        ["Requerente", f"{processo.requerente} ({processo.requerente_doc or '—'})"],
        ["Requerido", f"{processo.requerido} ({processo.requerido_doc or '—'})"],
        ["Comarca / Vara", f"{processo.comarca or '—'} — {processo.vara or '—'}"],
        ["Tribunal", processo.tribunal or "—"],
        ["Tipo de ação", processo.tipo_acao or "—"],
        ["Data do cálculo", _data_str(processo.data_calculo)],
    ]
    if processo.observacoes:
        identificacao.append(["Observações", processo.observacoes])
    elementos.append(_tabela(identificacao))
    elementos.append(Spacer(1, 12))

    elementos.append(Paragraph("Quadro de premissas", estilos["Heading2"]))
    premissas = [["Critério", "Período / Data", "Índice / Taxa", "Fonte"]]
    for seg in processo.correcao_segmentos_default:
        premissas.append(
            ["Correção (padrão)", f"{_data_str(seg.data_inicio)} a {_data_str(seg.data_fim)}", seg.indice.value, seg.fonte_criterio or "—"]
        )
    for seg in processo.juros_segmentos_default:
        premissas.append(
            ["Juros (padrão)", f"{_data_str(seg.data_inicio)} a {_data_str(seg.data_fim)}", seg.tipo_taxa.value, seg.fonte_criterio or "—"]
        )
    for acessorio in processo.acessorios:
        base = _percentual(acessorio.percentual) if acessorio.percentual is not None else _moeda(acessorio.valor_fixo)
        premissas.append([acessorio.tipo.value, _data_str(acessorio.data_evento), base, acessorio.fonte_criterio or "—"])
    for parada in processo.paradas:
        premissas.append(
            ["Parada extraordinária", f"{_data_str(parada.data_inicio)} a {_data_str(parada.data_fim)}", parada.motivo, "—"]
        )
    if len(premissas) > 1:
        elementos.append(_tabela(premissas, repetir_cabecalho=True))
    else:
        elementos.append(Paragraph("Nenhum critério cadastrado.", estilos["Normal"]))
    elementos.append(Spacer(1, 12))

    linhas_por_parcela: dict = {}
    linhas_por_acessorio: dict = {}
    linhas_por_deducao: dict = {}
    for linha in execucao.memoria_linhas:
        if linha.parcela_id is not None:
            linhas_por_parcela.setdefault(linha.parcela_id, []).append(linha)
        elif linha.acessorio_id is not None:
            linhas_por_acessorio.setdefault(linha.acessorio_id, []).append(linha)
        else:
            linhas_por_deducao.setdefault(linha.deducao_id, []).append(linha)

    elementos.append(Paragraph("Parcelas — memória de cálculo mês a mês", estilos["Heading2"]))
    for parcela in processo.parcelas:
        linhas = sorted(linhas_por_parcela.get(parcela.id, []), key=lambda l: l.competencia)
        if not linhas:
            continue
        elementos.append(
            Paragraph(
                f"{parcela.historico} — vencimento {_data_str(parcela.vencimento)}, "
                f"valor original {_moeda(parcela.valor_bruto)}",
                estilos["Heading3"],
            )
        )
        for deducao in parcela.pagamentos:
            elementos.append(
                Paragraph(f"Dedução ({deducao.tipo.value}) em {_data_str(deducao.data)}: {_moeda(deducao.valor)}", estilos["Normal"])
            )
        elementos.append(_tabela_memoria(linhas))
        elementos.append(Spacer(1, 8))

    if linhas_por_acessorio:
        elementos.append(Paragraph("Acessórios com linha do tempo própria", estilos["Heading2"]))
        for acessorio in processo.acessorios:
            linhas = sorted(linhas_por_acessorio.get(acessorio.id, []), key=lambda l: l.competencia)
            if not linhas or len(linhas) == 1:
                continue  # linha sintética única (sem data_evento) não tem timeline pra detalhar
            elementos.append(Paragraph(acessorio.tipo.value, estilos["Heading3"]))
            elementos.append(_tabela_memoria(linhas))
            elementos.append(Spacer(1, 8))

    if linhas_por_deducao:
        elementos.append(Paragraph("Deduções (passo 4) com linha do tempo própria", estilos["Heading2"]))
        for deducao in processo.deducoes:
            linhas = sorted(linhas_por_deducao.get(deducao.id, []), key=lambda l: l.competencia)
            if not linhas or len(linhas) == 1:
                continue
            elementos.append(Paragraph(f"{deducao.tipo.value} — {deducao.historico or ''}", estilos["Heading3"]))
            elementos.append(_tabela_memoria(linhas))
            elementos.append(Spacer(1, 8))

    elementos.append(Paragraph("Totalização por natureza", estilos["Heading2"]))
    elementos.append(_tabela_totalizacao(execucao))
    elementos.append(Spacer(1, 16))

    competencia_limite = _competencia_limite_indices(db)
    rodape = (
        f"Índices aplicados até {_competencia_str(competencia_limite) if competencia_limite else '—'} "
        f"(última competência publicada). Hash SHA-256 do conteúdo: {execucao.hash_conteudo}"
    )
    elementos.append(Paragraph(rodape, estilos["Normal"]))

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    doc.build(elementos)
    return buffer.getvalue()
