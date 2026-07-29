"""paridade soscalculos passo 3

Revision ID: 7ba5aab6bd1b
Revises: 4a0986c594ca
Create Date: 2026-07-29 10:03:12.662742

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import app.models.tipos


# revision identifiers, used by Alembic.
revision: str = '7ba5aab6bd1b'
down_revision: Union[str, Sequence[str], None] = '4a0986c594ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DONO_CHECK_NOVO = (
    "(processo_id IS NOT NULL AND parcela_id IS NULL AND acessorio_id IS NULL) OR "
    "(processo_id IS NULL AND parcela_id IS NOT NULL AND acessorio_id IS NULL) OR "
    "(processo_id IS NULL AND parcela_id IS NULL AND acessorio_id IS NOT NULL)"
)
_DONO_CHECK_ANTIGO = (
    "(processo_id IS NOT NULL AND parcela_id IS NULL) OR "
    "(processo_id IS NULL AND parcela_id IS NOT NULL)"
)


def upgrade() -> None:
    """Upgrade schema."""
    # base_calculo_acessorio ganha "Sobre o Valor da Causa" (paridade
    # SOSCálculos) — mesmo tratamento dialeto-específico da migração
    # anterior (619d9c58a5ff): Postgres usa ALTER TYPE ADD VALUE, SQLite
    # recria a coluna via batch (é só VARCHAR+CHECK lá). Todas as
    # alterações de `acessorio` ficam num único batch_alter_table — dois
    # blocos separados na mesma tabela deixam a tabela temporária
    # `_alembic_tmp_acessorio` do primeiro sem limpar a tempo do segundo.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE base_calculo_acessorio ADD VALUE IF NOT EXISTS 'VALOR_DA_CAUSA'")
        with op.batch_alter_table('acessorio', schema=None) as batch_op:
            batch_op.add_column(sa.Column('historico', sa.String(), nullable=True))
            batch_op.add_column(
                sa.Column('usa_correcao_default', sa.Boolean(), server_default=sa.text('1'), nullable=False)
            )
            batch_op.add_column(
                sa.Column('usa_juros_default', sa.Boolean(), server_default=sa.text('1'), nullable=False)
            )
    else:
        with op.batch_alter_table('acessorio', schema=None) as batch_op:
            batch_op.add_column(sa.Column('historico', sa.String(), nullable=True))
            batch_op.add_column(
                sa.Column('usa_correcao_default', sa.Boolean(), server_default=sa.text('1'), nullable=False)
            )
            batch_op.add_column(
                sa.Column('usa_juros_default', sa.Boolean(), server_default=sa.text('1'), nullable=False)
            )
            batch_op.alter_column(
                'base_calculo',
                existing_type=sa.VARCHAR(length=28),
                type_=sa.Enum(
                    'TOTAL_LIQUIDO_PARCELAS', 'VALOR_PRINCIPAL_SEM_CORRECAO',
                    'VALOR_FIXO_ABSOLUTO', 'SALDO_REMANESCENTE_EM_DATA_EVENTO', 'VALOR_DA_CAUSA',
                    name='base_calculo_acessorio',
                ),
                existing_nullable=False,
            )

    with op.batch_alter_table('correcao_segmento', schema=None) as batch_op:
        batch_op.add_column(sa.Column('acessorio_id', sa.Uuid(), nullable=True))
        batch_op.alter_column('dono_tipo',
               existing_type=sa.VARCHAR(length=16),
               type_=sa.Enum('PROCESSO_DEFAULT', 'PARCELA_OVERRIDE', 'ACESSORIO_OVERRIDE', name='dono_tipo'),
               existing_nullable=False)
        batch_op.create_index(batch_op.f('ix_correcao_segmento_acessorio_id'), ['acessorio_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_correcao_segmento_acessorio_id', 'acessorio', ['acessorio_id'], ['id'], ondelete='CASCADE'
        )
        batch_op.drop_constraint('ck_correcao_segmento_dono_exclusivo', type_='check')
        batch_op.create_check_constraint('ck_correcao_segmento_dono_exclusivo', _DONO_CHECK_NOVO)

    with op.batch_alter_table('juros_segmento', schema=None) as batch_op:
        batch_op.add_column(sa.Column('acessorio_id', sa.Uuid(), nullable=True))
        batch_op.alter_column('dono_tipo',
               existing_type=sa.VARCHAR(length=16),
               type_=sa.Enum('PROCESSO_DEFAULT', 'PARCELA_OVERRIDE', 'ACESSORIO_OVERRIDE', name='dono_tipo'),
               existing_nullable=False)
        batch_op.create_index(batch_op.f('ix_juros_segmento_acessorio_id'), ['acessorio_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_juros_segmento_acessorio_id', 'acessorio', ['acessorio_id'], ['id'], ondelete='CASCADE'
        )
        batch_op.drop_constraint('ck_juros_segmento_dono_exclusivo', type_='check')
        batch_op.create_check_constraint('ck_juros_segmento_dono_exclusivo', _DONO_CHECK_NOVO)

    with op.batch_alter_table('processo', schema=None) as batch_op:
        batch_op.add_column(sa.Column('valor_causa', app.models.tipos.DecimalText(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('processo', schema=None) as batch_op:
        batch_op.drop_column('valor_causa')

    with op.batch_alter_table('juros_segmento', schema=None) as batch_op:
        batch_op.drop_constraint('ck_juros_segmento_dono_exclusivo', type_='check')
        batch_op.create_check_constraint('ck_juros_segmento_dono_exclusivo', _DONO_CHECK_ANTIGO)
        batch_op.drop_constraint('fk_juros_segmento_acessorio_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_juros_segmento_acessorio_id'))
        batch_op.alter_column('dono_tipo',
               existing_type=sa.Enum('PROCESSO_DEFAULT', 'PARCELA_OVERRIDE', 'ACESSORIO_OVERRIDE', name='dono_tipo'),
               type_=sa.VARCHAR(length=16),
               existing_nullable=False)
        batch_op.drop_column('acessorio_id')

    with op.batch_alter_table('correcao_segmento', schema=None) as batch_op:
        batch_op.drop_constraint('ck_correcao_segmento_dono_exclusivo', type_='check')
        batch_op.create_check_constraint('ck_correcao_segmento_dono_exclusivo', _DONO_CHECK_ANTIGO)
        batch_op.drop_constraint('fk_correcao_segmento_acessorio_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_correcao_segmento_acessorio_id'))
        batch_op.alter_column('dono_tipo',
               existing_type=sa.Enum('PROCESSO_DEFAULT', 'PARCELA_OVERRIDE', 'ACESSORIO_OVERRIDE', name='dono_tipo'),
               type_=sa.VARCHAR(length=16),
               existing_nullable=False)
        batch_op.drop_column('acessorio_id')

    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        with op.batch_alter_table('acessorio', schema=None) as batch_op:
            batch_op.alter_column(
                'base_calculo',
                existing_type=sa.Enum(
                    'TOTAL_LIQUIDO_PARCELAS', 'VALOR_PRINCIPAL_SEM_CORRECAO',
                    'VALOR_FIXO_ABSOLUTO', 'SALDO_REMANESCENTE_EM_DATA_EVENTO', 'VALOR_DA_CAUSA',
                    name='base_calculo_acessorio',
                ),
                type_=sa.VARCHAR(length=28),
                existing_nullable=False,
            )
            batch_op.drop_column('usa_juros_default')
            batch_op.drop_column('usa_correcao_default')
            batch_op.drop_column('historico')
    else:
        with op.batch_alter_table('acessorio', schema=None) as batch_op:
            batch_op.drop_column('usa_juros_default')
            batch_op.drop_column('usa_correcao_default')
            batch_op.drop_column('historico')
