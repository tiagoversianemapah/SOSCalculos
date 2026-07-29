"""multa diaria competencia e salario minimo

Revision ID: 61c69a501267
Revises: af3c682d5ed7
Create Date: 2026-07-29 13:51:16.200153

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import app.models.tipos


# revision identifiers, used by Alembic.
revision: str = '61c69a501267'
down_revision: Union[str, Sequence[str], None] = 'af3c682d5ed7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_XOR_CHECK_NOVO = (
    "(percentual IS NOT NULL AND valor_fixo IS NULL AND valor_diario IS NULL AND salario_minimo_quantidade IS NULL) OR "
    "(percentual IS NULL AND valor_fixo IS NOT NULL AND valor_diario IS NULL AND salario_minimo_quantidade IS NULL) OR "
    "(percentual IS NULL AND valor_fixo IS NULL AND valor_diario IS NOT NULL AND salario_minimo_quantidade IS NULL) OR "
    "(percentual IS NULL AND valor_fixo IS NULL AND valor_diario IS NULL AND salario_minimo_quantidade IS NOT NULL)"
)
_XOR_CHECK_ANTIGO = (
    "(percentual IS NOT NULL AND valor_fixo IS NULL AND valor_diario IS NULL) OR "
    "(percentual IS NULL AND valor_fixo IS NOT NULL AND valor_diario IS NULL) OR "
    "(percentual IS NULL AND valor_fixo IS NULL AND valor_diario IS NOT NULL)"
)


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('acessorio', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('diaria_por_competencia', sa.Boolean(), server_default=sa.text('0'), nullable=False)
        )
        batch_op.add_column(sa.Column('salario_minimo_quantidade', app.models.tipos.DecimalText(), nullable=True))
        batch_op.drop_constraint('ck_acessorio_percentual_xor_valor_fixo', type_='check')
        batch_op.create_check_constraint('ck_acessorio_percentual_xor_valor_fixo', _XOR_CHECK_NOVO)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('acessorio', schema=None) as batch_op:
        batch_op.drop_constraint('ck_acessorio_percentual_xor_valor_fixo', type_='check')
        batch_op.create_check_constraint('ck_acessorio_percentual_xor_valor_fixo', _XOR_CHECK_ANTIGO)
        batch_op.drop_column('salario_minimo_quantidade')
        batch_op.drop_column('diaria_por_competencia')
