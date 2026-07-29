"""Ponto de entrada do executável (seção 6.1). Sequência exata:

1. Resolver `%APPDATA%\\CalculoJudicial\\`; criar se não existir.
2. Se `dados.db` não existe, copiar o banco semente embarcado.
3. Rodar `alembic upgrade head` programaticamente.
4. Escolher uma porta livre.
5. Subir o uvicorn numa thread daemon, só em `127.0.0.1`.
6. Disparar em background: atualização de índices + checagem de versão
   — nunca bloquear a abertura da janela.
7. Abrir a janela `pywebview`; ao fechar, encerrar o servidor.
"""
from __future__ import annotations

import ctypes
import shutil
import socket
import threading
from datetime import date

import uvicorn
import webview
from alembic import command
from alembic.config import Config

from app.core.config import caminho_banco, diretorio_base_recursos, diretorio_dados
from app.core.db import configurar_sessao, criar_engine, get_db
from app.services import versao
from app.services.indices.atualizador import atualizar_todos

_URL_DOWNLOAD_WEBVIEW2 = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"


def _garantir_banco() -> None:
    """Passo 1 e 2: cria o diretório de dados e copia o banco semente
    na primeira execução."""
    diretorio_dados()  # cria %APPDATA%\CalculoJudicial\ se não existir
    destino = caminho_banco()
    if destino.exists():
        return
    semente = diretorio_base_recursos() / "packaging" / "dados_semente.db"
    if semente.exists():
        shutil.copyfile(semente, destino)
    # sem banco semente embarcado (ex.: rodando de fonte sem ter gerado
    # um ainda) — a migração abaixo cria o schema vazio normalmente.


def _rodar_migracoes() -> None:
    """Passo 3: `alembic upgrade head` via API, nunca subprocess."""
    raiz = diretorio_base_recursos()
    alembic_cfg = Config(str(raiz / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(raiz / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{caminho_banco()}")
    command.upgrade(alembic_cfg, "head")


def _porta_livre() -> int:
    """Passo 4: bind em porta 0 e lê a porta atribuída pelo SO."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _subir_servidor(porta: int) -> uvicorn.Server:
    """Passo 5: uvicorn numa thread daemon, só em 127.0.0.1."""
    from app.main import app  # import tardio: só depois do banco/migrações prontos

    config = uvicorn.Config(app, host="127.0.0.1", port=porta, log_level="warning")
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, daemon=True).start()
    return server


def _atualizar_em_background() -> None:
    """Passo 6: índices (seção 5) + checagem de versão (seção 9) — cada
    um na sua exceção própria, um não pode derrubar o outro nem travar
    a janela."""

    def _tarefa() -> None:
        try:
            db = next(get_db())
            try:
                atualizar_todos(db, date.today())
            finally:
                db.close()
        except Exception:  # noqa: BLE001 — nunca deixar isso quebrar a abertura do app
            pass
        try:
            versao.checar_e_armazenar()
        except Exception:  # noqa: BLE001
            pass

    threading.Thread(target=_tarefa, daemon=True).start()


def _webview2_instalado() -> bool:
    """Checagem best-effort via registro do Windows (seção 9) — se não
    der pra confirmar, assume que está instalado e deixa o pywebview
    tentar (evita falso negativo travando o app à toa)."""
    try:
        import winreg

        for hive, subkey in (
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"),
        ):
            try:
                winreg.OpenKey(hive, subkey)
                return True
            except FileNotFoundError:
                continue
        return False
    except Exception:  # noqa: BLE001
        return True


def _avisar_webview2_ausente() -> None:
    mensagem = (
        "Este aplicativo precisa do Microsoft WebView2 Runtime, que normalmente já "
        "vem instalado no Windows 10/11.\n\nClique OK para abrir a página de download."
    )
    ctypes.windll.user32.MessageBoxW(0, mensagem, "Cálculo Judicial", 0x40)
    import webbrowser

    webbrowser.open(_URL_DOWNLOAD_WEBVIEW2)


def main() -> None:
    _garantir_banco()
    engine = criar_engine(caminho_banco())
    configurar_sessao(engine)
    _rodar_migracoes()

    if not _webview2_instalado():
        _avisar_webview2_ausente()
        return

    porta = _porta_livre()
    servidor = _subir_servidor(porta)
    _atualizar_em_background()
    print(f"Servidor local rodando em http://127.0.0.1:{porta}", flush=True)

    webview.create_window("Cálculo Judicial", f"http://127.0.0.1:{porta}")
    webview.start()

    servidor.should_exit = True


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        # empacotado com console=False (packaging/app.spec) — sem isso,
        # uma falha antes de qualquer janela abrir seria 100% silenciosa
        # pro usuário, parecendo que o app "não faz nada" ao clicar.
        ctypes.windll.user32.MessageBoxW(
            0, f"O aplicativo encontrou um erro e será fechado:\n\n{exc}", "Cálculo Judicial", 0x10
        )
        raise
