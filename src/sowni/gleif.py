from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .matching import name_similarity
from .models import Address, Alias, Entity, Relationship
from .normalize import normalize_name


GLEIF_API_ROOT = "https://api.gleif.org/api/v1"
GLEIF_SOURCE = "GLEIF Global LEI Index"
GLEIF_SOURCE_URL = "https://www.gleif.org/en/lei-data/gleif-api"
Transport = Callable[[str], dict]


class GleifError(RuntimeError):
    """Raised when GLEIF enrichment cannot be completed."""


@dataclass(slots=True)
class GleifSearchCandidate:
    lei: str
    name: str
    country: str
    jurisdiction: str
    entity_status: str
    registration_status: str
    match_score: float = 0.0
    ranking_basis: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class GleifEnrichmentResult:
    selected_lei: str
    selected_name: str
    entities: list[Entity] = field(default_factory=list)
    aliases: list[Alias] = field(default_factory=list)
    addresses: list[Address] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    retrieved_at: str = ""

    def summary(self) -> dict:
        return {
            "provider": GLEIF_SOURCE,
            "selected_lei": self.selected_lei,
            "selected_name": self.selected_name,
            "entity_count": len(self.entities),
            "relationship_count": len(self.relationships),
            "relationships": [item.to_dict() for item in self.relationships],
            "warnings": self.warnings,
            "retrieved_at": self.retrieved_at,
            "scope_note": (
                "GLEIF Level 2 links identify direct or ultimate accounting "
                "consolidating parents. They do not establish percentage ownership "
                "and are excluded from OFAC 50 Percent Rule propagation."
            ),
        }


def _name_value(value: object) -> str:
    if isinstance(value, dict):
        return str(value.get("name") or "")
    return str(value or "")


def _record_attributes(resource: dict) -> dict:
    return resource.get("attributes") or {}


def _candidate_name_score(query: str, candidate_name: str) -> tuple[float, str]:
    query_full = normalize_name(query)
    candidate_full = normalize_name(candidate_name)
    query_core = normalize_name(query, strip_legal_suffixes=True)
    candidate_core = normalize_name(candidate_name, strip_legal_suffixes=True)
    query_compact = query_core.replace(" ", "")
    candidate_compact = candidate_core.replace(" ", "")

    if query_full and query_full == candidate_full:
        return 100.0, "Exact normalized legal name"
    if query_core and query_core == candidate_core:
        return 98.0, "Legal-suffix-normalized name"
    if query_compact and query_compact == candidate_compact:
        return 97.0, "Spacing-normalized name"

    score = name_similarity(query, candidate_name)
    basis = "Token-aware name similarity"
    extra_characters = max(0, len(candidate_compact) - len(query_compact))
    if query_compact and candidate_compact.startswith(query_compact):
        compact_score = max(70.0, 94.0 - 0.75 * extra_characters)
        if compact_score > score:
            score = compact_score
            basis = "Compact-name prefix match"
    elif query_compact and query_compact in candidate_compact:
        compact_score = max(65.0, 85.0 - 0.75 * extra_characters)
        if compact_score > score:
            score = compact_score
            basis = "Compact-name contained match"
    return round(min(score, 100.0), 2), basis


