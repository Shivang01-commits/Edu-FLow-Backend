"""
PadhAI Backend v4 — robust background task + /status polling
"""

import re, time, logging, asyncio, httpx, threading
from contextlib import asynccontextmanager
import fitz
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("edulens")

# ─── Config ───────────────────────────────────────────────────────────────────


class Config:
    LLM_BASE_URL: str = "http://localhost:11435/v1"
    LLM_MODEL: str = "qwen2.5:3b"  # ← run `ollama list` and paste exact name
    LLM_TIMEOUT: int = 900
    MAX_PDF_PAGES: int = 100
    MAX_PDF_SIZE_MB: int = 25
    CHUNK_CHARS: int = 3000
    SUMMARY_CHUNKS: int = 2
    QA_CHUNKS: int = 99
    QUIZ_CHUNKS: int = 3


config = Config()

# ─── Job store (in-memory) ────────────────────────────────────────────────────

job_store: dict = {
    "status": "idle",  # idle | running | done | error
    "progress": [],
    "result": None,
    "error": None,
    "started_at": None,
    "finished_at": None,
}


def push(msg: str):
    entry = {"time": time.time(), "msg": msg}
    job_store["progress"].append(entry)
    logger.info(msg)


# ─── App ──────────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        f"EduLens v4 starting. LLM: {config.LLM_BASE_URL} model={config.LLM_MODEL}"
    )
    yield


app = FastAPI(title="EduLens API", version="4.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Pydantic models ──────────────────────────────────────────────────────────


class QuizOption(BaseModel):
    label: str
    text: str


class QuizQuestion(BaseModel):
    question: str
    options: list[QuizOption]
    answer: str
    explanation: str


class ChapterQA(BaseModel):
    question: str
    answer: str


class AnalysisResult(BaseModel):
    filename: str
    page_count: int
    word_count: int
    summary: str
    key_concepts: list[str]
    chapter_qa: list[ChapterQA]
    quiz: list[QuizQuestion]
    processing_time_seconds: float


# ─── PDF helpers ──────────────────────────────────────────────────────────────


def extract_pdf_text(pdf_bytes: bytes) -> tuple[str, int]:
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page_count = len(doc)
        if page_count > config.MAX_PDF_PAGES:
            raise ValueError(
                f"PDF has {page_count} pages. Max is {config.MAX_PDF_PAGES}."
            )
        pages = [
            page.get_text("text").strip()
            for page in doc
            if page.get_text("text").strip()
        ]
        doc.close()
        return "\n\n".join(pages), page_count
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"PDF extraction failed: {e}")


def split_into_chunks(text: str, chunk_size: int) -> list[str]:
    chunks, remaining = [], text
    while remaining:
        if len(remaining) <= chunk_size:
            chunks.append(remaining.strip())
            break
        cut = remaining[:chunk_size]
        split_at = cut.rfind("\n\n")
        if split_at < chunk_size * 0.5:
            split_at = max(cut.rfind(". "), cut.rfind(".\n"))
        if split_at < chunk_size * 0.3:
            split_at = chunk_size
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    return [c for c in chunks if c]


# ─── LLM client (sync — runs in thread) ──────────────────────────────────────

SYSTEM_PROMPT = (
    "You are EduLens, an expert educational assistant helping teachers analyze academic chapters. "
    "Be precise, structured, and always follow the exact output format requested. "
    "Never add extra commentary outside the requested format."
)


def call_llm_sync(prompt: str, max_tokens: int = 800) -> str:
    """Synchronous LLM call — safe to run in a background thread."""
    import requests

    payload = {
        "model": config.LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }
    url = f"{config.LLM_BASE_URL}/chat/completions"
    try:
        resp = requests.post(url, json=payload, timeout=config.LLM_TIMEOUT)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"Cannot connect to LLM at {url}. Is Ollama running?")
    except requests.exceptions.Timeout:
        raise RuntimeError("LLM request timed out.")
    except Exception as e:
        raise RuntimeError(f"LLM error: {e}")


# ─── Parsers ──────────────────────────────────────────────────────────────────


def parse_concepts(raw: str) -> list[str]:
    out = []
    for line in raw.splitlines():
        line = re.sub(r"^[\-\*\d\.\)]+\s*", "", line).strip()
        if line and len(line) > 3:
            out.append(line)
    return out


def parse_qa(raw: str) -> list[ChapterQA]:
    pairs = []
    for block in re.split(r"\n(?=Q\d*\s*[:\.])", raw, flags=re.IGNORECASE):
        q = re.search(r"Q\d*\s*[:.]\s*(.+?)(?:\n|$)", block, re.IGNORECASE)
        a = re.search(
            r"A\d*\s*[:.]\s*(.+?)(?=\nQ|\Z)", block, re.IGNORECASE | re.DOTALL
        )
        if q and a:
            question, answer = q.group(1).strip(), a.group(1).strip()
            if question and answer and not any(p.question == question for p in pairs):
                pairs.append(ChapterQA(question=question, answer=answer))
    return pairs


