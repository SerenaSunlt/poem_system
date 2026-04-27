<template>
  <AppHeader v-if="showHeader" />
  <RouterView />
  <Toast />
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { RouterView } from 'vue-router'
import { useUserStore } from './stores/user'
import AppHeader from './components/AppHeader.vue'
import Toast from './components/Toast.vue'

const userStore = useUserStore()
const route = useRoute()

// 登录页和注册页不显示导航
// 游客状态在浏览页面也不显示导航(保持沉浸)
const showHeader = computed(() => {
  if (route.name === 'login' || route.name === 'register') return false
  if (!userStore.isLoggedIn) return false
  return true
})
</script>