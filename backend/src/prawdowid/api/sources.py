from fastapi import APIRouter

from prawdowid.api.deps import ServicesDep
from prawdowid.schemas import SourceCatalog, SourceInfo

router = APIRouter(prefix="/v1", tags=["sources"])


@router.get("/sources")
async def get_sources(services: ServicesDep) -> SourceCatalog:
    """The auditable source catalog (brief §5 "Źródła"), with per-source document counts."""
    stats = services.corpus.get_stats() if services.corpus is not None else None
    counts = stats.documents_by_source if stats else {}
    return SourceCatalog(
        corpus_version=services.pipeline.corpus_version,
        documents=stats.documents if stats else 0,
        chunks=stats.chunks if stats else 0,
        sources=[
            SourceInfo(
                id=source.id,
                name=source.name,
                publisher=source.publisher,
                domain=source.domain,
                urls=[str(url) for url in source.urls],
                type=source.type,
                quality_tier=source.quality_tier,
                fetch_mode=source.fetch_mode.value,
                use=source.use.value,
                license=source.license,
                license_verified=source.license_verified,
                qualification=source.qualification,
                excluded=source.excluded,
                exclusion_reason=source.exclusion_reason,
                documents=counts.get(source.id, 0),
            )
            for source in services.sources
        ],
    )
