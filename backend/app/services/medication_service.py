"""
Medication catalogue service.
Provides read-only fuzzy search for the agent's verify_medication tool.
Never modifies the medications table.
"""
import re
from sqlalchemy.orm import Session
from app.models.models import Medication


def fuzzy_search(query: str, db: Session, limit: int = 5) -> list[dict]:
    """
    Fuzzy-search the medication catalogue by name or generic_name.
    Returns up to `limit` results sorted by confidence (descending).
    Confidence is a float in [0.0, 1.0].

    This function is purely read-only — it never modifies the medications table.

    Algorithm (SQLite-compatible):
    - Normalise query to lowercase tokens (strip dosage numerics for matching)
    - For each medication, compute token overlap ratio against name + generic_name
    - Exact match (case-insensitive) → confidence 1.0
    """
    if not query or not query.strip():
        return []

    query_norm = query.strip().lower()

    # Strip common dosage parts (e.g. "500mg", "10 mg") to focus on drug name
    query_clean = re.sub(r"\d+\s*m?g\b", "", query_norm).strip()
    query_tokens = set(re.split(r"[\s\-/]+", query_clean)) - {""}

    # Fetch all — catalogue is at most a few hundred rows
    medications = db.query(Medication).all()

    results = []
    for med in medications:
        name_norm = med.name.lower()
        generic_norm = med.generic_name.lower()

        # Exact match
        if query_clean == name_norm or query_clean == generic_norm:
            results.append({"medication": med, "confidence": 1.0})
            continue

        # Substring containment (high confidence)
        if query_clean and (query_clean in name_norm or query_clean in generic_norm):
            results.append({"medication": med, "confidence": 0.9})
            continue

        # Token overlap ratio
        name_tokens = set(re.split(r"[\s\-/]+", name_norm)) - {""}
        generic_tokens = set(re.split(r"[\s\-/]+", generic_norm)) - {""}
        all_med_tokens = name_tokens | generic_tokens

        if not query_tokens or not all_med_tokens:
            continue

        overlap = len(query_tokens & all_med_tokens)
        union = len(query_tokens | all_med_tokens)
        jaccard = overlap / union if union else 0.0

        # Boost if all query tokens appear in the medication tokens
        if query_tokens and query_tokens.issubset(all_med_tokens):
            jaccard = max(jaccard, 0.85)

        # Individual character n-gram similarity for typo tolerance
        # Simple Levenshtein-lite: check if long tokens differ by ≤ 2 chars
        char_score = 0.0
        for qt in query_tokens:
            if len(qt) < 3:
                continue
            for mt in all_med_tokens:
                if len(mt) < 3:
                    continue
                if _char_similarity(qt, mt) >= 0.8:
                    char_score = max(char_score, 0.75)

        confidence = max(jaccard, char_score)
        if confidence >= 0.3:
            results.append({"medication": med, "confidence": round(confidence, 3)})

    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results[:limit]


def _char_similarity(a: str, b: str) -> float:
    """Simple character overlap ratio (not full edit distance) for typo tolerance."""
    if not a or not b:
        return 0.0
    # Count common characters by frequency
    from collections import Counter
    ca, cb = Counter(a), Counter(b)
    common = sum((ca & cb).values())
    return 2 * common / (len(a) + len(b))
