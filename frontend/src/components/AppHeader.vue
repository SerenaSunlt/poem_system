<template>
  <header class="app-header">
    <div class="container header-inner">
      <RouterLink to="/recommend" class="logo">诗笺</RouterLink>

      <nav class="nav">
        <RouterLink to="/recommend">推荐</RouterLink>
        <RouterLink to="/favorites">我的收藏</RouterLink>
      </nav>

      <div class="user-menu" v-if="userStore.isLoggedIn">
        <button class="user-btn" @click="showMenu = !showMenu">
          {{ userStore.user?.username }} ▾
        </button>
        <div v-if="showMenu" class="dropdown" @click="showMenu = false">
          <button @click="handleLogout">登出</button>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ref } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { useUserStore } from "../stores/user";

const userStore = useUserStore();
const router = useRouter();
const showMenu = ref(false);

function handleLogout() {
  userStore.logout();
  router.push("/login");
}
</script>

<style scoped>
.app-header {
  height: var(--header-height);
  background: var(--color-bg);
  border-bottom: 1px solid var(--color-border);
  position: sticky;
  top: 0;
  z-index: 100;
}
.header-inner {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.logo {
  font-family: var(--font-kaiti);
  font-size: var(--fs-xl);
  color: var(--color-accent);
  letter-spacing: 4px;
}
.nav {
  display: flex;
  gap: var(--space-6);
}
.nav a {
  color: var(--color-text-soft);
  font-size: var(--fs-base);
  padding: var(--space-2) 0;
  border-bottom: 1px solid transparent;
  transition: var(--transition);
}
.nav a:hover,
.nav a.router-link-active {
  color: var(--color-text);
  border-bottom-color: var(--color-accent);
}
.user-menu {
  position: relative;
}
.user-btn {
  font-size: var(--fs-sm);
  color: var(--color-text-soft);
}
.user-btn:hover {
  color: var(--color-text);
}
.dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  min-width: 100px;
  margin-top: var(--space-2);
}
.dropdown button {
  width: 100%;
  padding: var(--space-2) var(--space-4);
  text-align: left;
  font-size: var(--fs-sm);
}
.dropdown button:hover {
  background: var(--color-border-soft);
}
</style>
