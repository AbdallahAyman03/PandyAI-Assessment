import json
import logging
from typing import List, Dict, Any
from groq import Groq
from app.settings import config
from app.schemas.job import Job
from app.schemas.candidate import Candidate
from app.schemas.llm_respone import LLMRerankResponse

logging.basicConfig(level=logging.INFO)

def _serialize_for_llm(job: Job, candidates: List[Candidate]) -> tuple[str, str]:
    """Converts Pydantic objects into dense, readable strings for the LLM."""
    
    # 1. Serialize Job
    job_text = f"Job Title: {job.title}\nDescription: {job.description}\n"
    job_text += f"Must-Haves: {', '.join(job.requirements.mustHaveSkills)}\n"
    job_text += f"Nice-to-Haves: {', '.join(job.requirements.niceToHaveSkills)}\n"
    job_text += f"Min Years Required: {job.requirements.minYears}\n"

    # 2. Serialize Candidates
    cands_text = ""
    for c in candidates:
        cands_text += f"\n--- CANDIDATE ID: {c.id} ---\n"
        cands_text += f"Name: {c.fullName}\n"
        cands_text += f"Status: {c.status}\n"
        cands_text += f"Experience: {c.yearsOfExperience} years\n"
        cands_text += f"Reported Skills: {', '.join(c.skills)}\n"
        
        # Build the context payload
        context = [c.headline]
        if c.summary: context.append(c.summary)
        if c.experience:
            for exp in c.experience[:3]:  # Top 3 roles
                context.append(f"Role: {exp.title}. Highlights: {' '.join(exp.highlights)}")
        if c.projects:
            for proj in c.projects[:2]:   # Top 2 projects
                context.append(f"Project: {proj.name}. Tech: {', '.join(proj.tech)}")
                
        cands_text += f"Context: {' | '.join(context)}\n"
    
    return job_text, cands_text
  
  
def generate_ai_rerank_and_insights(job: Job, top_candidates: List[Candidate]) -> Dict[str, Any]:
    if not hasattr(config, 'groq_api_key') or not config.groq_api_key:
        logging.error("No GROQ_API_KEY found. Cannot run LLM Reranker.")
        return {}

    client = Groq(api_key=config.groq_api_key)
    job_text, cands_text = _serialize_for_llm(job, top_candidates)

    # 1. Dynamically extract the JSON schema from Pydantic
    schema_json = json.dumps(LLMRerankResponse.model_json_schema(), indent=2)

    system_prompt = f"""
    You are an expert ATS AI evaluating candidates for a software engineering role.
    You MUST output valid JSON ONLY that exactly matches the following JSON Schema:
    
    {schema_json}

    CRITICAL RULES:
    1. The sum of the "weight" values inside the "reasons" array MUST exactly equal the final "score".
    2. BASE SCORING SYSTEM (Total 100 points):
       - Must-Have Skills: Up to {config.weight_must_have} points total. (Penalize heavily using negative weights if core skills are missing).
       - Experience: Up to {config.weight_experience} points for meeting requirements, with up to {config.exp_max_bonus} bonus points for exceeding them.
       - Nice-to-Have Skills: Up to {config.weight_nice_to_have} points total.
       - Location/Availability: Up to {config.weight_location} points.
    3. Infer skills from their "Context" if they are missing from "Reported Skills".
    4. Ensure the total final "score" is calculated out of 100 based on these limits.
    """

    user_prompt = f"JOB DESCRIPTION:\n{job_text}\n\nCANDIDATES TO EVALUATE:\n{cands_text}"

    try:
        logging.info(f"🚀 Calling Groq API ({config.llm_model}) to evaluate {len(top_candidates)} candidates...")
        response = client.chat.completions.create(
            model=config.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        raw_json = response.choices[0].message.content
        
        # 2. THE MAGIC: Pydantic instantly validates the LLM's raw string 
        # against all your types, lists, and required fields.
        validated_response = LLMRerankResponse.model_validate_json(raw_json)
        
        # 3. Convert it back to a standard Python dictionary for the CLI to use
        return validated_response.model_dump()['evaluations']
        
    except Exception as e:
        logging.error(f"Groq API Error or Validation Failure: {e}")
        return {}