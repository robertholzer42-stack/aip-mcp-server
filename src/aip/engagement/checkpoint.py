"""Checkpoint read/write."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from aip.config import ENGAGEMENTS_DIR
from aip.models import Checkpoint, CompletedAgent, DVFASnapshot
from aip.engagement.manager import get_completed_agents
from aip.engagement.dvfa import get_dvfa_scores

# Map tier numbers to the agents that should be complete by that tier
TIER_AGENTS = {
    2: ["scout", "empathy", "architect"],
    3: ["visionary", "integrator", "sentinel"],
    4: ["radar", "banker", "scorekeeper", "bridge"],
}

NEXT_STAGE_MAP = {
    2: ("intersection", ["visionary", "integrator", "sentinel"]),
    3: ("operational", ["radar", "banker", "scorekeeper", "bridge"]),
    4: ("orchestration", ["conductor"]),
}


def write_checkpoint(engagement_id: str, tier: int) -> str:
    """Generate and save a checkpoint file. Returns file path."""
    eng_dir = ENGAGEMENTS_DIR / engagement_id
    checkpoint_dir = eng_dir / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    completed = get_completed_agents(engagement_id)
    dvfa = get_dvfa_scores(engagement_id)
    next_stage, next_agents = NEXT_STAGE_MAP.get(tier, ("complete", []))

    # Build checkpoint markdown
    lines = [
        f"## Checkpoint: {engagement_id} -- After Tier {tier}",
        "",
        "### Engagement Context",
        f"- Challenge: {engagement_id.replace('-', ' ').title()}",
        f"- Session: checkpoint after tier {tier}",
        f"- Date: {datetime.now().isoformat()}",
        "",
        "### Completed Agents",
        "| Agent | File | Key Finding |",
        "|-------|------|-------------|",
    ]
    for agent in completed:
        lines.append(f"| {agent.codename} | {agent.file_path} | {agent.key_finding[:80]} |")

    lines.extend(["", "### DVFA Snapshot"])
    if dvfa:
        lines.append("| Dimension | Score | Confidence |")
        lines.append("|-----------|-------|------------|")
        for s in dvfa.scores:
            lines.append(f"| {s.dimension} | {s.score} | {s.confidence.value if s.confidence else 'N/A'} |")
    else:
        lines.append("No DVFA scores available yet.")

    lines.extend([
        "",
        "### Next Session Instructions",
        f"1. Continue from stage: {next_stage}",
        f"2. Agents to run: {', '.join(next_agents)}",
    ])

    content = "\n".join(lines) + "\n"
    filepath = checkpoint_dir / f"checkpoint-tier{tier}.md"
    filepath.write_text(content, encoding="utf-8")
    return str(filepath)


def read_checkpoint(engagement_id: str, tier: int) -> Optional[Checkpoint]:
    """Read and parse a checkpoint file."""
    filepath = ENGAGEMENTS_DIR / engagement_id / "checkpoints" / f"checkpoint-tier{tier}.md"
    if not filepath.exists():
        return None

    completed = get_completed_agents(engagement_id)
    dvfa = get_dvfa_scores(engagement_id)
    next_stage, next_agents = NEXT_STAGE_MAP.get(tier, ("complete", []))

    return Checkpoint(
        engagement_id=engagement_id,
        tier=tier,
        completed_agents=completed,
        dvfa_snapshot=dvfa,
        next_agents=next_agents,
        next_stage=next_stage,
    )
