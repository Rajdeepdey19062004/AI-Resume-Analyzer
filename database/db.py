import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "resume_analyzer.db"
LEGACY_DB_PATH = BASE_DIR / "database" / "resume_analyzer.sqlite3"


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS resumes (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                filename TEXT NOT NULL,
                upload_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                file_path TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                UNIQUE (title, description)
            );
            CREATE TABLE IF NOT EXISTS analysis (
                id TEXT PRIMARY KEY,
                resume_id TEXT NOT NULL REFERENCES resumes(id),
                job_id INTEGER NOT NULL REFERENCES jobs(id),
                skill_score REAL NOT NULL,
                semantic_score REAL NOT NULL,
                final_score REAL NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        if DB_PATH.resolve() == (BASE_DIR / "database" / "resume_analyzer.db").resolve():
            _import_legacy_database(connection)


def _import_legacy_database(connection: sqlite3.Connection) -> None:
    if not LEGACY_DB_PATH.is_file() or LEGACY_DB_PATH.resolve() == DB_PATH.resolve():
        return

    with sqlite3.connect(LEGACY_DB_PATH) as legacy:
        legacy.row_factory = sqlite3.Row
        tables = {
            row["name"]
            for row in legacy.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        if not {"resume_uploads", "analyses"}.issubset(tables):
            return

        resumes = legacy.execute("SELECT * FROM resume_uploads").fetchall()
        analyses = legacy.execute("SELECT * FROM analyses").fetchall()
        if not resumes:
            return

        connection.execute(
            """
            INSERT INTO users (name, email)
            VALUES ('Imported user', 'imported@local.invalid')
            ON CONFLICT(email) DO NOTHING
            """
        )
        user_id = connection.execute(
            "SELECT id FROM users WHERE email = ?",
            ("imported@local.invalid",),
        ).fetchone()["id"]

        for resume in resumes:
            connection.execute(
                """
                INSERT OR IGNORE INTO resumes
                    (id, user_id, filename, upload_date, file_path)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    resume["id"],
                    user_id,
                    resume["file_name"],
                    resume["created_at"],
                    resume["file_path"],
                ),
            )

        for item in analyses:
            if connection.execute(
                "SELECT 1 FROM analysis WHERE id = ?", (item["id"],)
            ).fetchone():
                continue

            result = json.loads(item["result_json"])
            connection.execute(
                """
                INSERT INTO jobs (title, description)
                VALUES ('Imported job', ?)
                ON CONFLICT(title, description) DO NOTHING
                """,
                (item["job_description"],),
            )
            job_id = connection.execute(
                "SELECT id FROM jobs WHERE title = ? AND description = ?",
                ("Imported job", item["job_description"]),
            ).fetchone()["id"]
            connection.execute(
                """
                INSERT INTO analysis (
                    id, resume_id, job_id, skill_score, semantic_score,
                    final_score, result_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["id"],
                    item["resume_id"],
                    job_id,
                    float(result.get("skill_score", 0)),
                    float(result.get("semantic_score", 0)),
                    float(result.get("final_score", 0)),
                    item["result_json"],
                    item["created_at"],
                ),
            )


def get_or_create_user(name: str, email: str) -> int:
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO users (name, email) VALUES (?, ?) ON CONFLICT(email) DO NOTHING",
            (name, email),
        )
        connection.execute(
            "UPDATE users SET name = ? WHERE email = ?",
            (name, email),
        )
        row = connection.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    return int(row["id"])


def add_resume(
    resume_id: str,
    user_id: int,
    filename: str,
    file_path: str,
) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO resumes (id, user_id, filename, file_path)
            VALUES (?, ?, ?, ?)
            """,
            (resume_id, user_id, filename, file_path),
        )


def get_resume(resume_id: str) -> sqlite3.Row | None:
    with get_connection() as connection:
        return connection.execute(
            "SELECT * FROM resumes WHERE id = ?",
            (resume_id,),
        ).fetchone()


def get_or_create_job(title: str, description: str) -> int:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO jobs (title, description) VALUES (?, ?)
            ON CONFLICT(title, description) DO NOTHING
            """,
            (title, description),
        )
        row = connection.execute(
            "SELECT id FROM jobs WHERE title = ? AND description = ?",
            (title, description),
        ).fetchone()
    return int(row["id"])


def list_jobs() -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id, title, description FROM jobs ORDER BY id"
        ).fetchall()
    return [dict(row) for row in rows]


def add_analysis(
    analysis_id: str,
    resume_id: str,
    job_id: int,
    result: dict,
) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO analysis (
                id, resume_id, job_id, skill_score, semantic_score,
                final_score, result_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                analysis_id,
                resume_id,
                job_id,
                float(result["skill_score"]),
                float(result["semantic_score"]),
                float(result["final_score"]),
                json.dumps(result),
            ),
        )


def get_analysis(analysis_id: str) -> dict | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT analysis.*, resumes.filename, resumes.upload_date,
                   jobs.title AS job_title, jobs.description AS job_description
            FROM analysis
            JOIN resumes ON resumes.id = analysis.resume_id
            JOIN jobs ON jobs.id = analysis.job_id
            WHERE analysis.id = ?
            """,
            (analysis_id,),
        ).fetchone()

    if row is None:
        return None

    return {
        "id": row["id"],
        "resume_id": row["resume_id"],
        "created_at": row["created_at"],
        "filename": row["filename"],
        "upload_date": row["upload_date"],
        "job_title": row["job_title"],
        "job_description": row["job_description"],
        "skill_score": row["skill_score"],
        "semantic_score": row["semantic_score"],
        "final_score": row["final_score"],
        "result": json.loads(row["result_json"]),
    }


def list_user_analyses(email: str) -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT analysis.id, analysis.resume_id, analysis.created_at,
                   analysis.skill_score, analysis.semantic_score,
                   analysis.final_score, analysis.result_json,
                   resumes.filename, resumes.upload_date,
                   jobs.title AS job_title, jobs.description AS job_description
            FROM analysis
            JOIN resumes ON resumes.id = analysis.resume_id
            JOIN users ON users.id = resumes.user_id
            JOIN jobs ON jobs.id = analysis.job_id
            WHERE users.email = ?
            ORDER BY analysis.created_at DESC, analysis.rowid DESC
            """,
            (email,),
        ).fetchall()

    return [
        {
            "id": row["id"],
            "resume_id": row["resume_id"],
            "created_at": row["created_at"],
            "filename": row["filename"],
            "upload_date": row["upload_date"],
            "job_title": row["job_title"],
            "job_description": row["job_description"],
            "skill_score": row["skill_score"],
            "semantic_score": row["semantic_score"],
            "final_score": row["final_score"],
            "result": json.loads(row["result_json"]),
        }
        for row in rows
    ]