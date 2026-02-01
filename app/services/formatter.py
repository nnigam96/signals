"""
Lovable Data Schema Formatter

Transforms raw pipeline output into the standardized Lovable frontend schema.
Uses proxy/default values for any missing fields to ensure consistent structure.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Literal
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


# =============================================================================
# TYPE DEFINITIONS (matching Lovable TypeScript interfaces)
# =============================================================================

SignalStrength = Literal["high", "medium", "low"]
SignalType = Literal[
    "leadership_change", "funding_round", "expansion", "product_launch",
    "hiring_surge", "partnership", "acquisition", "tech_adoption",
    "market_entry", "regulatory_change"
]
JobStatus = Literal["pending", "processing", "completed", "failed"]


@dataclass
class Company:
    """Primary entity representing a target company."""
    id: str
    name: str
    sector: str
    location: str
    employees: str
    signal: str | None = None
    signalStrength: SignalStrength | None = None
    website: str | None = None
    founded: int | None = None
    funding: str | None = None
    lastFundingRound: str | None = None
    description: str | None = None
    tags: list[str] = field(default_factory=list)
    createdAt: str | None = None
    updatedAt: str | None = None

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class Signal:
    """A detected market signal associated with a company."""
    id: str
    companyId: str
    type: SignalType
    strength: SignalStrength
    source: str
    headline: str
    detectedAt: str
    sourceUrl: str | None = None
    details: str | None = None
    expiresAt: str | None = None

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class SearchResults:
    """Final results payload when job completes."""
    companies: list[dict]
    signals: dict[str, list[dict]]
    metadata: dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)


# =============================================================================
# PROXY/DEFAULT VALUES
# =============================================================================

DEFAULT_SECTOR = "Technology"
DEFAULT_LOCATION = "United States"
DEFAULT_EMPLOYEES = "Unknown"
DEFAULT_SIGNAL_STRENGTH = "medium"


# =============================================================================
# SECTOR INFERENCE
# =============================================================================

SECTOR_KEYWORDS = {
    "AI/ML": ["ai", "machine learning", "ml", "artificial intelligence", "llm", "gpt", "neural"],
    "Fintech": ["payment", "banking", "finance", "crypto", "blockchain", "trading", "fintech"],
    "SaaS": ["saas", "software", "platform", "cloud", "subscription"],
    "Developer Tools": ["developer", "devtools", "api", "sdk", "infrastructure", "devops", "ci/cd"],
    "E-commerce": ["ecommerce", "e-commerce", "retail", "shopping", "marketplace"],
    "Healthcare": ["health", "medical", "healthcare", "biotech", "pharma"],
    "Security": ["security", "cybersecurity", "privacy", "encryption", "auth"],
    "Design": ["design", "figma", "creative", "ui", "ux"],
    "Productivity": ["productivity", "workspace", "collaboration", "project management", "notion"],
    "Data": ["data", "analytics", "database", "warehouse", "etl"],
}


def infer_sector(name: str, description: str | None = None) -> str:
    """Infer sector from company name and description."""
    text = f"{name} {description or ''}".lower()

    for sector, keywords in SECTOR_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return sector

    return DEFAULT_SECTOR


# =============================================================================
# EMPLOYEE COUNT INFERENCE
# =============================================================================

def infer_employees(agent_metrics: dict | None) -> str:
    """Infer employee range from hiring data."""
    if not agent_metrics:
        return DEFAULT_EMPLOYEES

    hiring = agent_metrics.get("hiring_velocity", {})
    open_roles = hiring.get("open_roles_count")

    if open_roles is None:
        return DEFAULT_EMPLOYEES

    # Rough heuristic: open roles often correlate with company size
    if open_roles > 200:
        return "1000+"
    elif open_roles > 100:
        return "500-1000"
    elif open_roles > 50:
        return "200-500"
    elif open_roles > 20:
        return "50-200"
    elif open_roles > 5:
        return "10-50"
    else:
        return "1-10"


# =============================================================================
# SIGNAL INFERENCE
# =============================================================================

def infer_signal_type(agent_metrics: dict | None, analysis: dict | None) -> tuple[SignalType | None, str | None]:
    """
    Infer the primary signal type and headline from agent/analysis data.
    Returns (signal_type, headline).
    """
    if not agent_metrics and not analysis:
        return None, None

    # Check hiring velocity
    hiring = agent_metrics.get("hiring_velocity", {}) if agent_metrics else {}
    hiring_status = hiring.get("hiring_status", "").lower()

    if hiring_status == "aggressive":
        open_roles = hiring.get("open_roles_count", "many")
        return "hiring_surge", f"Aggressive hiring: {open_roles} open positions"

    # Check for product/tech signals
    dev = agent_metrics.get("dev_velocity", {}) if agent_metrics else {}
    update_freq = dev.get("update_frequency", "").lower()
    latest_feature = dev.get("latest_feature")

    if update_freq in ["daily", "weekly"] and latest_feature:
        return "product_launch", f"Active development: {latest_feature}"

    # Check pricing model for expansion signals
    pricing = agent_metrics.get("pricing_model", {}) if agent_metrics else {}
    if pricing.get("has_free_tier") and pricing.get("pricing_strategy") == "PLG":
        return "expansion", "PLG strategy with free tier indicates growth focus"

    # Fallback to analysis sentiment
    if analysis:
        sentiment = analysis.get("metrics", {}).get("sentiment", "").lower()
        if sentiment == "bullish":
            return "market_entry", "Strong market position and positive outlook"

    return None, None


def map_signal_strength(score: int | None, sentiment: str | None = None) -> SignalStrength:
    """Map numeric signal strength to categorical."""
    if score is not None:
        if score >= 70:
            return "high"
        elif score >= 40:
            return "medium"
        else:
            return "low"

    if sentiment:
        sentiment_lower = sentiment.lower()
        if sentiment_lower == "bullish":
            return "high"
        elif sentiment_lower == "bearish":
            return "low"

    return DEFAULT_SIGNAL_STRENGTH


# =============================================================================
# MAIN FORMATTERS
# =============================================================================

def format_company(raw_data: dict) -> dict:
    """
    Transform raw pipeline output to Lovable Company schema.

    Args:
        raw_data: Raw company document from MongoDB/pipeline

    Returns:
        Formatted Company dict matching Lovable schema
    """
    # Extract nested data
    analysis = raw_data.get("analysis", {})
    agent_metrics = raw_data.get("agent_metrics", {})
    metrics = analysis.get("metrics", {})

    # Generate or extract ID
    company_id = str(raw_data.get("_id", uuid.uuid4()))

    # Core fields
    name = raw_data.get("name") or "Unknown Company"
    description = raw_data.get("description") or analysis.get("summary")

    # Inferred fields
    sector = infer_sector(name, description)
    employees = infer_employees(agent_metrics)

    # Signal inference
    signal_type, signal_headline = infer_signal_type(agent_metrics, analysis)
    signal_strength = map_signal_strength(
        metrics.get("signal_strength"),
        metrics.get("sentiment")
    )

    # Timestamps
    created_at = raw_data.get("crawled_at")
    updated_at = raw_data.get("updated_at")

    if isinstance(created_at, datetime):
        created_at = created_at.isoformat()
    if isinstance(updated_at, datetime):
        updated_at = updated_at.isoformat()

    # Build company object
    company = Company(
        id=company_id,
        name=name,
        sector=sector,
        location=DEFAULT_LOCATION,  # Could be enhanced with location detection
        employees=employees,
        signal=signal_type,
        signalStrength=signal_strength if signal_type else None,
        website=raw_data.get("website"),
        founded=None,  # Could be extracted from analysis
        funding=analysis.get("funding"),
        lastFundingRound=None,
        description=description,
        tags=_generate_tags(raw_data, analysis, agent_metrics),
        createdAt=created_at,
        updatedAt=updated_at,
    )

    return company.to_dict()


def format_signal(raw_data: dict, company_id: str) -> dict | None:
    """
    Transform agent/analysis data to Lovable Signal schema.

    Args:
        raw_data: Raw company document
        company_id: Parent company ID

    Returns:
        Formatted Signal dict or None if no signal detected
    """
    analysis = raw_data.get("analysis", {})
    agent_metrics = raw_data.get("agent_metrics", {})
    metrics = analysis.get("metrics", {})

    signal_type, headline = infer_signal_type(agent_metrics, analysis)

    if not signal_type:
        return None

    signal = Signal(
        id=str(uuid.uuid4()),
        companyId=company_id,
        type=signal_type,
        strength=map_signal_strength(
            metrics.get("signal_strength"),
            metrics.get("sentiment")
        ),
        source="Signals Intelligence",
        headline=headline or f"Signal detected for {raw_data.get('name', 'company')}",
        detectedAt=datetime.now(timezone.utc).isoformat(),
        sourceUrl=raw_data.get("website"),
        details=_format_signal_details(agent_metrics, analysis),
    )

    return signal.to_dict()


def format_signals_for_company(raw_data: dict, company_id: str) -> list[dict]:
    """
    Generate all applicable signals for a company.

    Returns list of Signal dicts.
    """
    signals = []
    agent_metrics = raw_data.get("agent_metrics", {})
    analysis = raw_data.get("analysis", {})
    metrics = analysis.get("metrics", {})

    now = datetime.now(timezone.utc).isoformat()
    base_strength = map_signal_strength(
        metrics.get("signal_strength"),
        metrics.get("sentiment")
    )

    # Hiring signal
    hiring = agent_metrics.get("hiring_velocity", {})
    if hiring.get("hiring_status"):
        status = hiring["hiring_status"]
        open_roles = hiring.get("open_roles_count", 0)

        if status.lower() in ["aggressive", "active"]:
            signals.append(Signal(
                id=str(uuid.uuid4()),
                companyId=company_id,
                type="hiring_surge",
                strength="high" if status.lower() == "aggressive" else "medium",
                source="Careers Page Analysis",
                headline=f"{status} hiring: {open_roles} open positions",
                detectedAt=now,
                details=f"Top departments: {', '.join(hiring.get('top_departments', []))}",
            ).to_dict())

    # Product/Dev velocity signal
    dev = agent_metrics.get("dev_velocity", {})
    if dev.get("update_frequency"):
        freq = dev["update_frequency"]
        if freq.lower() in ["daily", "weekly"]:
            signals.append(Signal(
                id=str(uuid.uuid4()),
                companyId=company_id,
                type="product_launch",
                strength="high" if freq.lower() == "daily" else "medium",
                source="Changelog Analysis",
                headline=f"{freq} product updates",
                detectedAt=now,
                details=f"Latest: {dev.get('latest_feature', 'N/A')}. Last update: {dev.get('last_update_date', 'N/A')}",
            ).to_dict())

    # Pricing/Expansion signal
    pricing = agent_metrics.get("pricing_model", {})
    if pricing.get("pricing_strategy"):
        strategy = pricing["pricing_strategy"]
        has_free = pricing.get("has_free_tier", False)

        if strategy == "PLG" and has_free:
            signals.append(Signal(
                id=str(uuid.uuid4()),
                companyId=company_id,
                type="expansion",
                strength="medium",
                source="Pricing Analysis",
                headline="Product-led growth with free tier",
                detectedAt=now,
                details=f"Lowest paid: ${pricing.get('lowest_paid_price', 'N/A')}/mo. Enterprise: {'Contact Sales' if pricing.get('is_enterprise_opaque') else 'Public pricing'}",
            ).to_dict())

    return signals


def format_search_results(
    companies_raw: list[dict],
    query: str | None = None,
    search_duration_ms: int | None = None
) -> dict:
    """
    Transform multiple companies into Lovable SearchResults schema.

    Args:
        companies_raw: List of raw company documents
        query: Original search query
        search_duration_ms: Search duration in milliseconds

    Returns:
        SearchResults dict with companies grouped by signal
    """
    formatted_companies = []
    signals_grouped: dict[str, list[dict]] = {}

    for raw in companies_raw:
        company = format_company(raw)
        formatted_companies.append(company)

        # Group by signal type
        signal_type = company.get("signal")
        if signal_type:
            if signal_type not in signals_grouped:
                signals_grouped[signal_type] = []
            signals_grouped[signal_type].append(company)

    # Build metadata
    metadata = {
        "totalMatches": len(formatted_companies),
        "queryTokens": query.split() if query else [],
        "searchDurationMs": search_duration_ms or 0,
    }

    results = SearchResults(
        companies=formatted_companies,
        signals=signals_grouped,
        metadata=metadata,
    )

    return results.to_dict()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _generate_tags(raw_data: dict, analysis: dict, agent_metrics: dict) -> list[str]:
    """Generate classification tags from available data."""
    tags = []

    # From analysis
    if analysis.get("competitors"):
        tags.append("has_competitors")
    if analysis.get("strengths"):
        tags.append("strengths_identified")
    if analysis.get("red_flags"):
        tags.append("has_red_flags")

    # From agent metrics
    hiring = agent_metrics.get("hiring_velocity", {})
    if hiring.get("hiring_status", "").lower() == "aggressive":
        tags.append("rapid_growth")
    if hiring.get("hiring_status", "").lower() == "freeze":
        tags.append("hiring_freeze")

    pricing = agent_metrics.get("pricing_model", {})
    if pricing.get("has_free_tier"):
        tags.append("freemium")
    if pricing.get("pricing_strategy") == "PLG":
        tags.append("plg")
    if pricing.get("pricing_strategy") == "Enterprise-Only":
        tags.append("enterprise")

    dev = agent_metrics.get("dev_velocity", {})
    if dev.get("update_frequency", "").lower() in ["daily", "weekly"]:
        tags.append("active_development")

    # From watchlist
    if raw_data.get("watchlist"):
        tags.append("watchlisted")

    return tags


def _format_signal_details(agent_metrics: dict, analysis: dict) -> str:
    """Format detailed signal information."""
    details_parts = []

    # Add metrics summary
    metrics = analysis.get("metrics", {})
    if metrics.get("sentiment"):
        details_parts.append(f"Sentiment: {metrics['sentiment']}")
    if metrics.get("signal_strength"):
        details_parts.append(f"Signal Strength: {metrics['signal_strength']}/100")
    if metrics.get("pmf_score"):
        details_parts.append(f"PMF Score: {metrics['pmf_score']}/10")

    # Add agent findings summary
    if agent_metrics.get("hiring_velocity"):
        hiring = agent_metrics["hiring_velocity"]
        details_parts.append(f"Hiring: {hiring.get('hiring_status', 'Unknown')}")

    if agent_metrics.get("pricing_model"):
        pricing = agent_metrics["pricing_model"]
        details_parts.append(f"GTM: {pricing.get('pricing_strategy', 'Unknown')}")

    return " | ".join(details_parts) if details_parts else ""


# =============================================================================
# CONVENIENCE WRAPPER
# =============================================================================

def format_pipeline_output(raw_data: dict) -> dict:
    """
    Main entry point: Format complete pipeline output for Lovable frontend.

    Returns a dict with:
    - company: Formatted Company object
    - signals: List of detected Signal objects
    - raw_metrics: Original agent metrics (for debugging)
    """
    company = format_company(raw_data)
    company_id = company["id"]

    signals = format_signals_for_company(raw_data, company_id)

    return {
        "company": company,
        "signals": signals,
        "raw_metrics": raw_data.get("agent_metrics", {}),
    }
