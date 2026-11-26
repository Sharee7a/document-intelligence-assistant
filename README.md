# Document Intelligence Assistant

A local-first PDF assistant that extracts document text and page regions, retrieves relevant passages, and answers questions with inspectable citations. It combines PDF layout extraction/OCR, lexical or optional dense semantic retrieval, and grounded NLP question answering.

## Features

- Upload and manage PDF files, with size validation and content hashes.
- Extract digital PDF text and page bounding boxes; use Tesseract OCR when a page has no extractable text.
- Search passages with TF-IDF; optionally enable local Sentence Transformers embeddings for hybrid semantic retrieval.
- Answer with either cited extractive passages or an OpenAI-compatible chat completion endpoint.
- Return document, page, and bounding-box citations; click a citation to open the original PDF page.
- Run an evaluation script against question/page ground truth.

## Run locally

Requires Python 3.10+ and Node.js 20.19+ or 22.12+. For OCR of scanned PDFs, install the Tesseract executable and ensure it is on `PATH`.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite address (usually `http://localhost:5173`). API docs are at `http://localhost:8000/docs`.

### Optional LLM answers

Copy `.env.example` to `.env`, set `OPENAI_API_KEY` and `OPENAI_MODEL`, and restart the API. `OPENAI_BASE_URL` supports compatible chat-completions endpoints. The app sends only the question and retrieved excerpts to the configured provider. Without an LLM configuration it returns an extractive answer with citations.

### Optional semantic embeddings

Install `requirements-dense.txt`, set `USE_DENSE_EMBEDDINGS=1`, and configure `EMBEDDING_MODEL`. The first use loads the model and may download it. In Docker, set `INSTALL_DENSE=1` in `.env` to install the optional package; the model cache is persisted in a volume. Set up the cache ahead of time for offline deployments. TF-IDF retrieval remains available as fallback.

## API

- `GET /api/health`
- `GET /api/documents`
- `POST /api/documents` — multipart PDF upload
- `DELETE /api/documents/{id}`
- `GET /api/documents/{id}/file`
- `GET /api/search?q=...&top_k=5`
- `POST /api/ask` — JSON: `{"question":"...","document_ids":null,"top_k":5}`

Ask responses include `answer`, `mode`, and citations with filename, page number, excerpt, and PDF-point bounding box. OCR bounding boxes are derived from Tesseract word coordinates. A citation identifies evidence; it does not guarantee that the generated answer is correct, so verify important claims in the source.

## Evaluation

Upload the evaluation PDFs first. Create JSONL records with `question`, optional `expected_document_id` or `expected_filename`, and `expected_pages` (an array of page numbers), then run:

```powershell
python -m evaluation.score --dataset path\to\questions.jsonl --top-k 5
```

The evaluator reports page-level recall@k and mean reciprocal rank. Add answer quality scoring (e.g. ANLS/exact match) for datasets that include reference answers. Do not mix pages from the same source document across train and evaluation splits.

## Docker

From the project root:

```powershell
Copy-Item .env.example .env
# Set OPENAI_API_KEY and OPENAI_MODEL if desired
docker compose -f infrastructure/compose/docker-compose.yml up --build
```

Dashboard: port 8080. API: port 8000. Uploaded PDFs and SQLite metadata persist in the `document_data` volume. The container includes Tesseract.

## Data and privacy

PDF extraction and retrieval run locally. If an LLM is configured, only retrieved passages and the user question leave the machine. Store secrets in environment variables, restrict network access as appropriate, and avoid uploading documents you are not authorized to process. Set `DATA_DIR` and `MAX_UPLOAD_MB` to fit the environment.

## Project layout

- `app/`: API, PDF/OCR pipeline, retrieval, answers, SQLite
- `frontend/`: PDF library, Q&A, citations, page links
- `evaluation/`: page-retrieval evaluation
- `docs/`: architecture and evaluation notes