"""RAG pipeline for a YouTube chatbot.

Flow: URL -> video id -> transcript -> chunks -> embeddings -> FAISS
      -> retriever -> prompt (context + history + question) -> LLM -> parser
"""
import os
import re
from operator import itemgetter
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv
from youtube_transcript_api import (
    CouldNotRetrieveTranscript,
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
    YouTubeTranscriptApi,
)
from langchain_community.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda, RunnableParallel
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()  # .env file se GROQ_API_KEY load hoti hai

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL = "openai/gpt-oss-120b"

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


class TranscriptError(Exception):
    """Transcript fetch na ho sake to user-friendly message ke sath."""


# --------------------------------------------------------------------------
# Step 0: URL -> video id
# --------------------------------------------------------------------------
def extract_video_id(url_or_id: str) -> str:
    """Har common YouTube URL format (ya seedhi 11-char id) se video id nikalta hai."""
    text = (url_or_id or "").strip()
    if _ID_RE.match(text):
        return text

    if "://" not in text:
        text = "https://" + text
    parsed = urlparse(text)
    host = (parsed.hostname or "").lower()

    video_id = None
    if host == "youtu.be":
        video_id = parsed.path.lstrip("/").split("/")[0]
    elif host.endswith("youtube.com") or host.endswith("youtube-nocookie.com"):
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [None])[0]
        else:
            parts = [p for p in parsed.path.split("/") if p]
            if len(parts) >= 2 and parts[0] in {"embed", "shorts", "live", "v"}:
                video_id = parts[1]

    if video_id and _ID_RE.match(video_id):
        return video_id
    raise ValueError("Yeh valid YouTube URL nahi lag raha. Please link dobara check karein.")


# --------------------------------------------------------------------------
# Step 1: Document ingestion
# --------------------------------------------------------------------------
def fetch_transcript(video_id: str, languages=("en", "hi", "ur")) -> str:
    """Transcript fetch karke aik bari string bana deta hai."""
    api = YouTubeTranscriptApi()
    try:
        try:
            fetched = api.fetch(video_id, languages=list(languages))
        except NoTranscriptFound:
            # Pasandida languages nahi mili to jo bhi pehli available ho wo le lo
            fetched = next(iter(api.list(video_id))).fetch()
    except TranscriptsDisabled:
        raise TranscriptError("Is video ke captions disabled hain.")
    except VideoUnavailable:
        raise TranscriptError("Video available nahi hai (private ya removed ho sakti hai).")
    except (NoTranscriptFound, StopIteration):
        raise TranscriptError("Is video ke liye koi transcript nahi mila.")
    except CouldNotRetrieveTranscript as exc:
        raise TranscriptError(f"Transcript fetch nahi ho saka: {exc}")

    return " ".join(snippet.text for snippet in fetched)


# --------------------------------------------------------------------------
# Step 2: Split -> embed -> vector store
# --------------------------------------------------------------------------
def split_transcript(transcript: str, chunk_size: int = 1000, chunk_overlap: int = 200):
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.create_documents([transcript])


def get_embeddings():
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


def build_vector_store(chunks, embeddings):
    return FAISS.from_documents(chunks, embeddings)


# --------------------------------------------------------------------------
# Step 3: Retrieval + augmentation + generation (chain)
# --------------------------------------------------------------------------
PROMPT = PromptTemplate(
    template="""You are a helpful assistant answering questions about a YouTube video.
Answer ONLY from the transcript context below.
If the context is insufficient, say you don't know. Do not make things up.
Reply in the same language the user writes in.

Transcript context:
{context}

Chat history:
{history}

Question: {question}

Answer:""",
    input_variables=["context", "history", "question"],
)


def format_docs(docs) -> str:
    return "\n\n".join(doc.page_content for doc in docs)


def format_history(messages, max_turns: int = 6) -> str:
    """messages = [{'role': 'user'|'assistant', 'content': str}, ...]"""
    recent = messages[-max_turns * 2:]
    if not recent:
        return "No previous messages."
    return "\n".join(
        f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}" for m in recent
    )


def get_llm():
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("GROQ_API_KEY set nahi hai. .env file ya environment variable mein add karein.")
    return ChatGroq(model=LLM_MODEL, temperature=0.3)


def build_chain(vector_store, k: int = 5):
    """Chain input: {'question': str, 'history': str}  ->  output: str"""
    retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": k})
    parallel_chain = RunnableParallel(
        {
            "context": itemgetter("question") | retriever | RunnableLambda(format_docs),
            "question": itemgetter("question"),
            "history": itemgetter("history"),
        }
    )
    return parallel_chain | PROMPT | get_llm() | StrOutputParser()