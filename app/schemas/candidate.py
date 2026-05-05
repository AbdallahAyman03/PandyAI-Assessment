from typing import List, Optional, Any
from pydantic import BaseModel, field_validator, model_validator
from app.utils.skill_normalization import normalize_skills_list

class Note(BaseModel):
    date: str
    text: str

class Experience(BaseModel):
    company: str
    title: str
    start: str
    end: str
    highlights: List[str]

class Project(BaseModel):
    name: str
    description: str
    tech: List[str]

class Links(BaseModel):
    portfolio: Optional[str] = None
    github: Optional[str] = None
    linkedin: Optional[str] = None

class Candidate(BaseModel):
    id: str
    fullName: str
    headline: str
    location: str
    yearsOfExperience: float
    skills: List[str]
    availability: str
    updatedAt: str
    status: str
    score: float

    availabilityDays: int = 90 

    # OPTIONAL
    summary: Optional[str] = None
    languages: Optional[List[str]] = None
    education: Optional[str] = None
    links: Optional[Links] = None
    experience: Optional[List[Experience]] = None
    projects: Optional[List[Project]] = None
    notes: Optional[List[Note]] = None
    willingToRelocate: Optional[bool] = True

    @field_validator('skills')
    @classmethod
    def clean_candidate_skills(cls, v: List[str]) -> List[str]:
        return normalize_skills_list(v)

    @model_validator(mode='before')
    @classmethod
    def calculate_availability_days(cls, data: Any) -> Any:
        if isinstance(data, dict):
            avail = str(data.get('availability', '')).lower()
            if 'immediate' in avail:
                data['availabilityDays'] = 0
            elif '1 week' in avail:
                data['availabilityDays'] = 7
            elif '2 week' in avail:
                data['availabilityDays'] = 14
            elif '3 week' in avail:
                data['availabilityDays'] = 21
            elif '1 month' in avail:
                data['availabilityDays'] = 30
            elif '2 month' in avail:
                data['availabilityDays'] = 60
            else:
                data['availabilityDays'] = 90 # Default high penalty for unknown/long times
        return data