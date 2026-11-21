"""Admin endpoints (Bearer ADMIN_TOKEN): metrics, moderator cases, export."""

import csv
import io
import json
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import Response

from prawdowid.api.deps import AdminDep, ServicesDep

router = APIRouter(tags=["admin"])

EXPORT_TABLES = ("checks", "cases", "events")


@router.get("/metrics")
async def get_metrics(_admin: AdminDep, services: ServicesDep) -> dict:
    metrics = services.database.get_metrics()
    metrics["corpus_version"] = services.pipeline.corpus_version
    metrics["llm"] = services.pipeline.llm.model_id
    return metrics


@router.get("/v1/cases")
async def list_cases(_admin: AdminDep, services: ServicesDep) -> list[dict]:
    return services.database.get_rows("cases")


@router.get("/v1/cases/{case_id}")
async def get_case(case_id: UUID, _admin: AdminDep, services: ServicesDep) -> dict:
    case = services.database.get_case(str(case_id))
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    return {
        "case_id": case.case_id,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
        "claim_text": case.claim_text,
        "status": case.status,
        "report_count": case.report_count,
        "high_risk": case.high_risk,
        "handed_over_at": case.handed_over_at,
    }


@router.get("/v1/export")
async def export_data(
    _admin: AdminDep,
    services: ServicesDep,
    table: Annotated[Literal["checks", "cases", "events"], Query()] = "checks",
    format: Annotated[Literal["json", "csv"], Query()] = "json",
) -> Response:
    rows = services.database.get_rows(table)
    if format == "json":
        return Response(
            json.dumps(rows, ensure_ascii=False, default=str),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="prawdowid-{table}.json"'},
        )
    buffer = io.StringIO()
    if rows:
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return Response(
        buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="prawdowid-{table}.csv"'},
    )
