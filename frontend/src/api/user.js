// src/api/user.js
import client from "./client";

export function register(username, password) {
  return client.post("/api/users/register", { username, password });
}

export function login(username, password) {
  return client.post("/api/users/login", { username, password });
}

export function getMe() {
  return client.get("/api/users/me");
}
