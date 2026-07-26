from __future__ import annotations

import re
import tomllib
from pathlib import Path


REQUIRED_PUBLICATION_FILES = {
    Path(".env.example"),
    Path(".github/ISSUE_TEMPLATE/bug_report.yml"),
    Path(".github/ISSUE_TEMPLATE/feature_request.yml"),
    Path(".github/pull_request_template.md"),
    Path(".github/workflows/tests.yml"),
    Path("CHANGELOG.md"),
    Path("CITATION.cff"),
    Path("CONTRIBUTING.md"),
    Path("LICENSE"),
    Path("README.md"),
    Path("SECURITY.md"),
    Path("docs/ARCHITECTURE.md"),
    Path("docs/DEMO_WALKTHROUGH.md"),
    Path("docs/METHODOLOGY.md"),
    Path("docs/MODEL_CARD.md"),
    Path("docs/PORTFOLIO_BRIEF.md"),
    Path("docs/RELEASE_NOTES_v1.0.0.md"),
    Path("pyproject.toml"),
}
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
PACKAGE_VERSION_PATTERN = re.compile(
    r'^__version__\s*=\s*"(?P<version>[^"]+)"\s*$',
    flags=re.MULTILINE,
)
CITATION_VERSION_PATTERN = re.compile(
    r"^version:\s*(?P<version>\S+)\s*$",
    flags=re.MULTILINE,
)


def project_version(project_root: Path) -> str:
    metadata = tomllib.loads(
        (project_root / "pyproject.toml").read_text(encoding="utf-8")
    )
    return str(metadata["project"]["version"])


def _captured_version(path: Path, pattern: re.Pattern[str]) -> str | None:
    match = pattern.search(path.read_text(encoding="utf-8"))
    return match.group("version") if match else None


def _local_markdown_targets(markdown_path: Path) -> list[Path]:
    targets: list[Path] = []
    for raw_target in MARKDOWN_LINK_PATTERN.findall(
        markdown_path.read_text(encoding="utf-8")
    ):
        target = raw_target.strip().split("#", maxsplit=1)[0]
        if (
            not target
            or target.startswith("#")
            or "://" in target
            or target.startswith("mailto:")
        ):
            continue
        targets.append((markdown_path.parent / target).resolve())
    return targets


def validate_publication(project_root: Path) -> list[str]:
    root = project_root.resolve()
    issues: list[str] = []

    for relative in sorted(REQUIRED_PUBLICATION_FILES):
        if not (root / relative).is_file():
            issues.append(f"Missing required publication file: {relative.as_posix()}")

    if issues:
        return issues

    version = project_version(root)
    package_version = _captured_version(
        root / "src/sowni/__init__.py",
        PACKAGE_VERSION_PATTERN,
    )
    citation_version = _captured_version(
        root / "CITATION.cff",
        CITATION_VERSION_PATTERN,
    )
    model_card = (root / "docs/MODEL_CARD.md").read_text(encoding="utf-8")
    release_notes = root / f"docs/RELEASE_NOTES_v{version}.md"

    if package_version != version:
        issues.append(
            f"Package version {package_version!r} does not match project version {version!r}."
        )
    if citation_version != version:
        issues.append(
            f"Citation version {citation_version!r} does not match project version {version!r}."
        )
    if f"version {version}" not in model_card:
        issues.append(f"Model card does not identify version {version}.")
    if not release_notes.is_file():
        issues.append(f"Missing release notes for version {version}: {release_notes.name}")

    readme = " ".join(
        (root / "README.md").read_text(encoding="utf-8").lower().split()
    )
    for statement in (
        "not production-ready compliance software",
        "not a final legal determination",
    ):
        if statement not in readme:
            issues.append(f"README is missing boundary statement: {statement!r}.")

    if (root / ".env").exists():
        issues.append("Local .env file must not be present in the publication source.")

    for markdown_path in [root / "README.md", *sorted((root / "docs").glob("*.md"))]:
        for target in _local_markdown_targets(markdown_path):
            if not target.exists():
                relative_source = markdown_path.relative_to(root).as_posix()
                issues.append(
                    f"Broken local link in {relative_source}: "
                    f"{target.relative_to(root).as_posix()}"
                )

    return sorted(set(issues))


__all__ = [
    "REQUIRED_PUBLICATION_FILES",
    "project_version",
    "validate_publication",
]
