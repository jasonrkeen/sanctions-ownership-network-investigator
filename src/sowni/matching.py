from __future__ import annotations

from collections import defaultdict
from difflib import SequenceMatcher
from typing import Iterable

from .models import Alias, Entity, MatchResult
from .normalize import normalize_country, normalize_name, normalized_tokens


def _sequence_similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, left, right).ratio()


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def name_similarity(query: str, candidate: str) -> float:
    query_full = normalize_name(query)
    candidate_full = normalize_name(candidate)
    query_core = normalize_name(query, strip_legal_suffixes=True)
    candidate_core = normalize_name(candidate, strip_legal_suffixes=True)

    if not query_full or not candidate_full:
        return 0.0
    if query_full == candidate_full:
        return 100.0
    if query_core and query_core == candidate_core:
        return 98.0

    direct = _sequence_similarity(query_full, candidate_full)
    core = _sequence_similarity(query_core, candidate_core)
    token_sort = _sequence_similarity(
        " ".join(sorted(normalized_tokens(query))),
        " ".join(sorted(normalized_tokens(candidate))),
    )
    token_overlap = _jaccard(normalized_tokens(query), normalized_tokens(candidate))
    score = 100 * (0.75 * max(direct, core, token_sort) + 0.25 * token_overlap)
    return round(min(score, 100.0), 2)


class EntityMatcher:
    def __init__(self, entities: Iterable[Entity], aliases: Iterable[Alias]) -> None:
        self.entities = {entity.entity_id: entity for entity in entities}
        self.names: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for entity in self.entities.values():
            self.names[entity.entity_id].append((entity.name, "primary"))
        for alias in aliases:
            if alias.entity_id in self.entities:
                self.names[alias.entity_id].append((alias.name, alias.alias_type))

    def search(
        self,
        query: str,
        *,
        country: str = "",
        identifier_type: str = "",
        identifier_value: str = "",
        designated_only: bool = False,
        threshold: float = 55.0,
        limit: int = 20,
    ) -> list[MatchResult]:
        results: list[MatchResult] = []
        normalized_country = normalize_country(country)
        for entity_id, entity in self.entities.items():
            if designated_only and not entity.designated:
                continue

            reasons: list[str] = []
            identifier_exact = False
            if identifier_type and identifier_value:
                stored = entity.identifiers.get(identifier_type, "")
                identifier_exact = bool(stored) and (
                    normalize_name(stored) == normalize_name(identifier_value)
                )

            best_name = entity.name
            best_type = "primary"
            best_score = 0.0
            for candidate_name, match_type in self.names[entity_id]:
                score = name_similarity(query, candidate_name)
                if score > best_score:
                    best_name = candidate_name
                    best_type = match_type
                    best_score = score

            if identifier_exact:
                best_score = 100.0
                reasons.append(f"Exact {identifier_type} identifier")
            if best_score >= 98:
                reasons.append("Exact or legal-suffix-normalized name")
            elif best_score >= 85:
                reasons.append("Strong name similarity")
            elif best_score >= threshold:
                reasons.append("Partial name similarity")

            if normalized_country and entity.country:
                if normalize_country(entity.country) == normalized_country:
                    best_score = min(100.0, best_score + 3.0)
                    reasons.append("Country agrees")
                else:
                    reasons.append("Country differs")

            if best_score >= threshold:
                results.append(
                    MatchResult(
                        query=query,
                        entity_id=entity_id,
                        entity_name=entity.name,
                        matched_name=best_name,
                        match_type=best_type,
                        score=round(best_score, 2),
                        designated=entity.designated,
                        programs=entity.programs,
                        country=entity.country,
                        reasons=reasons,
                    )
                )
        return sorted(results, key=lambda item: (-item.score, item.entity_name))[:limit]
