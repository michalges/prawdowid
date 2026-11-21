from pathlib import Path

import yaml
from pydantic import TypeAdapter

from prawdowid.corpus.models import SourceEntry

SOURCE_LIST_ADAPTER = TypeAdapter(list[SourceEntry])


class SourceCatalogError(ValueError):
    pass


def load_sources(path: Path) -> list[SourceEntry]:
    raw_entries = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    sources = SOURCE_LIST_ADAPTER.validate_python(raw_entries)
    duplicate_ids = {
        source.id for source in sources if [s.id for s in sources].count(source.id) > 1
    }
    if duplicate_ids:
        raise SourceCatalogError(f"Duplicate source ids: {sorted(duplicate_ids)}")
    return sources
