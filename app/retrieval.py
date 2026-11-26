import os
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from app.database import transaction

_encoder = None

def _dense_scores(query, texts):
    """Optional local semantic embeddings; fall back cleanly when the extra is absent."""
    global _encoder
    if os.getenv("USE_DENSE_EMBEDDINGS", "0") != "1":
        return None
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return None
    if _encoder is None:
        _encoder = SentenceTransformer(os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))
    vectors = _encoder.encode([query, *texts], normalize_embeddings=True)
    return np.asarray(vectors[1:] @ vectors[0])


def retrieve(query, document_ids=None, top_k=5):
    with transaction() as db:
        sql = "SELECT c.id,c.document_id,c.page_number,c.text,c.bbox,d.filename FROM chunks c JOIN documents d ON d.id=c.document_id"
        params = []
        if document_ids:
            placeholders = ",".join("?" for _ in document_ids)
            sql += f" WHERE c.document_id IN ({placeholders})"
            params.extend(document_ids)
        rows = [dict(row) for row in db.execute(sql, params).fetchall()]
    if not rows:
        return []
    texts = [row["text"] for row in rows]
    try:
        matrix = TfidfVectorizer(ngram_range=(1, 2), stop_words="english").fit_transform(texts + [query])
        lexical = cosine_similarity(matrix[-1], matrix[:-1]).ravel()
    except ValueError:
        lexical = np.zeros(len(texts))
    dense = _dense_scores(query, texts)
    scores = lexical if dense is None else (0.35 * lexical + 0.65 * dense)
    best = np.argsort(scores)[::-1][:max(1, min(int(top_k), 12))]
    result = []
    for rank, idx in enumerate(best, 1):
        row = rows[int(idx)]
        row["score"] = float(scores[idx])
        row["source_id"] = f"S{rank}"
        result.append(row)
    return result