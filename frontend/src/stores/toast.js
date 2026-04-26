// src/stores/toast.js
import { defineStore } from "pinia";
import { ref } from "vue";

export const useToastStore = defineStore("toast", () => {
  const messages = ref([]);

  function show(text, type = "info", duration = 2500) {
    const id = Date.now() + Math.random();
    messages.value.push({ id, text, type });
    setTimeout(() => {
      messages.value = messages.value.filter((m) => m.id !== id);
    }, duration);
  }

  function info(text) {
    show(text, "info");
  }
  function success(text) {
    show(text, "success");
  }
  function error(text) {
    show(text, "error");
  }

  return { messages, show, info, success, error };
});
