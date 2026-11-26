import { useEffect, useState } from 'react';
import { askQuestion, deleteDocument, fileUrl, getDocuments, uploadDocument } from './services/api.js';

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [selected, setSelected] = useState([]);
  const [file, setFile] = useState(null);
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function refresh() {
    try { const data = await getDocuments(); setDocuments(data.items); setSelected((prev) => prev.filter((id) => data.items.some((doc) => doc.id === id))); }
    catch (e) { setError(e.message); }
  }
  useEffect(() => { refresh(); }, []);
  async function onUpload(event) {
    event.preventDefault(); if (!file) return;
    setBusy(true); setError(''); setAnswer(null);
    try { await uploadDocument(file); setFile(null); event.target.reset(); await refresh(); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }
  async function onAsk(event) {
    event.preventDefault(); if (!question.trim()) return;
    setBusy(true); setError(''); setAnswer(null);
    try { setAnswer(await askQuestion(question, selected.length ? selected : null)); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }
  async function onDelete(id) {
    if (!window.confirm('Delete this PDF and its extracted text?')) return;
    try { await deleteDocument(id); await refresh(); }
    catch (e) { setError(e.message); }
  }
  return <main>
    <header><div className="brand"><div className="mark">DI</div><div><p className="eyebrow">DOCUMENT WORKSPACE</p><h1>Document Intelligence</h1></div></div><span className="chip">OCR · Search · Grounded answers</span></header>
    <p className="intro">Ask questions across your PDFs and inspect the page evidence behind every answer.</p>
    {error && <div className="error">{error}</div>}
    <section className="layout">
      <aside className="panel library"><div className="section-head"><div><p className="eyebrow">YOUR LIBRARY</p><h2>Documents <span className="count">{documents.length}</span></h2></div></div>
        <form className="upload" onSubmit={onUpload}><label className="drop"><input type="file" accept="application/pdf,.pdf" onChange={(e) => setFile(e.target.files?.[0] || null)}/><span className="upload-icon">↑</span><b>{file ? file.name : 'Choose a PDF'}</b><small>PDF · max 40 MB</small></label><button disabled={!file || busy}>{busy ? 'Working…' : 'Add document'}</button></form>
        <div className="doc-list">{documents.map((doc) => <article className="doc" key={doc.id}><label className="doc-select"><input type="checkbox" checked={selected.includes(doc.id)} onChange={(e) => setSelected(e.target.checked ? [...selected, doc.id] : selected.filter((x) => x !== doc.id))}/><span className="pdf-icon">PDF</span></label><div className="doc-info"><b title={doc.filename}>{doc.filename}</b><small>{doc.page_count} pages · {doc.chunk_count} passages</small></div><button className="icon-btn" title="Delete document" onClick={() => onDelete(doc.id)}>×</button></article>)}{!documents.length && <p className="empty">Your documents will appear here.</p>}</div>
        <p className="hint">Select documents to limit search, or leave all unchecked to search the full library.</p>
      </aside>
      <section className="main-column"><article className="panel ask-panel"><p className="eyebrow">ASK YOUR DOCUMENTS</p><h2>What do you need to find?</h2><form onSubmit={onAsk}><textarea value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ask a question about the uploaded documents…" rows="3"/><div className="ask-bottom"><small>{selected.length ? `Searching ${selected.length} selected document(s)` : `Searching all ${documents.length} document(s)`}</small><button disabled={!question.trim() || busy || !documents.length}>{busy ? 'Searching…' : 'Ask question'} <span>→</span></button></div></form></article>
        {answer && <article className="panel answer"><div className="answer-top"><div><p className="eyebrow">ANSWER</p><span className="mode">{answer.mode === 'llm' ? 'LLM grounded' : 'Extractive fallback'}</span></div></div><div className="answer-text">{answer.answer}</div>{answer.citations.length > 0 && <div className="sources"><h3>Evidence</h3>{answer.citations.map((source) => <a className="source" key={source.source_id} href={fileUrl(source.document_id, source.page_number)} target="_blank" rel="noreferrer"><span className="source-tag">{source.source_id}</span><span className="source-body"><b>{source.filename} · page {source.page_number}</b><small>{source.excerpt}</small><em>Region: {source.bbox.map((n) => Math.round(n)).join(', ')} pt</em></span><span className="open">↗</span></a>)}</div>}</article>}
        {!answer && <article className="empty-state"><div className="spark">✳</div><h3>Answers with evidence</h3><p>Upload PDFs, ask a question, and open cited pages to verify the source passage.</p><div className="steps"><span>01 · Add documents</span><span>02 · Ask a question</span><span>03 · Review citations</span></div></article>}
        <p className="privacy">PDF text is processed locally. If an LLM API is configured, only retrieved passages and your question are sent to that provider.</p>
      </section>
    </section>
  </main>;
}