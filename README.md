# Cálculo Judicial

Aplicativo desktop (Windows) de cálculo de liquidação de sentença — correção monetária, juros moratórios e acessórios, com memória de cálculo auditável mês a mês e emissão de PDF. Especificação completa em `especificacao-tecnica-motor-calculo-judicial.md`.

Custo zero de infraestrutura: tudo roda localmente na máquina do usuário (backend, banco SQLite, interface). Não há servidor central, conta ou login.

## Instalação (usuário final)

1. Baixe o executável mais recente em [Releases](../../releases).
2. Ao abrir pela primeira vez, o Windows SmartScreen provavelmente vai avisar "Windows protegeu seu PC" — isso acontece porque o executável não tem assinatura digital (certificado paga, e o orçamento deste projeto é zero), não porque é malware. Clique em **"Mais informações"** e depois em **"Executar assim mesmo"**.
3. O app precisa do **Microsoft WebView2 Runtime**, que já vem instalado por padrão no Windows 10/11. Se faltar, o próprio app abre a página de download na primeira execução.
4. Seus dados ficam em `%APPDATA%\CalculoJudicial\dados.db`. Use os botões **Exportar backup** / **Restaurar backup** na tela inicial regularmente — é a única proteção contra perda de disco (não há nuvem nem sincronização).

## Desenvolvimento

### Backend

```
cd backend
python -m pip install -r requirements.txt
python -m alembic upgrade head   # cria/atualiza o dados.db local
python -m pytest app/tests -q    # suíte completa
```

Rodar em modo dev (sem empacotar):

```
python -m app.desktop
```

### Frontend

```
cd frontend
npm install
npm run build   # gera frontend/dist, servido pelo FastAPI local
```

## Empacotamento (gerar o `.exe`)

```
cd frontend && npm run build
cd ../backend
python packaging/build_seed_db.py packaging/dados_semente.db   # opcional, baixa o histórico completo de índices
pyinstaller packaging/app.spec
```

O executável final fica em `backend/dist/CalculoJudicial.exe`.

## Publicar uma versão (GitHub Releases)

O app checa `GET /repos/{repo}/releases/latest` na abertura (seção 9 da especificação) para avisar sobre versão nova — falha em silêncio se não houver rede ou releases ainda. O repositório usado nessa checagem está configurado em `backend/app/core/config.py` (`GITHUB_REPO`).

Para publicar: crie uma tag semântica (`vX.Y.Z`), suba o `.exe` gerado como asset da release no GitHub. Isso é uma ação manual do responsável pelo projeto — nada aqui automatiza o `git push`/criação da release.
