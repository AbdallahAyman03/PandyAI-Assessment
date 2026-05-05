from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    data_dir: Path = BASE_DIR / "app" / "data"
    output_dir: Path = BASE_DIR / "outputs"
    action_map_path: Path = BASE_DIR / "app" / "data" / "action_map.json"

    # SCORING WEIGHTS
    weight_must_have: float = 50.0
    weight_experience: float = 25.0
    weight_nice_to_have: float = 20.0
    weight_location : float = 5.0

    # EXPERIENCE CURVE CONFIG
    exp_bonus_per_year: float = 2.0
    exp_max_bonus: float = 5.0
    

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore" 
    )

config = Settings()