# AIP MCP Server

MCP server for the [Applied Innovation Platform](https://github.com/robertholzer42-stack/applied-innovation-platform) -- makes 14 AI innovation agents callable as tools from any Claude session, plus a Prototyper that generates working web apps from design briefs.

## What It Does

- **14 agents on demand** -- Call Scout, Empathy, Architect, Conductor, and 10 other agents without setting up a Claude Project
- **Engagement lifecycle** -- Create engagements, run pipeline stages, track DVFA scores, manage checkpoints
- **Model-agnostic** -- Auto-detects Claude, Gemini, GPT-4, or local models (via LiteLLM)
- **Prototyper** -- Generates React/Vite or static HTML prototypes from Visionary's design briefs

## Quick Start

### 1. Prerequisites

- Python 3.10+ (install via `uv python install 3.12` or Homebrew)
- The [applied-innovation-platform](https://github.com/robertholzer42-stack/applied-innovation-platform) repo cloned alongside this one

### 2. Install

```bash
git clone https://github.com/robertholzer42-stack/aip-mcp-server.git
cd aip-mcp-server
uv venv --python 3.12
source .venv/bin/activate
uv pip install mcp[cli] litellm pydantic anthropic uvicorn python-dotenv httpx
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env: set your API key (ANTHROPIC_API_KEY, GOOGLE_API_KEY, etc.)
# Edit .env: set paths to your applied-innovation-platform directory
```

### 4. Register with Claude Code

Add to your project's `.mcp.json` or `~/.claude.json`:

```json
{
  "mcpServers": {
    "aip": {
      "command": "/path/to/aip-mcp-server/.venv/bin/python",
      "args": ["-m", "aip.server"],
      "cwd": "/path/to/aip-mcp-server/src",
      "env": {
        "AIP_SKILLS_DIR": "/path/to/applied-innovation-platform/skills",
        "AIP_ENGAGEMENTS_DIR": "/path/to/applied-innovation-platform/engagements"
      }
    }
  }
}
```

### 5. Use

From any Claude Code session:

```
"List the available innovation agents"
→ Calls list_agents tool

"Create a standard engagement analyzing AI in eldercare for healthcare executives"
→ Calls create_engagement tool

"Run the core analysis stage"
→ Calls run_stage tool

"Generate a prototype from the Visionary's design brief"
→ Calls generate_prototype tool
```

## Tools (17)

### Platform
| Tool | Description |
|------|------------|
| `list_agents` | Returns all 14 agents with codename, tier, role, frameworks |
| `get_agent_skill` | Returns the full SKILL.md content for any agent |
| `get_platform_status` | Agent count, engagement count, active LLM model |

### Engagement Lifecycle
| Tool | Description |
|------|------------|
| `create_engagement` | Creates an engagement with folder structure |
| `run_agent` | Runs a specific agent against an engagement |
| `run_stage` | Runs all agents for a pipeline stage |
| `write_agent_output` | Manually saves agent output to engagement folder |
| `get_engagement_status` | Shows completed agents, current tier, pending work |

### Pipeline
| Tool | Description |
|------|------------|
| `run_full_pipeline` | Orchestrates all 11 stages end-to-end |
| `run_critic_review` | Runs Critic quality review on a completed tier |
| `get_dvfa_scores` | Returns current DVFA scores with confidence and deltas |

### Checkpoints
| Tool | Description |
|------|------------|
| `write_checkpoint` | Saves engagement state for session continuity |
| `read_checkpoint` | Loads checkpoint data to resume in a new session |

### Prototyper
| Tool | Description |
|------|------------|
| `generate_prototype` | Generates a working web prototype from design briefs |
| `list_prototypes` | Lists all prototypes for an engagement |
| `get_prototype_spec` | Returns the spec used to generate a prototype |
| `preview_prototype` | Returns files and run instructions for a prototype |

## Model Support

The server auto-detects your LLM based on environment variables:

| Priority | Env Variable | Model |
|----------|-------------|-------|
| 1 | `AIP_MODEL` | Explicit override (any LiteLLM model string) |
| 2 | `ANTHROPIC_API_KEY` | Claude Sonnet 4 |
| 3 | `GOOGLE_API_KEY` | Gemini 2.0 Flash |
| 4 | `OPENAI_API_KEY` | GPT-4o |
| 5 | `OLLAMA_BASE_URL` | Llama 3 (local) |

## Architecture

```
src/aip/
  server.py          -- MCP server, 17 tool registrations
  config.py          -- Environment-based configuration
  models.py          -- Pydantic data models
  llm/
    router.py        -- Model-agnostic LLM routing
    claude.py        -- Anthropic SDK adapter
    openai_compat.py -- LiteLLM adapter (Gemini, GPT-4, Ollama)
  agents/
    registry.py      -- SKILL.md parser, agent catalog
    runner.py        -- Prompt construction, agent execution
  engagement/
    manager.py       -- Folder lifecycle, agent output I/O
    pipeline.py      -- 11-stage pipeline definitions
    checkpoint.py    -- Session continuity
    dvfa.py          -- DVFA score tracking
  prototyper/
    spec_builder.py  -- Extract specs from agent outputs
    generator.py     -- LLM-powered prototype generation
    templates/       -- React/Vite and static HTML scaffolds
```

## License

Apache License 2.0
