import os
from typing import Any, Iterable, List, Optional

import gradio as gr
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

load_dotenv()

DEBUG = os.getenv("DEBUG", "0").lower() in {"1", "true", "yes"}

# --- LLM ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY in environment (.env).")

llm = init_chat_model(
    "gpt-5-nano",
    model_provider="openai",
    api_key=OPENAI_API_KEY,
    temperature=float(os.getenv("LLM_TEMPERATURE", "1")),
)

# --- RAG retriever ---
from agent.create_retreiver import load_vector_store  # noqa: E402

RAG_VECTOR_DB_PATH = os.getenv("RAG_VECTOR_DB_PATH", "data/FAISS")
RAG_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "intfloat/e5-base-v2")
retriever = load_vector_store(RAG_EMBEDDING_MODEL, RAG_VECTOR_DB_PATH)

# --- Rate limiter ---
from agent.restrict_usage import RateLimiter  # noqa: E402

limiter = RateLimiter(
    max_requests=int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "5")),
    window_minutes=int(os.getenv("RATE_LIMIT_WINDOW_MINUTES", "60")),
)


def format_source(doc: Any) -> str:
    """Format source metadata in a human-friendly way."""
    metadata = getattr(doc, "metadata", {}) or {}
    source = metadata.get("source") or metadata.get("source_url") or "Unknown source"

    if "api.github" in source:
        return source.split("/blob")[0].replace("api.", "")

    if source.startswith(("http://", "https://")):
        return source

    if "data" in source:
        page_label = metadata.get("page_label")
        total_pages = metadata.get("total_pages")
        filename = source.split("/")[-1]
        if page_label is not None and total_pages:
            return f"{filename} page({page_label}/{total_pages})"
        return filename

    return str(source)


def _iter_history_turns(history: Any) -> Iterable[tuple[Optional[str], Optional[str]]]:
    """Yield (user_msg, assistant_msg) tuples from gradio history."""
    if not history:
        return

    for item in history:
        # Typical gr.ChatInterface format: List[Tuple[user, bot]]
        if isinstance(item, (list, tuple)) and len(item) == 2:
            yield (item[0], item[1])
            continue

        # Fallback: dict-like messages
        if isinstance(item, dict):
            role = item.get("role")
            content = item.get("content")
            if role == "user":
                yield (content, None)
            elif role == "assistant":
                yield (None, content)


def normalize_history(history: Any, max_turns: int = 6) -> List[Any]:
    """Convert gradio history to LangChain messages."""
    turns = list(_iter_history_turns(history))[-max_turns:]

    msgs: List[Any] = []
    for user_msg, bot_msg in turns:
        if user_msg:
            msgs.append(HumanMessage(content=str(user_msg)))
        if bot_msg:
            msgs.append(AIMessage(content=str(bot_msg)))
    return msgs


def safeguard(message: str) -> bool:
    triage = (
        "You are a Safeguard assistant making sure the user only ask for information "
        "related to Rémi Cazelles's projects, work and education. "
        "If the question is not related to these topics, or if the request is harmful, "
        "you should answer exactly '*** FLAGGED ***' else simply answer exactly '*** OK ***'."
    )

    resp = llm.invoke(
        [SystemMessage(content=triage), HumanMessage(content=message)],
        config={
            "tags": ["RAG-Bot", "safeguard"],
            "metadata": {"rag_llm": "gpt-5-nano"},
        },
    )

    content = (getattr(resp, "content", "") or "").strip()
    return "*** OK ***" in content


def route(message: str) -> str:
    routing_prompt = (
        "Does this question require specific information about Rémi Cazelles's projects, "
        "work, or education details?\n"
        "Answer ONLY 'RAG' if it needs specific facts/details, or 'CHAT' if it's a general "
        "greeting/chitchat.\n"
        f"Question: {message}"
    )

    resp = llm.invoke([HumanMessage(content=routing_prompt)])
    content = (getattr(resp, "content", "") or "").strip().upper()

    return "RAG" if content.startswith("RAG") else "CHAT"


# reranker 
from sentence_transformers import CrossEncoder
import numpy as np
import torch

