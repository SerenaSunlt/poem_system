<template>
  <div class="translation-page container">
    <header class="page-header">
      <button class="back-btn text-soft" @click="goBack">返回</button>
      <h1 v-if="poem" class="page-title font-kaiti">
        《{{ poem.title }}》翻译
      </h1>
    </header>

    <!-- 加载中(初次或重新翻译) -->
    <div v-if="loading" class="loading-block">
      <LoadingSpinner />
      <p class="loading-text text-soft font-kaiti">{{ loadingText }}</p>
    </div>

    <!-- 翻译失败 -->
    <div v-else-if="errorMessage" class="error-block text-soft">
      <p>{{ errorMessage }}</p>
      <button class="btn btn-soft" @click="doTranslate">重试</button>
    </div>

    <!-- 翻译内容 -->
    <article v-else-if="translation" class="translation-content">
      <!-- 整体翻译 -->
      <section class="overall-section">
        <h2 class="section-label text-soft">题解</h2>
        <p class="overall-text">{{ translation.overall }}</p>
      </section>

      <div class="divider"></div>

      <!-- 逐句翻译 -->
      <section class="lines-section">
        <h2 class="section-label text-soft">逐句</h2>
        <div class="lines-list">
          <div
            v-for="(line, idx) in translation.lines"
            :key="idx"
            class="line-block"
          >
            <p class="line-original font-kaiti">{{ line.original }}</p>
            <p class="line-translation">{{ line.translation }}</p>
            <ul v-if="line.annotations?.length" class="annotations">
              <li
                v-for="(ann, aIdx) in line.annotations"
                :key="aIdx"
                class="annotation"
              >
                <span class="ann-word font-kaiti">{{ ann.word }}</span>
                <span class="ann-sep text-faint">·</span>
                <span class="ann-meaning text-soft">{{ ann.meaning }}</span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      <!-- 操作栏 -->
      <footer class="action-bar">
        <!-- 临时翻译:可保存 / 重新翻译 -->
        <template v-if="!isSaved">
          <button class="btn-ghost" @click="doTranslate" :disabled="loading">
            重新翻译
          </button>
          <button class="btn" @click="doSave" :disabled="saving">
            {{ saving ? '保存中...' : '保 存' }}
          </button>
        </template>

        <!-- 已保存:可重新翻译(再点保存就覆盖) -->
        <template v-else>
          <p class="saved-hint text-faint">
            已保存 · {{ formatDate(updatedAt) }}
          </p>
          <button class="btn-ghost" @click="doTranslate" :disabled="loading">
            重新翻译
          </button>
        </template>
      </footer>
    </article>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as poemApi from '../api/poem'
import * as translationApi from '../api/translation'
import { useToastStore } from '../stores/toast'
import LoadingSpinner from '../components/LoadingSpinner.vue'

const route = useRoute()
const router = useRouter()
const toast = useToastStore()

// === 数据 ===
const poem = ref(null)
const translation = ref(null)        // { overall, lines }
const isSaved = ref(false)             // 当前展示的翻译是不是已保存
const updatedAt = ref(null)
const loading = ref(false)
const saving = ref(false)
const errorMessage = ref('')

// 加载提示文案随机(等 5-15 秒,加点趣味)
const loadingMessages = [
  '正在请古人解释自己 ...',
  '把诗翻给现代人看看 ...',
  '让 AI 读了几遍这首诗 ...',
  '正在咬文嚼字 ...',
  '稍等,推敲中 ...',
]
const loadingText = ref(loadingMessages[0])

function pickLoadingText() {
  loadingText.value =
    loadingMessages[Math.floor(Math.random() * loadingMessages.length)]
}

// === 操作 ===

async function loadPoem() {
  const id = route.params.id
  try {
    poem.value = await poemApi.getPoem(id)
  } catch (e) {
    // 拦截器已 toast
  }
}

async function loadOrTranslate() {
  // 先看有没有保存过的翻译
  loading.value = true
  errorMessage.value = ''
  pickLoadingText()

  try {
    const data = await translationApi.getMyTranslation(route.params.id)
    if (data.is_saved && data.translation) {
      // 已经有保存的,直接展示
      translation.value = data.translation
      isSaved.value = true
      updatedAt.value = data.updated_at
      loading.value = false
      return
    }
  } catch (e) {
    // 查询失败也无所谓,继续走翻译
  }

  // 没有保存过,调 Kimi 翻译
  await doTranslate()
}

