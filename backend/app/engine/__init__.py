"""Motor de cálculo de liquidação de sentença.

Módulo puro: nenhum arquivo neste pacote faz I/O (sem banco, sem rede,
sem framework). Toda dependência externa entra via parâmetro injetado
pelo chamador (ver `BuscarVariacao` em `types.py`). Isso é o que permite
testar o motor exaustivamente contra casos de referência sem precisar de
banco de dados ou API — ver `app/tests/unit/`.
"""
