<div align="center">

# 🎬 VideoMind — YouTube Chatbot using RAG

**Turn a YouTube transcript into a conversational resource. Paste a video link, then ask questions about its content.**

![Python](https://img.shields.io/badge/Python-application-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-interface-FF4B4B?logo=streamlit&logoColor=white)
![YouTube](https://img.shields.io/badge/YouTube-video-red?logo=youtube&logoColor=white)
![RAG](https://img.shields.io/badge/Pattern-RAG-7159c1)

[![Typing SVG](https://readme-typing-svg.demolab.com?font=DM+Sans&weight=600&size=20&pause=900&color=FF6B6B&center=true&vCenter=true&width=600&lines=Paste+a+YouTube+link;Read+the+available+transcript;Ask+questions+about+the+video)](https://git.io/typing-svg)

</div>

---

## 📌 About

VideoMind is a Streamlit application for asking questions about YouTube videos. The UI accepts a YouTube URL, calls the RAG pipeline to index the video, and then sends chat questions to the pipeline for answers. The sidebar displays the selected video's thumbnail, title, and indexed chunk count. Chat messages and the active video are kept in Streamlit session state.

**RAG** means Retrieval-Augmented Generation: retrieve relevant source material first, then use it to ground a generated answer. The provided `app.py` delegates indexing and answering to `rag_pipeline.py`; the exact transcript provider, embedding model, vector database, and LLM are determined by that pipeline and its dependencies.

## ✨ Features

- 🔗 Accepts YouTube video links, including common watch, short, shorts, and embed URL forms.
- 📝 Indexes a video through `index_video(url)` and displays its title and chunk count.
- 💬 Lets users ask questions through a chat interface and calls `answer_question(prompt)`.
- 🧠 Uses the project's RAG pipeline to answer against video content.
- 💡 Offers starter prompts: “Summarize this video”, “Key points?”, and “Main takeaway?”.
- 🗂️ Keeps the selected video and conversation in Streamlit session state.
- 🧹 “New video” clears the current video and conversation.
- 🎨 Includes a custom animated video scrubber and hover effects, with reduced-motion styling.

## 🏛️ Architecture

```mermaid
flowchart LR
	 User[👤 User] -->|YouTube URL| App[🎈 Streamlit app.py]
	 App --> Validate[Extract video ID]
	 App -->|index_video(url)| Pipeline[🧠 rag_pipeline.py]
	 Pipeline --> Transcript[📝 Transcript processing]
	 Transcript --> Index[(🔎 Searchable index)]
	 Index --> Pipeline
	 User -->|Question| App
	 App -->|answer_question(prompt)| Pipeline
	 Pipeline -->|Retrieved context + generated response| App
	 App -->|Chat answer| User
```

### Component responsibilities

| Component | Responsibility |
| --- | --- |
| `app.py` | Streamlit page, CSS, URL form, ID validation, session state, sidebar, prompt suggestions, and chat rendering. |
| `rag_pipeline.py` | Exposes `index_video(url)` and `answer_question(prompt)` to the UI. Its internal implementation defines transcript retrieval, indexing, retrieval, and generation details. |
| YouTube | Source video; the pipeline needs accessible transcript/caption content to index it. |
| `Requirements.txt` | Lists Python packages needed by the project. |
| `RAG (1).ipynb` | Notebook associated with the RAG work; suitable for experimentation and exploration. |
| `config.toml` | Streamlit configuration/theme, if present. It should not contain secret credentials. |

> **Implementation note:** Only `app.py` was available in the supplied context. The precise models, vector-store technology, prompt design, chunking settings, configuration values, and dependency versions cannot be verified here. Check `rag_pipeline.py`, `RAG (1).ipynb`, `Requirements.txt`, and `config.toml` for those specifics rather than assuming a particular provider or database.

## 🔁 Step-by-step flow

1. **Start on the home screen.** Streamlit shows the URL field and a short three-step introduction.
2. **Enter a YouTube URL.** Submitting the form calls `extract_video_id(url)`. A link without a recognized 11-character video ID is rejected with a validation message.
3. **Index the video.** The app calls `index_video(url)` inside a Streamlit status indicator. The pipeline is expected to return a mapping containing `title` and `chunks`.
4. **Open the chat.** On successful indexing, the app stores the video ID, title, and chunk count in session state, then reruns to render the chat view.
5. **Choose a prompt or type a question.** Starter suggestions are shown before the first message; `st.chat_input` accepts free-form questions.
6. **Generate an answer.** The app calls `answer_question(prompt)`, displays the answer, and appends the user and assistant messages to session state.
7. **Switch videos when needed.** “New video” resets the video, messages, and pending suggestion.

### Request sequence

```text
Browser                 app.py                  rag_pipeline.py
	|                       |                           |
	|--- YouTube URL ------>|                           |
	|                       |--- index_video(url) ----->|
	|                       |<-- title, chunk count ----|
	|<-- video chat view ---|                           |
	|--- question --------->|                           |
	|                       |--- answer_question(q) --->|
	|                       |<------ answer ------------|
	|<-- chat response -----|                           |
```

## 🧰 Technologies

| Technology | Role evidenced by the project UI / integration |
| --- | --- |
| 🐍 **Python** | Application language. |
| 🎈 **Streamlit** | Web UI, forms, chat elements, sidebar, status messages, and session state. |
| ▶️ **YouTube** | Video URL source and thumbnail image source. |
| 🧠 **RAG pipeline** | Project-specific indexing and question-answering interface. |
| 🎨 **HTML and CSS** | Custom typography, scrubber animation, hover effects, and reduced-motion behavior. |
| 📓 **Jupyter Notebook** | Notebook-based project exploration (`RAG (1).ipynb`). |

The exact transcript library, embeddings, vector store, LLM provider, and their versions should be documented from the implementation and `Requirements.txt` once verified.

## 📁 Project files

```text
project-folder/
├── app.py                 # Streamlit front end
├── rag_pipeline.py        # Video indexing and question-answering logic
├── RAG (1).ipynb          # RAG notebook / experiments
├── Requirements.txt       # Python dependencies
├── config.toml            # Streamlit configuration (location may be .streamlit/config.toml)
└── Readme.md              # Project documentation
```

## ⚙️ Run locally

1. Install Python and create/activate a virtual environment:

	```bash
	python -m venv .venv
	# Windows PowerShell
	.venv\Scripts\Activate.ps1
	# macOS / Linux
	source .venv/bin/activate
	```

2. Install the dependencies (use the exact filename and capitalization in the repository):

	```bash
	pip install -r Requirements.txt
	```

3. Configure any API keys required by `rag_pipeline.py` using environment variables or Streamlit secrets. Do not commit credentials. The key names cannot be specified reliably without inspecting the pipeline.

4. Launch the application:

	```bash
	streamlit run app.py
	```

5. Open the local Streamlit address, submit a YouTube link with available transcript/captions, and ask a question.

## 🧩 Key app integration points

The UI validates common video URL shapes with a regular expression:

```python
def extract_video_id(url: str) -> str | None:
	 match = re.search(r"(?:v=|youtu\.be/|shorts/|embed/)([A-Za-z0-9_-]{11})", url or "")
	 return match.group(1) if match else None
```

The app's pipeline boundary is intentionally small:

```python
result = index_video(url)                 # expected: {"title": str, "chunks": int}
answer = answer_question(prompt)          # expected: str
```

This keeps presentation and session handling in Streamlit while delegating video processing and answer generation to `rag_pipeline.py`.

## ⚠️ Notes and troubleshooting

- **Invalid link:** Confirm the URL contains a supported YouTube video ID.
- **Indexing error:** The video may not have accessible captions, or an external dependency/service may be unavailable. The UI shows the pipeline exception.
- **Missing dependencies:** Install from the repository's requirements file in the active environment.
- **Missing credentials:** Check `rag_pipeline.py` for required environment variables; never place secrets in a public README or committed config.
- **Answers:** Response quality depends on transcript availability and the pipeline's retrieval/model setup.
- **Reduced motion:** The decorative scrubber and hover effects respect `prefers-reduced-motion`.

---

<div align="center">

🎥 **Paste a link · Read the transcript · Ask away**

Developed by Abdullah Asim

</div>