async function doTranslate() {
  loading.value = true
  errorMessage.value = ''
  pickLoadingText()

  try {
    const data = await translationApi.requestTranslation(route.params.id)
    translation.value = data.translation
    isSaved.value = false      // 临时翻译,未保存
    updatedAt.value = null
  } catch (e) {
    // 拦截器已 toast,这里设置 errorMessage 作为页面级提示
    errorMessage.value = '翻译失败,请稍后再试'
  } finally {
    loading.value = false
  }
}

async function doSave() {
  if (!translation.value) return

  saving.value = true
  try {
    const data = await translationApi.saveTranslation(
      route.params.id,
      translation.value
    )
    isSaved.value = true
    updatedAt.value = data.updated_at
    toast.success('已保存')
  } catch (e) {
    // 拦截器已 toast
  } finally {
    saving.value = false
  }
}

function goBack() {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push({ name: 'poem-detail', params: { id: route.params.id } })
  }
}

function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}.${m}.${day}`
}

// === 初始化 ===
onMounted(async () => {
  await loadPoem()
  await loadOrTranslate()
})
</script>

<style scoped>
.translation-page {
  padding: var(--space-5) var(--space-5) var(--space-8);
  max-width: 700px;
  margin: 0 auto;
  min-height: calc(100vh - var(--header-height));
}

/* 头部 */
.page-header {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}
.back-btn {
  font-size: var(--fs-sm);
  padding: var(--space-2) 0;
}
.back-btn:hover {
  color: var(--color-accent);
}
.page-title {
  font-size: var(--fs-xl);
  letter-spacing: 4px;
}

/* 加载 */
.loading-block {
  text-align: center;
  padding: var(--space-8) 0;
}
.loading-text {
  margin-top: var(--space-4);
  font-size: var(--fs-base);
  letter-spacing: 2px;
}

/* 错误 */
.error-block {
  text-align: center;
  padding: var(--space-7) var(--space-5);
}
.error-block .btn {
  margin-top: var(--space-4);
}

/* 翻译内容 */
.translation-content {
  padding: var(--space-3) 0;
}
.section-label {
  font-size: var(--fs-sm);
  letter-spacing: 4px;
  margin-bottom: var(--space-3);
  font-family: var(--font-kaiti);
}
.overall-section {
  margin-bottom: var(--space-5);
}
.overall-text {
  font-size: var(--fs-base);
  line-height: 1.9;
  letter-spacing: 1px;
  color: var(--color-text);
}

.divider {
  height: 1px;
  background: var(--color-border-soft);
  margin: var(--space-6) auto;
  max-width: 200px;
}

/* 逐句 */
.lines-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}
.line-block {
  padding: var(--space-3) 0;
}
.line-original {
  font-size: var(--fs-lg);
  letter-spacing: 4px;
  line-height: 2;
  color: var(--color-text);
  margin-bottom: var(--space-2);
}
.line-translation {
  font-size: var(--fs-base);
  line-height: 1.9;
  color: var(--color-text-soft);
  letter-spacing: 1px;
  padding-left: var(--space-3);
  border-left: 2px solid var(--color-border-soft);
}
.annotations {
  margin-top: var(--space-3);
  padding-left: var(--space-4);
  list-style: none;
}
.annotation {
  font-size: var(--fs-sm);
  line-height: 1.9;
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
}
.ann-word {
  color: var(--color-accent);
  font-size: var(--fs-base);
  letter-spacing: 1px;
  min-width: 40px;
}
.ann-meaning {
  flex: 1;
}

/* 操作栏 */
.action-bar {
  margin-top: var(--space-7);
  padding-top: var(--space-5);
  border-top: 1px solid var(--color-border-soft);
  display: flex;
  justify-content: center;
  align-items: center;
  gap: var(--space-5);
  flex-wrap: wrap;
}
.saved-hint {
  font-size: var(--fs-sm);
  margin-right: var(--space-3);
}

/* 移动端 */
@media (max-width: 640px) {
  .line-original {
    font-size: var(--fs-base);
    letter-spacing: 2px;
  }
  .overall-text,
  .line-translation {
    font-size: var(--fs-sm);
  }
}
</style>