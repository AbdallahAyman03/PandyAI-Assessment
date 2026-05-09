## Candidate Matching Engine

This repository implements a three-approach candidate matching engine that scores software candidates against job descriptions. It produces ranked results and explanations, with deterministic, hybrid semantic, and LLM + RAG ranking modes.

## System Overview
For each job and candidate pool, the system outputs:

- Ranked results (numerical scores and matched/missing skills)
- Insights (strengths, skill gaps, and recommended next steps)

## Skill Normalization Logic
Normalization is applied to both candidate skills and job requirements to ensure consistent matching.

Steps:
1. Trim whitespace
2. Lowercase
3. Map aliases via app/data/skill_aliases.json
4. Remove empty strings
5. Deduplicate and sort

Example:
- Input: [" React.js ", "JS", "javascript", " "]
- Output: ["javascript", "react"]

## Approach 1: Deterministic
The deterministic approach uses explicit weights and mathematical heuristics for a 100-point score.

Weights:
- Must-have skills: 50
- Nice-to-have skills: 20
- Experience fit: 25
- Location fit: 5
- Experience bonus: up to +5 (2 points per year, capped)

Scoring details:
- Must-have ratio: $R_{must} = \frac{m_{exp} + 0.5\,m_{inf}}{M}$
- Nice-to-have ratio: $R_{nice} = \frac{n_{exp} + 0.5\,n_{inf}}{N}$
- Must-have score: $S_{must} = 50 \times R_{must}$
- Nice-to-have score: $S_{nice} = 20 \times R_{nice}$
- Experience score:
	- If $y < y_{req}$: $S_{exp} = 25 \times (\frac{y}{y_{req}})^2$
	- Else: $S_{exp} = 25 + \min(2(y - y_{req}), 5)$
- Location score: $S_{loc} \in \{0, 2.5, 5\}$ depending on remote/match/relocation
- Must-have penalty: $S_{final} = (S_{must}+S_{nice}+S_{exp}+S_{loc}) \times R_{must}$
- Status penalty:
	- Not looking: $\times 0.50$
	- Open to offers/interviewing: $\times 0.90$
	- Otherwise: $\times 1.00$

Example output snippet:
{
	"candidateId": "c-001",
	"score": 45.56,
	"matchedSkills": ["python", "sql"],
	"missingMustHaveSkills": [],
	"missingNiceToHaveSkills": ["aws"],
	"summary": "Potential match. Meets experience requirements. Matches all core must-have requirements. (1 missing skill(s) were rescued by scanning experience/projects)."
}

## Approach 2: Hybrid (Semantic Fusion)
The hybrid approach blends deterministic scoring with semantic similarity from embeddings.

Pipeline:
- Model: BAAI/bge-small-en-v1.5
- Storage: ChromaDB (persistent)
- Similarity: cosine similarity in [0, 1]

Hybrid formula:
- $S_{hybrid} = (W_{det} \times S_{det}) + (W_{sem} \times (100 \times \text{cosine}))$
- Default weights are overridden when running the hybrid approach.

Example output snippet:
{
	"candidateId": "c-002",
	"score": 73.24,
	"reasons": [
		{"type": "semantic_similarity", "weight": 18.0}
	]
}

## Approach 3: LLM + RAG Ranking
The LLM + RAG approach uses hybrid retrieval to select top candidates, then an LLM re-ranks them and produces structured insights.

Two-phase flow:
1. Hybrid top-K retrieval
2. LLM re-ranking with schema-validated JSON output

Example output snippet:
{
	"candidateId": "c-003",
	"score": 88.5,
	"insights": {
		"strengths": ["Strong foundational alignment in backend stack."],
		"skillGaps": {"mustHave": [], "niceToHave": ["kafka"]},
		"recommendedNextSteps": ["Upskill Opportunity (KAFKA): Build a small event-driven pipeline."]
	}
}

## Comparative Analysis

| Metric | Deterministic | Hybrid | LLM + RAG |
| --- | --- | --- | --- |
| Latency | Very Low | Low–Medium | High (API dependent) |
| Cost | Minimal | Low (embedding compute) | High (token usage) |
| Explainability | High | Medium | High (natural language) |
| Implicit Skill Detection | Low | Medium | High |
| Failure Modes | Keyword misses | Embedding drift | API/JSON failures |
| Best Use Case | Fast filtering | Default ranking | Final shortlists |

## Trade-Offs
- Deterministic: Fast and transparent, but brittle to synonyms and context.
- Hybrid: Better recall and semantic matching, but adds embedding cost and complexity.
- LLM + RAG: Highest quality insights and reasoning, but slower and costlier with API dependency.

## Next Improvements
- Cache LLM results.
- Optimize the system prompt.
- Let the LLM self-reoptimize weights per job.

## Time Spent Estimate
- Deterministic approach: 3 hours
- Hybrid approach: 1.5 hours
- LLM + RAG approach: 1.5 hours

## Setup
Requirements:
- Python >= 3.13

Install dependencies:
- pip install -r (use uv or pip based on your workflow)

Environment variables:
- Copy .env-example to app/.env and set groq_api_key

## How to Run

Run batch ranking:
- python -m app.demo --approach deterministic --top-k 5
- python -m app.demo --approach hybrid --top-k 5
- python -m app.demo --approach llm-rag --top-k 5

Explain a single candidate:
- python -m app.explain --job-id j-001 --candidate-id c-001 --approach llm-rag

Run tests:
- python -m unittest discover -s tests

Outputs:
- Results are written to outputs/{approach}/rank and outputs/{approach}/insights

## Project Structure (Key Files)
- app/utils/approaches.py: approach routing and orchestration
- app/utils/scorer.py: deterministic scoring and reasoning
- app/utils/embedding.py: embedding indexing and semantic retrieval
- app/utils/llm_reranker.py: LLM scoring and insight generation
- app/utils/skill_normalization.py: skill normalization
