# -*- mode: python ; coding: utf-8 -*-
"""Spec do PyInstaller (seção 6.1) — gera um executável único do
Windows a partir de `app/desktop.py`.

Uso: `pyinstaller packaging/app.spec` (a partir de `backend/`).

Datas embutidos:
- `frontend/dist/` — build do Vite, servido pelo FastAPI local
  (`app/main.py`); precisa existir antes (`npm run build` no frontend).
- `alembic/` + `alembic.ini` — as migrações são lidas do disco pelo
  `ScriptDirectory` do Alembic em tempo de execução (não são resolvidas
  por `import` estático), então precisam ir como arquivo de dados, não
  como módulo compilado.
- `packaging/dados_semente.db` — banco pré-populado (seção 5), se já
  tiver sido gerado por `packaging/build_seed_db.py`; opcional aqui —
  sem ele, o app cria o banco vazio na primeira execução.

`reportlab` (seção 8) é Python puro — nenhum binário nativo extra.
"""
import os

backend_dir = os.path.dirname(SPECPATH)  # SPECPATH = backend/packaging

frontend_dist = os.path.join(backend_dir, "..", "frontend", "dist")
alembic_dir = os.path.join(backend_dir, "alembic")
alembic_ini = os.path.join(backend_dir, "alembic.ini")
seed_db = os.path.join(backend_dir, "packaging", "dados_semente.db")

if not os.path.isdir(frontend_dist):
    raise SystemExit(
        f"frontend/dist não existe ({frontend_dist}) — rode `npm run build` no frontend/ antes de empacotar."
    )

datas = [
    (frontend_dist, "frontend/dist"),
    (alembic_dir, "alembic"),
    (alembic_ini, "."),
]
if os.path.exists(seed_db):
    datas.append((seed_db, "packaging"))

a = Analysis(
    [os.path.join(backend_dir, "app", "desktop.py")],
    pathex=[backend_dir],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="CalculoJudicial",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
