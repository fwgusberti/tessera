from abc import ABC, abstractmethod


class EmailPort(ABC):
    @abstractmethod
    async def send_verification(self, *, to: str, domain: str, verify_url: str) -> None:
        """Send domain verification email to `to` address."""

    @abstractmethod
    async def send_invitation(
        self, *, to: str, company_name: str, invited_by: str, accept_url: str
    ) -> None:
        """Send team invitation email."""

    @abstractmethod
    async def send_join_request_notification(
        self,
        *,
        to: str,
        requester_name: str,
        requester_email: str,
        company_name: str,
        review_url: str,
    ) -> None:
        """Notify company admin of a new join request."""

    @abstractmethod
    async def send_join_request_decision(
        self, *, to: str, company_name: str, approved: bool, dashboard_url: str
    ) -> None:
        """Notify requester that their join request was approved or denied."""

    @abstractmethod
    async def send_password_reset(
        self,
        *,
        to: str,
        reset_url: str,
        expires_in_minutes: int,
    ) -> None:
        """Send password reset link email."""