def parse_quiz(raw: str) -> list[QuizQuestion]:
    questions = []
    for block in re.split(r"\n(?=\d+[\.\)])", raw):
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        q_line = re.sub(r"^\d+[\.\)]\s*", "", lines[0]).strip()
        options, answer_label, explanation = [], "", ""
        for line in lines[1:]:
            m = re.match(r"^([A-D])[\.\)]\s*(.+)", line, re.IGNORECASE)
            am = re.match(r"^(?:Answer|Correct)[:\s]+([A-D])", line, re.IGNORECASE)
            em = re.match(r"^Explanation[:\s]+(.+)", line, re.IGNORECASE)
            if m:
                options.append(
                    QuizOption(label=m.group(1).upper(), text=m.group(2).strip())
                )
            if am:
                answer_label = am.group(1).upper()
            if em:
                explanation = em.group(1).strip()
        if q_line and len(options) >= 2 and answer_label:
            if not any(q.question.lower() == q_line.lower() for q in questions):
                questions.append(
                    QuizQuestion(
                        question=q_line,
                        options=options,
                        answer=answer_label,
                        explanation=explanation or "Refer to the chapter.",
                    )
                )
    return questions


# ─── Generation tasks (all synchronous — run inside thread) ──────────────────


def gen_summary(chunks: list[str]) -> tuple[str, list[str]]:
    use = chunks[: config.SUMMARY_CHUNKS]
    all_s, all_c = [], []
    for i, chunk in enumerate(use):
        push(f"📝 Summary — section {i + 1} of {len(use)}…")
        raw = call_llm_sync(
            f"""Part {i + 1} of {len(use)} of an academic chapter.

Respond ONLY in this exact format:

SUMMARY:
[Write a detailed paragraph of 150-200 words covering main ideas, explanations, concepts in this section.]

KEY CONCEPTS:
- [concept]
- [concept]
- [concept]
- [concept]
- [concept]
- [concept]

Chapter section:
\"\"\"{chunk}\"\"\"

Respond now:""",
            max_tokens=700,
        )
        s_m = re.search(
            r"SUMMARY:\s*(.*?)(?=KEY CONCEPTS:|$)", raw, re.DOTALL | re.IGNORECASE
        )
        c_m = re.search(r"KEY CONCEPTS:\s*(.*?)$", raw, re.DOTALL | re.IGNORECASE)
        all_s.append(s_m.group(1).strip() if s_m else raw[:500])
        if c_m:
            all_c.extend(parse_concepts(c_m.group(1)))
        push(f"✅ Summary section {i + 1} complete.")

    if len(all_s) > 1:
        push("🔀 Merging summaries into final overview…")
        combined = "\n\n".join(f"[Section {i + 1}]\n{s}" for i, s in enumerate(all_s))
        final = call_llm_sync(
            f"Combine these into ONE coherent 300-400 word summary in flowing paragraphs. No labels.\n\n{combined}\n\nWrite now:",
            max_tokens=900,
        )
        push("✅ Summary merged.")
    else:
        final = all_s[0] if all_s else "Summary unavailable."

    seen, unique = set(), []
    for c in all_c:
        k = c.lower().strip()
        if k not in seen:
            seen.add(k)
            unique.append(c)
    return final, unique[:15]


def gen_qa(chunks: list[str]) -> list[ChapterQA]:
    all_pairs: list[ChapterQA] = []
    for i, chunk in enumerate(chunks):
        push(f"❓ Q&A — scanning section {i + 1} of {len(chunks)}…")
        raw = call_llm_sync(
            f"""Read this academic chapter section.

1. Find explicit questions in the text (exercises, review questions, numbered questions) and answer them in detail.
2. If none exist, generate 3 comprehension questions with detailed answers.

Section:
\"\"\"{chunk}\"\"\"

Format ONLY:
Q1: [question]
A1: [2-4 sentence answer]

Q2: [question]
A2: [2-4 sentence answer]

Q3: [question]
A3: [2-4 sentence answer]""",
            max_tokens=800,
        )
        new = parse_qa(raw)
        added = 0
        for p in new:
            if not any(e.question.lower() == p.question.lower() for e in all_pairs):
                all_pairs.append(p)
                added += 1
        push(f"✅ Q&A section {i + 1} done — {added} question(s) found.")
    return all_pairs


