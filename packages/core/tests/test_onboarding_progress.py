"""Unit tests for the onboarding-satisfaction predicate — pure domain logic.

TDD: written before implementation (Constitution Principle IV). Covers the C1
truth table from ``contracts/onboarding-gate.md``: company membership OR a set
``completed_at`` satisfies onboarding; neither leaves the user un-onboarded.

Run: cd packages/core && .venv/bin/python -m pytest tests/test_onboarding_progress.py -v
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from tessera_core.domain.onboarding_progress import (
    OnboardingProgress,
    has_completed_onboarding,
)


def _progress(completed_at: datetime | None) -> OnboardingProgress:
    return OnboardingProgress(user_id=uuid.uuid4(), completed_at=completed_at)


class TestHasCompletedOnboarding:
    def test_completed_at_set_no_membership_is_true(self):
        # (a) completed_at set + no membership → True
        progress = _progress(datetime.now(UTC))
        assert has_completed_onboarding(progress, has_company_membership=False) is True

    def test_completed_at_none_with_membership_is_true(self):
        # (b) completed_at None + has membership → True (the admin-added case)
        progress = _progress(None)
        assert has_completed_onboarding(progress, has_company_membership=True) is True

    def test_completed_at_none_no_membership_is_false(self):
        # (c) completed_at None + no membership → False (still onboarding — FR-007)
        progress = _progress(None)
        assert has_completed_onboarding(progress, has_company_membership=False) is False

    def test_progress_none_with_membership_is_true(self):
        # (d) progress is None + has membership → True (recovery path — FR-006)
        assert has_completed_onboarding(None, has_company_membership=True) is True

    def test_progress_none_no_membership_is_false(self):
        # (e) progress is None + no membership → False (brand-new user)
        assert has_completed_onboarding(None, has_company_membership=False) is False

    def test_completed_at_set_with_membership_is_true(self):
        # Both satisfying conditions present → True.
        progress = _progress(datetime.now(UTC))
        assert has_completed_onboarding(progress, has_company_membership=True) is True
