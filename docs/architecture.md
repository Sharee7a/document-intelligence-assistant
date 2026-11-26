# Architecture

1. PDF bytes are validated and stored under a UUID filename. SHA-256 supports duplicate identification.
2. PyMuPDF extracts text blocks with page-space bounding boxes. Image-only pages fall back to Tesseract OCR and word coordinates.
3. Text is split into bounded passages while preserving page and block geometry. Passage text, document metadata, and citations are stored in SQLite.
4. Retrieval ranks passages with TF-IDF. Optional Sentence Transformers embeddings add dense semantic similarity in a hybrid score.
5. The answer layer uses a configured OpenAI-compatible chat-completions endpoint or an extractive fallback. The LLM receives only top passages, is instructed to cite known source IDs, and citations are filtered against retrieved IDs.
6. The frontend displays citations with page and region metadata and links to the original PDF page.

## Important limits

The PDF parser is not a full table reconstruction engine. OCR quality depends on scan quality and a local Tesseract installation. TF-IDF is the default retrieval method; dense retrieval is optional. Citation filtering constrains source references but does not prove semantic entailment. Treat answers as assisted search and verify important content in the source.