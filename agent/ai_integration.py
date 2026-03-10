from typing import Dict, Any
from .vat_store import get_country_record


def format_vat_summary(country_code: str) -> Dict[str, Any]:
    """Return a concise AI-style VAT summary for a country code."""
    rec = get_country_record(country_code)
    code = country_code.upper()
    if not rec:
        return {
            "country": code,
            "summary": f"No VAT record found for {code}.",
            "action": "Use PUT /agent/vat/{country} to add data or check spelling."
        }

    name = rec.get("name", code)
    rate = rec.get("standard_rate")
    reduced = rec.get("reduced_rates")
    notes = rec.get("notes")

    lines = []
    lines.append(f"Country: {name} ({code})")
    if rate is not None:
        lines.append(f"Standard VAT rate: {rate}%")
    if reduced:
        rr = ", ".join([f"{k}: {v}" for k, v in (reduced.items() if isinstance(reduced, dict) else [])])
        if rr:
            lines.append(f"Reduced rates: {rr}")
    if notes:
        lines.append(f"Notes: {notes}")

    # Compliance quickchecks
    checks = [
        "Validate buyer VAT number via VIES for EU B2B",
        "Record EUR value at time of payment and keep TX ID for audit",
        "OSS applies for EU B2C cross-border digital/physical sales over EUR 10,000"
    ]

    return {
        "country": code,
        "summary": "\n".join(lines),
        "quick_checks": checks
    }
