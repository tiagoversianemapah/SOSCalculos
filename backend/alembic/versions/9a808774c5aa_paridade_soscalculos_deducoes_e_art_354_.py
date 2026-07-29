"""paridade soscalculos deducoes e art 354 cc

Revision ID: 9a808774c5aa
Revises: f31350057d7f
Create Date: 2026-07-29 11:52:53.989372

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import app.models.tipos


# revision identifiers, used by Alembic.
revision: str = '9a808774c5aa'
down_revision: Union[str, Sequence[str], None] = 'f31350057d7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DONO_CHECK_4_VIAS = (
    "(processo_id IS NOT NULL AND parcela_id IS NULL AND acessorio_id IS NULL AND deducao_id IS NULL) OR "
    "(processo_id IS NULL AND parcela_id IS NOT NULL AND acessorio_id IS NULL AND deducao_id IS NULL) OR "
    "(processo_id IS NULL AND parcela_id IS NULL AND acessorio_id IS NOT NULL AND deducao_id IS NULL) OR "
    "(processo_id IS NULL AND parcela_id IS NULL AND acessorio_id IS NULL AND deducao_id IS NOT NULL)"
)
_DONO_CHECK_3_VIAS = (
    "(processo_id IS NOT NULL AND parcela_id IS NULL AND acessorio_id IS NULL) OR "
    "(processo_id IS NULL AND parcela_id IS NOT NULL AND acessorio_id IS NULL) OR "
    "(processo_id IS NULL AND parcela_id IS NULL AND acessorio_id IS NOT NULL)"
)
_MEMORIA_CHECK_3_VIAS = (
    "(parcela_id IS NOT NULL AND acessorio_id IS NULL AND deducao_id IS NULL) OR "
    "(parcela_id IS NULL AND acessorio_id IS NOT NULL AND deducao_id IS NULL) OR "
    "(parcela_id IS NULL AND acessorio_id IS NULL AND deducao_id IS NOT NULL)"
)
_MEMORIA_CHECK_2_VIAS = (
    "(parcela_id IS NOT NULL AND acessorio_id IS NULL) OR "
    "(parcela_id IS NULL AND acessorio_id IS NOT NULL)"
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'deducao',
        sa.Column('processo_id', sa.Uuid(), nullable=False),
        sa.Column('tipo', sa.Enum('ADJUDICACAO', 'ALVARA_LEVANTAMENTO', 'ALVARA_LEVANTAMENTO_ESTIMAR_TEMA_677', 'COMPENSACAO', 'COMPENSACAO_FINANCEIRO', 'DEPOSITO_JUDICIAL', 'DEPOSITO_JUDICIAL_TEMA_677', 'PAGAMENTO', 'RECIBO', name='tipo_deducao'), nullable=False),
        sa.Column('historico', sa.String(), nullable=True),
        sa.Column('data_inicial', sa.Date(), nullable=False),
        sa.Column('valor', app.models.tipos.DecimalText(), nullable=False),
        sa.Column('atualizacao_tipo', sa.Enum('DATA_INICIAL', 'DATA_CALCULO', 'DATA_LEVANTAMENTO', 'OUTRA_DATA', name='tipo_atualizacao_deducao'), nullable=False),
        sa.Column('data_atualizacao', sa.Date(), nullable=True),
        sa.Column('fonte_criterio', sa.String(), nullable=True),
        sa.Column('usa_correcao_default', sa.Boolean(), nullable=False),
        sa.Column('usa_juros_default', sa.Boolean(), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.CheckConstraint("atualizacao_tipo NOT IN ('outra_data', 'data_levantamento') OR data_atualizacao IS NOT NULL", name='ck_deducao_data_atualizacao_obrigatoria'),
        sa.ForeignKeyConstraint(['processo_id'], ['processo.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('deducao', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_deducao_processo_id'), ['processo_id'], unique=False)

    with op.batch_alter_table('correcao_segmento', schema=None) as batch_op:
        batch_op.add_column(sa.Column('deducao_id', sa.Uuid(), nullable=True))
        batch_op.create_index(batch_op.f('ix_correcao_segmento_deducao_id'), ['deducao_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_correcao_segmento_deducao_id', 'deducao', ['deducao_id'], ['id'], ondelete='CASCADE'
        )
        batch_op.drop_constraint('ck_correcao_segmento_dono_exclusivo', type_='check')
        batch_op.create_check_constraint('ck_correcao_segmento_dono_exclusivo', _DONO_CHECK_4_VIAS)

    with op.batch_alter_table('juros_segmento', schema=None) as batch_op:
        batch_op.add_column(sa.Column('deducao_id', sa.Uuid(), nullable=True))
        batch_op.create_index(batch_op.f('ix_juros_segmento_deducao_id'), ['deducao_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_juros_segmento_deducao_id', 'deducao', ['deducao_id'], ['id'], ondelete='CASCADE'
        )
        batch_op.drop_constraint('ck_juros_segmento_dono_exclusivo', type_='check')
        batch_op.create_check_constraint('ck_juros_segmento_dono_exclusivo', _DONO_CHECK_4_VIAS)

    with op.batch_alter_table('memoria_calculo', schema=None) as batch_op:
        batch_op.add_column(sa.Column('deducao_id', sa.Uuid(), nullable=True))
        batch_op.create_index(batch_op.f('ix_memoria_calculo_deducao_id'), ['deducao_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_memoria_calculo_deducao_id', 'deducao', ['deducao_id'], ['id'], ondelete='CASCADE'
        )
        batch_op.drop_constraint('ck_memoria_calculo_dono_exclusivo', type_='check')
        batch_op.create_check_constraint('ck_memoria_calculo_dono_exclusivo', _MEMORIA_CHECK_3_VIAS)

    with op.batch_alter_table('processo', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('configura_deducoes', sa.Boolean(), server_default=sa.text('0'), nullable=False)
        )
        batch_op.add_column(
            sa.Column('aplicar_art_354_cc', sa.Boolean(), server_default=sa.text('0'), nullable=False)
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('processo', schema=None) as batch_op:
        batch_op.drop_column('aplicar_art_354_cc')
        batch_op.drop_column('configura_deducoes')

    with op.batch_alter_table('memoria_calculo', schema=None) as batch_op:
        batch_op.drop_constraint('ck_memoria_calculo_dono_exclusivo', type_='check')
        batch_op.create_check_constraint('ck_memoria_calculo_dono_exclusivo', _MEMORIA_CHECK_2_VIAS)
        batch_op.drop_constraint('fk_memoria_calculo_deducao_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_memoria_calculo_deducao_id'))
        batch_op.drop_column('deducao_id')

    with op.batch_alter_table('juros_segmento', schema=None) as batch_op:
        batch_op.drop_constraint('ck_juros_segmento_dono_exclusivo', type_='check')
        batch_op.create_check_constraint('ck_juros_segmento_dono_exclusivo', _DONO_CHECK_3_VIAS)
        batch_op.drop_constraint('fk_juros_segmento_deducao_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_juros_segmento_deducao_id'))
        batch_op.drop_column('deducao_id')

    with op.batch_alter_table('correcao_segmento', schema=None) as batch_op:
        batch_op.drop_constraint('ck_correcao_segmento_dono_exclusivo', type_='check')
        batch_op.create_check_constraint('ck_correcao_segmento_dono_exclusivo', _DONO_CHECK_3_VIAS)
        batch_op.drop_constraint('fk_correcao_segmento_deducao_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_correcao_segmento_deducao_id'))
        batch_op.drop_column('deducao_id')

    with op.batch_alter_table('deducao', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_deducao_processo_id'))

    op.drop_table('deducao')
