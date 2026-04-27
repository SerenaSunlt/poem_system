// frontend/src/api/translation.js
import client from './client'

/**
 * 查询当前用户对某首诗的翻译(已保存的)
 * @returns {Promise<{poem_id, is_saved, translation, created_at?, updated_at?}>}
 */
export function getMyTranslation(poemId) {
  return client.get(`/api/translations/${poemId}`)
}

/**
 * 触发翻译(调 Kimi),返回翻译结果但不入库
 */
export function requestTranslation(poemId) {
  return client.post(`/api/translations/${poemId}`)
}

/**
 * 保存翻译
 * @param {object} translationData - { overall, lines: [...] }
 */
export function saveTranslation(poemId, translationData) {
  return client.put(`/api/translations/${poemId}`, {
    translation: translationData,
  })
}