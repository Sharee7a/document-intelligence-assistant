import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from app.answer import answer_question
from app.config import CORS_ORIGINS, MAX_UPLOAD_MB, OPENAI_API_KEY, OPENAI_MODEL, UPLOAD_DIR
from app.database import initialize_database, transaction
from app.pdf_pipeline import extract_pdf
from app.retrieval import retrieve

app = FastAPI(title="Document Intelligence Assistant", version="1.0.0", description="Search PDFs and answer with page and region citations.")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"], allow_credentials=False)

@app.on_event("startup")
def startup():
    initialize_database()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    document_ids: list[str] | None = None
    top_k: int = Field(default=5, ge=1, le=12)

@app.get("/api/health")
def health():
    return {"status": "ok", "llm_configured": bool(OPENAI_API_KEY and OPENAI_MODEL)}

@app.get("/api/documents")
def list_documents():
    with transaction() as db:
        rows = db.execute("SELECT id,filename,sha256,page_count,chunk_count,created_at FROM documents ORDER BY created_at DESC").fetchall()
    return {"items": [dict(row) for row in rows]}

@app.post("/api/documents")
async def upload_document(file: UploadFile = File(...)):
    filename = Path(file.filename or "document.pdf").name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Upload a PDF file")
    data = await file.read(MAX_UPLOAD_MB * 1024 * 1024 + 1)
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Maximum PDF size is {MAX_UPLOAD_MB} MB")
    digest = hashlib.sha256(data).hexdigest()
    doc_id = str(uuid.uuid4())
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    saved = UPLOAD_DIR / f"{doc_id}.pdf"
    saved.write_bytes(data)
    try:
        pages = extract_pdf(saved)
    except Exception as exc:
        saved.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    chunks = [chunk for page in pages for chunk in page["chunks"]]
    with transaction() as db:
        db.execute("INSERT INTO documents VALUES (?,?,?,?,?,?,?)", (doc_id, filename, digest, len(pages), len(chunks), str(saved), datetime.now(timezone.utc).isoformat()))
        db.executemany("INSERT INTO chunks (document_id,page_number,text,bbox) VALUES (?,?,?,?)", [(doc_id,c["page_number"],c["text"],json.dumps(c["bbox"])) for c in chunks])
    return {"id": doc_id, "filename": filename, "page_count": len(pages), "chunk_count": len(chunks), "sha256": digest}

@app.delete("/api/documents/{document_id}")
def delete_document(document_id: str):
    with transaction() as db:
        row = db.execute("SELECT stored_path FROM documents WHERE id=?", (document_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Document not found")
        db.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))
        db.execute("DELETE FROM documents WHERE id=?", (document_id,))
    Path(row["stored_path"]).unlink(missing_ok=True)
    return {"deleted": document_id}

@app.get("/api/documents/{document_id}/file")
def document_file(document_id: str):
    with transaction() as db:
        row = db.execute("SELECT filename,stored_path FROM documents WHERE id=?", (document_id,)).fetchone()
    if not row or not Path(row["stored_path"]).exists():
        raise HTTPException(status_code=404, detail="Document file not found")
    return FileResponse(row["stored_path"], media_type="application/pdf")

@app.post("/api/ask")
def ask(request: AskRequest):
    sources = retrieve(request.question, request.document_ids, request.top_k)
    if not sources:
        raise HTTPException(status_code=404, detail="Upload a readable PDF before asking questions")
    if sources[0]["score"] <= 0:
        return {"answer": "I could not find supporting information in the selected documents.", "citations": [], "mode": "extractive"}
    try:
        text, citations, mode = answer_question(request.question, sources)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    result_sources = [{"source_id":s["source_id"],"document_id":s["document_id"],"filename":s["filename"],"page_number":s["page_number"],"bbox":json.loads(s["bbox"]),"excerpt":s["text"],"score":s["score"]} for s in citations]
    return {"answer": text, "citations": result_sources, "mode": mode}

@app.get("/api/search")
def search(q: str = Query(min_length=2, max_length=500), top_k: int = Query(5, ge=1, le=12)):
    hits = retrieve(q, top_k=top_k)
    return {"items": [{"document_id":h["document_id"],"filename":h["filename"],"page_number":h["page_number"],"bbox":json.loads(h["bbox"]),"excerpt":h["text"],"score":h["score"]} for h in hits]}
