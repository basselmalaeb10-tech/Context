const BASE = '/api';

export async function uploadPdf(file: File) {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${BASE}/upload`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getSession(sessionId: string) {
  const res = await fetch(`${BASE}/sessions/${sessionId}`);
  if (!res.ok) throw new Error('Session not found');
  return res.json();
}

export async function submitCalibration(sessionId: string, answers: Record<string, number>) {
  const res = await fetch(`${BASE}/sessions/${sessionId}/calibrate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ answers }),
  });
  if (!res.ok) throw new Error('Calibration failed');
  return res.json();
}

export async function getPages(sessionId: string) {
  const res = await fetch(`${BASE}/sessions/${sessionId}/pages`);
  if (!res.ok) throw new Error('Failed to load pages');
  return res.json();
}

export async function getPdfUrl(sessionId: string) {
  return `${BASE}/sessions/${sessionId}/pdf`;
}

export async function getExplanation(
  sessionId: string,
  selectedText: string,
  surroundingText: string,
  page: number,
  mode: string,
) {
  const res = await fetch(`${BASE}/sessions/${sessionId}/explain`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      selected_text: selectedText,
      surrounding_text: surroundingText,
      page,
      mode,
    }),
  });
  if (!res.ok) throw new Error('Explanation failed');
  return res.json();
}

export async function checkNudge(sessionId: string, page: number) {
  const res = await fetch(`${BASE}/sessions/${sessionId}/nudge?page=${page}`);
  if (!res.ok) return { nudge: null };
  return res.json();
}

export async function updatePage(sessionId: string, page: number) {
  await fetch(`${BASE}/sessions/${sessionId}/page?page=${page}`, { method: 'PUT' });
}
