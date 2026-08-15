import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from controllers.NLPController import NLPController
from dependencies.auth import get_current_user
from models.AssetModel import AssetModel
from models.ChunkModel import ChunkModel
from models.ProjectModel import ProjectModel
from schemas.auth import CurrentUserResponse
from schemas.search import (
    AskRequest,
    AskResponse,
    CitationInfo,
    HybridSearchRequest,
    HybridSearchResponse,
    HybridSearchResult,
)
from utils.conversation import local_conversation_response
from utils.cohere_reranker import CohereReranker
from utils.result_deduplicator import ResultDeduplicator
from utils.query_rewriter import QueryRewriter


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


async def _hybrid(
    request,
    project,
    tenant_id,
    payload,
):
    chunk_model = await ChunkModel.create_instance(
        db_client=request.app.db_client
    )

    keyword_results = await chunk_model.keyword_search(
        tenant_id=tenant_id,
        project_id=project.project_id,
        query_text=payload.query,
        limit=payload.keyword_limit,
    )

    use_rerank = (
        bool(payload.rerank)
        and CohereReranker.enabled()
    )

    candidate_limit = (
        min(
            max(
                payload.rerank_candidates,
                payload.limit,
            ),
            100,
        )
        if use_rerank
        else payload.limit
    )

    results = await _nlp(
        request
    ).hybrid_search(
        project=project,
        query=payload.query,
        keyword_results=keyword_results,
        limit=candidate_limit,
        semantic_limit=max(
            payload.semantic_limit,
            candidate_limit,
        ),
        rrf_k=payload.rrf_k,
    )

    if not results:
        return []

    deduplicator = getattr(
        request.app,
        "result_deduplicator",
        None,
    )

    if deduplicator is None:
        deduplicator = ResultDeduplicator(
            similarity_threshold=0.92,
            shingle_size=5,
        )

        request.app.result_deduplicator = (
            deduplicator
        )

    # Remove duplicated candidates before Cohere.
    unique_candidates = (
        deduplicator.deduplicate(results)
    )

    if not unique_candidates:
        return []

    if not use_rerank:
        return unique_candidates[:payload.limit]

    reranker = getattr(
        request.app,
        "reranker_client",
        None,
    )

    if reranker is None:
        reranker = (
            CohereReranker.from_environment()
        )

        request.app.reranker_client = reranker

    reranked_results = await reranker.rerank(
        query=payload.query,
        results=unique_candidates,
        top_n=min(
            payload.limit * 2,
            len(unique_candidates),
        ),
    )

    # Final protection against duplicated results.
    final_results = deduplicator.deduplicate(
        reranked_results,
        limit=payload.limit,
    )

    return final_results


def _positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 1 else None


def _citation_from_result(
    item: dict,
    asset,
) -> CitationInfo:
    metadata = dict(item.get("metadata") or {})
    asset_config = dict(getattr(asset, "asset_config", None) or {})

    stored_file_name = (
        metadata.get("stored_file_name")
        or metadata.get("file_id")
        or getattr(asset, "asset_name", None)
    )
    original_file_name = (
        asset_config.get("original_file_name")
        or metadata.get("original_file_name")
        or stored_file_name
        or "unknown-file"
    )
    file_type = metadata.get("file_type")
    if not file_type and original_file_name:
        file_type = str(original_file_name).rsplit(".", 1)[-1].lower()

    page_number = _positive_int(metadata.get("page_number"))
    if page_number is None:
        page_index = metadata.get("page_index")
        if page_index is None:
            page_index = metadata.get("page")
        try:
            page_number = int(page_index) + 1
        except (TypeError, ValueError):
            page_number = None

    row_start = _positive_int(metadata.get("row_start"))
    row_end = _positive_int(metadata.get("row_end"))
    if row_start is not None and row_end is None:
        row_end = row_start

    sheet_name = metadata.get("sheet_name") or None

    return CitationInfo(
        file_name=str(original_file_name),
        stored_file_name=(
            str(stored_file_name)
            if stored_file_name
            else None
        ),
        file_type=str(file_type) if file_type else None,
        page_number=page_number,
        sheet_name=str(sheet_name) if sheet_name else None,
        row_start=row_start,
        row_end=row_end,
    )


