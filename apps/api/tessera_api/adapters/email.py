"""FastMail-backed implementation of EmailPort."""

from __future__ import annotations

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from tessera_api.config import get_settings
from tessera_core.ports.providers import EmailPort


def _get_mail_config() -> ConnectionConfig:
    s = get_settings()
    return ConnectionConfig(
        MAIL_USERNAME=s.mail_username,
        MAIL_PASSWORD=s.mail_password,
        MAIL_FROM=s.mail_from,
        MAIL_PORT=s.mail_port,
        MAIL_SERVER=s.mail_server,
        MAIL_STARTTLS=s.mail_starttls,
        MAIL_SSL_TLS=s.mail_ssl_tls,
        MAIL_DEBUG=False,
        SUPPRESS_SEND=int(s.mail_suppress_send),
    )


class FastMailEmailAdapter(EmailPort):
    async def _send(self, to: str, subject: str, body: str) -> None:
        message = MessageSchema(
            subject=subject,
            recipients=[to],
            body=body,
            subtype=MessageType.html,
        )
        fm = FastMail(_get_mail_config())
        await fm.send_message(message)

    async def send_verification(self, *, to: str, domain: str, verify_url: str) -> None:
        body = (
            f"<p>You requested domain verification for <strong>{domain}</strong>.</p>"
            f"<p><a href='{verify_url}'>Click here to verify your domain</a></p>"
            f"<p>This link expires in 24 hours.</p>"
        )
        await self._send(to, f"Verify your domain: {domain}", body)

    async def send_invitation(self, *, to: str, company_name: str, invited_by: str, accept_url: str) -> None:
        body = (
            f"<p><strong>{invited_by}</strong> has invited you to join <strong>{company_name}</strong> on Tessera.</p>"
            f"<p><a href='{accept_url}'>Accept invitation</a></p>"
            f"<p>This invitation expires in 7 days.</p>"
        )
        await self._send(to, f"You've been invited to {company_name}", body)

    async def send_join_request_notification(
        self,
        *,
        to: str,
        requester_name: str,
        requester_email: str,
        company_name: str,
        review_url: str,
    ) -> None:
        body = (
            f"<p><strong>{requester_name}</strong> ({requester_email}) has requested to join "
            f"<strong>{company_name}</strong>.</p>"
            f"<p><a href='{review_url}'>Review join requests</a></p>"
        )
        await self._send(to, f"New join request for {company_name}", body)

    async def send_join_request_decision(
        self, *, to: str, company_name: str, approved: bool, dashboard_url: str
    ) -> None:
        if approved:
            subject = f"You've been approved to join {company_name}"
            body = (
                f"<p>Your request to join <strong>{company_name}</strong> has been approved!</p>"
                f"<p><a href='{dashboard_url}'>Go to dashboard</a></p>"
            )
        else:
            subject = f"Your join request to {company_name} was not approved"
            body = f"<p>Your request to join <strong>{company_name}</strong> was not approved.</p>"
        await self._send(to, subject, body)
