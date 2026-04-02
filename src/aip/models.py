"""Pydantic data models for the AIP MCP server."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# --- Enums ---

class Depth(str, Enum):
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"


class Tier(int, Enum):
    CLIENT = 1
    CORE = 2
    INTERSECTION = 3
    OPERATIONAL = 4
    QA = 45  # 4.5 stored as int
    ORCHESTRATION = 5


class Confidence(str, Enum):
    HIGH = "H"
    MEDIUM = "M"
    LOW = "L"


class CriticVerdict(str, Enum):
    PASS = "PASS"
    REVISE = "REVISE"
    FLAG = "FLAG"


class TechChoice(str, Enum):
    AUTO = "auto"
    REACT = "react"
    STATIC = "static"


# --- Agent ---

class AgentInfo(BaseModel):
    codename: str
    tier: int
    tier_name: str
    role: str
    frameworks: List[str] = Field(default_factory=list)
    category: str = ""
    version: str = "1.0"


# --- DVFA ---

class DVFAScore(BaseModel):
    dimension: str  # D, V, F, A
    score: Optional[float] = None
    confidence: Optional[Confidence] = None
    source: str = ""
    evidence: List[str] = Field(default_factory=list)


class DVFASnapshot(BaseModel):
    scores: List[DVFAScore] = Field(default_factory=list)
    is_preliminary: bool = True
    delta_from_preliminary: Optional[List[DVFAScore]] = None
    overall_score: Optional[float] = None


# --- Engagement ---

class CompletedAgent(BaseModel):
    codename: str
    file_path: str
    key_finding: str = ""


class Engagement(BaseModel):
    id: str
    challenge: str
    depth: Depth
    time_horizon: str = ""
    audience: str = ""
    status: str = "created"
    created_at: datetime = Field(default_factory=datetime.now)
    completed_agents: List[CompletedAgent] = Field(default_factory=list)
    current_tier: int = 0
    dvfa: Optional[DVFASnapshot] = None


# --- Checkpoint ---

class Checkpoint(BaseModel):
    engagement_id: str
    tier: int
    session_number: int = 1
    total_sessions: int = 1
    completed_agents: List[CompletedAgent] = Field(default_factory=list)
    dvfa_snapshot: Optional[DVFASnapshot] = None
    tensions: List[str] = Field(default_factory=list)
    next_agents: List[str] = Field(default_factory=list)
    next_stage: str = ""
    key_questions: List[str] = Field(default_factory=list)


# --- Critic ---

class CriterionScore(BaseModel):
    name: str  # Completeness, Evidence Quality, Writing Standards, Integration Readiness
    score: int  # 1-5
    issues: List[str] = Field(default_factory=list)


class CriticReview(BaseModel):
    agent_codename: str
    verdict: CriticVerdict
    scores: List[CriterionScore] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    recommendation: str = ""


# --- Prototyper ---

class PrototypeSpec(BaseModel):
    concept_name: str
    description: str
    features: List[str] = Field(default_factory=list)
    personas: List[str] = Field(default_factory=list)
    tech_choice: TechChoice = TechChoice.AUTO
    source_agent: str = ""
    engagement_id: str = ""


class PrototypeResult(BaseModel):
    prototype_id: str
    engagement_id: str
    concept_name: str
    tech: str  # "react" or "static"
    files: List[str] = Field(default_factory=list)
    run_instructions: str = ""
    created_at: datetime = Field(default_factory=datetime.now)


# --- Pipeline ---

class PipelineStage(BaseModel):
    name: str
    stage_number: int
    agents: List[str]
    parallel: bool = False
    prerequisites: List[str] = Field(default_factory=list)
    description: str = ""
