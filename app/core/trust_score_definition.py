SCORING_VERSION = "trust-score-v1.1"

DEFAULT_WEIGHTS = {
    "c1_completeness": 10,
    "c2_verification": 25,
    "c3_credibility": 20,
    "c4_relevance": 20,
    "c5_recency": 10,
    "c6_style": 10,
    "c7_duplicate_concentration": 5,
}

DEFAULT_THRESHOLDS = {
    "labels": {
        "reliable": 85,
        "acceptable": 70,
        "needs_review": 50,
    },
    "relevance": {
        "high": 0.80,
        "good": 0.70,
        "medium": 0.60,
        "weak": 0.50,
        "low": 0.40,
    },
    "recency": {
        "fresh_years": 3,
        "acceptable_years": 5,
        "review_years": 10,
        "old_years": 15,
    },
    "publisher_whitelist": [],
    "venue_whitelist": [],
}

TRUST_SCORE_COMPONENTS = [
    {
        "key": "c1",
        "summary_key": "c1_metadata_completeness",
        "weight_key": "c1_completeness",
        "code": "C1",
        "label": "Metadata completeness",
        "max_score": 10,
    },
    {
        "key": "c2",
        "summary_key": "c2_metadata_verification",
        "weight_key": "c2_verification",
        "code": "C2",
        "label": "Identity and metadata verification",
        "max_score": 25,
    },
    {
        "key": "c3",
        "summary_key": "c3_source_credibility",
        "weight_key": "c3_credibility",
        "code": "C3",
        "label": "Source credibility evidence",
        "max_score": 20,
    },
    {
        "key": "c4",
        "summary_key": "c4_relevance",
        "weight_key": "c4_relevance",
        "code": "C4",
        "label": "Relevance to report",
        "max_score": 20,
    },
    {
        "key": "c5",
        "summary_key": "c5_recency",
        "weight_key": "c5_recency",
        "code": "C5",
        "label": "Recency",
        "max_score": 10,
    },
    {
        "key": "c6",
        "summary_key": "c6_citation_style",
        "weight_key": "c6_style",
        "code": "C6",
        "label": "Citation-style compliance",
        "max_score": 10,
    },
    {
        "key": "c7",
        "summary_key": "c7_duplicate_concentration",
        "weight_key": "c7_duplicate_concentration",
        "code": "C7",
        "label": "Duplicate and concentration risk",
        "max_score": 5,
    },
]


def build_trust_score_definition(
    version: str | None = None,
    weights: dict | None = None,
    thresholds: dict | None = None,
) -> dict:
    active_weights = weights or DEFAULT_WEIGHTS
    return {
        "version": version or SCORING_VERSION,
        "scale": 100,
        "components": [
            {
                **component,
                "weight": active_weights.get(component["weight_key"], component["max_score"]),
            }
            for component in TRUST_SCORE_COMPONENTS
        ],
        "weights": active_weights,
        "thresholds": thresholds or DEFAULT_THRESHOLDS,
        "limitations": [
            "Trust Score is a screening and review-support score, not a proof of scientific correctness.",
            "NOT_FOUND means metadata was not found in configured providers; it does not prove that a source is fake.",
            "Relevance depends on extracted report text and available title/abstract metadata.",
        ],
    }
