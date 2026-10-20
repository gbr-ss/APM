"""Add payment splits and manual discount to sales.

Revision ID: d137a9c8e241
Revises: c92e8b53d6f2
Create Date: 2026-10-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d137a9c8e241"
down_revision: Union[str, Sequence[str], None] = "c92e8b53d6f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "vendas",
        sa.Column("desconto_manual_tipo", sa.String(length=10), nullable=True),
    )
    op.add_column(
        "vendas",
        sa.Column(
            "desconto_manual_valor",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.create_table(
        "pagamentos_venda",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("venda_id", sa.Integer(), nullable=False),
        sa.Column("metodo", sa.String(length=20), nullable=False),
        sa.Column("valor", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["venda_id"], ["vendas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_pagamentos_venda_id"), "pagamentos_venda", ["id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_pagamentos_venda_id"), table_name="pagamentos_venda")
    op.drop_table("pagamentos_venda")
    op.drop_column("vendas", "desconto_manual_valor")
    op.drop_column("vendas", "desconto_manual_tipo")
