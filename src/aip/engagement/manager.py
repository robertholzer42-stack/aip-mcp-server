"""Manages engagement folder lifecycle."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from aip.config import ENGAGEMENTS_DIR
from aip.models import Engagement, Depth, CompletedAgent

# Tier 2 agents and their expected files
AGENT_FILE_MAP = {
    "navigator": ("intake", "navigator-engagement-brief.md"),
    "scout": ("analysis", "scout-future-thinking.md"),
    "empathy": ("analysis", "empathy-design-thinking.md"),
    "architect": ("analysis", "architect-systems-thinking.md"),
    "visionary": ("synthesis", "visionary-future-design.md"),
    "integrator": ("synthesis", "integrator-design-systems.md"),
    "sentinel": ("synthesis", "sentinel-future-systems.md"),
    "radar": ("operations", "radar-competitive-intel.md"),
    "banker": ("operations", "banker-portfolio-fit.md"),
    "scorekeeper": ("operations", "scorekeeper-dvfa-scoring.md"),
    "bridge": ("operations", "bridge-change-readiness.md"),
    "conductor": ("deliverables", "integrated-strategy.md"),
    "publisher": ("deliverables", "executive-summary.md"),
    "critic": ("reviews", "critic-review.md"),
}


def _slugify(text: str) -> str:
    """Convert challenge text to folder-safe slug."""
    slug = re.sub(r'[^\w\s-]', '', text.lower())
    slug = re.sub(r'[\s_]+', '-', slug)
    return slug[:60].strip('-')


def create_engagement(challenge: str, depth: str, time_horizon: str = "", audience: str = "") -> Engagement:
    """Create engagement folder structure and return Engagement model."""
    slug = _slugify(challenge)
    eng_dir = ENGAGEMENTS_DIR / slug

    # Create subdirectories
    for subdir in ["intake", "analysis", "synthesis", "operations", "deliverables", "checkpoints", "reviews", "prototypes"]:
        (eng_dir / subdir).mkdir(parents=True, exist_ok=True)

    engagement = Engagement(
        id=slug,
        challenge=challenge,
        depth=Depth(depth.lower()),
        time_horizon=time_horizon,
        audience=audience,
        status="created",
    )
    return engagement


def list_engagements() -> List[Engagement]:
    """Scan engagements directory and return metadata for each."""
    engagements = []
    if not ENGAGEMENTS_DIR.exists():
        return engagements

    for d in sorted(ENGAGEMENTS_DIR.iterdir()):
        if d.is_dir() and not d.name.startswith('.'):
            eng = Engagement(
                id=d.name,
                challenge=d.name.replace('-', ' ').title(),
                depth=Depth.STANDARD,  # default, could parse from checkpoint
                status="unknown",
            )
            # Determine status by checking completed files
            completed = get_completed_agents(d.name)
            eng.completed_agents = completed
            if len(completed) == 0:
                eng.status = "created"
            elif len(completed) < 14:
                eng.status = "in_progress"
            else:
                eng.status = "complete"
            engagements.append(eng)
    return engagements


def get_completed_agents(engagement_id: str) -> List[CompletedAgent]:
    """Scan engagement folder for completed agent output files."""
    eng_dir = ENGAGEMENTS_DIR / engagement_id
    completed = []

    for codename, (subdir, filename) in AGENT_FILE_MAP.items():
        filepath = eng_dir / subdir / filename
        if filepath.exists() and filepath.stat().st_size > 0:
            # Extract first heading or first non-empty line as key finding
            key_finding = ""
            try:
                text = filepath.read_text(encoding="utf-8")
                for line in text.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        key_finding = line[:120]
                        break
            except Exception:
                pass
            completed.append(CompletedAgent(
                codename=codename,
                file_path=str(filepath.relative_to(ENGAGEMENTS_DIR)),
                key_finding=key_finding,
            ))
    return completed


def write_agent_output(engagement_id: str, agent: str, content: str) -> str:
    """Write agent output to the correct engagement subfolder. Returns file path."""
    agent_lower = agent.lower()
    if agent_lower not in AGENT_FILE_MAP:
        raise ValueError(f"Unknown agent: {agent}. Valid: {list(AGENT_FILE_MAP.keys())}")

    subdir, filename = AGENT_FILE_MAP[agent_lower]
    eng_dir = ENGAGEMENTS_DIR / engagement_id
    filepath = eng_dir / subdir / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content, encoding="utf-8")
    return str(filepath)


def get_engagement_dir(engagement_id: str) -> Path:
    """Return the path to an engagement directory."""
    return ENGAGEMENTS_DIR / engagement_id
