"""Checagem de versão nova no GitHub Releases (seção 9).

Falha em silêncio: sem internet, rate limit, repositório sem releases
ainda — nada disso pode atrapalhar o uso do app. O resultado fica em
cache num módulo-nível (setado pela checagem em background que
`app/desktop.py` dispara na abertura, seção 6.1) para que `GET
/app/status` devolva na hora, sem esperar rede a cada consulta.
"""
from __future__ import annotations

import httpx

from app.core.config import APP_VERSION, GITHUB_REPO

TIMEOUT_SEGUNDOS = 5.0

_versao_nova_disponivel: str | None = None


def _parse_semver(versao: str) -> tuple[int, ...] | None:
    texto = versao.strip().lstrip("v")
    partes = texto.split(".")
    try:
        return tuple(int(p) for p in partes[:3])
    except ValueError:
        return None


def verificar_versao_nova() -> str | None:
    """Consulta o GitHub Releases agora. Devolve a tag publicada se for
    maior que `APP_VERSION`, senão `None` — inclusive em qualquer falha
    (nunca levanta exceção, seção 9)."""
    try:
        resposta = httpx.get(
            f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
            timeout=TIMEOUT_SEGUNDOS,
            headers={"Accept": "application/vnd.github+json"},
        )
        resposta.raise_for_status()
        tag = resposta.json().get("tag_name", "")
    except (httpx.HTTPError, ValueError, KeyError):
        return None

    versao_publicada = _parse_semver(tag)
    versao_local = _parse_semver(APP_VERSION)
    if versao_publicada is None or versao_local is None:
        return None
    return tag if versao_publicada > versao_local else None


def checar_e_armazenar() -> None:
    """Roda a checagem e guarda o resultado em cache — chamado pela
    thread de background do `desktop.py` na abertura do app."""
    global _versao_nova_disponivel
    _versao_nova_disponivel = verificar_versao_nova()


def versao_nova_disponivel() -> str | None:
    """Lê o resultado da última checagem (sem tocar rede)."""
    return _versao_nova_disponivel
