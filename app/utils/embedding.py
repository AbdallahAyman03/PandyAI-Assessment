"""
Embedding module — lazy-loaded to avoid pulling in sentence-transformers
and ChromaDB on every import (e.g. when using the deterministic approach).

The SentenceTransformer model and the ChromaDB client are only initialised
the first time index_candidates() or get_semantic_scores() is called.
"""

import logging
from typing import Dict, List

import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings
from chromadb.config import Settings as ChromaSettings

from app.schemas.candidate import Candidate
from app.schemas.job import Job
from app.settings import config

logging.basicConfig(level=logging.INFO)



def get_candidate_text(candidate: Candidate) -> str:
    """Converts a Candidate object into a dense semantic paragraph."""
    parts = [f"Title: {candidate.headline}."]
    if candidate.summary:
        parts.append(f"Summary: {candidate.summary}")
    if candidate.skills:
        parts.append(f"Core Skills: {', '.join(candidate.skills)}.")
    if candidate.experience:
        for exp in candidate.experience:
            parts.append(f"Worked as {exp.title} at {exp.company}.")
            if exp.highlights:
                parts.append(" ".join(exp.highlights))
    if candidate.projects:
        for proj in candidate.projects:
            parts.append(f"Built project {proj.name}: {proj.description}")
            if proj.tech:
                parts.append(f"Technologies used: {', '.join(proj.tech)}.")

    dense_text = " ".join(parts).replace("\n", " ").strip().lower()
    while "  " in dense_text:
        dense_text = dense_text.replace("  ", " ")
    return dense_text


def get_job_text(job: Job) -> str:
    """Converts a Job object into a semantic search query string."""
    parts = [f"Job Title: {job.title}.", job.description]
    if job.requirements.mustHaveSkills:
        parts.append(f"Must have skills: {', '.join(job.requirements.mustHaveSkills)}.")
    if job.requirements.niceToHaveSkills:
        parts.append(
            f"Nice to have skills: {', '.join(job.requirements.niceToHaveSkills)}."
        )

    dense_text = " ".join(parts).replace("\n", " ").strip().lower()
    while "  " in dense_text:
        dense_text = dense_text.replace("  ", " ")
    return dense_text



class BGEEmbeddingFunction(EmbeddingFunction):
    """
    Custom wrapper for BAAI/bge-small-en-v1.5 with ChromaDB.
    Normalising embeddings is critical for accurate Cosine Similarity.
    Only instantiated on demand (lazy) to avoid slow startup when
    the deterministic-only approach is used.
    """

    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer  # lazy import

        logging.info(
            "Loading BAAI/bge-small-en-v1.5 model "
            "(this may take a moment on first run)..."
        )
        self.model = SentenceTransformer("BAAI/bge-small-en-v1.5", device="cpu")

    def __call__(self, input: Documents) -> Embeddings:
        embeddings = self.model.encode(input, normalize_embeddings=True)
        return embeddings.tolist()


_embedding_fn: "BGEEmbeddingFunction | None" = None
_chroma_client: "chromadb.PersistentClient | None" = None
_collection = None

_indexed_candidate_ids: set = set()


def _get_embedding_fn() -> BGEEmbeddingFunction:
    global _embedding_fn
    if _embedding_fn is None:
        _embedding_fn = BGEEmbeddingFunction()
    return _embedding_fn


def _get_collection():
    global _collection, _chroma_client, _indexed_candidate_ids
    if _collection is None:
        db_path = config.data_dir / "chroma_db"
        db_path.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(
            path=str(db_path),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        _collection = _chroma_client.get_or_create_collection(
            name="candidates_v1",
            embedding_function=_get_embedding_fn(),
            metadata={"hnsw:space": "cosine"},
        )
        
        # Hydrate the in-memory cache with IDs already saved to disk
        existing = _collection.get(include=[])
        if existing and "ids" in existing:
            _indexed_candidate_ids.update(existing["ids"])
            
    return _collection



def index_candidates(candidates: List[Candidate]) -> None:
    """
    Embeds and upserts candidates into ChromaDB.

    Candidates already indexed in the current process session are skipped
    to avoid redundant re-embedding (safe for repeated calls in demo mode).
    """
    global _indexed_candidate_ids

    to_index = [c for c in candidates if c.id not in _indexed_candidate_ids]

    if not to_index:
        logging.info("All candidates already indexed in this session. Skipping.")
        return

    coll = _get_collection()

    ids = [c.id for c in to_index]
    documents = [get_candidate_text(c) for c in to_index]
    metadatas = [{"name": c.fullName, "exp": c.yearsOfExperience} for c in to_index]

    logging.info(f"Upserting {len(to_index)} candidate(s) into ChromaDB...")
    coll.upsert(ids=ids, documents=documents, metadatas=metadatas)

    _indexed_candidate_ids.update(ids)
    logging.info("Indexing complete.")


def get_semantic_scores(job: Job, top_k: int = 100) -> Dict[str, float]:
    """
    Queries ChromaDB with the job description and returns a dict mapping
    Candidate ID -> cosine similarity score (0.0 – 1.0).
    """
    coll = _get_collection()

    count = coll.count()
    if count == 0:
        logging.warning("ChromaDB collection is empty. No semantic scores available.")
        return {}

    job_query = get_job_text(job)

    results = coll.query(
        query_texts=[job_query],
        n_results=min(top_k, count),
    )

    semantic_scores: Dict[str, float] = {}
    if results["ids"] and results["distances"]:
        for cid, distance in zip(results["ids"][0], results["distances"][0]):
            # ChromaDB 'cosine' distance = 1 – cosine_similarity
            similarity = 1.0 - distance
            semantic_scores[cid] = max(0.0, similarity)

    return semantic_scores
