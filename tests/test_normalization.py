import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.utils import skill_normalization


class TestSkillNormalization(unittest.TestCase):
    def test_normalize_skills_with_aliases_and_dedup(self) -> None:
        alias_map = {
            "javascript": ["js", "java script"],
            "react": ["react.js"],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            alias_path = Path(tmp_dir) / "skill_aliases.json"
            alias_path.write_text(json.dumps(alias_map), encoding="utf-8")

            with patch.object(skill_normalization, "ALIASES_FILE_PATH", alias_path):
                result = skill_normalization.normalize_skills_list(
                    [" JS ", "React.js", "javascript", "", "java script"]
                )

        self.assertEqual(result, ["javascript", "react"])

    def test_normalize_skills_empty_input(self) -> None:
        self.assertEqual(skill_normalization.normalize_skills_list([]), [])


if __name__ == "__main__":
    unittest.main()