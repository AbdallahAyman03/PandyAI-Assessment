import json
import logging
from pathlib import Path
from typing import List, Optional
from pydantic import ValidationError

from app.schemas.candidate import Candidate
from app.schemas.job import Job
from app.settings import config

logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')

def load_candidates(filepath: Optional[Path] = None) -> List[Candidate]:
    """
    Loads candidates from a JSON file, pushing them through Pydantic validation.
    Gracefully skips malformed entries and logs a warning.
    """
    if filepath is None:
        filepath = config.data_dir / "candidates.json"

    valid_candidates = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        for item in data:
            try:
                valid_candidates.append(Candidate(**item))
            except ValidationError as e:
                cid = item.get('id', 'UNKNOWN_ID')
                logging.warning(f"Skipping malformed candidate {cid}: {e.errors()[0]['msg']}")
                
    except FileNotFoundError:
        logging.error(f"File not found: {filepath}")
        
    return valid_candidates


def load_jobs(filepath: Optional[Path] = None) -> List[Job]:
    """
    Loads jobs from a JSON file, pushing them through Pydantic validation.
    Gracefully skips malformed entries and logs a warning.
    """
    if filepath is None:
        filepath = config.data_dir / "jobs.json"

    valid_jobs = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        for item in data:
            try:
                valid_jobs.append(Job(**item))
            except ValidationError as e:
                jid = item.get('id', 'UNKNOWN_ID')
                logging.warning(f"Skipping malformed job {jid}: {e.errors()[0]['msg']}")
                
    except FileNotFoundError:
        logging.error(f"File not found: {filepath}")
        
    return valid_jobs