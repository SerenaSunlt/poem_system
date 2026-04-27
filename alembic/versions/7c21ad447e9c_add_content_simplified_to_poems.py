"""add content_simplified to poems

Revision ID: 7c21ad447e9c
Revises: d0e52d00bc0b
Create Date: 2026-04-27 20:55:19.756355

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c21ad447e9c'
down_revision: Union[str, None] = 'd0e52d00bc0b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # MySQL 不允许 TEXT 列有 DEFAULT 值,所以分三步走:
    # 1. 允许 NULL 加上列
    op.add_column(
        'poems',
        sa.Column('content_simplified', sa.Text(), nullable=True)
    )
    # 2. 把现有行的这个字段填成空字符串
    op.execute("UPDATE poems SET content_simplified = '' WHERE content_simplified IS NULL")
    # 3. 改成 NOT NULL
    op.alter_column(
        'poems',
        'content_simplified',
        existing_type=sa.Text(),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column('poems', 'content_simplified')
