import unittest

from app.schemas.candidate import Candidate, Experience
from app.schemas.job import Job, JobRequirements
from app.utils.scorer import score_candidate


class TestScorer(unittest.TestCase):
    def test_score_candidate_infers_must_have_and_applies_penalty(self) -> None:
        candidate = Candidate(
            id="c-001",
            fullName="Alex Doe",
            headline="Backend Engineer",
            location="Cairo",
            yearsOfExperience=3,
            skills=["python"],
            availability="Immediate",
            updatedAt="2026-05-09",
            status="Open to offers",
            score=0.0,
            experience=[
                Experience(
                    company="DataCorp",
                    title="Engineer",
                    start="2022-01",
                    end="2026-01",
                    highlights=["Built APIs with SQL and Python."],
                )
            ],
        )

        job = Job(
            id="j-001",
            title="Backend Engineer",
            description="Backend role",
            requirements=JobRequirements(
                mustHaveSkills=["python", "sql"],
                niceToHaveSkills=["aws"],
                minYears=3,
                remote=True,
                location=None,
            ),
        )

        result = score_candidate(candidate, job)

        self.assertAlmostEqual(result["score"], 45.56, places=2)
        self.assertIn("python", result["matchedSkills"])
        self.assertIn("sql", result["matchedSkills"])
        self.assertEqual(result["missingMustHaveSkills"], [])
        self.assertEqual(result["missingNiceToHaveSkills"], ["aws"])


if __name__ == "__main__":
    unittest.main()