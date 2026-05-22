from __future__ import annotations
import json
from pathlib import Path

from schemas import Artifact

_STORE_DIR = Path("state/artifacts")
_COUNTER_FILE = _STORE_DIR / "_counter.json"


class ArtifactStore:
    def __init__(self, store_dir: Path = _STORE_DIR):
        self._dir = store_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def _next_id(self) -> str:
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
        key = art_id[4:]
        return (self._dir / f"{key}.bin").read_bytes()

    def get_meta(self, art_id: str) -> Artifact:
        key = art_id[4:]
        data = json.loads((self._dir / f"{key}.json").read_text())
        return Artifact(**data)

    def exists(self, art_id: str) -> bool:
        if not art_id.startswith("art:"):
            return False
        key = art_id[4:]
        return (self._dir / f"{key}.bin").exists()
