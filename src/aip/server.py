"""Applied Innovation Platform — MCP Server.

Registers all 17 tools for the AIP and runs via stdio transport.
"""
from __future__ import annotations

import asyncio
import json
import traceback

from mcp.server.fastmcp import FastMCP

from aip.agents.registry import (
    get_agent,
    get_skill_content,
    list_agents as _list_agents,
    load_agents,
)
from aip.agents.runner import run_agent as _run_agent
from aip.config import ENGAGEMENTS_DIR, SKILLS_DIR
from aip.engagement.checkpoint import (
    read_checkpoint as _read_checkpoint,
    write_checkpoint as _write_checkpoint,
)
from aip.engagement.dvfa import get_dvfa_scores as _get_dvfa_scores
from aip.engagement.manager import (
    create_engagement as _create_engagement,
    get_completed_agents,
    list_engagements as _list_engagements,
    write_agent_output as _write_agent_output,
)
from aip.engagement.pipeline import (
    STAGES,
    get_stage,
    get_stage_agents,
    get_stages,
)
from aip.llm.router import get_active_model
from aip.models import Depth

# ---------------------------------------------------------------------------
# Bootstrap: load agent registry on import
# ---------------------------------------------------------------------------
load_agents()

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------
mcp = FastMCP("Applied Innovation Platform")


# ===========================================================================
# PLATFORM TOOLS (3)
# ===========================================================================


