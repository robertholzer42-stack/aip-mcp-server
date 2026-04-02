from __future__ import annotations
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from aip.config import ENGAGEMENTS_DIR
from aip.llm.router import complete
from aip.models import PrototypeSpec, PrototypeResult, TechChoice
from aip.prototyper.spec_builder import extract_spec


# Template directories
_TEMPLATES_DIR = Path(__file__).parent / "templates"


def _slugify(text: str) -> str:
    import re
    slug = re.sub(r'[^\w\s-]', '', text.lower())
    return re.sub(r'[\s_]+', '-', slug)[:40].strip('-')


def _get_prototype_dir(engagement_id: str, concept_name: str) -> Path:
    slug = _slugify(concept_name)
    return ENGAGEMENTS_DIR / engagement_id / "prototypes" / slug


def _resolve_tech(spec: PrototypeSpec) -> str:
    """Resolve 'auto' tech choice to concrete type."""
    if spec.tech_choice == TechChoice.REACT:
        return "react"
    elif spec.tech_choice == TechChoice.STATIC:
        return "static"
    else:  # AUTO
        return "react" if len(spec.features) > 3 else "static"


async def generate_prototype(
    engagement_id: str,
    source_agent: str = "visionary",
    concept_index: int = 0,
    tech: str = "auto",
    feedback: str = "",
) -> PrototypeResult:
    """Generate a working web prototype from an agent's design brief."""

    # Extract spec
    spec = extract_spec(engagement_id, source_agent, concept_index)
    if spec is None:
        raise ValueError(f"No prototype spec found for engagement '{engagement_id}' from agent '{source_agent}'")

    if tech != "auto":
        spec.tech_choice = TechChoice(tech)

    resolved_tech = _resolve_tech(spec)
    proto_dir = _get_prototype_dir(engagement_id, spec.concept_name)
    proto_dir.mkdir(parents=True, exist_ok=True)

    # Save the spec
    spec_file = proto_dir / "prototype-spec.json"
    spec_file.write_text(spec.model_dump_json(indent=2), encoding="utf-8")

    # Generate the prototype via LLM
    if resolved_tech == "react":
        files = await _generate_react(spec, proto_dir, feedback)
        run_instructions = f"cd {proto_dir}\nnpm install\nnpm run dev"
    else:
        files = await _generate_static(spec, proto_dir, feedback)
        run_instructions = f"open {proto_dir / 'index.html'}"

    result = PrototypeResult(
        prototype_id=_slugify(spec.concept_name),
        engagement_id=engagement_id,
        concept_name=spec.concept_name,
        tech=resolved_tech,
        files=[str(f.relative_to(proto_dir)) for f in files],
        run_instructions=run_instructions,
    )

    # Save result metadata
    meta_file = proto_dir / "prototype-meta.json"
    meta_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")

    return result


async def _generate_react(spec: PrototypeSpec, proto_dir: Path, feedback: str = "") -> List[Path]:
    """Generate a React + Vite + Tailwind prototype."""

    prompt = f"""Generate a complete React + Vite + Tailwind CSS web application prototype.

## Concept
Name: {spec.concept_name}
Description: {spec.description[:1500]}

## Features to implement:
{chr(10).join(f"- {f}" for f in spec.features)}

## Target users:
{chr(10).join(f"- {p}" for p in spec.personas) if spec.personas else "- General users"}

{"## Iteration feedback: " + feedback if feedback else ""}

## Requirements:
- Generate these files: package.json, vite.config.js, index.html, src/main.jsx, src/App.jsx, src/index.css
- Use React 18+ with Vite as bundler
- Use Tailwind CSS for styling (via CDN in index.html or PostCSS config)
- Make it visually polished: good typography, spacing, color scheme
- Include realistic placeholder content based on the concept
- Make it functional: buttons should do things, forms should validate, dashboards should show data
- Use a modern, professional design with a clean color palette

## Output format:
For each file, output:
```filename.ext
[file contents]
```

Generate ALL files needed for a complete, runnable prototype."""

    system = "You are a senior frontend developer. Generate clean, production-quality React code."
    response = await complete(prompt, system=system, max_tokens=8192)

    return _parse_and_write_files(response, proto_dir)


