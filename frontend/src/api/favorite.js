// src/api/favorite.js
import client from "./client";

export function addFavorite(poemId, userTags = [], note = null) {
  return client.post("/api/favorites", {
    poem_id: poemId,
    user_tags: userTags,
    note,
  });
}

export function removeFavorite(poemId) {
  return client.delete(`/api/favorites/${poemId}`);
}

export function updateFavorite(poemId, { userTags, note }) {
  const payload = {};
  if (userTags !== undefined) payload.user_tags = userTags;
  if (note !== undefined) payload.note = note;
  return client.patch(`/api/favorites/${poemId}`, payload);
}

export function listFavorites({ tag, keyword, page = 1, pageSize = 20 } = {}) {
  return client.get("/api/favorites", {
    params: { tag, keyword, page, page_size: pageSize },
  });
}

export function listMyTags() {
  return client.get("/api/favorites/tags");
}
