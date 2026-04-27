<template>
  <div class="recommend-page">
    <!-- 输入区 -->
    <section class="prompt-section container">
      <div class="prompt-input-wrap">
        <input
          v-model="promptInput"
          class="prompt-input"
          placeholder="这一刻你在想什么 ..."
          maxlength="100"
          @keydown.enter="handlePromptSubmit"
        />
        <button
          class="prompt-btn"
          :disabled="loading"
          @click="handlePromptSubmit"
        >
          寻 诗
        </button>
      </div>

      <div v-if="lastPrompt" class="prompt-keywords">
        <span class="text-faint">关于「{{ lastPrompt }}」 · </span>
        <span v-for="kw in keywords" :key="kw" class="keyword">{{ kw }}</span>
        <button v-if="lastPrompt" class="clear-prompt" @click="clearPrompt">
          清除
        </button>
      </div>
    </section>

    <!-- 内容区:加载中 / 诗词 / 空 -->
    <main class="poem-main container">
      <LoadingSpinner v-if="loading" />

      <article
        v-else-if="currentPoem"
        :key="currentPoem.id"
        class="poem-card fade-up"
      >
        <header class="poem-header">
          <h1 class="poem-title font-kaiti">{{ currentPoem.title }}</h1>
          <p class="poem-meta text-soft">
            <span>{{ currentPoem.author || "佚名" }}</span>
            <span v-if="currentPoem.dynasty"> · {{ currentPoem.dynasty }}</span>
          </p>
        </header>

        <div class="poem-content">
          <p v-for="(line, idx) in poemLines" :key="idx" class="poem-line">
            {{ line }}
          </p>
        </div>

        <footer class="poem-actions">
          <button
            class="action-btn"
            :class="{ 'is-active': currentPoem.is_favorited }"
            @click="handleFavoriteClick"
          >
            <span class="action-icon">{{
              currentPoem.is_favorited ? "♥" : "♡"
            }}</span>
            <span>{{ currentPoem.is_favorited ? "已收藏" : "收藏" }}</span>
          </button>

          <button class="action-btn" @click="loadNext">
            <span class="action-icon">↻</span>
            <span>换一首</span>
          </button>

          <button class="action-btn" @click="handleDislike">
            <span class="action-icon">✕</span>
            <span>不喜欢</span>
          </button>
        </footer>
      </article>

      <div v-else class="empty-state text-soft">暂无内容</div>
    </main>

    <!-- 收藏弹窗 -->
    <FavoriteDialog
      v-model="showFavoriteDialog"
      :poem="currentPoem"
      :my-tags="myTagNames"
      @success="onFavoriteSuccess"
    />

    <!-- 游客底部入口(已登录用户不显示) -->
    <footer v-if="!userStore.isLoggedIn" class="guest-entry">
      <RouterLink
        :to="{ path: '/login', query: { redirect: $route.fullPath } }"
        class="guest-entry-link"
      >
        登录 / 注册 · 收藏你心仪的诗句
      </RouterLink>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { RouterLink, useRouter, useRoute } from 'vue-router'
import { useRecommendStore } from '../stores/recommend'
import { useUserStore } from '../stores/user'
import { useToastStore } from '../stores/toast'
import * as favoriteApi from '../api/favorite'
import * as dislikeApi from '../api/dislike'
import FavoriteDialog from '../components/FavoriteDialog.vue'
import LoadingSpinner from '../components/LoadingSpinner.vue'

const recommendStore = useRecommendStore()
const userStore = useUserStore()
const toast = useToastStore()
const router = useRouter()
const route = useRoute()

// 从 store 解构出响应式状态(用 storeToRefs 保持响应性)
const { currentPoem, lastPrompt, keywords, loading } = storeToRefs(recommendStore)

// 输入框的本地状态
const promptInput = ref('')

// 收藏弹窗
const showFavoriteDialog = ref(false)

// 用户已用过的标签列表
const myTags = ref([])
const myTagNames = computed(() => myTags.value.map(t => t.name))

// === 诗句分行处理 ===
const poemLines = computed(() => {
  if (!currentPoem.value?.content) return []

  const rawLines = currentPoem.value.content
    .split('\n')
    .map(s => s.trim())
    .filter(Boolean)

  const result = []

  for (const line of rawLines) {
    const subs = line.split(/(?<=[,。;!?,.;!?])/g)
      .map(s => s.trim())
      .filter(Boolean)

    const maxSubLen = subs.reduce((max, s) => Math.max(max, s.length), 0)

    if (maxSubLen <= 6) {
      result.push(line)
    } else {
      result.push(...subs)
    }
  }

  return result
})

// === 进入页面:确保有诗显示 ===
onMounted(async () => {
  // 关键:只在 store 没诗时才加载,保留状态
  await recommendStore.ensurePoem()

  // 把 store 里的 lastPrompt 同步到输入框
  promptInput.value = lastPrompt.value

  // 如果已登录,顺便拉一下用户的标签列表
  if (userStore.isLoggedIn) {
    fetchMyTags()
  }
})

// === 用户主动操作 ===

// 寻诗(根据当前输入)
async function handlePromptSubmit() {
  if (loading.value) return
  await recommendStore.loadNewPoem(promptInput.value.trim())
}

// 换一首(沿用上次的 prompt)
async function loadNext() {
  await recommendStore.loadNewPoem(lastPrompt.value)
}