def _entity_from_record(resource: dict, retrieved_at: str) -> tuple[
    Entity, list[Alias], list[Address]
]:
    attributes = _record_attributes(resource)
    entity_data = attributes.get("entity") or {}
    registration = attributes.get("registration") or {}
    lei = str(attributes.get("lei") or resource.get("id") or "").upper()
    if not lei:
        raise GleifError("GLEIF returned an LEI record without an LEI identifier.")

    legal_name = _name_value(entity_data.get("legalName")) or lei
    legal_address = entity_data.get("legalAddress") or {}
    headquarters_address = entity_data.get("headquartersAddress") or {}
    legal_form = entity_data.get("legalForm") or {}
    registered_as = str(entity_data.get("registeredAs") or "")
    identifiers = {
        key: value
        for key, value in {
            "lei": lei,
            "registered_as": registered_as,
            "legal_form": str(legal_form.get("id") or legal_form.get("other") or ""),
            "entity_status": str(entity_data.get("status") or ""),
            "registration_status": str(registration.get("status") or ""),
            "corroboration_level": str(registration.get("corroborationLevel") or ""),
            "jurisdiction": str(entity_data.get("jurisdiction") or ""),
        }.items()
        if value
    }
    entity = Entity(
        entity_id=f"gleif:{lei}",
        name=legal_name,
        entity_type="Legal Entity",
        source=GLEIF_SOURCE,
        designated=False,
        country=str(legal_address.get("country") or headquarters_address.get("country") or ""),
        identifiers=identifiers,
        remarks=(
            "GLEIF Level 1 identity record. Registration status: "
            f"{registration.get('status') or 'not supplied'}."
        ),
        retrieved_at=retrieved_at,
    )

    aliases: list[Alias] = []
    other_names = [
        *(entity_data.get("otherNames") or []),
        *(entity_data.get("transliteratedOtherNames") or []),
    ]
    for index, item in enumerate(other_names, start=1):
        name = _name_value(item)
        if not name or name == legal_name:
            continue
        alias_type = (
            str(item.get("type") or "OTHER_NAME")
            if isinstance(item, dict)
            else "OTHER_NAME"
        )
        aliases.append(
            Alias(
                alias_id=f"gleif:{lei}:alias:{index}",
                entity_id=entity.entity_id,
                name=name,
                alias_type=alias_type,
                source=GLEIF_SOURCE,
            )
        )

    addresses: list[Address] = []
    for kind, item in (
        ("legal", legal_address),
        ("headquarters", headquarters_address),
    ):
        if not item:
            continue
        address_lines = item.get("addressLines") or []
        street = ", ".join(str(part) for part in address_lines if part)
        locality = ", ".join(
            str(part)
            for part in (
                item.get("city"),
                item.get("region"),
                item.get("postalCode"),
            )
            if part
        )
        country = str(item.get("country") or "")
        if not any((street, locality, country)):
            continue
        addresses.append(
            Address(
                address_id=f"gleif:{lei}:address:{kind}",
                entity_id=entity.entity_id,
                address=street,
                city_state_postal=locality,
                country=country,
                source=GLEIF_SOURCE,
                remarks=f"GLEIF {kind} address.",
            )
        )
    return entity, aliases, addresses


def _relationship_from_record(resource: dict, kind: str) -> Relationship:
    attributes = _record_attributes(resource)
    relationship_data = attributes.get("relationship") or {}
    start_node = relationship_data.get("startNode") or {}
    end_node = relationship_data.get("endNode") or {}
    child_lei = str(start_node.get("id") or "").upper()
    parent_lei = str(end_node.get("id") or "").upper()
    if not child_lei or not parent_lei:
        raise GleifError("GLEIF returned a parent relationship without both LEI nodes.")

    periods = relationship_data.get("periods") or attributes.get("periods") or []
    valid_from = ""
    valid_to = ""
    if periods:
        period = periods[0] or {}
        valid_from = str(period.get("startDate") or "")
        valid_to = str(period.get("endDate") or "")

    relationship_type = (
        "DIRECT_ACCOUNTING_CONSOLIDATING_PARENT_OF"
        if kind == "direct"
        else "ULTIMATE_ACCOUNTING_CONSOLIDATING_PARENT_OF"
    )
    source_type = str(
        relationship_data.get("relationshipType") or relationship_type
    )
    registration = attributes.get("registration") or {}
    status = str(
        registration.get("status")
        or relationship_data.get("relationshipStatus")
        or "not supplied"
    )
    return Relationship(
        relationship_id=f"gleif:{kind}:{parent_lei}:{child_lei}",
        source_id=f"gleif:{parent_lei}",
        target_id=f"gleif:{child_lei}",
        relationship_type=relationship_type,
        source=GLEIF_SOURCE,
        ownership_pct=None,
        confidence=1.0,
        valid_from=valid_from,
        valid_to=valid_to,
        evidence=(
            f"GLEIF relationship type {source_type}; registration status {status}. "
            "This accounting-consolidation link does not establish percentage ownership."
        ),
        analyst_status="source_confirmed",
    )


