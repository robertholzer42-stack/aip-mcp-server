from __future__ import annotations
import re
from pathlib import Path
from typing import Optional, List
from aip.config import ENGAGEMENTS_DIR
from aip.models import PrototypeSpec, TechChoice


def extract_from_visionary(engagement_id: str, concept_index: int = 0) -> Optional[PrototypeSpec]:
    """Extract a prototype spec from Visionary's speculative design brief."""
    eng_dir = ENGAGEMENTS_DIR / engagement_id
    visionary_file = eng_dir / "synthesis" / "visionary-future-design.md"

    if not visionary_file.exists():
        return None

    text = visionary_file.read_text(encoding="utf-8")

    # Parse concept name from headings (look for ## sections about concepts)
    concepts = []
    current_concept = None
    current_text = []

    for line in text.split("\n"):
        # Look for concept headings (## Concept, ## Speculative Design, ## Artifact)
        if re.match(r'^##\s+(?:Concept|Speculative|Artifact|Design Brief)', line, re.IGNORECASE):
            if current_concept:
                concepts.append((current_concept, "\n".join(current_text)))
            current_concept = line.lstrip("# ").strip()
            current_text = []
        elif current_concept:
            current_text.append(line)

    if current_concept:
        concepts.append((current_concept, "\n".join(current_text)))

    # If no structured concepts found, treat the whole file as one concept
    if not concepts:
        # Extract title from first H1 or H2
        title_match = re.search(r'^#\s+(.+)', text, re.MULTILINE)
        title = title_match.group(1) if title_match else "Innovation Prototype"
        concepts = [(title, text)]

    if concept_index >= len(concepts):
        concept_index = 0

    name, description = concepts[concept_index]

    # Extract features (look for bullet lists)
    features = []
    for match in re.finditer(r'^[-*]\s+(.+)', description, re.MULTILINE):
        feature = match.group(1).strip()
        if len(feature) > 10 and len(feature) < 200:
            features.append(feature)
    features = features[:8]  # Cap at 8 features

    # Extract personas (look for persona references)
    personas = []
    for match in re.finditer(r'(?:persona|user|stakeholder)[:\s]+([^.\n]+)', description, re.IGNORECASE):
        personas.append(match.group(1).strip())
    personas = personas[:4]

    # Determine tech choice based on complexity
    tech = TechChoice.AUTO
    if len(features) <= 3:
        tech = TechChoice.STATIC
    elif len(features) > 5:
        tech = TechChoice.REACT

    return PrototypeSpec(
        concept_name=name,
        description=description[:2000],
        features=features,
        personas=personas,
        tech_choice=tech,
        source_agent="visionary",
        engagement_id=engagement_id,
    )


def extract_from_publisher(engagement_id: str) -> Optional[PrototypeSpec]:
    """Extract spec from Publisher one-pager or integrated strategy."""
    eng_dir = ENGAGEMENTS_DIR / engagement_id

    # Try integrated strategy first, then any deliverable
    for filename in ["integrated-strategy.md", "executive-summary.md"]:
        filepath = eng_dir / "deliverables" / filename
        if filepath.exists():
            text = filepath.read_text(encoding="utf-8")
            title_match = re.search(r'^#\s+(.+)', text, re.MULTILINE)
            title = title_match.group(1) if title_match else "Innovation Prototype"

            features = []
            for match in re.finditer(r'^[-*]\s+(.+)', text, re.MULTILINE):
                feature = match.group(1).strip()
                if len(feature) > 10:
                    features.append(feature)

            return PrototypeSpec(
                concept_name=title,
                description=text[:2000],
                features=features[:8],
                tech_choice=TechChoice.REACT if len(features) > 3 else TechChoice.STATIC,
                source_agent="publisher",
                engagement_id=engagement_id,
            )
    return None


def extract_spec(engagement_id: str, source_agent: str = "visionary", concept_index: int = 0) -> Optional[PrototypeSpec]:
    """Main entry point: extract a prototype spec from the specified agent's output."""
    if source_agent.lower() == "visionary":
        return extract_from_visionary(engagement_id, concept_index)
    elif source_agent.lower() in ("publisher", "conductor"):
        return extract_from_publisher(engagement_id)
    else:
        # Try visionary first, fall back to publisher
        spec = extract_from_visionary(engagement_id, concept_index)
        if spec is None:
            spec = extract_from_publisher(engagement_id)
        return spec
