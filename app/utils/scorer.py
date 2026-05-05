import json
import logging
from typing import List, Dict, Any, Set
from app.schemas.candidate import Candidate
from app.schemas.job import Job
from app.settings import config

logging.basicConfig(level=logging.INFO)

def load_action_map() -> Dict[str, str]:
    try:
        with open(config.action_map_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"Action map file not found: {config.action_map_path}")
        return {}

def _generate_candidate_insights(cand_exp: float, req_exp: float, matched_must: Set[str], matched_nice: Set[str], missing_must: List[str], missing_nice: List[str], inferred_must: Set[str] = None) -> Dict[str, Any]:
    strengths = []
    
    if cand_exp >= req_exp and req_exp > 0:
        bonus = cand_exp - req_exp
        if bonus >= 2:
            strengths.append(f"Highly experienced: Brings {cand_exp} years of background, significantly exceeding the {req_exp}-year requirement.")
        else:
            strengths.append(f"Meets the baseline experience requirement with {cand_exp} years of relevant work.")
            
    if matched_must:
        must_str = ", ".join(list(matched_must)[:3])
        strengths.append(f"Strong foundational alignment: Proven capability in core job requirements including {must_str}.")
        
    if inferred_must:
        inf_str = ", ".join(list(inferred_must)[:3])
        strengths.append(f"Demonstrated practical exposure: Evidence of {inf_str} found within project and experience history.")
        
    if matched_nice:
        nice_str = ", ".join(list(matched_nice)[:3])
        strengths.append(f"Provides immediate bonus value with nice-to-have skills like {nice_str}.")

    if not strengths:
        strengths.append("Currently lacks alignment with the core technical stack and experience required for this role.")

    next_steps = []
    action_map = load_action_map()

    if missing_must:
        for skill in missing_must[:2]:
            step = action_map.get(skill.lower(), f"Build a practical proof-of-concept project heavily utilizing {skill}.")
            next_steps.append(f"Critical Gap ({skill.upper()}): {step}")
            
    elif missing_nice:
        for skill in missing_nice[:2]:
            step = action_map.get(skill.lower(), f"Review the official documentation and build a small feature using {skill}.")
            next_steps.append(f"Upskill Opportunity ({skill.upper()}): {step}")
            
    if cand_exp < req_exp:
        shortfall = req_exp - cand_exp
        next_steps.append(f"Experience Gap: Offset the {shortfall}-year shortfall by contributing to relevant open-source repositories or building high-complexity portfolio pieces.")

    return {
        "strengths": strengths,
        "skillGaps": {
            "mustHave": missing_must,
            "niceToHave": missing_nice
        },
        "recommendedNextSteps": next_steps
    }

def _generate_dynamic_summary(final_score: float, req_exp: float, cand_exp: float, missing_must: List[str], matched_nice: Set[str], inferred_count: int) -> str:
    summary_parts = []
    
    if final_score >= 85:
        summary_parts.append("Strong candidate.")
    elif final_score >= 65:
        summary_parts.append("Potential match.")
    else:
        summary_parts.append("Weak fit.")
        
    if req_exp > 0:
        if cand_exp < req_exp:
            summary_parts.append(f"Falls short of the {req_exp}-year requirement ({cand_exp} yrs).")
        elif cand_exp >= req_exp + 2:
            summary_parts.append(f"Highly experienced ({cand_exp} yrs).")
        else:
            summary_parts.append("Meets experience requirements.")
            
    if missing_must:
        missed_str = ", ".join(missing_must[:2])
        if len(missing_must) > 2:
            missed_str += ", etc."
        summary_parts.append(f"Missing core skills: {missed_str}.")
    else:
        if matched_nice:
            nice_list = list(matched_nice)
            nice_str = ", ".join(nice_list[:2])
            summary_parts.append(f"Matches all must-haves, plus bonus skills ({nice_str}).")
        else:
            summary_parts.append("Matches all core must-have requirements.")
            
    if inferred_count > 0:
        summary_parts.append(f"({inferred_count} missing skills were rescued by scanning experience/projects).")
            
    return " ".join(summary_parts)


