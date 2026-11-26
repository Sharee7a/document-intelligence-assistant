const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, options);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  return response.json();
}
export const getDocuments = () => request('/api/documents');
export const uploadDocument = (file) => { const form = new FormData(); form.append('file', file); return request('/api/documents', { method: 'POST', body: form }); };
export const deleteDocument = (id) => request(`/api/documents/${id}`, { method: 'DELETE' });
export const askQuestion = (question, document_ids, top_k = 5) => request('/api/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question, document_ids, top_k }) });
export const fileUrl = (id, page) => `${API}/api/documents/${id}/file#page=${page}`;