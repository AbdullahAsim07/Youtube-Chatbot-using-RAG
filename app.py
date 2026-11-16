import html
import itertools
import json
import os
import time
import urllib.parse
import urllib.request

import streamlit as st

from rag_pipeline import (
    TranscriptError,
    build_chain,
    build_vector_store,
    extract_video_id,
    fetch_transcript,
    format_history,
    get_embeddings,
    split_transcript,
)

st.set_page_config(
    page_title="YouTube Chatbot",
    page_icon="🎬",
    layout="centered",
    initial_sidebar_state="expanded",
)

# On Streamlit Cloud the key comes from st.secrets; locally it comes from .env
try:
    if not os.getenv("GROQ_API_KEY") and "GROQ_API_KEY" in st.secrets:
        os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
except Exception:
    pass


# ====================================================================== styling
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=Instrument+Sans:wght@400;500;600&display=swap');

:root {
  --bg: #0A0C12;
  --surface: #12151F;
  --surface-2: #1A1E2C;
  --line: #262B3B;
  --text: #ECEEF5;
  --muted: #8B92A8;
  --accent: #7C86FF;
  --accent-2: #2DD4BF;
  --play: #FF4E45;
}

html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
  background: var(--bg);
  color: var(--text);
  font-family: 'Instrument Sans', system-ui, sans-serif;
}
h1, h2, h3 { font-family: 'Bricolage Grotesque', 'Instrument Sans', sans-serif; letter-spacing: -0.025em; }
footer, [data-testid="stDecoration"] { display: none !important; }
[data-testid="stHeader"] { background: transparent; }
.block-container, [data-testid="stMainBlockContainer"] {
  max-width: 780px; padding-top: 2rem; padding-bottom: 7rem; position: relative; z-index: 1;
}

