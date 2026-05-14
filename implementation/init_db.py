from __future__ import annotations

import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "lab.db"


SCHEMA_SQL = """
CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cohort TEXT NOT NULL,
    age INTEGER NOT NULL CHECK(age > 0)
);

CREATE TABLE courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    credit INTEGER NOT NULL CHECK(credit > 0)
);

CREATE TABLE enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    score REAL NOT NULL CHECK(score >= 0 AND score <= 100),
    FOREIGN KEY(student_id) REFERENCES students(id),
    FOREIGN KEY(course_id) REFERENCES courses(id)
);
"""


SEED_SQL = """
INSERT INTO students (name, cohort, age) VALUES
('An', 'A1', 20),
('Binh', 'A1', 21),
('Chi', 'B2', 19),
('Dung', 'B2', 22);

INSERT INTO courses (title, credit) VALUES
('Databases', 3),
('Python', 2),
('AI Fundamentals', 4);

INSERT INTO enrollments (student_id, course_id, score) VALUES
(1, 1, 88.5),
(1, 2, 92.0),
(2, 1, 77.0),
(3, 3, 85.0),
(4, 2, 90.0);
"""


def create_database(db_path: str | Path = DB_PATH, reset: bool = True) -> Path:
    """Create and seed the SQLite database in a reproducible way."""
    path = Path(db_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    if reset and path.exists():
        path.unlink()

    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA_SQL)
        conn.executescript(SEED_SQL)
        conn.commit()

    return path


if __name__ == "__main__":
    created = create_database()
    print(f"Database initialized at: {created}")

