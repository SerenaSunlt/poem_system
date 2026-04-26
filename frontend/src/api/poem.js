// src/api/poem.js
import client from "./client";

export function recommend(prompt, count = 1) {
  return client.get("/api/poems/recommend", {
    params: { prompt: prompt || undefined, count },
  });
}

export function getPoem(id) {
  return client.get(`/api/poems/${id}`);
}
