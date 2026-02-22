"""Initial migration - create papers and authors tables

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create extension for vector support
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Create authors table
    op.create_table(
        'authors',
        sa.Column('id', sa.String(32), primary_key=True, index=True),
        sa.Column('full_name', sa.String(300), nullable=False, index=True),
        sa.Column('full_name_ru', sa.String(300), nullable=True),
        sa.Column('affiliations', sa.ARRAY(sa.String), nullable=True),
        sa.Column('affiliations_ru', sa.ARRAY(sa.String), nullable=True),
        sa.Column('orcid', sa.String(50), unique=True, nullable=True, index=True),
        sa.Column('rsci_id', sa.String(50), unique=True, nullable=True),
        sa.Column('elib_id', sa.String(50), unique=True, nullable=True),
        sa.Column('email', sa.String(256), nullable=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create papers table
    op.create_table(
        'papers',
        sa.Column('id', sa.String(32), primary_key=True, index=True),
        sa.Column('title', sa.Text, nullable=False, index=True),
        sa.Column('title_ru', sa.Text, nullable=True),
        sa.Column('abstract', sa.Text, nullable=True),
        sa.Column('abstract_ru', sa.Text, nullable=True),
        sa.Column('doi', sa.String(256), unique=True, nullable=True, index=True),
        sa.Column('arxiv_id', sa.String(50), unique=True, nullable=True, index=True),
        sa.Column('source_type', sa.String(50), nullable=False, index=True),
        sa.Column('source_url', sa.Text, nullable=True),
        sa.Column('source_id', sa.String(100), nullable=True),
        sa.Column('journal', sa.String(500), nullable=True, index=True),
        sa.Column('journal_ru', sa.String(500), nullable=True),
        sa.Column('publisher', sa.String(300), nullable=True),
        sa.Column('volume', sa.String(50), nullable=True),
        sa.Column('issue', sa.String(50), nullable=True),
        sa.Column('pages', sa.String(50), nullable=True),
        sa.Column('publication_date', sa.DateTime, nullable=True, index=True),
        sa.Column('publication_year', sa.Integer, nullable=True, index=True),
        sa.Column('crawled_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('full_text', sa.Text, nullable=True),
        sa.Column('keywords', sa.ARRAY(sa.String), nullable=True),
        sa.Column('keywords_ru', sa.ARRAY(sa.String), nullable=True),
        sa.Column('pdf_path', sa.String(500), nullable=True),
        sa.Column('pdf_url', sa.Text, nullable=True),
        sa.Column('pdf_size_mb', sa.Float, nullable=True),
        sa.Column('citation_count', sa.Integer, default=0),
        sa.Column('citation_count_rsci', sa.Integer, default=0),
        sa.Column('is_processed', sa.Integer, default=0),
        sa.Column('has_full_text', sa.Integer, default=0),
        sa.Column('language', sa.String(10), default='ru'),
        sa.Column('title_embedding', pgvector.sqlalchemy.Vector(384), nullable=True),
        sa.Column('abstract_embedding', pgvector.sqlalchemy.Vector(384), nullable=True),
        sa.Column('full_text_embedding', pgvector.sqlalchemy.Vector(384), nullable=True),
    )
    
    # Create indexes for vector search
    op.create_index('idx_papers_title_embedding', 'papers', ['title_embedding'], postgresql_using='ivfflat')
    op.create_index('idx_papers_abstract_embedding', 'papers', ['abstract_embedding'], postgresql_using='ivfflat')
    op.create_index('idx_papers_source_type_year', 'papers', ['source_type', 'publication_year'])
    
    # Create paper_author association table
    op.create_table(
        'paper_author',
        sa.Column('paper_id', sa.String(32), sa.ForeignKey('papers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('author_id', sa.String(32), sa.ForeignKey('authors.id', ondelete='CASCADE'), nullable=False),
    )
    
    op.create_index('idx_paper_author_paper', 'paper_author', ['paper_id'])
    op.create_index('idx_paper_author_author', 'paper_author', ['author_id'])
    op.create_index('idx_paper_author_unique', 'paper_author', ['paper_id', 'author_id'], unique=True)
    
    # Create citations table
    op.create_table(
        'citations',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('citing_paper_id', sa.String(32), sa.ForeignKey('papers.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('cited_paper_id', sa.String(32), sa.ForeignKey('papers.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )
    
    op.create_index('idx_citations_unique', 'citations', ['citing_paper_id', 'cited_paper_id'], unique=True)


def downgrade() -> None:
    op.drop_table('citations')
    op.drop_table('paper_author')
    op.drop_table('papers')
    op.drop_table('authors')
