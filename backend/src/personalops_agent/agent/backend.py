from __future__ import annotations

from pathlib import Path


def get_project_backend_root() -> Path:
    return Path(__file__).resolve().parents[3]


def create_project_backend():
    from deepagents.backends import FilesystemBackend

    return FilesystemBackend(root_dir=str(get_project_backend_root()), virtual_mode=True)
