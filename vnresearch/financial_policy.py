"""Unified financial-statement completeness rules for ALL supported sectors.

Requirements are based on accounting models, not on individual ticker symbols.
Do not confuse missing published facts with uncomputed ratios or zero values.
"""

FINANCIAL_MODELS = {
    "bank": "bank",
    "securities": "securities",
}
NON_FINANCIAL = frozenset({
    "technology", "steel", "real_estate", "retail", "energy", "oil_gas",
    "telecom", "manufacturing", "construction", "agriculture", "logistics",
    "transportation", "pharmaceuticals", "consumer", "utilities", "materials",
    "industrial", "services", "insurance_non_bank", "other_nonfinancial",
})
BASE = ("assets", "equity", "net_income", "cfo")
STATEMENTS = ("balance_sheet", "income_statement", "cash_flow")


def accounting_model(sector):
    """Unknown classifications must not be silently treated as banking/non-banking."""
    if sector in FINANCIAL_MODELS:
        return FINANCIAL_MODELS[sector]
    if sector in NON_FINANCIAL:
        return "nonfinancial"
    return "unclassified"


def top_line_options(sector):
    model = accounting_model(sector)
    if model == "bank":
        return ("operating_income",)
    if model == "securities":
        return ("securities_revenue", "revenue")
    if model == "nonfinancial":
        return ("revenue",)
    # Unknown industry: do not call a banking or securities concept 'required',
    # but do not reject clearly present top-line financial statement fields.
    return ("revenue", "securities_revenue", "operating_income")


def top_line(values, sector):
    """Return (source field, value) without adding unrelated accounting lines."""
    for field in top_line_options(sector):
        value = values.get(field)
        if value is not None:
            return field, value
    return None, None


def required_missing(values, sector):
    """Required BASE values and ONE suitable top-line. 0 is present, not missing."""
    missing = [key for key in BASE if values.get(key) is None]
    field, _ = top_line(values, sector)
    if field is None:
        model = accounting_model(sector)
        missing.append({"bank": "operating_income",
                        "securities": "securities_revenue_or_revenue",
                        "nonfinancial": "revenue",
                        "unclassified": "top_line_unclassified"}[model])
    return missing


def missing_statements(present):
    return [statement for statement in STATEMENTS if statement not in set(present)]