// 清除当前 prompt,加载随机诗
async function clearPrompt() {
  promptInput.value = ''
  await recommendStore.loadNewPoem('')
}

// 收藏按钮
async function handleFavoriteClick() {
  if (!currentPoem.value) return

  // 未登录:跳登录页,带 redirect 回来
  if (!userStore.isLoggedIn) {
    router.push({
      path: '/login',
      query: { redirect: route.fullPath }
    })
    return
  }

  // 已收藏:取消
  if (currentPoem.value.is_favorited) {
    try {
      await favoriteApi.remove(currentPoem.value.id)
      recommendStore.updateFavoriteStatus(false)
      toast.success('已取消收藏')
    } catch (e) {
      // 拦截器已处理
    }
    return
  }

  // 未收藏:打开弹窗
  showFavoriteDialog.value = true
}

// 收藏弹窗成功回调
function onFavoriteSuccess() {
  showFavoriteDialog.value = false
  recommendStore.updateFavoriteStatus(true)
  fetchMyTags()
}

// 不喜欢
async function handleDislike() {
  if (!currentPoem.value) return

  // 游客也允许"不喜欢"?如果你想限制只有登录用户才能点,加上下面这段
  if (!userStore.isLoggedIn) {
    router.push({
      path: '/login',
      query: { redirect: route.fullPath }
    })
    return
  }

  try {
    await dislikeApi.add(currentPoem.value.id)
    toast.success('已标记,将不再推荐')
    await recommendStore.loadNewPoem(lastPrompt.value)
  } catch (e) {
    // 拦截器已处理
  }
}

// === 辅助:拉用户标签 ===
async function fetchMyTags() {
  try {
    const data = await favoriteApi.listTags()
    myTags.value = data.tags || []
  } catch (e) {
    // 静默失败
  }
}
</script>

<style scoped>
.recommend-page {
  min-height: calc(100vh - var(--header-height));
  padding: var(--space-6) 0 var(--space-8);
}

/* 输入区 */
.prompt-section {
  margin-bottom: var(--space-7);
}
.prompt-input-wrap {
  display: flex;
  gap: 0;
  border: 1px solid var(--color-border);
  background: var(--color-bg-card);
}
.prompt-input {
  flex: 1;
  padding: var(--space-3) var(--space-4);
  font-size: var(--fs-base);
  font-family: var(--font-kaiti);
  letter-spacing: 1px;
}
.prompt-btn {
  padding: 0 var(--space-5);
  background: var(--color-accent);
  color: #fff;
  font-family: var(--font-kaiti);
  letter-spacing: 6px;
  font-size: var(--fs-base);
  transition: background var(--transition);
}
.prompt-btn:hover:not(:disabled) {
  background: var(--color-accent-hover);
}
.prompt-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.prompt-keywords {
  margin-top: var(--space-3);
  font-size: var(--fs-sm);
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}
.keyword {
  color: var(--color-accent);
  padding: 0 var(--space-2);
  border-bottom: 1px dashed var(--color-border);
}
.clear-prompt {
  margin-left: auto;
  font-size: var(--fs-xs);
  color: var(--color-text-faint);
  border-bottom: 1px solid transparent;
}
.clear-prompt:hover {
  color: var(--color-text-soft);
  border-bottom-color: currentColor;
}

/* 诗词卡片 */
.poem-main {
  min-height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.poem-card {
  width: 100%;
  text-align: center;
  padding: var(--space-7) 0;
}
.poem-header {
  margin-bottom: var(--space-6);
}
.poem-title {
  font-size: var(--fs-3xl);
  letter-spacing: 6px;
  color: var(--color-text);
  margin-bottom: var(--space-3);
}
.poem-meta {
  font-size: var(--fs-base);
  letter-spacing: 2px;
}
.poem-content {
  margin-bottom: var(--space-7);
  font-family: var(--font-kaiti);
  line-height: 2.4;
}
.poem-line {
  font-size: var(--fs-xl);
  letter-spacing: 4px;
  color: var(--color-text);
}
.poem-actions {
  display: flex;
  justify-content: center;
  gap: var(--space-6);
  padding-top: var(--space-5);
  border-top: 1px solid var(--color-border-soft);
}
.action-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  font-size: var(--fs-sm);
  color: var(--color-text-soft);
  transition: color var(--transition);
}
.action-btn:hover {
  color: var(--color-accent);
}
.action-btn.is-active {
  color: var(--color-accent);
}
.action-icon {
  font-size: var(--fs-lg);
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: var(--space-7);
  font-size: var(--fs-sm);
}

.guest-entry {
  margin-top: var(--space-7);
  padding: var(--space-5) 0;
  text-align: center;
}
.guest-entry-link {
  font-family: var(--font-kaiti);
  font-size: var(--fs-sm);
  color: var(--color-text-faint);
  letter-spacing: 2px;
  padding: var(--space-2) var(--space-4);
  border-bottom: 1px solid transparent;
  transition: all var(--transition);
}
.guest-entry-link:hover {
  color: var(--color-accent);
  border-bottom-color: var(--color-border);
}

@media (max-width: 640px) {
  .poem-line {
    font-size: var(--fs-lg);
    letter-spacing: 2px;
    line-height: 2.2;
  }
  .poem-line:nth-child(even) {
    margin-bottom: var(--space-2);
  }
  .poem-title {
    font-size: var(--fs-2xl);
    letter-spacing: 4px;
  }
}
</style>