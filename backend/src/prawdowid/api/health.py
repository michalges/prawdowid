from importlib.metadata import version

from fastapi import APIRouter

from prawdowid.api.deps import ServicesDep
from prawdowid.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health")
async def get_health(services: ServicesDep) -> HealthResponse:
    corpus = services.corpus
    return HealthResponse(
        status="ok",
        version=version("prawdowid"),
        llm_provider=services.pipeline.llm.model_id,
        corpus_version=services.pipeline.corpus_version,
        corpus_chunks=corpus.chunk_count if corpus else 0,
        embedding_model=services.embedder.model_id,
        ocr=services.ocr.name,
        factcheck_enabled=services.pipeline.factcheck.is_enabled,
        moderator_notifications=services.pipeline.cases.notifier.is_configured,
        data_processing_pl=services.get_data_processing_note(),
    )
