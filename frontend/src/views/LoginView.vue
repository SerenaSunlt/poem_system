<template>
  <div class="auth-page">
    <div class="auth-box">
      <h1 class="title font-kaiti">诗笺</h1>
      <p class="subtitle text-soft">愿你寻得心仪之句</p>

      <form @submit.prevent="handleSubmit" class="form">
        <input
          v-model="username"
          class="input"
          placeholder="用户名"
          autocomplete="username"
          required
        />
        <input
          v-model="password"
          type="password"
          class="input"
          placeholder="密码"
          autocomplete="current-password"
          required
        />
        <button type="submit" class="btn" :disabled="loading">
          {{ loading ? "登录中..." : "登 录" }}
        </button>
      </form>

      <p class="footer text-soft">
        还没有账号?
        <RouterLink to="/register" class="text-accent">注册</RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { RouterLink, useRouter, useRoute } from "vue-router";
import { useUserStore } from "../stores/user";
import { useToastStore } from "../stores/toast";

const router = useRouter();
const route = useRoute();
const userStore = useUserStore();
const toastStore = useToastStore();

const username = ref("");
const password = ref("");
const loading = ref(false);

async function handleSubmit() {
  if (loading.value) return;
  loading.value = true;
  try {
    await userStore.login(username.value, password.value);
    toastStore.success("登录成功");
    const redirect = route.query.redirect || "/recommend";
    router.push(redirect);
  } catch (e) {
    // 拦截器已经弹了 toast,这里啥也不做
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-5);
}
.auth-box {
  width: 100%;
  max-width: 360px;
  text-align: center;
}
.title {
  font-size: var(--fs-3xl);
  letter-spacing: 8px;
  color: var(--color-accent);
  margin-bottom: var(--space-2);
}
.subtitle {
  font-family: var(--font-kaiti);
  font-size: var(--fs-base);
  margin-bottom: var(--space-7);
  letter-spacing: 2px;
}
.form {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin-bottom: var(--space-5);
}
.btn {
  margin-top: var(--space-3);
  letter-spacing: 4px;
}
.footer {
  font-size: var(--fs-sm);
}
</style>
