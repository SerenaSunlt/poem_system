<template>
  <div class="detail-page container">
    <button class="back-btn text-soft" @click="goBack">← 返回</button>

    <LoadingSpinner v-if="loading" />

    <div v-else-if="poem" class="detail-content">
      <PoemCard :poem="poem" mode="hero" />

      <div class="divider"></div>

      <!-- 收藏区 -->
      <section class="favorite-section">
        <!-- 已收藏 -->
        <div v-if="poem.is_favorited && poem.favorite_info" class="favorited">
          <p class="favorited-status">
            <span class="text-accent">♥ 已收藏</span>
            <span class="text-faint" v-if="poem.favorite_info.created_at">
              · {{ formatDate(poem.favorite_info.created_at) }}
            </span>
          </p>

          <div v-if="poem.favorite_info.user_tags?.length" class="user-tags">
            <span
              v-for="t in poem.favorite_info.user_tags"
              :key="t"
              class="user-tag"
              >{{ t }}</span
            >
          </div>

          <p v-if="poem.favorite_info.note" class="user-note text-soft">
            {{ poem.favorite_info.note }}
          </p>

          <div class="favorite-actions">
            <button class="action-link" @click="openEdit">编辑</button>
            <span class="action-divider text-faint">·</span>
            <button class="action-link" @click="handleRemove">取消收藏</button>
          </div>
        </div>

        <!-- 未收藏 -->
        <div v-else class="unfavorited">
          <button class="btn btn-outline" @click="handleFavoriteClick">
            ♡ 收藏这首诗
          </button>
        </div>
      </section>
    </div>

    <div v-else class="empty-state text-soft">未找到这首诗</div>

    <!-- 编辑弹窗 -->
    <FavoriteDialog
      v-model="showDialog"
      :poem="poem"
      :is-edit="isEditMode"
      :initial-tags="dialogInitialTags"
      :initial-note="dialogInitialNote"
      :my-tags="myTagNames"
      @success="onFavoriteSuccess"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import * as poemApi from "../api/poem";
import * as favoriteApi from "../api/favorite";
import { useUserStore } from "../stores/user";
import { useToastStore } from "../stores/toast";
import PoemCard from "../components/PoemCard.vue";
import LoadingSpinner from "../components/LoadingSpinner.vue";
import FavoriteDialog from "../components/FavoriteDialog.vue";

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
const toastStore = useToastStore();

// === 数据 ===
const poem = ref(null);
const loading = ref(false);
const myTags = ref([]);
const myTagNames = computed(() => myTags.value.map((t) => t.name));

// === 弹窗 ===
const showDialog = ref(false);
const isEditMode = ref(false);
const dialogInitialTags = ref([]);
const dialogInitialNote = ref("");

// === 加载 ===
async function loadPoem() {
  const id = route.params.id;
  if (!id) return;
  loading.value = true;
  try {
    poem.value = await poemApi.getPoem(id);
  } catch (e) {
    poem.value = null;
  } finally {
    loading.value = false;
  }
}

async function loadMyTags() {
  if (!userStore.isLoggedIn) return;
  try {
    const data = await favoriteApi.listMyTags();
    myTags.value = data.tags || [];
  } catch (e) {
    myTags.value = [];
  }
}

// === 收藏(从未收藏出发) ===
async function handleFavoriteClick() {
  if (!userStore.isLoggedIn) {
    toastStore.info("请先登录后再收藏");
    router.push({
      name: "login",
      query: { redirect: route.fullPath },
    });
    return;
  }
  await loadMyTags();
  isEditMode.value = false;
  dialogInitialTags.value = [];
  dialogInitialNote.value = "";
  showDialog.value = true;
}

// === 编辑(从已收藏出发) ===
async function openEdit() {
  await loadMyTags();
  isEditMode.value = true;
  dialogInitialTags.value = [...(poem.value.favorite_info?.user_tags || [])];
  dialogInitialNote.value = poem.value.favorite_info?.note || "";
  showDialog.value = true;
}

async function onFavoriteSuccess() {
  // 重新加载诗,拿最新的 is_favorited 和 favorite_info
  await loadPoem();
}

// === 取消收藏 ===
async function handleRemove() {
  try {
    await favoriteApi.removeFavorite(poem.value.id);
    toastStore.success("已取消收藏");
    await loadPoem();
  } catch (e) {}
}

// === 工具 ===
function goBack() {
  if (window.history.length > 1) {
    router.back();
  } else {
    router.push("/recommend");
  }
}

function formatDate(iso) {
  const d = new Date(iso);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}.${m}.${day}`;
}

// === 路由参数变化时重新加载 ===
// (虽然这个页面是详情,但用户可能从详情跳到另一首详情)
watch(
  () => route.params.id,
  (newId, oldId) => {
    if (newId && newId !== oldId) {
      loadPoem();
    }
  },
);

onMounted(() => {
  loadPoem();
  loadMyTags();
});
</script>

<style scoped>
.detail-page {
  padding: var(--space-5) var(--space-5) var(--space-8);
  min-height: calc(100vh - var(--header-height));
}
.back-btn {
  font-size: var(--fs-sm);
  margin-bottom: var(--space-4);
  padding: var(--space-2) 0;
}
.back-btn:hover {
  color: var(--color-accent);
}

.detail-content {
  max-width: 700px;
  margin: 0 auto;
}

/* 收藏区 */
.favorite-section {
  text-align: center;
  padding: var(--space-5) 0;
}
.favorited-status {
  font-size: var(--fs-base);
  margin-bottom: var(--space-3);
  letter-spacing: 1px;
}
.user-tags {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}
.user-tag {
  font-size: var(--fs-sm);
  padding: 2px var(--space-3);
  background: var(--color-border-soft);
  color: var(--color-text-soft);
}
.user-note {
  font-size: var(--fs-sm);
  font-style: italic;
  margin-bottom: var(--space-4);
  max-width: 500px;
  margin-left: auto;
  margin-right: auto;
}
.favorite-actions {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--fs-sm);
}
.action-link {
  color: var(--color-text-soft);
  font-size: var(--fs-sm);
  transition: color var(--transition);
}
.action-link:hover {
  color: var(--color-accent);
}

.unfavorited {
  text-align: center;
}

.empty-state {
  text-align: center;
  padding: var(--space-8);
  font-size: var(--fs-sm);
}
</style>
