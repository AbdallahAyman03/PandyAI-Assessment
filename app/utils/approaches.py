"""
Approach orchestration module.

Exposes run_approach() and explain_approach() which route to the three engines:

  1. "deterministic"  – Pure O(1) math, no ML dependencies (fastest, purest).
  2. "hybrid"         – 70% deterministic + 30% local semantic via ChromaDB/BGE.
  3. "agentic"        – Hybrid retriever → Groq/Llama-3 LLM re-ranker (deepest).
"""
from typing import List, Dict, Any, Optional

from app.schemas.candidate import Candidate
from app.schemas.job import Job
from app.utils.scorer import rank_candidates, score_candidate

VALID_APPROACHES = ["deterministic", "hybrid", "agentic"]

# Blend weights used for both Hybrid and the retrieval phase of Agentic
_HYBRID_W_DET: float = 0.70
_HYBRID_W_SEM: float = 0.30


# ============================================================
# PUBLIC INTERFACE
# ============================================================

def run_approach(
    approach: str,
    candidates: List[Candidate],
    job: Job,
    top_k: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Route candidates through the chosen analytical engine and return
    a sorted list of score dicts (highest score first).
    """
    approach = approach.lower()
    if approach == "deterministic":
        return _run_deterministic(candidates, job, top_k)
    elif approach == "hybrid":
        return _run_hybrid(candidates, job, top_k)
    elif approach == "agentic":
        return _run_agentic(candidates, job, top_k)
    else:
        raise ValueError(
            f"Unknown approach '{approach}'. "
            f"Choose from: {VALID_APPROACHES}"
        )


def explain_approach(
    approach: str,
    candidate: Candidate,
    job: Job,
    all_candidates: Optional[List[Candidate]] = None,
) -> Dict[str, Any]:
    """
    Return a score + full reasoning dict for a *single* candidate.
    Used by app.explain for the terminal report.

    all_candidates is used by hybrid/agentic to populate ChromaDB with
    the full candidate pool before querying, giving more accurate rankings.
    """
    approach = approach.lower()
    if approach == "deterministic":
        return score_candidate(
            candidate, job,
            semantic_score=0.0,
            weight_deterministic=1.0,
            weight_semantic=0.0,
        )
    elif approach == "hybrid":
        return _explain_hybrid(candidate, job, all_candidates)
    elif approach == "agentic":
        return _explain_agentic(candidate, job, all_candidates)
    else:
        raise ValueError(
            f"Unknown approach '{approach}'. "
            f"Choose from: {VALID_APPROACHES}"
        )


# ============================================================
# APPROACH 1 – DETERMINISTIC
# ============================================================

def _run_deterministic(
    candidates: List[Candidate],
    job: Job,
    top_k: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Pure mathematical scoring. No ML, no external calls."""
    return rank_candidates(
        candidates, job,
        top_k=top_k,
        weight_deterministic=1.0,
        weight_semantic=0.0,
    )


# ============================================================
# APPROACH 2 – HYBRID
# ============================================================

def _run_hybrid(
    candidates: List[Candidate],
    job: Job,
    top_k: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Dense-vector semantic search (ChromaDB + BAAI/bge-small-en-v1.5)
    blended with the deterministic score via a linear weighted sum.
    """
    from app.utils.embedding import index_candidates  # lazy import

    print("  [Hybrid] Ensuring candidates are indexed in ChromaDB...")
    index_candidates(candidates)

    return rank_candidates(
        candidates, job,
        top_k=top_k,
        weight_deterministic=_HYBRID_W_DET,
        weight_semantic=_HYBRID_W_SEM,
    )


def _explain_hybrid(
    candidate: Candidate,
    job: Job,
    all_candidates: Optional[List[Candidate]] = None,
) -> Dict[str, Any]:
    from app.utils.embedding import index_candidates, get_semantic_scores  # lazy

    pool = all_candidates or [candidate]
    print("  [Hybrid] Ensuring candidates are indexed in ChromaDB...")
    index_candidates(pool)

    semantic_scores = get_semantic_scores(job, top_k=len(pool))
    cand_sem = semantic_scores.get(candidate.id, 0.0)

    return score_candidate(
        candidate, job,
        semantic_score=cand_sem,
        weight_deterministic=_HYBRID_W_DET,
        weight_semantic=_HYBRID_W_SEM,
    )


# ============================================================
# APPROACH 3 – AGENTIC RAG
# ============================================================

def _run_agentic(
    candidates: List[Candidate],
    job: Job,
    top_k: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Two-phase pipeline:
      Phase 1 – Hybrid engine retrieves top 2×k candidates.
      Phase 2 – Groq/Llama-3 re-ranks them with narrative reasoning.
    Falls back to hybrid results if the LLM call fails.
    """
    from app.utils.embedding import index_candidates  # lazy
    from app.utils.llm_reranker import generate_ai_rerank_and_insights

    retrieval_k = (top_k * 2) if top_k else len(candidates)

    # Phase 1 – Hybrid retrieval
    print("  [Agentic] Phase 1 – Hybrid retriever running...")
    index_candidates(candidates)
    hybrid_results = rank_candidates(
        candidates, job,
        top_k=retrieval_k,
        weight_deterministic=_HYBRID_W_DET,
        weight_semantic=_HYBRID_W_SEM,
    )

    top_ids = {r["candidateId"] for r in hybrid_results}
    top_candidates = [c for c in candidates if c.id in top_ids]

    # Phase 2 – LLM re-ranker
    print(
        f"  [Agentic] Phase 2 – Groq LLM evaluating "
        f"{len(top_candidates)} candidates..."
    )
    llm_evals = generate_ai_rerank_and_insights(job, top_candidates)

    if not llm_evals:
        print(
            "  [Agentic] LLM returned no evaluations. "
            "Falling back to Hybrid results."
        )
        return hybrid_results[:top_k] if top_k else hybrid_results

    # Phase 3 – Merge into standard result format and re-sort by LLM score
    id_to_cand = {c.id: c for c in top_candidates}
    results: List[Dict[str, Any]] = []

    for cid, eval_data in llm_evals.items():
        cand = id_to_cand.get(cid)
        if not cand:
            continue
        results.append({
            "candidateId": cid,
            "candidateName": cand.fullName,
            "score": eval_data["score"],
            "matchedSkills": eval_data["matchedSkills"],
            "missingMustHaveSkills": eval_data["missingMustHaveSkills"],
            "missingNiceToHaveSkills": eval_data["missingNiceToHaveSkills"],
            "reasons": eval_data["reasons"],
            "summary": eval_data["summary"],
            "availability": cand.availability,
            "insights": eval_data["insights"],
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k] if top_k else results


def _explain_agentic(
    candidate: Candidate,
    job: Job,
    all_candidates: Optional[List[Candidate]] = None,
) -> Dict[str, Any]:
    """
    Deep single-candidate explanation via the LLM.
    Falls back to Hybrid if the LLM call fails.
    """
    from app.utils.embedding import index_candidates, get_semantic_scores  # lazy
    from app.utils.llm_reranker import generate_ai_rerank_and_insights

    pool = all_candidates or [candidate]
    print("  [Agentic] Ensuring candidates are indexed in ChromaDB...")
    index_candidates(pool)

    print("  [Agentic] Querying Groq LLM for deep single-candidate explanation...")
    llm_evals = generate_ai_rerank_and_insights(job, [candidate])

    if llm_evals and candidate.id in llm_evals:
        eval_data = llm_evals[candidate.id]
        return {
            "candidateId": candidate.id,
            "candidateName": candidate.fullName,
            "score": eval_data["score"],
            "matchedSkills": eval_data["matchedSkills"],
            "missingMustHaveSkills": eval_data["missingMustHaveSkills"],
            "missingNiceToHaveSkills": eval_data["missingNiceToHaveSkills"],
            "reasons": eval_data["reasons"],
            "summary": eval_data["summary"],
            "availability": candidate.availability,
            "insights": eval_data["insights"],
        }

    # Fallback – hybrid
    print("  [Agentic] LLM evaluation failed. Falling back to Hybrid.")
    semantic_scores = get_semantic_scores(job, top_k=len(pool))
    cand_sem = semantic_scores.get(candidate.id, 0.0)
    return score_candidate(
        candidate, job,
        semantic_score=cand_sem,
        weight_deterministic=_HYBRID_W_DET,
        weight_semantic=_HYBRID_W_SEM,
    )