class GleifClient:
    def __init__(
        self,
        *,
        api_root: str = GLEIF_API_ROOT,
        timeout: float = 30.0,
        transport: Transport | None = None,
    ) -> None:
        self.api_root = api_root.rstrip("/")
        self.timeout = timeout
        self.transport = transport

    def _request(
        self,
        path: str,
        params: dict[str, str | int] | None = None,
        *,
        allow_not_found: bool = False,
    ) -> dict | None:
        url = f"{self.api_root}/{path.lstrip('/')}"
        if params:
            url = f"{url}?{urlencode(params)}"
        if self.transport:
            try:
                return self.transport(url)
            except KeyError:
                if allow_not_found:
                    return None
                raise

        request = Request(
            url,
            headers={
                "Accept": "application/vnd.api+json",
                "User-Agent": "sanctions-ownership-network-investigator/1.0.0",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 404 and allow_not_found:
                return None
            raise GleifError(f"GLEIF API returned HTTP {exc.code} for {url}.") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise GleifError(f"Unable to retrieve or parse GLEIF data from {url}.") from exc

    def search(self, name: str, *, country: str = "", limit: int = 5) -> list[
        GleifSearchCandidate
    ]:
        if not name.strip():
            raise GleifError("A legal-entity name is required for GLEIF search.")
        normalized_country = country.strip().upper()
        if normalized_country and (
            len(normalized_country) != 2 or not normalized_country.isalpha()
        ):
            raise GleifError("Country must be a two-letter ISO code, such as US or GB.")
        result_limit = max(1, min(limit, 20))
        retrieval_limit = min(20, max(result_limit, result_limit * 2))
        payload = self._request(
            "lei-records",
            {
                "filter[entity.legalName]": name.strip(),
                "page[number]": 1,
                "page[size]": retrieval_limit,
            },
        )
        candidates: list[GleifSearchCandidate] = []
        for resource in (payload or {}).get("data") or []:
            attributes = _record_attributes(resource)
            entity_data = attributes.get("entity") or {}
            registration = attributes.get("registration") or {}
            legal_address = entity_data.get("legalAddress") or {}
            candidate_name = _name_value(entity_data.get("legalName"))
            match_score, ranking_basis = _candidate_name_score(name, candidate_name)
            candidate = GleifSearchCandidate(
                lei=str(attributes.get("lei") or resource.get("id") or "").upper(),
                name=candidate_name,
                country=str(legal_address.get("country") or ""),
                jurisdiction=str(entity_data.get("jurisdiction") or ""),
                entity_status=str(entity_data.get("status") or ""),
                registration_status=str(registration.get("status") or ""),
                match_score=match_score,
                ranking_basis=ranking_basis,
            )
            if normalized_country and candidate.country.upper() != normalized_country:
                continue
            candidates.append(candidate)
        return sorted(
            candidates,
            key=lambda item: (
                -item.match_score,
                item.entity_status.upper() != "ACTIVE",
                item.registration_status.upper() != "ISSUED",
                len(normalize_name(item.name, strip_legal_suffixes=True)),
                item.name,
                item.lei,
            ),
        )[:result_limit]

    def get_record(self, lei: str) -> dict:
        normalized = lei.strip().upper()
        if not normalized:
            raise GleifError("An LEI is required.")
        payload = self._request(f"lei-records/{normalized}")
        resource = (payload or {}).get("data")
        if not isinstance(resource, dict):
            raise GleifError(f"GLEIF did not return a record for LEI {normalized}.")
        return resource

    def get_parent_relationship(self, lei: str, kind: str) -> dict | None:
        if kind not in {"direct", "ultimate"}:
            raise ValueError("Parent relationship kind must be 'direct' or 'ultimate'.")
        payload = self._request(
            f"lei-records/{lei.strip().upper()}/{kind}-parent-relationship",
            allow_not_found=True,
        )
        resource = (payload or {}).get("data")
        return resource if isinstance(resource, dict) else None

    def enrich(
        self,
        *,
        name: str = "",
        lei: str = "",
        country: str = "",
    ) -> GleifEnrichmentResult:
        retrieved_at = datetime.now(UTC).isoformat()
        selected_lei = lei.strip().upper()
        if not selected_lei:
            candidates = self.search(name, country=country, limit=10)
            if not candidates:
                context = f" in {country}" if country else ""
                raise GleifError(f"No GLEIF candidate found for {name!r}{context}.")
            selected_lei = candidates[0].lei

        child_record = self.get_record(selected_lei)
        child, child_aliases, child_addresses = _entity_from_record(
            child_record, retrieved_at
        )
        result = GleifEnrichmentResult(
            selected_lei=selected_lei,
            selected_name=child.name,
            entities=[child],
            aliases=child_aliases,
            addresses=child_addresses,
            retrieved_at=retrieved_at,
        )
        seen_entities = {child.entity_id}

        for kind in ("direct", "ultimate"):
            relationship_record = self.get_parent_relationship(selected_lei, kind)
            if not relationship_record:
                result.warnings.append(
                    f"No published {kind} accounting consolidating parent relationship "
                    f"was returned for LEI {selected_lei}."
                )
                continue
            relationship = _relationship_from_record(relationship_record, kind)
            parent_lei = relationship.source_id.removeprefix("gleif:")
            if relationship.relationship_id not in {
                item.relationship_id for item in result.relationships
            }:
                result.relationships.append(relationship)
            if relationship.source_id in seen_entities:
                continue
            parent_record = self.get_record(parent_lei)
            parent, parent_aliases, parent_addresses = _entity_from_record(
                parent_record, retrieved_at
            )
            result.entities.append(parent)
            result.aliases.extend(parent_aliases)
            result.addresses.extend(parent_addresses)
            seen_entities.add(parent.entity_id)
        return result


__all__ = [
    "GLEIF_API_ROOT",
    "GLEIF_SOURCE",
    "GLEIF_SOURCE_URL",
    "GleifClient",
    "GleifEnrichmentResult",
    "GleifError",
    "GleifSearchCandidate",
]
