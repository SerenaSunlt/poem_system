<template>
  <div class="auth-page">
    <RouterLink to="/recommend" class="back-home">返回</RouterLink>

    <div class="auth-box">
      <h1 class="title font-kaiti">诗笺</h1>
      <p class="subtitle text-soft">创建一个新账号</p>

      <form @submit.prevent="handleSubmit" class="form">
        <input
          v-model="username"
          class="input"
          placeholder="用户名(3-20 位字母数字下划线)"
          required
        />
        <input
          v-model="password"
          type="password"
          class="input"
          placeholder="密码(6-32 位)"
          required
        />
        <input
          v-model="passwordConfirm"
          type="password"
          class="input"
          placeholder="确认密码"
          required
        />
        <button type="submit" class="btn" :disabled="loading">
          {{ loading ? '注册中...' : '注 册' }}
        </button>
      </form>

      <p class="footer text-soft">
        已有账号?
        <RouterLink to="/login" class="text-accent">登录</RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { useUserStore } from "../stores/user";
import { useToastStore } from "../stores/toast";

const router = useRouter();
const userStore = useUserStore();
const toastStore = useToastStore();

const username = ref("");
const password = ref("");
const passwordConfirm = ref("");
const loading = ref(false);

async function handleSubmit() {
  if (loading.value) return;
  if (password.value !== passwordConfirm.value) {
    toastStore.error("两次密码不一致");
    return;
  }
  loading.value = true;
  try {
    await userStore.register(username.value, password.value);
    toastStore.success("注册成功,请登录");
    router.push("/login");
  } catch (e) {
    // 拦截器已 toast
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
/* 复用 LoginView 的样式 */
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
.back-home {
  position: absolute;
  top: var(--space-5);
  left: var(--space-5);
  font-size: var(--fs-sm);
  color: var(--color-text-faint);
  padding: var(--space-2) 0;
  transition: color var(--transition);
}
.back-home:hover {
  color: var(--color-accent);
}

/* 让 auth-page 成为定位上下文,这样 back-home 的 absolute 才相对它 */
.auth-page {
  position: relative;
}
</style>