async def _generate_static(spec: PrototypeSpec, proto_dir: Path, feedback: str = "") -> List[Path]:
    """Generate a static HTML + Tailwind prototype."""

    prompt = f"""Generate a complete single-page HTML prototype with Tailwind CSS.

## Concept
Name: {spec.concept_name}
Description: {spec.description[:1500]}

## Features to implement:
{chr(10).join(f"- {f}" for f in spec.features)}

## Target users:
{chr(10).join(f"- {p}" for p in spec.personas) if spec.personas else "- General users"}

{"## Iteration feedback: " + feedback if feedback else ""}

## Requirements:
- Generate a single index.html file
- Use Tailwind CSS via CDN (<script src="https://cdn.tailwindcss.com"></script>)
- Make it visually polished: good typography, spacing, color scheme
- Include realistic placeholder content based on the concept
- Make interactive elements work with vanilla JavaScript
- Responsive design (mobile + desktop)
- Professional, modern look

## Output format:
```index.html
[complete HTML file]
```"""

    system = "You are a senior frontend developer. Generate clean, polished HTML with Tailwind CSS."
    response = await complete(prompt, system=system, max_tokens=8192)

    return _parse_and_write_files(response, proto_dir)


def _parse_and_write_files(llm_output: str, proto_dir: Path) -> List[Path]:
    """Parse LLM output for code blocks and write files."""
    import re

    files_written = []
    # Match ```filename.ext followed by content followed by ```
    pattern = r'```(\S+)\n(.*?)```'
    matches = re.findall(pattern, llm_output, re.DOTALL)

    for filename, content in matches:
        # Skip if filename looks like a language hint (js, html, css, jsx, etc.)
        if '.' not in filename and filename.lower() in ('javascript', 'html', 'css', 'jsx', 'json', 'typescript', 'tsx'):
            continue

        filepath = proto_dir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content.strip() + "\n", encoding="utf-8")
        files_written.append(filepath)

    # If no files parsed (LLM didn't follow format), write the whole output as index.html
    if not files_written:
        filepath = proto_dir / "index.html"
        # Try to extract HTML content
        html_match = re.search(r'<!DOCTYPE html>.*</html>', llm_output, re.DOTALL | re.IGNORECASE)
        if html_match:
            filepath.write_text(html_match.group(0) + "\n", encoding="utf-8")
        else:
            filepath.write_text(llm_output, encoding="utf-8")
        files_written.append(filepath)

    return files_written


def list_prototypes(engagement_id: str) -> List[PrototypeResult]:
    """List all prototypes for an engagement."""
    proto_dir = ENGAGEMENTS_DIR / engagement_id / "prototypes"
    if not proto_dir.exists():
        return []

    results = []
    for meta_file in proto_dir.glob("*/prototype-meta.json"):
        try:
            data = json.loads(meta_file.read_text(encoding="utf-8"))
            results.append(PrototypeResult(**data))
        except Exception:
            continue
    return results


def get_prototype_spec(engagement_id: str, prototype_id: str) -> Optional[PrototypeSpec]:
    """Get the spec used to generate a prototype."""
    spec_file = ENGAGEMENTS_DIR / engagement_id / "prototypes" / prototype_id / "prototype-spec.json"
    if not spec_file.exists():
        return None
    try:
        data = json.loads(spec_file.read_text(encoding="utf-8"))
        return PrototypeSpec(**data)
    except Exception:
        return None


def preview_prototype(engagement_id: str, prototype_id: str) -> Optional[dict]:
    """Get preview info for a prototype."""
    proto_dir = ENGAGEMENTS_DIR / engagement_id / "prototypes" / prototype_id
    if not proto_dir.exists():
        return None

    meta_file = proto_dir / "prototype-meta.json"
    if meta_file.exists():
        result = PrototypeResult(**json.loads(meta_file.read_text(encoding="utf-8")))
        # List actual files on disk
        actual_files = [str(f.relative_to(proto_dir)) for f in proto_dir.rglob("*") if f.is_file() and f.name not in ("prototype-spec.json", "prototype-meta.json")]
        return {
            "prototype_id": result.prototype_id,
            "concept_name": result.concept_name,
            "tech": result.tech,
            "files": actual_files,
            "run_instructions": result.run_instructions,
            "directory": str(proto_dir),
        }
    return None
