// frontend/src/stores/recommend.js
import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as poemApi from '../api/poem'

export const useRecommendStore = defineStore('recommend', () => {
  // 当前显示的诗
  const currentPoem = ref(null)
  // 上次的输入(场景关键词)
  const lastPrompt = ref('')
  // 后端解析出的关键词 chip(展示用)
  const keywords = ref([])
  // Kimi 识别的意图
  const lastIntent = ref('random')
  // 已展示过的诗 ID(同一搜索条件下,避免"换一首"换出同一首)
  const seenIds = ref([])
  // 候选是否已耗尽
  const exhausted = ref(false)
  // 加载状态
  const loading = ref(false)

  /**
   * 加载新诗。
   *
   * @param {string} prompt - 新的搜索文案。空字符串 = 随机推荐
   * @param {boolean} resetSeen - 是否重置已看列表(改了 prompt 时为 true)
   */
  async function loadNewPoem(prompt = '', resetSeen = false) {
    loading.value = true

    // 改了 prompt(或显式重置),清空 seen
    if (resetSeen || prompt !== lastPrompt.value) {
      seenIds.value = []
      exhausted.value = false
    }

    try {
      const data = await poemApi.recommend(prompt, 1, seenIds.value)

      if (data.poems && data.poems.length > 0) {
        const newPoem = data.poems[0]
        currentPoem.value = newPoem
        // 把这首诗加入 seen
        if (!seenIds.value.includes(newPoem.id)) {
          seenIds.value.push(newPoem.id)
        }
        keywords.value = data.prompt_keywords || []
        lastPrompt.value = prompt
        lastIntent.value = data.intent || 'random'
        exhausted.value = false
      } else {
        // 没拿到诗(候选耗尽)
        exhausted.value = true
        // 注意:不清 currentPoem,让用户继续看到当前这首
      }
    } finally {
      loading.value = false
    }
  }

  /**
   * 进入页面时调用,只有空时才加载
   */
  async function ensurePoem() {
    if (!currentPoem.value) {
      await loadNewPoem('')
    }
  }

  /**
   * 换一首:沿用上次 prompt,但排除已看过的
   */
  async function loadAnother() {
    await loadNewPoem(lastPrompt.value, false)
  }

  /**
   * 重新搜索:用户改了输入,重置 seen 列表
   */
  async function searchNew(prompt) {
    await loadNewPoem(prompt, true)
  }

  /**
   * 更新当前诗的收藏状态
   */
  function updateFavoriteStatus(isFavorited) {
    if (currentPoem.value) {
      currentPoem.value.is_favorited = isFavorited
    }
  }

  function reset() {
    currentPoem.value = null
    lastPrompt.value = ''
    keywords.value = []
    lastIntent.value = 'random'
    seenIds.value = []
    exhausted.value = false
  }

  return {
    currentPoem,
    lastPrompt,
    keywords,
    lastIntent,
    seenIds,
    exhausted,
    loading,
    loadNewPoem,
    loadAnother,
    searchNew,
    ensurePoem,
    updateFavoriteStatus,
    reset,
  }
})