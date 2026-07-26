from __future__ import annotations

import os
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


DEFAULT_ARCHIVE_ROOT = "sanctions-ownership-network-investigator-mvp"
EXCLUDED_DIRECTORY_NAMES = {
    ".git",
    ".github-cache",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".venv-1",
    "__pycache__",
    "build",
    "dist",
    "tmp",
    "venv",
}
EXCLUDED_FILE_NAMES = {
    ".DS_Store",
    ".env",
    "Thumbs.db",
}
EXCLUDED_SUFFIXES = {
    ".db",
    ".pyc",
    ".pyo",
    ".sqlite",
    ".zip",
}
REQUIRED_RELEASE_FILES = {
    Path(".github/workflows/tests.yml"),
    Path("CHANGELOG.md"),
    Path("CITATION.cff"),
    Path("CONTRIBUTING.md"),
    Path("LICENSE"),
    Path("README.md"),
    Path("SECURITY.md"),
    Path("app.py"),
    Path("docs/RELEASE_NOTES_v1.0.0.md"),
    Path("main.py"),
    Path("pyproject.toml"),
    Path("src/sowni/__init__.py"),
}


def _directory_is_excluded(part: str) -> bool:
    return (
        part in EXCLUDED_DIRECTORY_NAMES
        or part.startswith(".venv")
        or part.endswith(".egg-info")
    )


def is_release_file(path: Path, project_root: Path) -> bool:
    if not path.is_file():
        return False
    relative = path.relative_to(project_root)
    if any(_directory_is_excluded(part) for part in relative.parts[:-1]):
        return False
    if relative.name in EXCLUDED_FILE_NAMES:
        return False
    if relative.suffix.lower() in EXCLUDED_SUFFIXES:
        return False

    if relative.parts[:3] == ("data", "raw", "ofac"):
        return relative == Path("data/raw/ofac/.gitkeep")
    if relative.parts and relative.parts[0] == "outputs":
        return relative == Path("outputs/.gitkeep")
    return True


def collect_release_files(project_root: Path) -> list[Path]:
    root = project_root.resolve()
    missing = sorted(
        str(relative)
        for relative in REQUIRED_RELEASE_FILES
        if not (root / relative).is_file()
    )
    if missing:
        raise ValueError(
            "Project is missing required release files: " + ", ".join(missing)
        )
    return sorted(
        (
            path
            for path in root.rglob("*")
            if is_release_file(path, root)
        ),
        key=lambda path: path.relative_to(root).as_posix(),
    )


def build_release_archive(
    project_root: Path,
    output_path: Path,
    *,
    archive_root: str = DEFAULT_ARCHIVE_ROOT,
) -> dict:
    root = project_root.resolve()
    destination = output_path.resolve()
    files = collect_release_files(root)
    if not archive_root or "/" in archive_root or "\\" in archive_root:
        raise ValueError("Archive root must be one non-empty directory name.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    os.close(file_descriptor)
    temporary_path = Path(temporary_name)
    try:
        with ZipFile(
            temporary_path,
            mode="w",
            compression=ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for path in files:
                relative = path.relative_to(root).as_posix()
                archive.write(path, arcname=f"{archive_root}/{relative}")
        with ZipFile(temporary_path) as archive:
            failed_member = archive.testzip()
            if failed_member:
                raise ValueError(f"Release archive failed CRC check: {failed_member}")
            members = archive.namelist()
            if not members or any(
                not member.startswith(f"{archive_root}/") for member in members
            ):
                raise ValueError("Release archive root validation failed.")
        os.replace(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)

    return {
        "output_path": str(destination),
        "archive_root": archive_root,
        "file_count": len(files),
        "size_bytes": destination.stat().st_size,
    }


__all__ = [
    "DEFAULT_ARCHIVE_ROOT",
    "build_release_archive",
    "collect_release_files",
    "is_release_file",
]
