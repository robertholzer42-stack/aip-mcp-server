"""DVFA score tracking."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from aip.config import ENGAGEMENTS_DIR
from aip.models import DVFAScore, DVFASnapshot, Confidence


def parse_dvfa_from_file(filepath: Path) -> Optional[DVFASnapshot]:
    """Parse DVFA scores from a Scorekeeper output file."""
    if not filepath.exists():
        return None

    text = filepath.read_text(encoding="utf-8")
    scores = []

    # Look for score patterns like "Desirability: 3.5 (M confidence)"
    # or table format "| Desirability | 3.5 | M | Empathy |"
    dimensions = {"Desirability": "D", "Viability": "V", "Feasibility": "F", "Adaptability": "A"}

    for dim_name, dim_code in dimensions.items():
        # Try table format first
        pattern = rf'\|\s*{dim_name}\s*\|\s*([\d.]+)\s*\|\s*([HML])\s*\|'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            score_val = float(match.group(1))
            conf = match.group(2).upper()
            confidence = Confidence(conf)
            scores.append(DVFAScore(
                dimension=dim_code,
                score=score_val,
                confidence=confidence,
                source=dim_name,
            ))
            continue

        # Try prose format
        pattern = rf'{dim_name}[:\s]+(\d+(?:\.\d+)?)\s*(?:\(([HML])|/5)'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            score_val = float(match.group(1))
            conf = match.group(2).upper() if match.group(2) else "M"
            scores.append(DVFAScore(
                dimension=dim_code,
                score=score_val,
                confidence=Confidence(conf),
                source=dim_name,
            ))

    if not scores:
        return None

    overall = sum(s.score for s in scores if s.score) / len([s for s in scores if s.score])
    return DVFASnapshot(scores=scores, overall_score=round(overall, 2))


def get_dvfa_scores(engagement_id: str) -> Optional[DVFASnapshot]:
    """Get current DVFA scores for an engagement."""
    eng_dir = ENGAGEMENTS_DIR / engagement_id

    # Check for final scorekeeper output first
    final = eng_dir / "operations" / "scorekeeper-dvfa-scoring.md"
    if final.exists():
        snapshot = parse_dvfa_from_file(final)
        if snapshot:
            snapshot.is_preliminary = False
            # Check for preliminary to compute delta
            prelim = eng_dir / "operations" / "scorekeeper-preliminary.md"
            if prelim.exists():
                prelim_snapshot = parse_dvfa_from_file(prelim)
                if prelim_snapshot:
                    snapshot.delta_from_preliminary = prelim_snapshot.scores
            return snapshot

    # Fall back to preliminary
    prelim = eng_dir / "operations" / "scorekeeper-preliminary.md"
    if prelim.exists():
        snapshot = parse_dvfa_from_file(prelim)
        if snapshot:
            snapshot.is_preliminary = True
            return snapshot

    return None
