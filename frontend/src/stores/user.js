// src/stores/user.js
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import * as userApi from "../api/user";

export const useUserStore = defineStore("user", () => {
  // 从 localStorage 恢复
  const token = ref(localStorage.getItem("token") || "");
  const user = ref(JSON.parse(localStorage.getItem("user") || "null"));

  const isLoggedIn = computed(() => !!token.value);

  async function login(username, password) {
    const data = await userApi.login(username, password);
    token.value = data.token;
    user.value = data.user;
    localStorage.setItem("token", data.token);
    localStorage.setItem("user", JSON.stringify(data.user));
  }

  async function register(username, password) {
    return userApi.register(username, password);
  }

  function logout() {
    token.value = "";
    user.value = null;
    localStorage.removeItem("token");
    localStorage.removeItem("user");
  }

  return { token, user, isLoggedIn, login, register, logout };
});
