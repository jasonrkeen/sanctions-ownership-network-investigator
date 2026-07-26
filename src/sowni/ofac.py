from __future__ import annotations

import csv
import hashlib
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .models import Address, Alias, Entity


OFAC_EXPORT_ROOT = (
    "https://sanctionslistservice.ofac.treas.gov/"
    "api/PublicationPreview/exports"
)
SDN_FILES = ("SDN.CSV", "ALT.CSV", "ADD.CSV", "SDN_COMMENTS.CSV")


@dataclass(slots=True)
class OfacLoadResult:
    entities: list[Entity]
    aliases: list[Alias]
    addresses: list[Address]
    file_hashes: dict[str, str]


def _clean(value: str) -> str:
    value = (value or "").strip()
    return "" if value == "-0-" else value


def _read_csv(path: Path) -> list[list[str]]:
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        return [row for row in csv.reader(handle) if row]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_sdn_files(
    destination: Path,
    user_agent: str = "SONI-Portfolio-Research/0.1",
    timeout: int = 60,
) -> dict[str, Path]:
    destination.mkdir(parents=True, exist_ok=True)
    downloaded: dict[str, Path] = {}
    for filename in SDN_FILES:
        url = f"{OFAC_EXPORT_ROOT}/{filename}"
        output_path = destination / filename.lower()
        request = urllib.request.Request(url, headers={"User-Agent": user_agent})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            output_path.write_bytes(response.read())
        downloaded[filename] = output_path
    return downloaded


def load_sdn_files(directory: Path) -> OfacLoadResult:
    retrieved_at = datetime.now(UTC).isoformat()
    main_path = directory / "sdn.csv"
    alias_path = directory / "alt.csv"
    address_path = directory / "add.csv"
    comments_path = directory / "sdn_comments.csv"

    missing = [
        path.name
        for path in (main_path, alias_path, address_path, comments_path)
        if not path.exists()
    ]
    if missing:
        raise FileNotFoundError(f"Missing OFAC files: {', '.join(missing)}")

    comments = {
        _clean(row[0]): _clean(row[1])
        for row in _read_csv(comments_path)
        if len(row) >= 2
    }

    entities: list[Entity] = []
    for row in _read_csv(main_path):
        if len(row) < 4:
            continue
        padded = row + [""] * max(0, 12 - len(row))
        ent_num = _clean(padded[0])
        programs = [
            item.strip()
            for item in _clean(padded[3]).replace(",", ";").split(";")
            if item.strip()
        ]
        remarks = " ".join(
            part for part in (_clean(padded[11]), comments.get(ent_num, "")) if part
        )
        identifiers: dict[str, str] = {}
        if _clean(padded[5]):
            identifiers["call_sign"] = _clean(padded[5])
        entities.append(
            Entity(
                entity_id=f"ofac:{ent_num}",
                name=_clean(padded[1]),
                entity_type=_clean(padded[2]) or "Unknown",
                source="OFAC SDN",
                designated=True,
                programs=programs,
                identifiers=identifiers,
                remarks=remarks,
                retrieved_at=retrieved_at,
            )
        )

    aliases: list[Alias] = []
    for row in _read_csv(alias_path):
        if len(row) < 4:
            continue
        padded = row + [""] * max(0, 5 - len(row))
        aliases.append(
            Alias(
                alias_id=f"ofac-alias:{_clean(padded[1])}",
                entity_id=f"ofac:{_clean(padded[0])}",
                alias_type=_clean(padded[2]) or "alias",
                name=_clean(padded[3]),
                source="OFAC SDN",
                remarks=_clean(padded[4]),
            )
        )

    addresses: list[Address] = []
    for row in _read_csv(address_path):
        if len(row) < 3:
            continue
        padded = row + [""] * max(0, 6 - len(row))
        addresses.append(
            Address(
                address_id=f"ofac-address:{_clean(padded[1])}",
                entity_id=f"ofac:{_clean(padded[0])}",
                address=_clean(padded[2]),
                city_state_postal=_clean(padded[3]),
                country=_clean(padded[4]),
                source="OFAC SDN",
                remarks=_clean(padded[5]),
            )
        )

    file_hashes = {
        path.name: sha256_file(path)
        for path in (main_path, alias_path, address_path, comments_path)
    }
    return OfacLoadResult(entities, aliases, addresses, file_hashes)
