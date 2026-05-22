"""Module for managing large data payloads in the agent's out-of-band ArtifactStore.

This module provides persistence for large execution payloads (e.g., crawled web
pages or multi-kilobyte text files) that exceed memory limits or prompt budget
capacities. Objects are saved sequentially on disk as binary blobs with corresponding
metadata schemas.
"""

from __future__ import annotations
import json
from pathlib import Path

from schemas import Artifact

_STORE_DIR = Path("state/artifacts")
_COUNTER_FILE = _STORE_DIR / "_counter.json"


class ArtifactStore:
    """Manages reading, writing, and checking existence of large execution artifacts.

    Artifacts are stored under a designated directory as binary files (`.bin`) and
    JSON metadata files (`.json`), keyed by an auto-incrementing sequential identifier
    (e.g., 'art:0001').
    """

    def __init__(self, store_dir: Path = _STORE_DIR):
        """Initializes the artifact store directory.

        Args:
            store_dir: The filesystem path directory where artifacts should be saved.
        """
        self._dir = store_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def _next_id(self) -> str:
        """Generates and reserves the next sequential artifact identifier.

        Increments the integer stored in the `_counter.json` file inside the store
        directory to guarantee uniqueness.

        Returns:
            A formatted string ID in the form 'art:NNNN' (e.g., 'art:0001').
        """
        if _COUNTER_FILE.exists():
            n = json.loads(_COUNTER_FILE.read_text())["n"]
        else:
            n = 0
        n += 1
        _COUNTER_FILE.write_text(json.dumps({"n": n}))
        return f"art:{n:04d}"

    def put(
        self,
        blob: bytes,
        *,
        content_type: str,
        source: str,
        descriptor: str,
    ) -> str:
        """Saves a binary payload as a new artifact and persists its metadata.

        Args:
            blob: The raw bytes to store.
            content_type: The MIME/content type of the data (e.g., 'text/html').
            source: The originating tool or system module that produced the data.
            descriptor: A short descriptive summary of what the data represents.

        Returns:
            The generated unique identifier for the saved artifact (e.g., 'art:0001').
        """
        art_id = self._next_id()
        key = art_id[4:]
        bin_path = self._dir / f"{key}.bin"
        meta_path = self._dir / f"{key}.json"
        bin_path.write_bytes(blob)
        artifact = Artifact(
            id=art_id,
            content_type=content_type,
            size_bytes=len(blob),
            source=source,
            descriptor=descriptor,
        )
        meta_path.write_text(artifact.model_dump_json(indent=2))
        return art_id

    def get_bytes(self, art_id: str) -> bytes:
        """Retrieves the raw binary payload of a stored artifact.

        Args:
            art_id: The unique artifact identifier (e.g., 'art:0001').

        Returns:
            The raw bytes of the saved artifact.
        """
        key = art_id[4:]
        return (self._dir / f"{key}.bin").read_bytes()

    def get_meta(self, art_id: str) -> Artifact:
        """Retrieves the structured metadata associated with a stored artifact.

        Args:
            art_id: The unique artifact identifier (e.g., 'art:0001').

        Returns:
            An Artifact instance containing content_type, size, source, and descriptor.
        """
        key = art_id[4:]
        data = json.loads((self._dir / f"{key}.json").read_text())
        return Artifact(**data)

    def exists(self, art_id: str) -> bool:
        """Checks if an artifact exists in the store.

        Args:
            art_id: The identifier to check.

        Returns:
            True if the identifier is valid and the binary file exists, otherwise False.
        """
        if not art_id.startswith("art:"):
            return False
        key = art_id[4:]
        return (self._dir / f"{key}.bin").exists()
