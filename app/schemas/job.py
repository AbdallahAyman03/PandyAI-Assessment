from typing import List, Optional
from pydantic import BaseModel, field_validator
from app.utils.skill_normalization import normalize_skills_list

class JobRequirements(BaseModel):
    mustHaveSkills: List[str]
    niceToHaveSkills: List[str]
    minYears: float
    
    # OPTIONAL
    location: Optional[str] = None
    remote: Optional[bool] = False

    @field_validator('mustHaveSkills', 'niceToHaveSkills')
    @classmethod
    def clean_job_skills(cls, v: List[str]) -> List[str]:
        return normalize_skills_list(v)

class Job(BaseModel):
    id: str
    title: str
    description: str
    requirements: JobRequirements