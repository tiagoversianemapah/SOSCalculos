"""Rotas de índices, backup e status do app (seção 4.5/5/9).

`indices/importar` (planilha manual) e `parcelas/importar` ficam de fora
por enquanto: dependem de `import_planilha.py`, que ainda não existe —
implementar agora seria arriscar um recorte errado antes da peça existir.
"""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import APP_VERSION, caminho_banco
from app.core.db import get_db
from app.engine.types import Indice
from app.models.indice_serie_valor import IndiceSerieValor
from app.models.salario_minimo_valor import SalarioMinimoValor
from app.schemas.salario_minimo import SalarioMinimoValorCreate, SalarioMinimoValorOut
from app.schemas.sistema import AppStatusOut, AtualizarIndicesOut, IndiceStatusOut
from app.services import versao
from app.services.backup_service import BackupInvalidoError, exportar_backup, restaurar_backup
from app.services.indices.atualizador import atualizar_todos

router = APIRouter(tags=["sistema"])


@router.get("/indices/salario-minimo", response_model=list[SalarioMinimoValorOut])
def listar_salario_minimo(db: Session = Depends(get_db)) -> list[SalarioMinimoValor]:
    return db.execute(
        select(SalarioMinimoValor).order_by(SalarioMinimoValor.competencia)
    ).scalars().all()


@router.post("/indices/salario-minimo", response_model=SalarioMinimoValorOut, status_code=201)
def criar_salario_minimo(payload: SalarioMinimoValorCreate, db: Session = Depends(get_db)) -> SalarioMinimoValor:
    existente = db.execute(
        select(SalarioMinimoValor).where(SalarioMinimoValor.competencia == payload.competencia.replace(day=1))
    ).scalar_one_or_none()
    if existente is not None:
        existente.valor = payload.valor
        db.commit()
        db.refresh(existente)
        return existente
    registro = SalarioMinimoValor(competencia=payload.competencia.replace(day=1), valor=payload.valor)
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro


@router.delete("/indices/salario-minimo/{registro_id}", status_code=204)
def remover_salario_minimo(registro_id: UUID, db: Session = Depends(get_db)) -> None:
    registro = db.get(SalarioMinimoValor, registro_id)
    if registro is None:
        raise HTTPException(status_code=404, detail="registro não encontrado")
    db.delete(registro)
    db.commit()


@router.get("/indices/status", response_model=list[IndiceStatusOut])
def status_indices(db: Session = Depends(get_db)) -> list[IndiceStatusOut]:
    linhas = db.execute(
        select(IndiceSerieValor).where(
            IndiceSerieValor.superseded_por.is_(None), IndiceSerieValor.tribunal_codigo == ""
        )
    ).scalars().all()

    por_indice: dict[Indice, IndiceSerieValor] = {}
    for linha in linhas:
        atual = por_indice.get(linha.indice)
        if atual is None or linha.competencia > atual.competencia:
            por_indice[linha.indice] = linha

    return [
        IndiceStatusOut(
            indice=indice,
            ultima_competencia=linha.competencia,
            fonte=linha.fonte,
            ultima_atualizacao=linha.importado_em,
        )
        for indice, linha in sorted(por_indice.items(), key=lambda item: item[0].value)
    ]


@router.post("/indices/atualizar", response_model=AtualizarIndicesOut)
def atualizar_indices(db: Session = Depends(get_db)) -> AtualizarIndicesOut:
    resultado = atualizar_todos(db, date.today())
    return AtualizarIndicesOut(resultado={indice.value: str(valor) for indice, valor in resultado.items()})


def _verificar_online() -> bool:
    try:
        httpx.get(
            "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados/ultimos/1",
            params={"formato": "json"},
            timeout=3.0,
        )
        return True
    except httpx.HTTPError:
        return False


@router.get("/app/status", response_model=AppStatusOut)
def status_app() -> AppStatusOut:
    return AppStatusOut(
        versao_local=APP_VERSION,
        versao_publicada=versao.versao_nova_disponivel(),
        caminho_banco=str(caminho_banco()),
        online=_verificar_online(),
    )


@router.post("/backup/exportar")
def backup_exportar() -> Response:
    conteudo = exportar_backup()
    nome_arquivo = f"calculo-judicial-backup-{datetime.now():%Y%m%d-%H%M%S}.db"
    return Response(
        content=conteudo,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )


@router.post("/backup/restaurar")
async def backup_restaurar(arquivo: UploadFile) -> dict[str, str]:
    conteudo = await arquivo.read()
    try:
        restaurar_backup(conteudo)
    except BackupInvalidoError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"status": "restaurado"}
