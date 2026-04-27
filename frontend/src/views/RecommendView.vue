<template>
  <div class="recommend-page">
    <!-- 输入区 -->
    <section class="prompt-section container">
      <div class="prompt-input-wrap">
        <input
          v-model="promptInput"
          class="prompt-input"
          placeholder="这一刻想写点什么 ..."
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
      <RouterLink to="/login" class="guest-entry-link">
        登录 / 注册 · 收藏你心仪的诗句
      </RouterLink>
    </footer>
  </div>

</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import * as poemApi from "../api/poem";
import * as favoriteApi from "../api/favorite";
import * as dislikeApi from "../api/dislike";
import { useUserStore } from "../stores/user";
import { useToastStore } from "../stores/toast";
import LoadingSpinner from "../components/LoadingSpinner.vue";
import FavoriteDialog from "../components/FavoriteDialog.vue";

const router = useRouter();
const userStore = useUserStore();
const toastStore = useToastStore();

// === 状态 ===
const promptInput = ref(""); // 输入框当前值
const lastPrompt = ref(""); // 上次提交的 prompt(决定"换一首"是否带 prompt)
const keywords = ref([]); // AI 解析出的关键词
const currentPoem = ref(null);
const loading = ref(false);
const showFavoriteDialog = ref(false);
const myTags = ref([]); // 用户已有标签(给弹窗推荐用)

// === 计算属性 ===
// 把诗词正文按换行拆成数组,方便每行单独渲染
const poemLines = computed(() => {
  if (!currentPoem.value?.content) return []

  const rawLines = currentPoem.value.content
    .split('\n')
    .map(s => s.trim())
    .filter(Boolean)

  const result = []

  for (const line of rawLines) {
    // 把这一行切成分句
    const subs = line.split(/(?<=[,。;!?,.;!?])/g)
      .map(s => s.trim())
      .filter(Boolean)

    // 看这一行里最长的分句多少字符
    const maxSubLen = subs.reduce((max, s) => Math.max(max, s.length), 0)

    if (maxSubLen <= 6) {
      // 短行(五言、四言等)→ 保持原样,把这一行作为整体
      result.push(line)
    } else {
      // 长行(七言以上)→ 拆成单句
      result.push(...subs)
    }
  }

  return result
})
const myTagNames = computed(() => myTags.value.map((t) => t.name));


// === 加载诗 ===
async function loadPoem(prompt = "") {
  loading.value = true;
  try {
    const data = await poemApi.recommend(prompt, 1);
    if (data.poems && data.poems.length > 0) {
      currentPoem.value = data.poems[0];
      keywords.value = data.prompt_keywords || [];
      lastPrompt.value = prompt;
    } else {
      currentPoem.value = null;
    }
  } catch (e) {
    // 拦截器已弹 toast
  } finally {
    loading.value = false;
  }
}

async function loadNext() {
  await loadPoem(lastPrompt.value);
}

// === Prompt 处理 ===
async function handlePromptSubmit() {
  const p = promptInput.value.trim();
  if (!p) return;
  await loadPoem(p);
}

function clearPrompt() {
  promptInput.value = "";
  lastPrompt.value = "";
  keywords.value = [];
  loadPoem();
}

// === 收藏 ===
async function handleFavoriteClick() {
  // 游客提示登录
  if (!userStore.isLoggedIn) {
    toastStore.info("请先登录后再收藏");
    router.push({ name: "login", query: { redirect: "/recommend" } });
    return;
  }

  // 已收藏 → 取消收藏
  if (currentPoem.value.is_favorited) {
    try {
      await favoriteApi.removeFavorite(currentPoem.value.id);
      currentPoem.value.is_favorited = false;
      toastStore.success("已取消收藏");
    } catch (e) {}
    return;
  }

  // 未收藏 → 打开弹窗
  await loadMyTags();
  showFavoriteDialog.value = true;
}

async function loadMyTags() {
  try {
    const data = await favoriteApi.listMyTags();
    myTags.value = data.tags || [];
  } catch (e) {
    myTags.value = [];
  }
}

function onFavoriteSuccess() {
  if (currentPoem.value) {
    currentPoem.value.is_favorited = true;
  }
}

// === 不喜欢 ===
async function handleDislike() {
  if (!userStore.isLoggedIn) {
    toastStore.info("请先登录");
    router.push({ name: "login", query: { redirect: "/recommend" } });
    return;
  }
  if (!currentPoem.value) return;

  try {
    await dislikeApi.addDislike(currentPoem.value.id);
    toastStore.info("已为你过滤这首");
    await loadNext();
  } catch (e) {}
}

// === 初始化 ===
onMounted(() => {
  loadPoem();
});
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
