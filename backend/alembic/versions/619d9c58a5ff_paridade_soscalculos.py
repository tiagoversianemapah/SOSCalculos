"""paridade soscalculos

Revision ID: 619d9c58a5ff
Revises: dd00a3f879e8
Create Date: 2026-07-28 17:55:17.640950

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import app.models.tipos

# revision identifiers, used by Alembic.
revision: str = '619d9c58a5ff'
down_revision: Union[str, Sequence[str], None] = 'dd00a3f879e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('pagamento_parcial',
    sa.Column('parcela_id', sa.Uuid(), nullable=False),
    sa.Column('data', sa.Date(), nullable=False),
    sa.Column('valor', app.models.tipos.DecimalText(), nullable=False),
    sa.Column('tipo', sa.Enum('PAGAMENTO', 'DEPOSITO_JUDICIAL', 'COMPENSACAO', 'OUTRO', name='tipo_pagamento_parcial'), nullable=False),
    sa.Column('descricao', sa.String(), nullable=True),
    sa.Column('fonte_criterio', sa.String(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['parcela_id'], ['parcela.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('pagamento_parcial', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_pagamento_parcial_parcela_id'), ['parcela_id'], unique=False)

    with op.batch_alter_table('acessorio', schema=None) as batch_op:
        batch_op.add_column(sa.Column('fonte_criterio', sa.String(), nullable=True))
        batch_op.create_check_constraint(
            'ck_acessorio_data_evento_obrigatoria_para_saldo_remanescente',
            "base_calculo <> 'saldo_remanescente_em_data_evento' OR data_evento IS NOT NULL",
        )

    # base_calculo_acessorio ganha um valor novo. No SQLite isso é só um
    # VARCHAR+CHECK (batch recreate da tabela). No Postgres o tipo já
    # existe como ENUM nativo (criado na migração anterior) — precisa de
    # ALTER TYPE ... ADD VALUE em vez de tentar recriar a coluna como se
    # fosse um type change genérico (invariante 12.1.6: a cadeia precisa
    # rodar limpa também num Postgres vazio).
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "ALTER TYPE base_calculo_acessorio ADD VALUE IF NOT EXISTS "
            "'saldo_remanescente_em_data_evento'"
        )
    else:
        with op.batch_alter_table('acessorio', schema=None) as batch_op:
            batch_op.alter_column(
                'base_calculo',
                existing_type=sa.VARCHAR(length=28),
                type_=sa.Enum(
                    'TOTAL_LIQUIDO_PARCELAS', 'VALOR_PRINCIPAL_SEM_CORRECAO',
                    'VALOR_FIXO_ABSOLUTO', 'SALDO_REMANESCENTE_EM_DATA_EVENTO',
                    name='base_calculo_acessorio',
                ),
                existing_nullable=False,
            )

    with op.batch_alter_table('correcao_segmento', schema=None) as batch_op:
        batch_op.add_column(sa.Column('fonte_criterio', sa.String(), nullable=True))

    with op.batch_alter_table('juros_segmento', schema=None) as batch_op:
        batch_op.add_column(sa.Column('fonte_criterio', sa.String(), nullable=True))

    with op.batch_alter_table('processo', schema=None) as batch_op:
        batch_op.add_column(sa.Column('titulo_calculo', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('requerente_doc', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('requerido_doc', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('tribunal', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('tipo_acao', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('observacoes', sa.String(), nullable=True))

    # Migração de dados: cada parcela com valor_pago preenchido vira uma
    # linha de pagamento_parcial (tipo=pagamento) ANTES de remover as
    # colunas antigas — nenhum dado histórico pode se perder aqui.
    parcela_tbl = sa.table(
        'parcela',
        sa.column('id', sa.Uuid()),
        sa.column('valor_pago', app.models.tipos.DecimalText()),
        sa.column('valor_pago_data', sa.Date()),
    )
    pagamento_tbl = sa.table(
        'pagamento_parcial',
        sa.column('id', sa.Uuid()),
        sa.column('parcela_id', sa.Uuid()),
        sa.column('data', sa.Date()),
        sa.column('valor', app.models.tipos.DecimalText()),
        sa.column('tipo', sa.String()),
    )
    linhas = bind.execute(
        sa.select(parcela_tbl.c.id, parcela_tbl.c.valor_pago, parcela_tbl.c.valor_pago_data)
        .where(parcela_tbl.c.valor_pago.is_not(None))
    ).all()
    for parcela_id, valor_pago, valor_pago_data in linhas:
        bind.execute(
            sa.insert(pagamento_tbl).values(
                id=uuid.uuid4(),
                parcela_id=parcela_id,
                data=valor_pago_data,
                valor=valor_pago,
                tipo='PAGAMENTO',
            )
        )

    with op.batch_alter_table('parcela', schema=None) as batch_op:
        # precisa cair ANTES do drop_column: o batch mode do SQLite
        # recria a tabela copiando os constraints existentes, e esse
        # CHECK referencia justamente as colunas sendo removidas.
        batch_op.drop_constraint('ck_parcela_valor_pago_requer_data', type_='check')
        batch_op.drop_column('valor_pago_data')
        batch_op.drop_column('valor_pago')


def downgrade() -> None:
    # Reverte o schema. A migração de dados NÃO é revertida — os
    # pagamentos migrados para pagamento_parcial ficam lá (a tabela
    # continua existindo até o downgrade seguinte que a remova, se
    # houver); não há como reconstruir "o único valor_pago" de uma
    # parcela que ganhou várias deduções depois do upgrade sem uma
    # regra de negócio nova. Downgrade serve para reverter uma migração
    # recém-aplicada em dev, não para produção com dados reais.
    with op.batch_alter_table('parcela', schema=None) as batch_op:
        batch_op.add_column(sa.Column('valor_pago', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('valor_pago_data', sa.Date(), nullable=True))
        batch_op.create_check_constraint(
            'ck_parcela_valor_pago_requer_data',
            'valor_pago IS NULL OR valor_pago_data IS NOT NULL',
        )

    with op.batch_alter_table('processo', schema=None) as batch_op:
        batch_op.drop_column('observacoes')
        batch_op.drop_column('tipo_acao')
        batch_op.drop_column('tribunal')
        batch_op.drop_column('requerido_doc')
        batch_op.drop_column('requerente_doc')
        batch_op.drop_column('titulo_calculo')

    with op.batch_alter_table('juros_segmento', schema=None) as batch_op:
        batch_op.drop_column('fonte_criterio')

    with op.batch_alter_table('correcao_segmento', schema=None) as batch_op:
        batch_op.drop_column('fonte_criterio')

    # Postgres não suporta remover valor de ENUM (sem DROP TYPE/recriar);
    # no SQLite o batch recreate reverte a coluna para VARCHAR simples.
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        with op.batch_alter_table('acessorio', schema=None) as batch_op:
            batch_op.alter_column(
                'base_calculo',
                existing_type=sa.Enum(
                    'TOTAL_LIQUIDO_PARCELAS', 'VALOR_PRINCIPAL_SEM_CORRECAO',
                    'VALOR_FIXO_ABSOLUTO', 'SALDO_REMANESCENTE_EM_DATA_EVENTO',
                    name='base_calculo_acessorio',
                ),
                type_=sa.VARCHAR(length=28),
                existing_nullable=False,
            )

    with op.batch_alter_table('acessorio', schema=None) as batch_op:
        batch_op.drop_constraint(
            'ck_acessorio_data_evento_obrigatoria_para_saldo_remanescente', type_='check'
        )
        batch_op.drop_column('fonte_criterio')

    with op.batch_alter_table('pagamento_parcial', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_pagamento_parcial_parcela_id'))

    op.drop_table('pagamento_parcial')
