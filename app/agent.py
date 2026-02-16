"""RAG-based agent: retrieve relevant data from CSV, inject into prompt, let LLM answer.

Flow: User Query -> Retrieve Context (CSV) -> Build Prompt -> LLM -> Answer

The LLM generates every answer using the retrieved data.
If the queried cancer type or gene is not in the dataset, the LLM tells the user.
"""
import concurrent.futures
import logging
from typing import AsyncIterator

from langchain_community.chat_models import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from config.settings import OLLAMA_BASE_URL, OLLAMA_MODEL
from app.data import (
    get_targets as _get_targets,
    get_expressions_for_cancer as _get_expressions_for_cancer,
    get_available_cancers,
    get_all_genes,
    get_expressions,
)

logger = logging.getLogger(__name__)

INVOKE_TIMEOUT_SEC = 600


# ── LLM ──────────────────────────────────────────────────────────────

def _build_llm(num_predict: int = 256):
    return ChatOllama(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_MODEL,
        temperature=0,
        num_predict=num_predict,
        num_ctx=2048,
    )


def get_model_name() -> str:
    return OLLAMA_MODEL


# ── Context retrieval ────────────────────────────────────────────────

def _retrieve_context(query: str) -> str:
    """Scan the query for cancer types and gene names that exist in the CSV.

    Returns a structured data block injected into the LLM prompt.
    """
    q_lower = query.lower()
    cancers = get_available_cancers()
    all_genes = get_all_genes()
    cancer_list_str = ", ".join(cancers)

    mentioned_cancers = [c for c in cancers if c.lower() in q_lower]
    q_clean = q_lower.replace(",", " ").replace(";", " ").replace("?", " ").replace(".", " ")
    q_tokens = set(q_clean.split())
    mentioned_genes = [g for g in all_genes if g.lower() in q_tokens]

    parts: list[str] = []

    for cancer in mentioned_cancers:
        targets = _get_targets(cancer)
        if targets:
            exprs = _get_expressions_for_cancer(cancer, targets)
            lines = [f"Cancer type: {cancer}"]
            lines.append(f"Gene targets ({len(targets)}): {', '.join(targets)}")
            if exprs:
                lines.append("Median expression values:")
                for gene in targets:
                    val = exprs.get(gene)
                    if val is not None:
                        lines.append(f"  - {gene}: {val}")
            parts.append("\n".join(lines))

    if mentioned_genes and not mentioned_cancers:
        exprs = get_expressions(mentioned_genes)
        if exprs:
            lines = ["Requested gene expression values:"]
            for gene, val in exprs.items():
                lines.append(f"  - {gene}: {val}")
            parts.append("\n".join(lines))

    if parts:
        return "\n\n".join(parts)

    q_words = [w.strip("?.,!") for w in q_lower.split() if len(w) > 3]
    skip = {"what", "which", "that", "this", "with", "from", "have", "been",
            "genes", "gene", "cancer", "involved", "main", "median", "value",
            "expression", "values", "help", "your", "about", "tell"}
    hint = next((w for w in q_words if w not in skip), "the requested topic")
    return (
        f'No data found for "{hint}" in the dataset.\n'
        f"Available cancer types: {cancer_list_str}."
    )


# ── Prompt ───────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are a cancer gene research assistant. You have access to a dataset of cancer types, \
their gene targets, and median expression values.

RETRIEVED DATA:
{context}

INSTRUCTIONS:
- Answer the user's question using ONLY the data above.
- If the data says "No data found", tell the user their cancer type is not in the dataset \
and list the available cancer types.
- When the user asks about genes for a cancer, list the gene names from the data.
- When the user asks about expression values, list gene names with their values from the data.
- Be concise and accurate. Do not invent data."""


def _build_prompt(query: str) -> list:
    """Build system + human message pair with retrieved context."""
    context = _retrieve_context(query)
    logger.info("retrieved context (%d chars) for query: %s", len(context), query[:80])
    return [
        SystemMessage(content=SYSTEM_PROMPT.format(context=context)),
        HumanMessage(content=query),
    ]


# ── Invoke ───────────────────────────────────────────────────────────

def _output_to_str(output) -> str:
    if output is None:
        return ""
    if hasattr(output, "content"):
        return (output.content or "").strip()
    return (str(output) or "").strip()


def _invoke_impl(query: str) -> str:
    """Retrieve context, call LLM once, return answer."""
    q = (query or "").strip()
    if not q:
        q = "How can you help me?"

    messages = _build_prompt(q)
    llm = _build_llm()
    response = llm.invoke(messages)
    answer = _output_to_str(response)

    if not answer:
        return "I couldn't generate an answer. Please try rephrasing your question."

    logger.info("LLM answered (%d chars)", len(answer))
    return answer


def invoke(query: str) -> str:
    """Run with a timeout so the UI WebSocket doesn't drop."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(_invoke_impl, (query or "").strip())
        try:
            return future.result(timeout=INVOKE_TIMEOUT_SEC)
        except concurrent.futures.TimeoutError:
            return "The request took too long. Please try a simpler question."


async def invoke_stream(query: str) -> AsyncIterator[str]:
    """Stream answer in chunks for smooth UI display."""
    q = (query or "").strip()
    if not q:
        q = "How can you help me?"

    try:
        messages = _build_prompt(q)
        llm = _build_llm()
        response = llm.invoke(messages)
        answer = _output_to_str(response)
    except Exception as e:
        answer = f"Error: {str(e)}"

    if not answer:
        answer = "I couldn't generate an answer. Please try rephrasing your question."

    chunk_size = 15
    for i in range(0, len(answer), chunk_size):
        yield answer[i:i + chunk_size]
