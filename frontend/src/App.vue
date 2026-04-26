<template>
  <AppHeader v-if="userStore.isLoggedIn" />
  <RouterView />
  <Toast />
</template>

<script setup>
import { RouterView } from "vue-router";
import { useUserStore } from "./stores/user";
import AppHeader from "./components/AppHeader.vue";
import Toast from "./components/Toast.vue";

const userStore = useUserStore();
</script>
