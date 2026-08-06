from fastapi import APIRouter, Depends, HTTPException, Request, status

from controllers.NLPController import NLPController
from dependencies.auth import get_current_user
from models.ChunkModel import ChunkModel
from models.ProjectModel import ProjectModel
from schemas.auth import CurrentUserResponse
from schemas.search import (
    AskRequest,
    AskResponse,
    HybridSearchRequest,
    HybridSearchResponse,
    HybridSearchResult,
)


search_router = APIRouter(
    prefix="/api/v1/projects",
    tags=["search and rag"],
)


async def _get_project(request, tenant_id, project_id):
    model = await ProjectModel.create_instance(
        db_client=request.app.db_client
    )
    project = await model.get_project_by_id(
        tenant_id=tenant_id,
        project_id=project_id,
    )
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="project not found",
        )
    return project


def _nlp(request: Request) -> NLPController:
    return NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
    )


async def _hybrid(request, project, tenant_id, payload):
    chunk_model = await ChunkModel.create_instance(
        db_client=request.app.db_client
    )
    keyword_results = await chunk_model.keyword_search(
        tenant_id=tenant_id,
        project_id=project.project_id,
        query_text=payload.query,
        limit=payload.keyword_limit,
    )
    return await _nlp(request).hybrid_search(
        project=project,
        query=payload.query,
        keyword_results=keyword_results,
        limit=payload.limit,
        semantic_limit=payload.semantic_limit,
        rrf_k=payload.rrf_k,
    )


@search_router.post(
    "/{project_id}/search",
    response_model=HybridSearchResponse,
)
async def hybrid_search(
    request: Request,
    project_id: int,
    payload: HybridSearchRequest,
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    tenant_id = current_user.user.tenant_id
    project = await _get_project(request, tenant_id, project_id)
    results = await _hybrid(request, project, tenant_id, payload)
    return HybridSearchResponse(
        project_id=project_id,
        query=payload.query,
        results=[HybridSearchResult(**item) for item in results],
        total=len(results),
    )


@search_router.post(
    "/{project_id}/ask",
    response_model=AskResponse,
)
async def ask_project(
    request: Request,
    project_id: int,
    payload: AskRequest,
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    tenant_id = current_user.user.tenant_id
    project = await _get_project(request, tenant_id, project_id)
    search_payload = HybridSearchRequest(
        query=payload.question,
        limit=payload.limit,
        semantic_limit=payload.semantic_limit,
        keyword_limit=payload.keyword_limit,
        rrf_k=payload.rrf_k,
    )
    results = await _hybrid(
        request, project, tenant_id, search_payload
    )
    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="no relevant indexed content was found",
        )
    answer = _nlp(request).answer_from_hybrid_results(
        question=payload.question,
        results=results,
    )
    return AskResponse(
        project_id=project_id,
        question=payload.question,
        answer=answer,
        sources=[HybridSearchResult(**item) for item in results],
    )
