from typing import List
import json
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent.parent
ALIASES_FILE_PATH = APP_DIR / "data" / "skill_aliases.json"

def load_and_invert_aliases(ALIASES_FILE_PATH) -> dict:
    """
    Loads the JSON file and creates a flat, inverted dictionary for O(1) lookups.
    Example output: {"react.js": "react", "ts": "typescript", "react": "react"}
    """
    inverted_aliases = {}
    
    try:
        with open(ALIASES_FILE_PATH, 'r', encoding='utf-8') as f:
            raw_mapping = json.load(f)
            
        for standard_skill, aliases in raw_mapping.items():
            # Map the standard name to itself (e.g., "react": "react")
            inverted_aliases[standard_skill] = standard_skill
            
            # Map every alias to the standard name (e.g., "react.js": "react")
            for alias in aliases:
                inverted_aliases[alias] = standard_skill
                
    except FileNotFoundError:
        print(f"Warning: Alias file not found at {ALIASES_FILE_PATH}. Aliasing disabled.")
        
    return inverted_aliases
  
  
def normalize_skills_list(skills: List[str]) -> List[str]:
    """
    Normalizes a list of skills by:
    1. Trimming whitespace
    2. Lowercasing
    3. Mapping aliases to a standard term
    4. Deduplicating
    5. Sorting
    """
    if not skills:
        return []

    normalized_set = set()
    
    SKILL_ALIASES = load_and_invert_aliases(ALIASES_FILE_PATH)

    for skill in skills:
        # Trim whitespace and convert to lowercase
        cleaned = skill.strip().lower()
        
        # Guard against empty strings
        if cleaned == "":
            continue
    
        # Apply alias mapping. 
        standardized = SKILL_ALIASES.get(cleaned, cleaned)
        
        normalized_set.add(standardized)

    return sorted(list(normalized_set))