class ProductionReranker:
    def __init__(self, model_name="jinaai/jina-reranker-v2-base-multilingual"):
        self.model = CrossEncoder(
            model_name,
            max_length=512,
            device='cuda' if torch.cuda.is_available() else 'cpu',
            trust_remote_code=True
        )
    
    def rerank(self, query, documents, k=5):
        # Extract text
        doc_texts = [
            doc.page_content if hasattr(doc, 'page_content') else str(doc) 
            for doc in documents
        ]
        
        # Score in batches for efficiency
        pairs = [[query, doc] for doc in doc_texts]
        scores = self.model.predict(pairs, batch_size=32)
        
        # Get top-k
        top_indices = np.argsort(scores)[::-1][:k]
        
        # Return with scores
        reranked = [(documents[i], float(scores[i])) for i in top_indices]
        return [doc for doc, score in reranked]


def predict(message: str, history: Any, request: gr.Request):
    message = (message or "").strip()
    if not message:
        return ""

    # Rate limit
    client_ip = None
    try:
        client = getattr(request, "client", None)
        client_ip = getattr(client, "host", None)
    except Exception:
        client_ip = None

    if client_ip and not limiter.is_allowed(client_ip):
        return (
            f"**Rate limit exceeded.** You've used {limiter.max_requests} requests per hour. "
            "Please try again in an hour.\n"
            "LinkedIn Profile : https://www.linkedin.com/in/rcaz33/"
        )

    # Safeguard
    if not safeguard(message):
        return "This app can only answer questions about Rémi Cazelles's projects, work and education."

    # Build history once (fixes the previous bug where CHAT branch used an undefined variable)
    history_langchain = normalize_history(history, max_turns=6)

    # Route
    if route(message) == "CHAT":
        messages = [
            SystemMessage(
                content=(
                    "You are a helpful assistant providing information about Rémi Cazelles' professional "
                    "career. Keep responses brief and friendly."
                )
            ),
            *history_langchain,
            HumanMessage(content=message),
        ]
        response = llm.invoke(messages)
        return response.content

    # RAG
    print("retreive docs ...")
    top_k = int(os.getenv("RAG_TOP_K", "20"))
    relevant_docs = retriever.similarity_search(message, k=top_k)

    # reank docs
    print("reranking ...")
    RERANKER = ProductionReranker()
    top_r = int(os.getenv("RAG_TOP_R", "10"))
    relevant_docs = RERANKER.rerank(message, relevant_docs, k=top_r)

    # Build context from retrieved documents
    print("build context ...")
    context = "\nExtracted documents:\n" + "\n".join([
        f"Content document {i+1}: {doc.page_content}\n\n---"
        for i, doc in enumerate(relevant_docs)
    ])








    max_doc_chars = int(os.getenv("RAG_MAX_DOC_CHARS", "1800"))
    context_chunks = []
    for i, doc in enumerate(relevant_docs, start=1):
        text = getattr(doc, "page_content", "") or ""
        context_chunks.append(f"[{i}] {text[:max_doc_chars]}")

    context = "\n\n".join(context_chunks)

    rag_system = (
        "You are an assistant answering questions using ONLY the provided context. "
        "All information in the context is about Rémi Cazelles's projects, work, and education. "
        "If the answer cannot be deduced from the context, say that you cannot find the answer in the sources."
    )

    messages = [
        SystemMessage(content=rag_system),
        *history_langchain,
        HumanMessage(content=f"Context:\n{context}\n\nQuestion: {message}"),
    ]

    if DEBUG:
        print("[DEBUG] Retrieved docs:", len(relevant_docs))

    gpt_response = llm.invoke(
        messages,
        config={
            "tags": ["RAG-Bot", "V1"],
            "metadata": {
                "rag_llm": "gpt-5-nano",
                "num_retrieved_docs": len(relevant_docs),
            },
        },
    )

    sources = "\n".join([f"- {format_source(doc)}" for doc in relevant_docs])
    return f"{gpt_response.content}\n\nSources:\n{sources}"


# --- LangSmith tracing ---
os.environ["LANGSMITH_PROJECT"] = "Test_avatar_bot"
os.environ["LANGSMITH_TRACING"] = "true"
if os.environ.get("LANGSMITH_API_KEY"):
    os.environ["LANGSMITH_API_KEY"] = os.environ["LANGSMITH_API_KEY"]

# Default endpoint
os.environ.setdefault("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")


iface = gr.ChatInterface(
    predict,
    api_name="chat",
    chatbot=gr.Chatbot(placeholder="Hello! Ask me about Rémi Cazelles's projects, work, or education."),
    description="Ask me anything about Rémi’s work, projects, or education. I’ll cite the source documents.",
    examples=[
        "How many years of experience does Rémi have in Python, and what significant project did he work on?",
        "When did Rémi graduate from his doctorate, and what was his research topic?",
        "I have a project in *** using ***, will Rémi be able to contribute readily?",
    ],
)

iface.launch()
