import logging
from typing import Any

import resend

from app.config import settings

logger = logging.getLogger(__name__)


def _init() -> None:
    resend.api_key = settings.resend_api_key


def send_intelligence_alert(
    to_email: str,
    company_name: str,
    summary: str,
    changes: list[str] | None = None,
) -> bool:
    """Send an intelligence alert email via Resend."""
    _init()

    changes_html = ""
    if changes:
        items = "".join(f"<li>{c}</li>" for c in changes)
        changes_html = f"<h3>What Changed</h3><ul>{items}</ul>"

    html = f"""
    <div style="font-family: system-ui, sans-serif; max-width: 600px;">
        <h2>📡 Signals Intelligence Update: {company_name}</h2>
        <p>{summary}</p>
        {changes_html}
        <hr style="border: 1px solid #333; margin: 20px 0;" />
        <p style="color: #888; font-size: 12px;">
            Sent by Signals — AI-Powered Market Intelligence
        </p>
    </div>
    """

    try:
        result = resend.Emails.send({
            "from": "Signals <signals@updates.yourdomain.com>",
            "to": to_email,
            "subject": f"🔔 Intelligence Update: {company_name}",
            "html": html,
        })
        logger.info(f"[resend] Alert sent to {to_email} for {company_name}")
        return True
    except Exception as e:
        logger.error(f"[resend] Failed to send alert: {e}")
        return False
