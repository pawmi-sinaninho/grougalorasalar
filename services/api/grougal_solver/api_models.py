from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class CreateAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schemaVersion: Literal["0.6.0", "0.7.0", "0.8.0"] = "0.8.0"
    locale: Literal["fr", "de", "en"] = "fr"
    retentionConsent: Literal["ephemeral_only"] = "ephemeral_only"
    qualityImprovementConsent: bool = False
    initialFight: dict[str, Any] | None = None


class SolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schemaVersion: Literal["0.6.0", "0.7.0", "0.8.0"] = "0.8.0"
    expectedStateVersion: int = Field(ge=0)
    mode: Literal["authoritative", "review"] = "review"
    confirmedSingleSourceRuleIds: list[str] = []
    maxAlternatives: int = Field(default=2, ge=0, le=2)
