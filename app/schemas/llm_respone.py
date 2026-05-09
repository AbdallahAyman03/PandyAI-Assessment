from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class Reason(BaseModel):
    type: str = Field(description="The category of the score, e.g., 'must_have_match', 'experience_fit'")
    evidence: str = Field(description="A clear sentence explaining the reason, mentioning specific rescued skills if applicable.")
    weight: float = Field(description="The mathematical weight added or subtracted from the total score.")

class SkillGaps(BaseModel):
    mustHave: List[str]
    niceToHave: List[str]

class Insights(BaseModel):
    strengths: List[str]
    skillGaps: SkillGaps
    recommendedNextSteps: List[str] = Field(description="Highly technical, actionable project steps to close the skill gap.")

class CandidateEvaluation(BaseModel):
    score: float = Field(description="Final calculated score out of 100. MUST equal the sum of all reason weights.")
    matchedSkills: List[str]
    missingMustHaveSkills: List[str]
    missingNiceToHaveSkills: List[str]
    reasons: List[Reason]
    summary: str = Field(default="Fit evaluated by LLM.", description="A 1-2 sentence summary of the candidate's fit.")
    insights: Optional[Insights] = Field(default=None, description="Insights about strengths and gaps.")

class LLMRerankResponse(BaseModel):
    evaluations: Dict[str, CandidateEvaluation] = Field(
        description="A dictionary where the key is the exact Candidate ID (e.g., 'c-001'), and the value is their evaluation."
    )