@mcp.tool()
async def list_agents() -> str:
    """List all 14 AIP agents with metadata (codename, tier, role, frameworks)."""
    try:
        agents = _list_agents()
        return json.dumps([a.model_dump() for a in agents], indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def get_agent_skill(agent: str) -> str:
    """Return the full SKILL.md content for an agent by codename."""
    try:
        return get_skill_content(agent)
    except KeyError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def get_platform_status() -> str:
    """Return platform status: agent count, engagement count, active LLM model."""
    try:
        agents = _list_agents()
        engagements = _list_engagements()
        model = get_active_model()
        return json.dumps({
            "agent_count": len(agents),
            "engagement_count": len(engagements),
            "active_model": model,
            "skills_dir": str(SKILLS_DIR),
            "engagements_dir": str(ENGAGEMENTS_DIR),
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ===========================================================================
# ENGAGEMENT LIFECYCLE (5)
# ===========================================================================


@mcp.tool()
async def create_engagement(
    challenge: str,
    depth: str = "standard",
    time_horizon: str = "",
    audience: str = "",
) -> str:
    """Create a new innovation engagement. Returns engagement metadata."""
    try:
        eng = _create_engagement(challenge, depth, time_horizon, audience)
        return eng.model_dump_json(indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def run_agent(
    engagement_id: str,
    agent: str,
    depth: str = "standard",
) -> str:
    """Run a single agent against an engagement via LLM. Writes output and returns it."""
    try:
        output = await _run_agent(engagement_id, agent, depth)
        filepath = _write_agent_output(engagement_id, agent, output)
        return json.dumps({
            "agent": agent,
            "engagement_id": engagement_id,
            "file": filepath,
            "output_length": len(output),
            "output": output,
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "traceback": traceback.format_exc()})


@mcp.tool()
async def run_stage(
    engagement_id: str,
    stage: str,
    depth: str = "standard",
) -> str:
    """Run all agents for a pipeline stage. Parallel stages run concurrently."""
    try:
        depth_enum = Depth(depth.lower())
        agents, is_parallel = get_stage_agents(stage, depth_enum)
        results = {}

        if is_parallel:
            tasks = [
                _run_agent(engagement_id, a, depth) for a in agents
            ]
            outputs = await asyncio.gather(*tasks, return_exceptions=True)
            for a, out in zip(agents, outputs):
                if isinstance(out, Exception):
                    results[a] = {"status": "error", "error": str(out)}
                else:
                    filepath = _write_agent_output(engagement_id, a, out)
                    results[a] = {"status": "complete", "file": filepath, "length": len(out)}
        else:
            for a in agents:
                try:
                    out = await _run_agent(engagement_id, a, depth)
                    filepath = _write_agent_output(engagement_id, a, out)
                    results[a] = {"status": "complete", "file": filepath, "length": len(out)}
                except Exception as agent_err:
                    results[a] = {"status": "error", "error": str(agent_err)}

        return json.dumps({
            "stage": stage,
            "parallel": is_parallel,
            "agents": results,
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "traceback": traceback.format_exc()})


@mcp.tool()
async def write_agent_output(
    engagement_id: str,
    agent: str,
    content: str,
) -> str:
    """Manually write agent output to the engagement folder."""
    try:
        filepath = _write_agent_output(engagement_id, agent, content)
        return json.dumps({"status": "written", "file": filepath})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def get_engagement_status(engagement_id: str) -> str:
    """Return completed agents, current tier, and pending work for an engagement."""
    try:
        completed = get_completed_agents(engagement_id)
        completed_names = {a.codename for a in completed}

        # Determine current tier
        tier = 0
        if completed_names & {"scout", "empathy", "architect"}:
            tier = 2
        if completed_names & {"visionary", "integrator", "sentinel"}:
            tier = 3
        if completed_names & {"radar", "banker", "scorekeeper", "bridge"}:
            tier = 4
        if "conductor" in completed_names:
            tier = 5

        # Determine pending agents
        all_agents = {
            "navigator", "scout", "empathy", "architect",
            "visionary", "integrator", "sentinel",
            "radar", "banker", "scorekeeper", "bridge",
            "conductor", "publisher", "critic",
        }
        pending = sorted(all_agents - completed_names)

        dvfa = _get_dvfa_scores(engagement_id)

        return json.dumps({
            "engagement_id": engagement_id,
            "current_tier": tier,
            "completed_count": len(completed),
            "completed_agents": [a.model_dump() for a in completed],
            "pending_agents": pending,
            "dvfa": dvfa.model_dump() if dvfa else None,
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ===========================================================================
# PIPELINE (3)
# ===========================================================================


@mcp.tool()
async def run_full_pipeline(
    engagement_id: str,
    depth: str = "standard",
) -> str:
    """Run the entire innovation pipeline end-to-end for an engagement."""
    try:
        depth_enum = Depth(depth.lower())
        stages = get_stages(depth_enum)
        stage_results = {}

        # Track tier boundaries for checkpoints
        tier_stages = {
            "core_analysis": 2,
            "intersection": 3,
            "operational": 4,
        }
        critic_stages = {"critic_tier2", "critic_tier3", "critic_tier4"}

        for stage_def in stages:
            agents, is_parallel = get_stage_agents(stage_def.name, depth_enum)

            agent_results = {}
            if is_parallel:
                tasks = [_run_agent(engagement_id, a, depth) for a in agents]
                outputs = await asyncio.gather(*tasks, return_exceptions=True)
                for a, out in zip(agents, outputs):
                    if isinstance(out, Exception):
                        agent_results[a] = {"status": "error", "error": str(out)}
                    else:
                        filepath = _write_agent_output(engagement_id, a, out)
                        agent_results[a] = {"status": "complete", "file": filepath}
            else:
                for a in agents:
                    try:
                        out = await _run_agent(engagement_id, a, depth)
                        filepath = _write_agent_output(engagement_id, a, out)
                        agent_results[a] = {"status": "complete", "file": filepath}
                    except Exception as agent_err:
                        agent_results[a] = {"status": "error", "error": str(agent_err)}

            stage_results[stage_def.name] = {
                "stage_number": stage_def.stage_number,
                "agents": agent_results,
            }

            # Write checkpoint at tier boundaries
            if stage_def.name in tier_stages:
                tier_num = tier_stages[stage_def.name]
                _write_checkpoint(engagement_id, tier_num)

        return json.dumps({
            "engagement_id": engagement_id,
            "depth": depth,
            "stages_run": len(stage_results),
            "stages": stage_results,
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "traceback": traceback.format_exc()})


@mcp.tool()
async def run_critic_review(engagement_id: str, tier: int) -> str:
    """Run the Critic agent to review a completed tier's outputs."""
    try:
        output = await _run_agent(engagement_id, "critic", "standard")
        filepath = _write_agent_output(engagement_id, "critic", output)
        return json.dumps({
            "engagement_id": engagement_id,
            "tier_reviewed": tier,
            "file": filepath,
            "output": output,
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "traceback": traceback.format_exc()})


@mcp.tool()
async def get_dvfa_scores(engagement_id: str) -> str:
    """Return current DVFA (Desirability, Viability, Feasibility, Adaptability) scores."""
    try:
        dvfa = _get_dvfa_scores(engagement_id)
        if dvfa is None:
            return json.dumps({"message": "No DVFA scores available yet for this engagement."})
        return dvfa.model_dump_json(indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ===========================================================================
# CHECKPOINT (2)
# ===========================================================================


@mcp.tool()
async def write_checkpoint(engagement_id: str, tier: int) -> str:
    """Save a checkpoint after completing a tier. Used for session resumption."""
    try:
        filepath = _write_checkpoint(engagement_id, tier)
        return json.dumps({"status": "checkpoint_saved", "file": filepath, "tier": tier})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def read_checkpoint(engagement_id: str, tier: int) -> str:
    """Read a checkpoint to resume work from a previous session."""
    try:
        checkpoint = _read_checkpoint(engagement_id, tier)
        if checkpoint is None:
            return json.dumps({"message": f"No checkpoint found for tier {tier}."})
        return checkpoint.model_dump_json(indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ===========================================================================
# PROTOTYPER (4) — stubs until generator module is built
# ===========================================================================


@mcp.tool()
async def generate_prototype(
    engagement_id: str,
    source_agent: str = "visionary",
    concept_index: int = 0,
    tech: str = "auto",
) -> str:
    """Generate a working prototype from an agent's concept output."""
    try:
        from aip.prototyper.generator import generate_prototype as _gen
        result = await _gen(engagement_id, source_agent, concept_index, tech)
        return result.model_dump_json(indent=2)
    except ImportError:
        return json.dumps({
            "status": "not_configured",
            "message": "Prototyper not yet configured. The aip.prototyper.generator module needs to be built.",
        })
    except Exception as e:
        return json.dumps({"error": str(e), "traceback": traceback.format_exc()})


@mcp.tool()
async def list_prototypes(engagement_id: str) -> str:
    """List all prototypes generated for an engagement."""
    try:
        from aip.prototyper.generator import list_prototypes as _list_proto
        protos = _list_proto(engagement_id)
        return json.dumps([p.model_dump() for p in protos], indent=2, default=str)
    except ImportError:
        return json.dumps({
            "status": "not_configured",
            "message": "Prototyper not yet configured. The aip.prototyper.generator module needs to be built.",
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def get_prototype_spec(engagement_id: str, prototype_id: str) -> str:
    """Return the spec used to generate a specific prototype."""
    try:
        from aip.prototyper.generator import get_prototype_spec as _get_spec
        spec = _get_spec(engagement_id, prototype_id)
        return spec.model_dump_json(indent=2)
    except ImportError:
        return json.dumps({
            "status": "not_configured",
            "message": "Prototyper not yet configured. The aip.prototyper.generator module needs to be built.",
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def preview_prototype(engagement_id: str, prototype_id: str) -> str:
    """Return prototype files and run instructions for previewing."""
    try:
        from aip.prototyper.generator import preview_prototype as _preview
        result = _preview(engagement_id, prototype_id)
        return json.dumps(result, indent=2)
    except ImportError:
        return json.dumps({
            "status": "not_configured",
            "message": "Prototyper not yet configured. The aip.prototyper.generator module needs to be built.",
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == "__main__":
    mcp.run(transport="stdio")
