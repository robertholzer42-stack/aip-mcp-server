from __future__ import annotations
from pathlib import Path
from typing import Optional
from aip.agents.registry import get_agent, get_skill_content
from aip.config import ENGAGEMENTS_DIR
from aip.llm.router import complete
from aip.models import Depth

# Map agents to the upstream files they need as context
AGENT_INPUTS = {
    "scout": ["intake/navigator-engagement-brief.md", "analysis/research-foundation.md"],
    "empathy": ["intake/navigator-engagement-brief.md", "analysis/research-foundation.md"],
    "architect": ["intake/navigator-engagement-brief.md", "analysis/research-foundation.md"],
    "visionary": ["analysis/scout-future-thinking.md", "analysis/empathy-design-thinking.md"],
    "integrator": ["analysis/empathy-design-thinking.md", "analysis/architect-systems-thinking.md"],
    "sentinel": ["analysis/scout-future-thinking.md", "analysis/architect-systems-thinking.md"],
    "radar": ["intake/navigator-engagement-brief.md", "analysis/research-foundation.md"],
    "banker": ["intake/navigator-engagement-brief.md"],
    "scorekeeper": ["analysis/scout-future-thinking.md", "analysis/empathy-design-thinking.md", "analysis/architect-systems-thinking.md"],
    "bridge": ["analysis/empathy-design-thinking.md", "synthesis/integrator-design-systems.md"],
    "conductor": [],  # Reads everything
    "publisher": ["deliverables/integrated-strategy.md"],
    "critic": [],  # Dynamic, based on tier
    "navigator": [],  # First agent, no upstream
}

def _read_file_if_exists(path: Path) -> Optional[str]:
    """Read a file's content if it exists, return None otherwise."""
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None

def _collect_upstream(engagement_id: str, agent: str) -> str:
    """Collect upstream agent outputs as context."""
    eng_dir = ENGAGEMENTS_DIR / engagement_id
    inputs = AGENT_INPUTS.get(agent.lower(), [])

    # Special case: conductor reads all available outputs
    if agent.lower() == "conductor":
        parts = []
        for subdir in ["analysis", "synthesis", "operations"]:
            subdir_path = eng_dir / subdir
            if subdir_path.exists():
                for f in sorted(subdir_path.glob("*.md")):
                    content = f.read_text(encoding="utf-8")
                    parts.append(f"--- {f.name} ---\n{content}")
        return "\n\n".join(parts)

    parts = []
    for relpath in inputs:
        filepath = eng_dir / relpath
        content = _read_file_if_exists(filepath)
        if content:
            parts.append(f"--- {relpath} ---\n{content}")
    return "\n\n".join(parts)

def construct_prompt(agent: str, engagement_id: str, depth: str = "standard") -> str:
    """Build the full prompt for running an agent."""
    skill_content = get_skill_content(agent)
    upstream = _collect_upstream(engagement_id, agent)

    # Read engagement brief for context
    eng_dir = ENGAGEMENTS_DIR / engagement_id
    brief = _read_file_if_exists(eng_dir / "intake" / "navigator-engagement-brief.md") or ""

    prompt_parts = [
        "You are operating as an agent in the Applied Innovation Platform.",
        f"Run this analysis at {depth.upper()} depth.",
        "",
        "## Your Agent Skill",
        skill_content,
        "",
    ]

    if brief:
        prompt_parts.extend([
            "## Engagement Brief",
            brief,
            "",
        ])

    if upstream:
        prompt_parts.extend([
            "## Upstream Agent Outputs (read these before starting your analysis)",
            upstream,
            "",
        ])

    prompt_parts.extend([
        "## Instructions",
        f"Produce your full {agent} analysis following the framework in your skill above.",
        f"Run at {depth.upper()} tier depth.",
        "Include the structured handoff block at the end of your output.",
        "Follow all quality standards and writing rules specified in your skill.",
    ])

    return "\n".join(prompt_parts)

async def run_agent(engagement_id: str, agent: str, depth: str = "standard") -> str:
    """Run an agent and return the output."""
    prompt = construct_prompt(agent, engagement_id, depth)
    system = "You are a specialized innovation analysis agent. Follow the skill instructions precisely."
    output = await complete(prompt, system=system, max_tokens=8192)
    return output
