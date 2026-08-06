"""Steps 15-17: Ollama AI code review, RAG knowledge retrieval, architecture validation.

`rag_knowledge_retrieval` degrades gracefully to "skipped" until the RAG
module (app.rag, Phase 5) exists — it is imported lazily here rather than at
module load time so this pipeline runs standalone before that phase lands.
"""
from __future__ import annotations

from pathlib import Path

from app.core.llm.base import ProviderError
from app.pipelines.base import PipelineContext, StepResult

_REVIEW_SYSTEM_PROMPT = (
    "You are a senior code reviewer. Review the following changed source file(s) for bugs, "
    "security issues, and maintainability concerns. Be specific and concise. If you find no "
    "issues, say so plainly in one sentence."
)

_MAX_REVIEW_CHARS = 6000


def _read_changed_sources(ctx: PipelineContext) -> str:
    chunks = []
    for file_path in ctx.changed_files:
        path = Path(file_path)
        if path.suffix != ".py" or not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        chunks.append(f"# File: {path.name}\n{text}")
    return "\n\n".join(chunks)[:_MAX_REVIEW_CHARS]


def ollama_code_review(ctx: PipelineContext) -> StepResult:
    model = ctx.settings.models.harness_review_model
    if not model:
        return StepResult(
            step_id="ollama_review", step_name="Ollama AI code review", status="skipped",
            detail="No Harness review model selected in Settings.",
        )

    source = _read_changed_sources(ctx)
    if not source.strip():
        return StepResult(
            step_id="ollama_review", step_name="Ollama AI code review", status="skipped",
            detail="No reviewable Python source in this change set.",
        )

    try:
        review = ctx.llm_client.chat(
            provider_id=ctx.settings.models.harness_review_provider,
            model=model,
            prompt=source,
            system=_REVIEW_SYSTEM_PROMPT,
            temperature=ctx.settings.temperature,
            label="AI Code Review",
            run_id=ctx.run_id,
        )
    except ProviderError as exc:
        return StepResult(step_id="ollama_review", step_name="Ollama AI code review", status="failed", detail=str(exc))

    return StepResult(
        step_id="ollama_review",
        step_name="Ollama AI code review",
        status="success",
        detail=review[:500],
        data={"full_review": review},
    )


def rag_knowledge_retrieval(ctx: PipelineContext) -> StepResult:
    try:
        from app.rag.vector_store import RagStore
    except ImportError:
        return StepResult(
            step_id="rag_retrieval", step_name="RAG knowledge retrieval", status="skipped",
            detail="RAG knowledge base not yet configured (arrives in Phase 5).",
        )

    embedding_model = ctx.settings.models.rag_embedding_model
    if not embedding_model:
        return StepResult(
            step_id="rag_retrieval", step_name="RAG knowledge retrieval", status="skipped",
            detail="No RAG embedding model selected in Settings.",
        )

    store = RagStore()
    if store.is_empty():
        return StepResult(
            step_id="rag_retrieval", step_name="RAG knowledge retrieval", status="skipped",
            detail="No knowledge sources ingested yet (see the RAG tab).",
        )

    query = " ".join(Path(f).stem for f in ctx.changed_files)[:300] or "project overview"
    try:
        snippets = store.query(ctx.llm_client, ctx.settings.models.rag_embedding_provider, embedding_model, query, top_k=3)
    except Exception as exc:  # noqa: BLE001
        return StepResult(step_id="rag_retrieval", step_name="RAG knowledge retrieval", status="failed", detail=str(exc))

    if not snippets:
        return StepResult(step_id="rag_retrieval", step_name="RAG knowledge retrieval", status="success", detail="No relevant knowledge found.")

    return StepResult(
        step_id="rag_retrieval",
        step_name="RAG knowledge retrieval",
        status="success",
        detail=f"{len(snippets)} relevant snippet(s) retrieved.",
        data={"snippets": snippets},
    )


_IMPROVEMENT_RELEVANT_STEP_IDS = ("security_scan", "build_verification", "unit_tests", "static_analysis")


def suggest_code_improvements(ctx: PipelineContext) -> StepResult:
    """Graph Engineering's Code Improvement Agent: read-only suggestions based
    on sibling DAG nodes' results (security/build/test/static analysis) —
    unlike Loop Engineering, this never writes to the project's files."""
    model = ctx.settings.models.graph_review_model or ctx.settings.models.harness_review_model
    provider_id = ctx.settings.models.graph_review_provider or ctx.settings.models.harness_review_provider
    if not model:
        return StepResult(
            step_id="code_improvement", step_name="Code improvement suggestions", status="skipped",
            detail="No Graph review model selected in Settings.",
        )

    failing = [
        f"{step_id}: {ctx.results[step_id].detail}"
        for step_id in _IMPROVEMENT_RELEVANT_STEP_IDS
        if ctx.results.get(step_id) and ctx.results[step_id].status == "failed"
    ]
    if not failing:
        return StepResult(
            step_id="code_improvement", step_name="Code improvement suggestions", status="success",
            detail="No failing checks — nothing to improve.",
        )

    source = _read_changed_sources(ctx)
    prompt = "Failing checks:\n" + "\n".join(failing) + "\n\nRelevant source:\n" + source
    try:
        suggestions = ctx.llm_client.chat(
            provider_id=provider_id,
            model=model,
            prompt=prompt,
            system=(
                "Suggest specific, actionable code improvements to resolve the listed failing checks. "
                "Be concise and concrete."
            ),
            temperature=ctx.settings.temperature,
            label="Code Improvement Agent",
            run_id=ctx.run_id,
        )
    except ProviderError as exc:
        return StepResult(step_id="code_improvement", step_name="Code improvement suggestions", status="failed", detail=str(exc))

    return StepResult(
        step_id="code_improvement",
        step_name="Code improvement suggestions",
        status="success",
        detail=suggestions[:500],
        data={"full_suggestions": suggestions},
    )


def architecture_validation(ctx: PipelineContext) -> StepResult:
    project = ctx.project
    warnings: list[str] = []

    if not project.has_tests_dir:
        warnings.append("No tests/ directory found.")
    if not project.build_files:
        warnings.append("No recognizable Python build/dependency file (requirements.txt, pyproject.toml, ...).")
    if not any((project.root / name).exists() for name in ("README.md", "README.rst", "README.txt")):
        warnings.append("No README found at project root.")

    if warnings:
        return StepResult(step_id="architecture_validation", step_name="Architecture validation", status="failed", detail="; ".join(warnings))
    return StepResult(
        step_id="architecture_validation", step_name="Architecture validation", status="success",
        detail="Project structure looks consistent with expected conventions.",
    )
