"""
HN Report Generator and Email Formatter.

Synthesizes HN discussions into actionable intelligence reports
and sends via Resend with mobile-friendly styling.
"""

import json
import logging
from typing import Any, Literal

import resend
from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

# OpenRouter client for synthesis
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.openrouter_api_key,
)

# Verdict types
VerdictType = Literal["VALIDATED", "NEEDS_RESEARCH", "CROWDED"]


def _init_resend() -> None:
    resend.api_key = settings.resend_api_key


async def analyze_hn_discussions(
    company_name: str,
    discussions: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Use LLM to synthesize HN discussions into structured report.

    Returns:
        {
            "verdict": "VALIDATED" | "NEEDS_RESEARCH" | "CROWDED",
            "summary": "Executive summary...",
            "sentiment": "Positive" | "Negative" | "Mixed",
            "key_themes": ["theme1", "theme2"],
            "notable_quotes": ["quote1", "quote2"],
            "competitor_mentions": ["comp1", "comp2"],
            "concerns": ["concern1"],
            "opportunities": ["opportunity1"]
        }
    """
    if not discussions:
        return {
            "verdict": "NEEDS_RESEARCH",
            "summary": f"No HN discussions found for {company_name} in the last 2 years.",
            "sentiment": "Neutral",
            "key_themes": [],
            "notable_quotes": [],
            "competitor_mentions": [],
            "concerns": [],
            "opportunities": [],
        }

    # Build context from discussions
    context_parts = []
    for d in discussions:
        part = f"Title: {d.get('title', '')}\n"
        part += f"Points: {d.get('points', 0)} | Comments: {d.get('num_comments', 0)}\n"
        part += f"Date: {d.get('created_at', '')}\n"

        if d.get("comments"):
            part += "Top Comments:\n"
            for c in d["comments"][:5]:
                text = c.get("text", "")[:300]
                part += f"  - {c.get('author', 'anon')}: {text}\n"

        context_parts.append(part)

    context = "\n---\n".join(context_parts)

    prompt = f"""Analyze these Hacker News discussions about {company_name}.

DISCUSSIONS:
{context}

TASK:
Determine the market validation status and synthesize insights.

VERDICT CRITERIA:
- VALIDATED: Strong positive sentiment, real users discussing actual usage, solving real problems, growing traction signals
- NEEDS_RESEARCH: Insufficient data, mixed signals, unclear positioning, or speculative discussions
- CROWDED: Multiple competitor mentions, market saturation signals, "yet another X" sentiment

Return JSON:
{{
    "verdict": "VALIDATED" | "NEEDS_RESEARCH" | "CROWDED",
    "summary": "2-3 sentence executive summary of HN community perception",
    "sentiment": "Positive" | "Negative" | "Mixed",
    "key_themes": ["theme1", "theme2", "theme3"],
    "notable_quotes": ["Most insightful quote from discussions", "Another key quote"],
    "competitor_mentions": ["Competitor names mentioned in discussions"],
    "concerns": ["Concerns or criticisms raised"],
    "opportunities": ["Potential opportunities identified"]
}}

Output valid JSON only.
"""

    try:
        response = await client.chat.completions.create(
            model=settings.model_name,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            timeout=90,
        )

        result = json.loads(response.choices[0].message.content)
        logger.info(f"[hn-report] Analysis complete for {company_name}: {result.get('verdict')}")
        return result

    except Exception as e:
        logger.error(f"[hn-report] Analysis failed: {e}")
        return {
            "verdict": "NEEDS_RESEARCH",
            "summary": f"Analysis failed for {company_name}",
            "sentiment": "Unknown",
            "key_themes": [],
            "notable_quotes": [],
            "competitor_mentions": [],
            "concerns": [],
            "opportunities": [],
            "error": str(e),
        }


def format_report_email(
    company_name: str,
    discussions: list[dict[str, Any]],
    analysis: dict[str, Any],
) -> str:
    """
    Generate mobile-friendly HTML email with verdict banner.

    Features:
    - Responsive design (max-width 600px)
    - Clear verdict banner with color coding
    - Section headers with icons
    - Bulleted lists for easy scanning
    - Linked discussion titles
    """
    verdict = analysis.get("verdict", "NEEDS_RESEARCH")

    # Verdict banner colors
    verdict_styles = {
        "VALIDATED": {
            "bg": "#10B981",
            "text": "#FFFFFF",
            "icon": "✓",
            "label": "VALIDATED",
        },
        "NEEDS_RESEARCH": {
            "bg": "#F59E0B",
            "text": "#FFFFFF",
            "icon": "?",
            "label": "NEEDS RESEARCH",
        },
        "CROWDED": {
            "bg": "#EF4444",
            "text": "#FFFFFF",
            "icon": "!",
            "label": "CROWDED MARKET",
        },
    }

    style = verdict_styles.get(verdict, verdict_styles["NEEDS_RESEARCH"])

    # Build discussion list HTML
    discussions_html = ""
    for d in discussions[:5]:
        title = d.get("title", "Untitled")
        url = d.get("url", "#")
        points = d.get("points", 0)
        comments = d.get("num_comments", 0)
        date = d.get("created_at", "")[:10]

        discussions_html += f"""
        <li style="margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid #E5E7EB;">
            <a href="{url}" style="color: #2563EB; text-decoration: none; font-weight: 500;">
                {title}
            </a>
            <div style="color: #6B7280; font-size: 13px; margin-top: 4px;">
                ▲ {points} points · {comments} comments · {date}
            </div>
        </li>
        """

    # Build key themes HTML
    themes_html = ""
    for theme in analysis.get("key_themes", [])[:5]:
        themes_html += f'<li style="margin-bottom: 6px;">{theme}</li>'

    # Build quotes HTML
    quotes_html = ""
    for quote in analysis.get("notable_quotes", [])[:3]:
        quotes_html += f"""
        <blockquote style="margin: 12px 0; padding: 12px 16px; background: #F3F4F6;
                          border-left: 4px solid #6B7280; font-style: italic; color: #374151;">
            "{quote}"
        </blockquote>
        """

    # Build competitors HTML
    competitors = analysis.get("competitor_mentions", [])
    competitors_html = ""
    if competitors:
        comp_list = ", ".join(competitors[:5])
        competitors_html = f"""
        <div style="margin-top: 20px;">
            <h3 style="color: #111827; font-size: 16px; margin-bottom: 8px;">
                🏁 Competitors Mentioned
            </h3>
            <p style="color: #4B5563;">{comp_list}</p>
        </div>
        """

    # Build concerns HTML
    concerns = analysis.get("concerns", [])
    concerns_html = ""
    if concerns:
        items = "".join(f'<li style="margin-bottom: 6px;">{c}</li>' for c in concerns[:3])
        concerns_html = f"""
        <div style="margin-top: 20px;">
            <h3 style="color: #111827; font-size: 16px; margin-bottom: 8px;">
                ⚠️ Concerns Raised
            </h3>
            <ul style="color: #4B5563; padding-left: 20px; margin: 0;">{items}</ul>
        </div>
        """

    # Build opportunities HTML
    opportunities = analysis.get("opportunities", [])
    opportunities_html = ""
    if opportunities:
        items = "".join(f'<li style="margin-bottom: 6px;">{o}</li>' for o in opportunities[:3])
        opportunities_html = f"""
        <div style="margin-top: 20px;">
            <h3 style="color: #111827; font-size: 16px; margin-bottom: 8px;">
                💡 Opportunities
            </h3>
            <ul style="color: #4B5563; padding-left: 20px; margin: 0;">{items}</ul>
        </div>
        """

    # Assemble full email
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background: #F9FAFB; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
    <div style="max-width: 600px; margin: 0 auto; background: #FFFFFF;">

        <!-- Header -->
        <div style="background: #111827; padding: 24px; text-align: center;">
            <h1 style="color: #FFFFFF; margin: 0; font-size: 20px;">
                📡 Signals HN Intelligence Report
            </h1>
            <p style="color: #9CA3AF; margin: 8px 0 0 0; font-size: 14px;">
                {company_name}
            </p>
        </div>

        <!-- Verdict Banner -->
        <div style="background: {style['bg']}; padding: 20px; text-align: center;">
            <span style="display: inline-block; width: 36px; height: 36px; line-height: 36px;
                        background: rgba(255,255,255,0.2); border-radius: 50%; font-size: 20px;">
                {style['icon']}
            </span>
            <h2 style="color: {style['text']}; margin: 12px 0 0 0; font-size: 24px; font-weight: 700;">
                {style['label']}
            </h2>
        </div>

        <!-- Content -->
        <div style="padding: 24px;">

            <!-- Summary -->
            <div style="margin-bottom: 24px;">
                <h3 style="color: #111827; font-size: 16px; margin-bottom: 8px;">
                    📋 Executive Summary
                </h3>
                <p style="color: #4B5563; line-height: 1.6; margin: 0;">
                    {analysis.get('summary', 'No summary available.')}
                </p>
                <p style="color: #6B7280; font-size: 13px; margin-top: 8px;">
                    Sentiment: <strong>{analysis.get('sentiment', 'Unknown')}</strong>
                </p>
            </div>

            <!-- Key Themes -->
            {"<div style='margin-bottom: 24px;'><h3 style='color: #111827; font-size: 16px; margin-bottom: 8px;'>🎯 Key Themes</h3><ul style='color: #4B5563; padding-left: 20px; margin: 0;'>" + themes_html + "</ul></div>" if themes_html else ""}

            <!-- Notable Quotes -->
            {"<div style='margin-bottom: 24px;'><h3 style='color: #111827; font-size: 16px; margin-bottom: 8px;'>💬 Notable Quotes</h3>" + quotes_html + "</div>" if quotes_html else ""}

            <!-- Top Discussions -->
            <div style="margin-bottom: 24px;">
                <h3 style="color: #111827; font-size: 16px; margin-bottom: 12px;">
                    📰 Top HN Discussions ({len(discussions)})
                </h3>
                <ul style="list-style: none; padding: 0; margin: 0;">
                    {discussions_html if discussions_html else '<li style="color: #6B7280;">No discussions found.</li>'}
                </ul>
            </div>

            {competitors_html}
            {concerns_html}
            {opportunities_html}

        </div>

        <!-- Footer -->
        <div style="background: #F3F4F6; padding: 20px; text-align: center; border-top: 1px solid #E5E7EB;">
            <p style="color: #6B7280; font-size: 12px; margin: 0;">
                Sent by <strong>Signals</strong> — AI-Powered Market Intelligence
            </p>
            <p style="color: #9CA3AF; font-size: 11px; margin: 8px 0 0 0;">
                Data sourced from Hacker News via Algolia API
            </p>
        </div>

    </div>
</body>
</html>
"""

    return html


def send_hn_report(
    to_email: str,
    company_name: str,
    discussions: list[dict[str, Any]],
    analysis: dict[str, Any],
) -> bool:
    """
    Send formatted HN report email via Resend.

    Returns:
        True if sent successfully, False otherwise.
    """
    _init_resend()

    html = format_report_email(company_name, discussions, analysis)
    verdict = analysis.get("verdict", "NEEDS_RESEARCH")

    # Subject line with verdict indicator
    verdict_emoji = {"VALIDATED": "✅", "NEEDS_RESEARCH": "🔍", "CROWDED": "⚠️"}
    emoji = verdict_emoji.get(verdict, "📊")

    try:
        result = resend.Emails.send({
            "from": "Signals <signals@updates.yourdomain.com>",
            "to": to_email,
            "subject": f"{emoji} HN Report: {company_name} — {verdict.replace('_', ' ')}",
            "html": html,
        })

        logger.info(f"[hn-report] Email sent to {to_email} for {company_name}")
        return True

    except Exception as e:
        logger.error(f"[hn-report] Failed to send email: {e}")
        return False


async def generate_and_send_report(
    company_name: str,
    discussions: list[dict[str, Any]],
    to_email: str,
) -> dict[str, Any]:
    """
    Full pipeline: analyze discussions and send email report.

    Returns:
        {
            "success": bool,
            "verdict": str,
            "analysis": dict,
            "email_sent": bool
        }
    """
    logger.info(f"[hn-report] Generating report for {company_name}")

    # Analyze discussions
    analysis = await analyze_hn_discussions(company_name, discussions)

    # Send email
    email_sent = send_hn_report(to_email, company_name, discussions, analysis)

    return {
        "success": True,
        "verdict": analysis.get("verdict"),
        "analysis": analysis,
        "email_sent": email_sent,
    }
