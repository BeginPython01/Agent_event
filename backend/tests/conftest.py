"""Shared test setup. pytest loads this file before any test."""

import os
import tempfile

# src.api.app builds an app (and a database) when it's imported. Point that at a
# throwaway file so tests never touch the real scout.db.
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(), "import-time.db")
