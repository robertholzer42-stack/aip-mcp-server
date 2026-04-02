from __future__ import annotations
from typing import List, Tuple
from aip.models import PipelineStage, Depth

# The 11-stage pipeline
STAGES: List[PipelineStage] = [
    PipelineStage(name="intake", stage_number=1, agents=["navigator"], description="Scope the challenge, assess innovation maturity"),
    PipelineStage(name="research_foundation", stage_number=2, agents=["conductor"], description="Shared fact base for all agents"),
    PipelineStage(name="core_analysis", stage_number=3, agents=["scout", "empathy", "architect"], parallel=True, description="Three independent analytical lenses"),
    PipelineStage(name="critic_tier2", stage_number=4, agents=["critic"], prerequisites=["core_analysis"], description="Quality check on core analysis"),
    PipelineStage(name="preliminary_scoring", stage_number=5, agents=["scorekeeper"], prerequisites=["core_analysis"], description="Early DVFA scores"),
    PipelineStage(name="intersection", stage_number=6, agents=["visionary", "integrator", "sentinel"], parallel=True, prerequisites=["core_analysis", "preliminary_scoring"], description="Where the lenses overlap"),
    PipelineStage(name="critic_tier3", stage_number=7, agents=["critic"], prerequisites=["intersection"], description="Quality check on intersection outputs"),
    PipelineStage(name="operational", stage_number=8, agents=["radar", "banker", "bridge", "scorekeeper"], prerequisites=["intersection"], description="Real-world grounding + final DVFA"),
    PipelineStage(name="critic_tier4", stage_number=9, agents=["critic"], prerequisites=["operational"], description="Quality check on operational outputs"),
    PipelineStage(name="orchestration", stage_number=10, agents=["conductor"], prerequisites=["operational"], description="Cross-agent synthesis, conflict resolution"),
    PipelineStage(name="deliverables", stage_number=11, agents=["publisher"], prerequisites=["orchestration"], description="Board-ready artifacts"),
]

# Which stages to skip at each depth
DEPTH_SKIP = {
    Depth.QUICK: {"research_foundation", "critic_tier2", "preliminary_scoring", "intersection", "critic_tier3", "operational", "critic_tier4"},
    Depth.STANDARD: {"critic_tier4"},  # Standard skips the final critic review
    Depth.DEEP: set(),  # Deep runs everything
}

def get_stages(depth: Depth) -> List[PipelineStage]:
    """Return the stages to execute for a given depth."""
    skip = DEPTH_SKIP.get(depth, set())
    return [s for s in STAGES if s.name not in skip]

def get_stage(name: str) -> PipelineStage:
    """Get a specific stage by name."""
    for s in STAGES:
        if s.name == name:
            return s
    raise ValueError(f"Unknown stage: {name}. Valid: {[s.name for s in STAGES]}")

def get_next_stage(current_stage: str, depth: Depth) -> str | None:
    """Determine the next stage after the current one."""
    stages = get_stages(depth)
    for i, s in enumerate(stages):
        if s.name == current_stage and i + 1 < len(stages):
            return stages[i + 1].name
    return None

def get_stage_agents(stage_name: str, depth: Depth) -> Tuple[List[str], bool]:
    """Return (agents, is_parallel) for a stage at given depth."""
    stage = get_stage(stage_name)
    # For quick scans, only run a subset of core agents
    if depth == Depth.QUICK and stage_name == "core_analysis":
        return (["scout", "empathy"], True)  # Skip architect for quick
    return (stage.agents, stage.parallel)
