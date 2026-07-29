"""multa diaria data final

Revision ID: f31350057d7f
Revises: 7ba5aab6bd1b
Create Date: 2026-07-29 10:43:26.769030

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import app.models.tipos


# revision identifiers, used by Alembic.
revision: str = 'f31350057d7f'
down_revision: Union[str, Sequence[str], None] = '7ba5aab6bd1b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_XOR_CHECK_NOVO = (
    "(percentual IS NOT NULL AND valor_fixo IS NULL AND valor_diario IS NULL) OR "
    "(percentual IS NULL AND valor_fixo IS NOT NULL AND valor_diario IS NULL) OR "
    "(percentual IS NULL AND valor_fixo IS NULL AND valor_diario IS NOT NULL)"
)
_XOR_CHECK_ANTIGO = (
    "(percentual IS NOT NULL AND valor_fixo IS NULL) OR "
    "(percentual IS NULL AND valor_fixo IS NOT NULL)"
)


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('acessorio', schema=None) as batch_op:
        batch_op.add_column(sa.Column('valor_diario', app.models.tipos.DecimalText(), nullable=True))
        batch_op.add_column(sa.Column('data_inicio_acumulo', sa.Date(), nullable=True))
        batch_op.drop_constraint('ck_acessorio_percentual_xor_valor_fixo', type_='check')
        batch_op.create_check_constraint('ck_acessorio_percentual_xor_valor_fixo', _XOR_CHECK_NOVO)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('acessorio', schema=None) as batch_op:
        batch_op.drop_constraint('ck_acessorio_percentual_xor_valor_fixo', type_='check')
        batch_op.create_check_constraint('ck_acessorio_percentual_xor_valor_fixo', _XOR_CHECK_ANTIGO)
        batch_op.drop_column('data_inicio_acumulo')
        batch_op.drop_column('valor_diario')
