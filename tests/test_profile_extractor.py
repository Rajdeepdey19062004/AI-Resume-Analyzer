import unittest

import pandas as pd

from analyzer.profile_extractor import extract_resume_profile
from analyzer.skill_extractor import extract_skills


class ResumeProfileExtractorTests(unittest.TestCase):
    def setUp(self):
        self.skills = pd.DataFrame(
            {
                "skill": ["Python", "SQL", "PostgreSQL", "C"],
                "category": ["programming", "database", "database", "programming"],
            }
        )

    def test_skills_match_complete_tokens_not_substrings(self):
        skills = extract_skills("Worked with Python, PostgreSQL, and SQLs.", self.skills)

        self.assertEqual(skills, ["PostgreSQL", "Python"])

    def test_extracts_role_experience_education_and_named_entities(self):
        profile = extract_resume_profile(
            "Worked as Python Developer for 2 years. "
            "Graduated with a BSc in Computer Science from the University of Oxford. "
            "Ada Lovelace joined Microsoft in London.",
            self.skills,
        )

        self.assertIn("Python Developer", profile["role"])
        self.assertEqual(profile["experience"][0]["duration"], "2 years")
        self.assertIn("Bachelor's degree", profile["education"]["degrees"])
        self.assertIn("Python", profile["skills"])
        self.assertTrue(
            any(entity["text"] == "Microsoft" for entity in profile["entities"])
        )
        self.assertIn("University of Oxford", profile["education"]["institutions"])


if __name__ == "__main__":
    unittest.main()