async def _enrich_results_with_citations(
    request: Request,
    tenant_id,
    results: list[dict],
) -> list[dict]:
    if not results:
        return []

    asset_model = await AssetModel.create_instance(
        db_client=request.app.db_client
    )
    assets: dict[int, Any] = {}
    for item in results:
        asset_id = item.get("asset_id")
        if asset_id is None or asset_id in assets:
            continue
        asset = await asset_model.get_asset_by_id(
            tenant_id=tenant_id,
            asset_id=int(asset_id),
        )
        if asset is not None:
            assets[int(asset_id)] = asset

    enriched_results: list[dict] = []
    for result in results:
        item = dict(result)
        asset_id = item.get("asset_id")
        asset = assets.get(int(asset_id)) if asset_id is not None else None
        item["citation"] = _citation_from_result(item, asset)
        enriched_results.append(item)
    return enriched_results


def _clean_answer_citation_markers(answer: str) -> str:
    clean_answer = str(answer or "")
    clean_answer = re.sub(
        r"\[\s*(?:Document|Source)\s+\d+\s*\]",
        "",
        clean_answer,
        flags=re.IGNORECASE,
    )
    clean_answer = re.sub(
        r"\[\s*المستند\s+\d+\s*\]",
        "",
        clean_answer,
    )
    clean_answer = re.sub(r"[ \t]{2,}", " ", clean_answer)
    clean_answer = re.sub(r"\n{3,}", "\n\n", clean_answer)
    return clean_answer.strip()


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
    results = await _enrich_results_with_citations(
        request=request,
        tenant_id=tenant_id,
        results=results,
    )
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
    current_user: CurrentUserResponse = Depends(
        get_current_user
    ),
):
    tenant_id = current_user.user.tenant_id

    project = await _get_project(
        request,
        tenant_id,
        project_id,
    )

    # Handle greetings and simple conversation locally.
    local_answer = local_conversation_response(
        payload.question
    )

    if local_answer is not None:
        return AskResponse(
            project_id=project_id,
            question=payload.question,
            search_query=payload.question,
            answer=local_answer,
            sources=[],
        )

    # Start with the original question.
    search_query = payload.question

    # Rewrite follow-up questions using conversation history.
    if (
        payload.rewrite_query
        and payload.conversation_history
    ):
        query_rewriter = getattr(
            request.app,
            "query_rewriter",
            None,
        )

        if query_rewriter is None:
            query_rewriter = (
                QueryRewriter.from_environment(
                    generation_client=(
                        request.app.generation_client
                    ),
                )
            )

            request.app.query_rewriter = (
                query_rewriter
            )

        search_query = await query_rewriter.rewrite(
            question=payload.question,
            conversation_history=(
                payload.conversation_history
            ),
        )

    search_payload = HybridSearchRequest(
        query=search_query,
        limit=payload.limit,
        semantic_limit=payload.semantic_limit,
        keyword_limit=payload.keyword_limit,
        rrf_k=payload.rrf_k,
        rerank=payload.rerank,
        rerank_candidates=(
            payload.rerank_candidates
        ),
    )

    results = await _hybrid(
        request,
        project,
        tenant_id,
        search_payload,
    )

    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "no relevant indexed content was found"
            ),
        )

    # The user-facing answer still receives the original question.
    answer = await _nlp(
        request
    ).answer_from_hybrid_results(
        question=payload.question,
        results=results,
        conversation_history=(
            payload.conversation_history
        ),
    )
    clean_answer = (
        _clean_answer_citation_markers(answer)
    )

    enriched_results = (
        await _enrich_results_with_citations(
            request=request,
            tenant_id=tenant_id,
            results=results,
        )
    )

    return AskResponse(
        project_id=project_id,
        question=payload.question,
        search_query=search_query,
        answer=clean_answer,
        sources=[
            HybridSearchResult(**item)
            for item in enriched_results
        ],
    )

