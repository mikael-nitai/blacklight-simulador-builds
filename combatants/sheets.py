"""Lossless character-sheet records; no combat rules execute during import."""

from dataclasses import dataclass
import json
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


ABILITIES = ("melee", "agility", "resilience", "vigilance", "ego", "logic")
KINDS = {"power", "trait", "tag", "equipment", "house_weapon"}
SCHEMA = "blacklight.character.v1"


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value):
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


@dataclass(frozen=True)
class Feature:
    id: str
    kind: str
    level: int
    parameters: Mapping
    sources: tuple[str, ...]


@dataclass(frozen=True)
class CharacterSheet:
    id: str
    revision: str
    name: str
    rank: int
    ruleset: str
    abilities: Mapping[str, int]
    defenses: Mapping[str, int]
    resources: Mapping[str, int]
    movement: Mapping[str, int]
    initiative_modifier: int
    features: tuple[Feature, ...]
    provenance: tuple[Mapping, ...]
    notes: tuple[str, ...]

    def level(self, feature_id: str, kind: str = "power") -> int:
        return next((f.level for f in self.features
                     if f.id == feature_id and f.kind == kind), 0)


def _integer(value: object, label: str, minimum: int | None = None) -> int:
    if type(value) is not int or (minimum is not None and value < minimum):
        raise ValueError(f"{label}: invalid integer {value!r}")
    return value


def _mapping(data: object, keys: set[str], label: str,
             *, minimum: int | None = None) -> Mapping[str, int]:
    if not isinstance(data, dict) or set(data) != keys:
        raise ValueError(f"{label}: expected exactly {sorted(keys)}")
    return MappingProxyType({key: _integer(value, f"{label}.{key}", minimum)
                             for key, value in data.items()})


def parse_sheet(data: dict) -> CharacterSheet:
    expected = {"schema", "id", "revision", "name", "rank", "ruleset",
                "abilities", "defenses", "resources", "movement",
                "initiative_modifier", "features", "provenance", "notes"}
    if not isinstance(data, dict) or set(data) != expected:
        raise ValueError(f"Sheet keys must be exactly {sorted(expected)}")
    if data["schema"] != SCHEMA:
        raise ValueError(f"Unsupported sheet schema: {data['schema']!r}")
    for key in ("id", "revision", "name", "ruleset"):
        if not isinstance(data[key], str) or not data[key].strip():
            raise ValueError(f"{key}: nonempty string required")
    rank = _integer(data["rank"], "rank", 1)
    if rank > 6:
        raise ValueError("Numeric combat Ranks are 1 to 6; Rank X needs narrative resolution")
    abilities = _mapping(data["abilities"], set(ABILITIES), "abilities")
    defenses = _mapping(data["defenses"], set(ABILITIES), "defenses", minimum=0)
    resources = _mapping(data["resources"], {"health", "focus", "karma"},
                         "resources", minimum=0)
    if min(resources["health"], resources["focus"]) < 1:
        raise ValueError("Health and Focus maxima must be positive")
    if not isinstance(data["movement"], dict) or "run" not in data["movement"]:
        raise ValueError("movement must include run; other named modes are retained")
    movement = MappingProxyType({str(key): _integer(value, f"movement.{key}", 0)
                                 for key, value in data["movement"].items()})
    features = []
    seen = set()
    if not isinstance(data["features"], list):
        raise ValueError("features must be a list")
    for row in data["features"]:
        if not isinstance(row, dict) or set(row) != {
                "id", "kind", "level", "parameters", "sources"}:
            raise ValueError("Feature requires id, kind, level, parameters, sources")
        if not isinstance(row["id"], str) or not row["id"] or row["kind"] not in KINDS:
            raise ValueError("Invalid feature identity/kind")
        identity = (row["kind"], row["id"])
        if identity in seen:
            raise ValueError(f"Duplicate feature {identity}; store its highest level once")
        seen.add(identity)
        if not isinstance(row["parameters"], dict):
            raise ValueError("Feature parameters must be a mapping")
        if (not isinstance(row["sources"], list) or not row["sources"] or
                any(not isinstance(s, str) or not s for s in row["sources"])):
            raise ValueError("Every feature needs at least one source reference")
        features.append(Feature(row["id"], row["kind"],
                                _integer(row["level"], "feature.level", 1),
                                _freeze(row["parameters"]),
                                tuple(row["sources"])))
    if (not isinstance(data["provenance"], list) or not data["provenance"] or
            any(not isinstance(row, dict) for row in data["provenance"])):
        raise ValueError("At least one provenance record is required")
    if not isinstance(data["notes"], list) or any(not isinstance(n, str) for n in data["notes"]):
        raise ValueError("notes must be a list of strings")
    return CharacterSheet(
        data["id"], data["revision"], data["name"], rank, data["ruleset"],
        abilities, defenses, resources, movement,
        _integer(data["initiative_modifier"], "initiative_modifier"),
        tuple(features), tuple(_freeze(row) for row in data["provenance"]),
        tuple(data["notes"]),
    )


def load_sheet(path: str | Path) -> CharacterSheet:
    return parse_sheet(json.loads(Path(path).read_text(encoding="utf-8")))


def sheet_record(sheet: CharacterSheet) -> dict:
    """Canonical serializable data for experiment provenance and seed identity."""
    return {'schema': SCHEMA, 'id': sheet.id, 'revision': sheet.revision,
            'name': sheet.name, 'rank': sheet.rank, 'ruleset': sheet.ruleset,
            'abilities': dict(sheet.abilities), 'defenses': dict(sheet.defenses),
            'resources': dict(sheet.resources), 'movement': dict(sheet.movement),
            'initiative_modifier': sheet.initiative_modifier,
            'features': [{'id': f.id, 'kind': f.kind, 'level': f.level,
                          'parameters': _thaw(f.parameters), 'sources': list(f.sources)}
                         for f in sheet.features],
            'provenance': _thaw(sheet.provenance), 'notes': list(sheet.notes)}
