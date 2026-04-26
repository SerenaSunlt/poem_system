// src/api/dislike.js
import client from "./client";

export function addDislike(poemId) {
  return client.post("/api/dislikes", { poem_id: poemId });
}

export function removeDislike(poemId) {
  return client.delete(`/api/dislikes/${poemId}`);
}