/* ============ buttons (test-ids work on current Streamlit; kind= kept for older) ============ */
.stButton > button, [data-testid="stBaseButton-secondary"], [data-testid="stDownloadButton"] button {
  border-radius: 12px; border: 1px solid var(--line); background: var(--surface-2); color: var(--text);
  font-weight: 500; transition: transform .15s ease, border-color .15s ease, background .15s ease, box-shadow .15s ease;
}
.stButton > button:hover, [data-testid="stBaseButton-secondary"]:hover, [data-testid="stDownloadButton"] button:hover {
  border-color: var(--accent); background: #212638; transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(124,134,255,.14);
}
.stButton > button:active { transform: translateY(0); }
[data-testid^="stBaseButton-primary"], button[kind="primary"], button[kind="primaryFormSubmit"] {
  background: linear-gradient(135deg, #8E97FF, #6670F5); color: #0B0D1A; border: none; font-weight: 600;
  border-radius: 12px; height: 3rem; box-shadow: 0 8px 24px rgba(124,134,255,.35);
  transition: transform .15s ease, box-shadow .15s ease, filter .15s ease;
}
[data-testid^="stBaseButton-primary"]:hover, button[kind="primary"]:hover, button[kind="primaryFormSubmit"]:hover {
  transform: translateY(-1px); filter: brightness(1.08); box-shadow: 0 10px 30px rgba(124,134,255,.45); color: #0B0D1A;
}

/* ============ inputs ============ */
[data-testid="stTextInput"] input {
  background: transparent; border: none; height: 3rem; font-size: 1rem; color: var(--text);
}
[data-testid="stTextInput"] > div > div, [data-testid="stTextInputRootElement"] {
  background: var(--surface); border: 1px solid var(--line); border-radius: 12px;
  transition: border-color .2s, box-shadow .2s;
}
[data-testid="stTextInputRootElement"]:focus-within { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(124,134,255,.2); }
[data-testid="stForm"] { border: none; padding: 0; background: transparent; }

/* ============ home ============ */
.aurora { position: fixed; inset: 0; z-index: 0; pointer-events: none; overflow: hidden; }
.aurora i { position: absolute; width: 46vw; height: 46vw; border-radius: 50%; filter: blur(90px); opacity: .32; }
.aurora i:nth-child(1) { background: #5B64F0; top: -18vw; left: -8vw; animation: drift1 22s ease-in-out infinite alternate; }
.aurora i:nth-child(2) { background: #14B8A6; top: 6vw; right: -16vw; animation: drift2 26s ease-in-out infinite alternate; }
.aurora i:nth-child(3) { background: #E0457B; bottom: -26vw; left: 26vw; opacity: .18; animation: drift1 30s ease-in-out infinite alternate-reverse; }
@keyframes drift1 { to { transform: translate(8vw, 6vw) scale(1.15); } }
@keyframes drift2 { to { transform: translate(-9vw, 8vw) scale(1.1); } }

.hero { text-align: center; padding: 2.4rem 0 1.6rem; }
.hero .badge { display: inline-block; font-size: .82rem; color: var(--muted); border: 1px solid var(--line);
  background: rgba(18,21,31,.7); backdrop-filter: blur(8px); padding: .3rem .8rem; border-radius: 999px; margin-bottom: 1.2rem;
  animation: rise .7s cubic-bezier(.2,.8,.2,1) both; }
.hero h1 { font-size: clamp(2.5rem, 7vw, 4rem); font-weight: 800; line-height: 1.02; margin: 0 0 1rem;
  animation: rise .8s cubic-bezier(.2,.8,.2,1) .08s both; }
.hero h1 em { font-style: normal; background: linear-gradient(100deg, #9AA2FF, #2DD4BF); -webkit-background-clip: text;
  background-clip: text; color: transparent; }
.hero p { color: var(--muted); font-size: 1.1rem; max-width: 30rem; margin: 0 auto; animation: rise .8s cubic-bezier(.2,.8,.2,1) .16s both; }
@keyframes rise { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }

.st-key-urlbar { background: rgba(18,21,31,.72); backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
  border: 1px solid var(--line); border-radius: 20px; padding: 1rem 1rem .4rem; margin-top: .4rem;
  box-shadow: 0 20px 60px rgba(0,0,0,.45); }
.hint { color: var(--muted); font-size: .85rem; text-align: center; margin: .9rem 0 0; }

.feats { display: flex; gap: .6rem; justify-content: center; flex-wrap: wrap; margin: 1.6rem 0 0; }
.feats span { font-size: .85rem; color: var(--text); border: 1px solid var(--line); background: rgba(18,21,31,.6);
  padding: .4rem .8rem; border-radius: 999px; }

/* orchestrated demo: plays once */
.demo { margin: 2.4rem auto 0; max-width: 34rem; border: 1px solid var(--line); border-radius: 18px;
  background: rgba(18,21,31,.78); backdrop-filter: blur(10px); padding: 1rem 1.1rem 1.1rem; }
.demo .cap { font-size: .75rem; color: var(--muted); margin-bottom: .8rem; }
.demo .u, .demo .a, .demo .t { opacity: 0; animation: rise .5s ease forwards; }
.demo .u { margin-left: auto; width: fit-content; max-width: 80%; background: var(--surface-2); border-radius: 16px 16px 4px 16px;
  padding: .55rem .9rem; font-size: .92rem; animation-delay: 1s; }
.demo .t { height: 1.6rem; margin-top: .5rem; animation: blip 1.3s ease 1.7s forwards; overflow: hidden; }
.demo .a { margin-top: .5rem; font-size: .92rem; line-height: 1.55; color: #D5D8E6; animation-delay: 3.1s; }
@keyframes blip { 0% { opacity: 0; } 15%, 80% { opacity: 1; } 100% { opacity: 0; height: 0; margin: 0; } }

/* ============ sidebar ============ */
[data-testid="stSidebar"] { background: var(--surface); border-right: 1px solid var(--line); }
[data-testid="stSidebar"] .stButton > button { justify-content: flex-start; text-align: left; }
.side-label { color: var(--muted); font-size: .8rem; margin: 1.2rem 0 .45rem; }
.vtitle { font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700; font-size: 1.02rem; line-height: 1.3; margin: .8rem 0 .15rem; }
.vchan { color: var(--muted); font-size: .85rem; }
.pill { display: inline-block; padding: .22rem .7rem; border-radius: 999px; background: var(--surface-2);
  border: 1px solid var(--line); color: var(--muted); font-size: .78rem; margin-top: .7rem; }
.pill::before { content: ""; display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: #4ADE80;
  margin-right: .45rem; box-shadow: 0 0 0 0 rgba(74,222,128,.6); animation: ping 2.4s infinite; }
@keyframes ping { 70% { box-shadow: 0 0 0 7px rgba(74,222,128,0); } 100% { box-shadow: 0 0 0 0 rgba(74,222,128,0); } }

/* ============ chat ============ */
.chat-head h2 { font-size: 1.5rem; margin: 0 0 .15rem; line-height: 1.25; }
.chat-head p { color: var(--muted); margin: 0 0 1.2rem; font-size: .92rem; }

.empty { text-align: center; padding: 2.2rem 0 1.2rem; }
.empty h3 { font-size: 1.7rem; margin: 0 0 .4rem; }
.empty p { color: var(--muted); max-width: 28rem; margin: 0 auto; }

[class*="st-key-start"] button { min-height: 4rem; white-space: normal; text-align: left; justify-content: flex-start;
  background: var(--surface); padding: .8rem 1rem; border-radius: 14px; }

[data-testid="stChatMessage"] { padding: .35rem 0; gap: .8rem; background: transparent; border: none; }
[class*="st-key-um-"] [data-testid="stChatMessage"] {
  flex-direction: row-reverse; margin-left: auto; width: fit-content; max-width: 80%;
  background: var(--surface-2); border: 1px solid #2E3550; border-radius: 18px 18px 4px 18px; padding: .6rem 1rem;
}
[class*="st-key-um-"] [data-testid^="stChatMessageAvatar"] { display: none; }
[class*="st-key-am-"] [data-testid="stChatMessage"] { max-width: 100%; }
[data-testid^="stChatMessageAvatar"] { background: var(--surface-2); border: 1px solid var(--line); }
[data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li { line-height: 1.65; }

[data-testid="stChatInput"] { border-radius: 16px; border: 1px solid var(--line); background: var(--surface);
  box-shadow: 0 10px 40px rgba(0,0,0,.4); transition: border-color .2s, box-shadow .2s; }
[data-testid="stChatInput"]:focus-within { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(124,134,255,.2), 0 10px 40px rgba(0,0,0,.4); }
[data-testid="stBottom"] > div { background: linear-gradient(to top, var(--bg) 55%, transparent); }

.meta { color: var(--muted); font-size: .78rem; }

.typing { display: inline-flex; align-items: center; gap: 6px; padding: .45rem 0; color: var(--muted); font-size: .88rem; }
.typing span { width: 7px; height: 7px; border-radius: 50%; background: var(--accent); animation: bounce 1.1s infinite ease-in-out; }
.typing span:nth-child(2) { animation-delay: .15s; }
.typing span:nth-child(3) { animation-delay: .3s; }
.typing em { font-style: normal; margin-left: .35rem; }
@keyframes bounce { 0%, 80%, 100% { transform: translateY(0); opacity: .4; } 40% { transform: translateY(-5px); opacity: 1; } }

.loader { margin: 1.6rem auto 0; max-width: 24rem; text-align: center; }
.loader .track { position: relative; height: 4px; border-radius: 4px; background: var(--line); overflow: hidden; }
.loader .track::before { content: ""; position: absolute; top: 0; bottom: 0; width: 30%; border-radius: 4px; background: var(--play);
  animation: sweep 1.3s infinite ease-in-out; }
.loader p { color: var(--text); font-size: .95rem; margin: .9rem 0 .15rem; }
.loader small { color: var(--muted); }
@keyframes sweep { 0% { left: -30%; } 100% { left: 100%; } }

@media (max-width: 640px) { [class*="st-key-um-"] [data-testid="stChatMessage"] { max-width: 92%; } }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
  .demo .u, .demo .a { opacity: 1; } .demo .t { display: none; }
}
</style>
"""

TYPING_HTML = '<div class="typing"><span></span><span></span><span></span><em>Searching the transcript…</em></div>'

STARTERS = [
    ("📝 Summarize in 5 points", "Summarize this video in 5 points."),
    ("⭐ Key takeaways", "What are the most important takeaways from this video?"),
    ("❓ Quiz me", "Give me 5 important questions based on this video to test my understanding."),
    ("🧒 Explain it simply", "Explain the main idea of this video in simple terms, as if I were a beginner."),
]

st.markdown(CSS, unsafe_allow_html=True)


def stretch(fn, *args, **kwargs):
    """Full-width widget that works on both new and older Streamlit versions."""
    try:
        return fn(*args, width="stretch", **kwargs)
    except TypeError:
        return fn(*args, use_container_width=True, **kwargs)


# ====================================================================== caching
@st.cache_resource(show_spinner=False)
def load_embeddings():
    return get_embeddings()


@st.cache_resource(show_spinner=False)
def prepare_video(video_id: str):
    """Transcript -> chunks -> embeddings -> FAISS. Runs once per video."""
    transcript = fetch_transcript(video_id)
    chunks = split_transcript(transcript)
    vector_store = build_vector_store(chunks, load_embeddings())
    return vector_store, len(chunks)


@st.cache_resource(show_spinner=False)
def get_chain(video_id: str):
    vector_store, _ = prepare_video(video_id)
    return build_chain(vector_store)


@st.cache_data(show_spinner=False, ttl=86400)
def video_meta(video_id: str):
    """Title and channel name via YouTube oEmbed. Returns (None, None) if unavailable."""
    watch = urllib.parse.quote(f"https://www.youtube.com/watch?v={video_id}", safe="")
    try:
        with urllib.request.urlopen(f"https://www.youtube.com/oembed?format=json&url={watch}", timeout=4) as r:
            data = json.load(r)
        return data.get("title"), data.get("author_name")
    except Exception:
        return None, None


# ====================================================================== state
st.session_state.setdefault("page", "home")
st.session_state.setdefault("video_id", None)
st.session_state.setdefault("messages", [])
st.session_state.setdefault("pending", None)


def go_home():
    st.session_state.update(page="home", video_id=None, messages=[], pending=None)


def clear_chat():
    st.session_state.update(messages=[], pending=None)


def ask_quick(text: str):
    st.session_state.pending = text


def chat_markdown(title: str | None) -> str:
    lines = [f"# Chat about: {title or 'YouTube video'}", ""]
    for m in st.session_state.messages:
        who = "You" if m["role"] == "user" else "Assistant"
        lines += [f"**{who}:**", "", m["content"], ""]
    return "\n".join(lines)


# ====================================================================== chat pieces
def message_actions(i: int, msg: dict):
    """Feedback, copy and response time under an assistant message."""
    if msg["content"].startswith("⚠️"):
        return
    c1, c2, c3 = st.columns([1.1, 1.3, 3], vertical_alignment="center")
    with c1:
        if hasattr(st, "feedback"):
            st.feedback("thumbs", key=f"fb_{i}")
    with c2:
        with st.popover("📋 Copy"):
            st.code(msg["content"], language=None)
    with c3:
        if msg.get("secs") is not None:
            st.markdown(f'<span class="meta">Answered in {msg["secs"]}s</span>', unsafe_allow_html=True)


def render_message(i: int, msg: dict):
    is_user = msg["role"] == "user"
    with st.container(key=f"{'um' if is_user else 'am'}-{i}"):
        with st.chat_message(msg["role"], avatar="🙂" if is_user else "🎬"):
            st.markdown(msg["content"])
            if not is_user:
                message_actions(i, msg)


def empty_state():
    st.markdown(
        '<div class="empty"><h3>What do you want to know?</h3>'
        "<p>Answers come from this video's transcript. Pick a starting point or type your own question below.</p></div>",
        unsafe_allow_html=True,
    )
    with st.container(key="starters"):
        cols = st.columns(2)
        for i, (label, prompt) in enumerate(STARTERS):
            with cols[i % 2]:
                with st.container(key=f"start-{i}"):
                    stretch(st.button, label, key=f"starter_btn_{i}", on_click=ask_quick, args=(prompt,))


# ====================================================================== pages
def home_page():
    st.markdown('<div class="aurora"><i></i><i></i><i></i></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero"><span class="badge">Answers grounded in the transcript</span>'
        "<h1>Talk to any <em>YouTube</em> video</h1>"
        "<p>Paste a link, then ask questions, get summaries or quiz yourself on what is said.</p></div>",
        unsafe_allow_html=True,
    )

    with st.container(key="urlbar"):
        with st.form("url_form"):
            c1, c2 = st.columns([5, 1.6])
            with c1:
                url = st.text_input("YouTube link", placeholder="Paste a YouTube link…", label_visibility="collapsed")
            with c2:
                submitted = stretch(st.form_submit_button, "Start chatting", type="primary")

    st.markdown(
        '<p class="hint">Works with watch, youtu.be, shorts and embed links.</p>'
        '<div class="feats"><span>⚡ Streaming answers</span><span>🧠 Remembers the conversation</span>'
        "<span>⭐ One-click summaries</span></div>"
        '<div class="demo"><div class="cap">Example</div>'
        '<div class="u">Summarize the main points</div>'
        '<div class="t"><div class="typing"><span></span><span></span><span></span></div></div>'
        '<div class="a">The speaker walks through how a URL shortener works: it creates a short key, stores the mapping '
        "and redirects on lookup, then covers scaling and caching.</div></div>",
        unsafe_allow_html=True,
    )

    if not submitted:
        return
    if not url.strip():
        st.warning("Paste a YouTube link to continue.")
        return

    try:
        video_id = extract_video_id(url)
    except ValueError as exc:
        st.error(str(exc))
        return

    loader = st.empty()
    loader.markdown(
        '<div class="loader"><div class="track"></div><p>Reading the transcript and indexing the video…</p>'
        "<small>The first run can take a minute while the embedding model loads.</small></div>",
        unsafe_allow_html=True,
    )
    try:
        prepare_video(video_id)
    except TranscriptError as exc:
        loader.empty()
        st.error(str(exc))
        return
    except Exception as exc:
        loader.empty()
        st.error(f"Something went wrong while processing the video: {exc}")
        return
    loader.empty()

    st.session_state.update(page="chat", video_id=video_id, messages=[], pending=None)
    st.rerun()


def chat_page():
    video_id = st.session_state.video_id
    _, n_chunks = prepare_video(video_id)
    title, channel = video_meta(video_id)

    with st.sidebar:
        st.video(f"https://www.youtube.com/watch?v={video_id}")
        if title:
            st.markdown(f'<div class="vtitle">{html.escape(title)}</div>', unsafe_allow_html=True)
        if channel:
            st.markdown(f'<div class="vchan">{html.escape(channel)}</div>', unsafe_allow_html=True)
        st.markdown(f'<span class="pill">Transcript indexed · {n_chunks} chunks</span>', unsafe_allow_html=True)

        st.markdown('<div class="side-label">Shortcuts</div>', unsafe_allow_html=True)
        for i, (label, prompt) in enumerate(STARTERS):
            stretch(st.button, label, key=f"side_btn_{i}", on_click=ask_quick, args=(prompt,))

        st.markdown('<div class="side-label">Conversation</div>', unsafe_allow_html=True)
        if st.session_state.messages:
            stretch(st.download_button, "⬇️ Export chat", data=chat_markdown(title),
                    file_name="chat.md", mime="text/markdown")
            stretch(st.button, "🧹 Clear chat", key="clear_btn", on_click=clear_chat)
        stretch(st.button, "🔄 New video", key="new_video_btn", on_click=go_home)

    st.markdown(
        f'<div class="chat-head"><h2>{html.escape(title) if title else "Chat with the video"}</h2>'
        f'<p>{html.escape(channel) if channel else "Ask anything about this video."}</p></div>',
        unsafe_allow_html=True,
    )

    if not st.session_state.messages and not st.session_state.pending:
        empty_state()

    for i, msg in enumerate(st.session_state.messages):
        render_message(i, msg)

    question = st.chat_input("Ask something about the video…")
    if not question and st.session_state.pending:
        question, st.session_state.pending = st.session_state.pending, None
    if not question:
        return

    history = format_history(st.session_state.messages)
    st.session_state.messages.append({"role": "user", "content": question})
    render_message(len(st.session_state.messages) - 1, st.session_state.messages[-1])

    a_idx = len(st.session_state.messages)
    with st.container(key=f"am-{a_idx}"):
        with st.chat_message("assistant", avatar="🎬"):
            holder = st.empty()
            holder.markdown(TYPING_HTML, unsafe_allow_html=True)
            start = time.perf_counter()
            try:
                stream = iter(get_chain(video_id).stream({"question": question, "history": history}))
                first = next(stream, None)  # waits for retrieval + first token
                holder.empty()
                answer = st.write_stream(itertools.chain([first] if first else [], stream))
            except Exception as exc:
                holder.empty()
                answer = f"⚠️ Could not generate an answer: {exc}"
                st.error(answer)
            msg = {"role": "assistant", "content": answer, "secs": round(time.perf_counter() - start, 1)}
            st.session_state.messages.append(msg)
            message_actions(a_idx, msg)


if st.session_state.page == "chat" and st.session_state.video_id:
    chat_page()
else:
    home_page()