"""Agent registry: parses SKILL.md files and provides lookup functions."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

from aip.config import SKILLS_DIR
from aip.models import AgentInfo, Tier

# ---------------------------------------------------------------------------
# Tier mapping: codename -> (Tier enum value, human-readable tier name)
# ---------------------------------------------------------------------------
_TIER_MAP: Dict[str, tuple[int, str]] = {
    "navigator":   (Tier.CLIENT,        "Client"),
    "publisher":   (Tier.CLIENT,        "Client"),
    "scout":       (Tier.CORE,          "Core"),
    "empathy":     (Tier.CORE,          "Core"),
    "architect":   (Tier.CORE,          "Core"),
    "visionary":   (Tier.INTERSECTION,  "Intersection"),
    "integrator":  (Tier.INTERSECTION,  "Intersection"),
    "sentinel":    (Tier.INTERSECTION,  "Intersection"),
    "radar":       (Tier.OPERATIONAL,   "Operational"),
    "banker":      (Tier.OPERATIONAL,   "Operational"),
    "scorekeeper": (Tier.OPERATIONAL,   "Operational"),
    "bridge":      (Tier.OPERATIONAL,   "Operational"),
    "critic":      (Tier.QA,            "QA"),
    "conductor":   (Tier.ORCHESTRATION, "Orchestration"),
}

# Files in the skills directory that are NOT agent SKILL.md files
_SKIP_FILES = {"setup-guide.md", "publisher-design-system.md"}

# ---------------------------------------------------------------------------
# Module-level caches (populated lazily on first access)
# ---------------------------------------------------------------------------
_agents: Dict[str, AgentInfo] = {}
_skills_content: Dict[str, str] = {}
_loaded: bool = False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_skill_file(path: Path) -> AgentInfo | None:
    """Parse a single SKILL.md file and return AgentInfo, or None on failure."""
    text = path.read_text(encoding="utf-8")

    # --- Extract role from the H1 header ---
    # Format: # Role Name - "Codename"
    role_match = re.search(r"^#\s+(.+?)\s*[-\u2013\u2014]\s*", text, re.MULTILINE)
    role = role_match.group(1).strip() if role_match else ""

    # --- Extract codename ---
    codename_match = re.search(
        r"\*\*Codename:\*\*\s*(.+)", text, re.IGNORECASE
    )
    if not codename_match:
        return None
    codename = codename_match.group(1).strip()

    # --- Extract category ---
    cat_match = re.search(r"\*\*Category:\*\*\s*(.+)", text, re.IGNORECASE)
    category = cat_match.group(1).strip() if cat_match else ""

    # --- Extract version ---
    ver_match = re.search(r"\*\*Version:\*\*\s*(.+)", text, re.IGNORECASE)
    version = ver_match.group(1).strip() if ver_match else "1.0"

    # --- Derive tier from codename ---
    key = codename.lower()
    tier_val, tier_name = _TIER_MAP.get(key, (Tier.CORE, "Core"))

    # --- Extract frameworks (look for lines with known framework keywords) ---
    frameworks: List[str] = []
    fw_patterns = [
        r"IFTF",
        r"STEEP",
        r"Design Thinking",
        r"Systems Thinking",
        r"Future Thinking",
        r"Three Horizons",
        r"DVFA",
        r"Causal Loop",
        r"Human-[Cc]entered [Dd]esign",
    ]
    for pat in fw_patterns:
        if re.search(pat, text):
            # Use the pattern itself (cleaned) as the framework name
            frameworks.append(pat.replace(r"\s+", " ").replace("\\", "")
                              .replace("[Cc]", "C").replace("[Dd]", "D"))

    # Store the full markdown content for later retrieval
    _skills_content[key] = text

    return AgentInfo(
        codename=codename,
        tier=int(tier_val),
        tier_name=tier_name,
        role=role,
        frameworks=frameworks,
        category=category,
        version=version,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_agents() -> None:
    """Scan the skills directory, parse all SKILL.md files, populate cache."""
    global _loaded
    _agents.clear()
    _skills_content.clear()

    skills_path = Path(SKILLS_DIR)
    if not skills_path.is_dir():
        _loaded = True
        return

    for md_file in sorted(skills_path.glob("*-SKILL.md")):
        if md_file.name in _SKIP_FILES:
            continue
        agent = _parse_skill_file(md_file)
        if agent is not None:
            _agents[agent.codename.lower()] = agent

    _loaded = True


def _ensure_loaded() -> None:
    """Load agents lazily on first access."""
    if not _loaded:
        load_agents()


def list_agents() -> List[AgentInfo]:
    """Return all registered agents sorted by tier then codename."""
    _ensure_loaded()
    return sorted(_agents.values(), key=lambda a: (a.tier, a.codename.lower()))


def get_agent(codename: str) -> AgentInfo:
    """Get agent metadata by codename (case-insensitive).

    Raises:
        KeyError: If no agent with the given codename is registered.
    """
    _ensure_loaded()
    key = codename.strip().lower()
    if key not in _agents:
        available = ", ".join(sorted(_agents.keys()))
        raise KeyError(
            f"Unknown agent '{codename}'. Available agents: {available}"
        )
    return _agents[key]


def get_skill_content(codename: str) -> str:
    """Return the full markdown content of an agent's SKILL.md file.

    Raises:
        KeyError: If no agent with the given codename is registered.
    """
    _ensure_loaded()
    key = codename.strip().lower()
    if key not in _skills_content:
        available = ", ".join(sorted(_skills_content.keys()))
        raise KeyError(
            f"No skill content for '{codename}'. Available: {available}"
        )
    return _skills_content[key]
