// frontend/src/stores/recommend.js
import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as poemApi from '../api/poem'

export const useRecommendStore = defineStore('recommend', () => {
  // 当前显示的诗
  const currentPoem = ref(null)
  // 上次的输入(场景关键词)
  const lastPrompt = ref('')
  // Kimi 解析出的关键词
  const keywords = ref([])
  // 加载状态
  const loading = ref(false)

  /**
   * 加载新诗(主动调用,会请求接口)
   */
  async function loadNewPoem(prompt = '') {
    loading.value = true
    try {
      const data = await poemApi.recommend(prompt, 1)
      if (data.poems && data.poems.length > 0) {
        currentPoem.value = data.poems[0]
        keywords.value = data.prompt_keywords || []
        lastPrompt.value = prompt
      } else {
        currentPoem.value = null
      }
    } finally {
      loading.value = false
    }
  }

  /**
   * 确保有诗显示(进入页面时调用,只有空时才加载)
   */
  async function ensurePoem() {
    if (!currentPoem.value) {
      await loadNewPoem()
    }
  }

  /**
   * 更新当前诗的收藏状态
   */
  function updateFavoriteStatus(isFavorited) {
    if (currentPoem.value) {
      currentPoem.value.is_favorited = isFavorited
    }
  }

  /**
   * 清空(可选)
   */
  function reset() {
    currentPoem.value = null
    lastPrompt.value = ''
    keywords.value = []
  }

  return {
    currentPoem,
    lastPrompt,
    keywords,
    loading,
    loadNewPoem,
    ensurePoem,
    updateFavoriteStatus,
    reset,
  }
})