const API_BASE = ''

export async function api(path) {
  const r = await fetch(`${API_BASE}${path}`)
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
  return r.json()
}
