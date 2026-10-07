import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient

from backend import main
from database import db


class ResumeApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "test.sqlite3"
        self.uploads_path = Path(self.temp_dir.name) / "uploads"
        self.database_patch = patch.object(db, "DB_PATH", self.database_path)
        self.uploads_patch = patch.object(main, "UPLOADS_DIR", self.uploads_path)
        self.database_patch.start()
        self.uploads_patch.start()
        self.client = TestClient(main.app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.database_patch.stop()
        self.uploads_patch.stop()
        self.temp_dir.cleanup()

    def test_upload_analyze_and_retrieve_saved_analysis(self):
        upload = self.client.post(
            "/upload-resume",
            files={"file": ("resume.pdf", b"%PDF-test", "application/pdf")},
            data={"name": "Ada Lovelace", "email": "ada@example.com"},
        )
        self.assertEqual(upload.status_code, 201)
        resume_id = upload.json()["resume_id"]

        with patch.object(main, "extract_text_from_pdf", return_value="python experience"):
            with patch(
                "analyzer.service.calculate_semantic_similarity",
                return_value=np.float32(82.5),
            ):
                analysis = self.client.post(
                    "/analyze",
                    json={
                        "resume_id": resume_id,
                        "job_title": "Python Developer",
                        "job_description": "Python developer",
                    },
                )

        self.assertEqual(analysis.status_code, 201)
        analysis_id = analysis.json()["id"]
        self.assertIn("role", analysis.json()["result"])
        self.assertIn("experience", analysis.json()["result"])
        self.assertIn("education", analysis.json()["result"])
        self.assertIn("entities", analysis.json()["result"])
        saved = self.client.get(f"/analysis/{analysis_id}")
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json()["result"]["semantic_score"], 82.5)
        self.assertEqual(saved.json()["job_title"], "Python Developer")
        self.assertEqual(saved.json()["filename"], "resume.pdf")

        history = self.client.get("/history", params={"email": "ADA@example.com"})
        self.assertEqual(history.status_code, 200)
        self.assertEqual(len(history.json()["analyses"]), 1)
        self.assertEqual(history.json()["analyses"][0]["id"], analysis_id)
        self.assertEqual(
            history.json()["analyses"][0]["final_score"],
            saved.json()["final_score"],
        )

    def test_upload_rejects_non_pdf_content(self):
        response = self.client.post(
            "/upload-resume",
            files={"file": ("resume.pdf", b"not a pdf", "application/pdf")},
        )
        self.assertEqual(response.status_code, 400)

    def test_upload_supports_older_clients_without_identity_fields(self):
        response = self.client.post(
            "/upload-resume",
            files={"file": ("resume.pdf", b"%PDF-test", "application/pdf")},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["email"], "guest@local.invalid")

    def test_skills_endpoint_returns_skill_records(self):
        response = self.client.get("/skills")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["skills"])
        self.assertIn("skill", response.json()["skills"][0])

    def test_database_uses_version_three_tables(self):
        with db.get_connection() as connection:
            tables = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        self.assertTrue({"users", "resumes", "jobs", "analysis"}.issubset(tables))


if __name__ == "__main__":
    unittest.main()