"""Initial schema

Revision ID: 236b9db11a9f
Revises: f96123a60137
Create Date: 2025-06-11 17:39:03.728587

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '236b9db11a9f'
down_revision: Union[str, None] = 'f96123a60137'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