def gen_quiz(chunks: list[str]) -> list[QuizQuestion]:
    all_q: list[QuizQuestion] = []
    use = chunks[: config.QUIZ_CHUNKS]
    for i, chunk in enumerate(use):
        count = 5 if i == 0 else 3
        push(f"🧩 Quiz — {count} questions from section {i + 1} of {len(use)}…")
        raw = call_llm_sync(
            f"""Create exactly {count} multiple-choice questions from this chapter section.
Rules: test understanding, 4 options A/B/C/D, one correct answer, brief explanation.

Section:
\"\"\"{chunk}\"\"\"

EXACT format only:
1. [Question]
A. [option]
B. [option]
C. [option]
D. [option]
Answer: [A/B/C/D]
Explanation: [one sentence]

2. [Next question]
...""",
            max_tokens=1000,
        )
        new = parse_quiz(raw)
        added = 0
        for q in new:
            if not any(e.question.lower() == q.question.lower() for e in all_q):
                all_q.append(q)
                added += 1
        push(f"✅ Quiz section {i + 1} done — {added} question(s) added.")
    return all_q[:12]


# ─── Main analysis runner (runs in a thread, NOT async) ───────────────────────


def run_analysis_thread(pdf_bytes: bytes, filename: str):
    """
    Runs entirely in a background thread using synchronous HTTP calls.
    This avoids asyncio.create_task issues with uvicorn --reload.
    """
    job_store.update(
        {
            "status": "running",
            "progress": [],
            "result": None,
            "error": None,
            "started_at": time.time(),
            "finished_at": None,
        }
    )
    try:
        push(f"📄 Processing: {filename}")
        full_text, page_count = extract_pdf_text(pdf_bytes)
        if not full_text.strip():
            raise ValueError("No readable text in PDF.")

        word_count = len(full_text.split())
        chunks = split_into_chunks(full_text, config.CHUNK_CHARS)
        push(
            f"📊 Extracted {word_count:,} words from {page_count} pages → {len(chunks)} sections to process"
        )

        push("=== TASK 1: Summary & Key Concepts ===")
        summary, key_concepts = gen_summary(chunks)
        push(f"📚 Summary complete — {len(key_concepts)} key concepts identified")

        push("=== TASK 2: Q&A Extraction ===")
        chapter_qa = gen_qa(chunks)
        push(f"❓ Q&A complete — {len(chapter_qa)} questions answered")

        push("=== TASK 3: Quiz Generation ===")
        quiz = gen_quiz(chunks)
        push(f"🧩 Quiz complete — {len(quiz)} questions generated")

        elapsed = round(time.time() - job_store["started_at"], 2)
        result = AnalysisResult(
            filename=filename,
            page_count=page_count,
            word_count=word_count,
            summary=summary,
            key_concepts=key_concepts,
            chapter_qa=chapter_qa,
            quiz=quiz,
            processing_time_seconds=elapsed,
        )
        job_store.update(
            {
                "result": result.model_dump(),
                "status": "done",
                "finished_at": time.time(),
            }
        )
        push(f"🎉 All done in {round(elapsed / 60, 1)} minutes!")

    except Exception as e:
        job_store.update(
            {"status": "error", "error": str(e), "finished_at": time.time()}
        )
        push(f"❌ Error: {e}")
        logger.error(f"Analysis failed: {e}", exc_info=True)


# ─── Endpoints ────────────────────────────────────────────────────────────────


@app.post("/analyze")
async def analyze_chapter(
    background_tasks: BackgroundTasks, file: UploadFile = File(...)
):
    """Upload PDF — analysis starts immediately in background. Poll /status for updates."""
    if job_store["status"] == "running":
        raise HTTPException(
            409, "An analysis is already running. Please wait for it to finish."
        )
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted.")
    pdf_bytes = await file.read()
    size_mb = len(pdf_bytes) / (1024 * 1024)
    if size_mb > config.MAX_PDF_SIZE_MB:
        raise HTTPException(
            400,
            f"File too large ({size_mb:.1f} MB). Max is {config.MAX_PDF_SIZE_MB} MB.",
        )

    # Use BackgroundTasks + threading to avoid asyncio.create_task issues with --reload
    def start():
        t = threading.Thread(
            target=run_analysis_thread, args=(pdf_bytes, file.filename), daemon=True
        )
        t.start()

    background_tasks.add_task(start)
    return {
        "message": "Analysis started. Poll /status for progress.",
        "filename": file.filename,
    }


@app.get("/status")
async def get_status():
    """Get current job status, live progress log, and result when done."""
    return {
        "status": job_store["status"],
        "progress": job_store["progress"],
        "result": job_store["result"],
        "error": job_store["error"],
        "started_at": job_store["started_at"],
        "finished_at": job_store["finished_at"],
    }


@app.get("/health")
async def health():
    llm_ok, llm_note = False, ""
    try:
        import requests

        r = requests.get(f"{config.LLM_BASE_URL}/models", timeout=5)
        llm_ok = r.status_code == 200
        llm_note = "reachable"
    except Exception as e:
        llm_note = str(e)
    return {
        "status": "ok",
        "llm_reachable": llm_ok,
        "llm_note": llm_note,
        "job_status": job_store["status"],
    }


@app.get("/")
async def root():
    return {"message": "EduLens API v4 running. POST /analyze then poll /status."}
