import client from './client'

export function recommend(prompt, count = 1, seenIds = []) {
  const params = { count }
  if (prompt) params.prompt = prompt
  if (seenIds && seenIds.length > 0) {
    params.seen_ids = seenIds.join(',')
  }
  return client.get('/api/poems/recommend', { params })
}

export function getPoem(id) {
  return client.get(`/api/poems/${id}`)
}