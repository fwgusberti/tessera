"""Backfill domain associations for existing companies (feature 055, US3)

Data-only migration (no DDL). For every ``companies`` row that currently has no
``domain_join_policies`` row, associate the founder's (``admin_user``) email
domain with the company when that domain is:

- non-empty and syntactically present (email contains ``@``),
- NOT a public / free email-provider domain (gmail/outlook/…), and
- NOT already claimed by any existing domain policy.

The created policy mirrors the runtime auto-association (feature 055): it is
``policy = 'request_approval'`` and ``verified = true`` (the admin-approval gate
is the safety net). On a domain shared by several existing companies, the
earliest-created company wins (``DISTINCT ON (dom) ... ORDER BY dom, created_at``);
the others are left unassociated.

This directly benefits already-existing organizations (e.g. the reporter's
``@gusba.dev`` company), which otherwise stay exposed to the duplicate-company
problem this feature fixes.

The backfill is idempotent: it only touches companies with no policy and only
claims domains that are still unclaimed, so re-running inserts nothing new.

Revision ID: 0016
Revises: 0015
Create Date: 2026-07-06
"""

from alembic import op
from tessera_core.domain.email_domain import _PUBLIC_EMAIL_DOMAINS

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def _public_domain_sql_list() -> str:
    """Render the classifier's public-domain set as a SQL literal ``IN`` list.

    Sourced from ``tessera_core.domain.email_domain`` so the backfill classifies
    domains exactly as the runtime auto-association does. Values are static,
    lowercase provider domains — no injection surface.
    """
    return ", ".join(f"'{d}'" for d in sorted(_PUBLIC_EMAIL_DOMAINS))


# Exposed as a module constant so the backfill can be tested directly against a
# connection without an Alembic op context (see
# test_migration_0016_backfill_company_domains.py). The founder domain is the
# lowercased substring after the LAST '@' in the admin's email, matching
# tessera_core.domain.email_domain.extract_domain.
BACKFILL_SQL = f"""
    INSERT INTO domain_join_policies (company_id, domain, policy, verified)
    SELECT DISTINCT ON (cand.dom)
           cand.company_id, cand.dom, 'request_approval', true
    FROM (
        SELECT c.id AS company_id,
               c.created_at AS created_at,
               lower(substring(u.email from '@([^@]*)$')) AS dom
        FROM companies c
        JOIN users u ON u.id = c.admin_user_id
        WHERE u.email LIKE '%@%'
          AND NOT EXISTS (
              SELECT 1 FROM domain_join_policies p WHERE p.company_id = c.id
          )
    ) AS cand
    WHERE cand.dom IS NOT NULL
      AND cand.dom <> ''
      AND cand.dom NOT IN ({_public_domain_sql_list()})
      AND NOT EXISTS (
          SELECT 1 FROM domain_join_policies p WHERE p.domain = cand.dom
      )
    ORDER BY cand.dom, cand.created_at ASC
"""


def upgrade() -> None:
    op.execute(BACKFILL_SQL)


def downgrade() -> None:
    # No-op: backfilled rows are indistinguishable from organically
    # auto-associated policies, and removing them would re-introduce the
    # duplicate-company exposure this feature fixes.
    pass