def score_candidate(candidate: Candidate, job: Job) -> Dict[str, Any]:
    cand_skills = set(candidate.skills)
    job_must = set(job.requirements.mustHaveSkills)
    job_nice = set(job.requirements.niceToHaveSkills)

    text_blocks = [candidate.headline]
    if candidate.summary:
        text_blocks.append(candidate.summary)
    
    if candidate.experience:
        for exp in candidate.experience:
            text_blocks.extend([exp.company, exp.title])
            text_blocks.extend(exp.highlights)
            
    if candidate.projects:
        for proj in candidate.projects:
            text_blocks.extend([proj.name, proj.description])
            text_blocks.extend(proj.tech)
            
    if candidate.notes:
        for note in candidate.notes:
            text_blocks.append(note.text)

    full_context = " ".join(text_blocks).lower()

    explicit_must = cand_skills & job_must
    initial_missing_must = job_must - cand_skills
    inferred_must = set()
    missing_must = []

    for skill in initial_missing_must:
        if skill.lower() in full_context:
            inferred_must.add(skill)
        else:
            missing_must.append(skill)

    explicit_nice = cand_skills & job_nice
    initial_missing_nice = job_nice - cand_skills
    inferred_nice = set()
    missing_nice = []

    for skill in initial_missing_nice:
        if skill.lower() in full_context:
            inferred_nice.add(skill)
        else:
            missing_nice.append(skill)

    reasons = []
    base_score = 0.0

    must_ratio = 1.0
    if job_must:
        must_ratio = (len(explicit_must) + (0.5 * len(inferred_must))) / len(job_must)
    
    must_score = must_ratio * config.weight_must_have
    base_score += must_score
    
    must_evidence = f"Explicitly matched {len(explicit_must)}/{len(job_must)} must-have skills."
    if inferred_must:
        must_evidence += f" Rescued {len(inferred_must)} from text ({', '.join(inferred_must)})."
    if missing_must:
        must_evidence += f" Missing: {', '.join(missing_must)}."
    
    reasons.append({
        "type": "must_have_match",
        "evidence": must_evidence,
        "weight": round(must_score, 2)
    })

    nice_ratio = 1.0
    if job_nice:
        nice_ratio = (len(explicit_nice) + (0.5 * len(inferred_nice))) / len(job_nice)
        
    nice_score = nice_ratio * config.weight_nice_to_have
    base_score += nice_score
    
    nice_evidence = f"Explicitly matched {len(explicit_nice)}/{len(job_nice)} nice-to-have skills."
    if inferred_nice:
        nice_evidence += f" Rescued {len(inferred_nice)} from text ({', '.join(inferred_nice)})."
    if missing_nice:
        nice_evidence += f" Missing: {', '.join(missing_nice)}."
    
    reasons.append({
        "type": "nice_to_have_match",
        "evidence": nice_evidence,
        "weight": round(nice_score, 2)
    })

    req_exp = job.requirements.minYears
    cand_exp = candidate.yearsOfExperience
    exp_score = 0.0

    if cand_exp < req_exp:
        ratio = cand_exp / req_exp
        exp_score = (ratio ** 2) * config.weight_experience
        exp_evidence = f"Candidate has {cand_exp} years, job requires {req_exp}. Exponential penalty applied."
        
    else:
        bonus_years = cand_exp - req_exp
        bonus_points = min(bonus_years * config.exp_bonus_per_year, config.exp_max_bonus)
        exp_score = config.weight_experience + bonus_points
        exp_evidence = f"Candidate meets or exceeds {req_exp} years requirement has {cand_exp} years, (+{round(bonus_points, 1)} bonus points applied)."

    base_score += exp_score
    reasons.append({
        "type": "experience_fit",
        "evidence": exp_evidence,
        "weight": round(exp_score, 2)
    })

    is_remote = job.requirements.remote
    job_loc = job.requirements.location
    cand_loc = candidate.location
    willing_to_relocate = candidate.willingToRelocate
    loc_score = 0.0
    
    weight_loc = config.weight_location

    if is_remote:
        loc_score = weight_loc
        loc_evidence = "Job is remote. Full location points awarded."
        
    elif job_loc and cand_loc and job_loc.lower() == cand_loc.lower():
        loc_score = weight_loc
        loc_evidence = f"Candidate and job both in {job_loc}. Full location points awarded."
        
    elif job_loc and willing_to_relocate:
        loc_score = weight_loc * 0.5
        loc_evidence = f"Candidate is in {cand_loc} but willing to relocate to {job_loc}. Half location points awarded."
        
    elif job_loc:
        loc_score = 0.0
        loc_evidence = f"Candidate is in {cand_loc} and not willing to relocate to {job_loc}. No location points awarded."
        
    else:
        loc_score = weight_loc
        loc_evidence = "Job has no specific location requirements. Full points awarded."

    base_score += loc_score
    reasons.append({
        "type": "location_match",
        "evidence": loc_evidence,
        "weight": round(loc_score, 2)
    })

    final_score = base_score
    if must_ratio < 1.0:
        final_score = base_score * must_ratio
        penalty_amount = base_score - final_score
        reasons.append({
            "type": "must_have_penalty",
            "evidence": f"Missing core must-have skills. Applied {round(must_ratio, 2)}x penalty multiplier.",
            "weight": -round(penalty_amount, 2)
        })

    final_score = min(round(final_score, 2), 100.0)

    total_inferred = len(inferred_must) + len(inferred_nice)
    summary_text = _generate_dynamic_summary(final_score, req_exp, cand_exp, missing_must, explicit_nice | inferred_nice, total_inferred)
    
    insights = _generate_candidate_insights(
        cand_exp=cand_exp,
        req_exp=req_exp,
        matched_must=explicit_must | inferred_must,
        matched_nice=explicit_nice | inferred_nice,
        missing_must=missing_must,
        missing_nice=missing_nice,
        inferred_must=inferred_must
    )

    return {
        "candidateId": candidate.id,
        "candidateName": candidate.fullName, 
        "score": final_score,
        "matchedSkills": list(explicit_must | explicit_nice | inferred_must | inferred_nice),
        "missingMustHaveSkills": missing_must,
        "missingNiceToHaveSkills": missing_nice,
        "reasons": reasons,
        "summary": summary_text,
        "availability": candidate.availability,
        "insights": insights
    }
    
def rank_candidates(candidates: List[Candidate], job: Job, top_k: int = None) -> List[Dict[str, Any]]:
    results = []
    for candidate in candidates:
        score_data = score_candidate(candidate, job)
        
        # Attach temporary sorting keys
        score_data['_must_count'] = len(set(candidate.skills) & set(job.requirements.mustHaveSkills))
        score_data['_nice_count'] = len(set(candidate.skills) & set(job.requirements.niceToHaveSkills))
        score_data['_exp'] = candidate.yearsOfExperience
        score_data['_location'] = candidate.location == job.requirements.location if getattr(job.requirements, 'location', None) else True
        score_data['_availability_days'] = candidate.availabilityDays
        
        results.append(score_data)

    results.sort(
        key=lambda x: (
            x['score'], 
            x['_must_count'], 
            x['_nice_count'], 
            x['_exp'], 
            x['_location'], 
            -x['_availability_days']
        ), 
        reverse=True
    )

    # Clean up the payload before returning
    for res in results:
        del res['_must_count']
        del res['_nice_count']
        del res['_exp']
        del res['_location']
        del res['_availability_days']

    if top_k is not None:
        return results[:top_k]
    
    return results