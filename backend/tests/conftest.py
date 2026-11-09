"""Tests never read/write a developer's library or call a configured provider."""

import os
import tempfile
from pathlib import Path

_TEST_DIR = tempfile.TemporaryDirectory(prefix="papermind-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DIR.name}/library.db"
os.environ["STORAGE_DIR"] = str(Path(_TEST_DIR.name) / "storage")
os.environ["JOBS_INLINE"] = "true"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["LLM_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""
