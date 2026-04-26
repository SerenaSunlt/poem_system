<template>
  <div class="favorites-page container">
    <!-- 头部 -->
    <header class="page-header">
      <h1 class="page-title font-kaiti">我的收藏</h1>
      <p class="page-meta text-soft">
        共 <span class="text-accent">{{ total }}</span> 首
      </p>
    </header>

    <!-- 搜索 + 筛选 -->
    <section class="filters">
      <div class="search-row">
        <input
          v-model="keyword"
          class="input"
          placeholder="搜索标题、作者、内容 ..."
          maxlength="50"
        />
      </div>

      <div v-if="myTags.length" class="tag-filter">
        <button
          class="tag-btn"
          :class="{ 'is-active': !selectedTag }"
          @click="selectTag('')"
        >
          全部
        </button>
        <button
          v-for="t in myTags"
          :key="t.name"
          class="tag-btn"
          :class="{ 'is-active': selectedTag === t.name }"
          @click="selectTag(t.name)"
        >
          {{ t.name }}
          <span class="tag-count">{{ t.count }}</span>
        </button>
      </div>
    </section>

    <!-- 列表 -->
    <main class="favorites-main">
      <LoadingSpinner v-if="loading" />

      <ul v-else-if="items.length" class="card-list">
        <li
          v-for="(item, idx) in items"
          :key="item.favorite_id"
          class="card-wrap fade-up"
          :style="{ animationDelay: idx * 60 + 'ms' }"
        >
          <div class="card-clickable" @click="goDetail(item.poem.id)">
            <PoemCard
              :poem="item.poem"
              mode="list"
              :user-tags="item.user_tags"
              :note="item.note"
            />
          </div>

          <div class="card-actions">
            <button class="action-link" @click="openEdit(item)">编辑</button>
            <span class="action-divider">·</span>
            <template v-if="confirmingId !== item.favorite_id">
              <button class="action-link" @click="confirmDelete(item)">
                删除
              </button>
            </template>
            <template v-else>
              <button class="action-link text-error" @click="doDelete(item)">
                确认删除
              </button>
              <span class="action-divider">·</span>
              <button class="action-link" @click="cancelDelete">取消</button>
            </template>
          </div>
        </li>
      </ul>

      <div v-else class="empty-state text-soft">
        <p v-if="keyword || selectedTag">没有匹配的收藏</p>
        <p v-else>
          还没有收藏的诗,
          <RouterLink to="/recommend" class="text-accent"
            >去发现一首</RouterLink
          >
        </p>
      </div>
    </main>

    <!-- 分页 -->
    <nav v-if="totalPages > 1" class="pagination">
      <button class="page-btn" :disabled="page <= 1" @click="goPage(page - 1)">
        上一页
      </button>

      <span class="page-info text-soft">{{ page }} / {{ totalPages }}</span>

      <button
        class="page-btn"
        :disabled="page >= totalPages"
        @click="goPage(page + 1)"
      >
        下一页
      </button>
    </nav>

    <!-- 编辑弹窗 -->
    <FavoriteDialog
      v-model="showEditDialog"
      :poem="editingPoem"
      :is-edit="true"
      :initial-tags="editingTags"
      :initial-note="editingNote"
      :my-tags="myTagNames"
      @success="onEditSuccess"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { useRouter } from "vue-router";
import * as favoriteApi from "../api/favorite";
import { useToastStore } from "../stores/toast";
import PoemCard from "../components/PoemCard.vue";
import LoadingSpinner from "../components/LoadingSpinner.vue";
import FavoriteDialog from "../components/FavoriteDialog.vue";

const router = useRouter();
const toastStore = useToastStore();

// === 列表数据 ===
const items = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = 10;
const loading = ref(false);

const totalPages = computed(() => Math.ceil(total.value / pageSize) || 1);

// === 筛选条件 ===
const keyword = ref("");
const selectedTag = ref("");
const myTags = ref([]);
const myTagNames = computed(() => myTags.value.map((t) => t.name));

// === 编辑弹窗 ===
const showEditDialog = ref(false);
const editingPoem = ref(null);
const editingTags = ref([]);
const editingNote = ref("");

// === 删除二次确认 ===
const confirmingId = ref(null);

// === 加载列表 ===
async function loadList() {
  loading.value = true;
  try {
    const data = await favoriteApi.listFavorites({
      tag: selectedTag.value || undefined,
      keyword: keyword.value || undefined,
      page: page.value,
      pageSize,
    });
    items.value = data.items || [];
    total.value = data.total || 0;
  } catch (e) {
    items.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
}

async function loadMyTags() {
  try {
    const data = await favoriteApi.listMyTags();
    myTags.value = data.tags || [];
  } catch (e) {
    myTags.value = [];
  }
}

// === 搜索防抖 ===
let searchTimer = null;
watch(keyword, () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    page.value = 1;
    loadList();
  }, 300);
});

// === 标签筛选 ===
function selectTag(tagName) {
  selectedTag.value = tagName;
  page.value = 1;
  loadList();
}

// === 分页 ===
function goPage(p) {
  if (p < 1 || p > totalPages.value) return;
  page.value = p;
  loadList();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// === 跳详情 ===
function goDetail(poemId) {
  router.push({ name: "poem-detail", params: { id: poemId } });
}

// === 编辑 ===
function openEdit(item) {
  editingPoem.value = item.poem;
  editingTags.value = [...item.user_tags];
  editingNote.value = item.note || "";
  showEditDialog.value = true;
}

async function onEditSuccess() {
  // 刷新列表 + 刷新标签(改了标签可能影响标签列表)
  await Promise.all([loadList(), loadMyTags()]);
}

// === 删除 ===
function confirmDelete(item) {
  confirmingId.value = item.favorite_id;
}

function cancelDelete() {
  confirmingId.value = null;
}

async function doDelete(item) {
  try {
    await favoriteApi.removeFavorite(item.poem.id);
    toastStore.success("已取消收藏");
    confirmingId.value = null;
    // 如果当前页删空了且不是第一页,回上一页
    if (items.value.length === 1 && page.value > 1) {
      page.value -= 1;
    }
    await Promise.all([loadList(), loadMyTags()]);
  } catch (e) {}
}

// === 初始化 ===
onMounted(() => {
  loadList();
  loadMyTags();
});
</script>

<style scoped>
.favorites-page {
  padding: var(--space-6) var(--space-5) var(--space-8);
}

/* 头部 */
.page-header {
  text-align: center;
  margin-bottom: var(--space-6);
}
.page-title {
  font-size: var(--fs-2xl);
  letter-spacing: 4px;
  margin-bottom: var(--space-2);
}
.page-meta {
  font-size: var(--fs-sm);
}

/* 筛选 */
.filters {
  margin-bottom: var(--space-6);
  padding-bottom: var(--space-5);
  border-bottom: 1px solid var(--color-border-soft);
}
.search-row {
  margin-bottom: var(--space-3);
}
.tag-filter {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.tag-btn {
  font-size: var(--fs-sm);
  padding: var(--space-1) var(--space-3);
  border: 1px solid var(--color-border);
  color: var(--color-text-soft);
  background: var(--color-bg-card);
  transition: all var(--transition);
}
.tag-btn:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}
.tag-btn.is-active {
  background: var(--color-accent);
  border-color: var(--color-accent);
  color: #fff;
}
.tag-count {
  margin-left: 4px;
  font-size: var(--fs-xs);
  opacity: 0.75;
}

/* 列表 */
.favorites-main {
  min-height: 200px;
}
.card-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.card-wrap {
  position: relative;
}
.card-clickable {
  cursor: pointer;
}
.card-actions {
  position: absolute;
  top: var(--space-3);
  right: var(--space-3);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--fs-xs);
}
.action-link {
  color: var(--color-text-soft);
  font-size: var(--fs-xs);
  transition: color var(--transition);
}
.action-link:hover {
  color: var(--color-accent);
}
.action-link.text-error:hover {
  color: var(--color-error);
}
.action-divider {
  color: var(--color-text-faint);
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: var(--space-8) var(--space-5);
  font-size: var(--fs-sm);
}

/* 分页 */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: var(--space-5);
  margin-top: var(--space-7);
}
.page-btn {
  padding: var(--space-2) var(--space-4);
  border: 1px solid var(--color-border);
  background: var(--color-bg-card);
  color: var(--color-text-soft);
  font-size: var(--fs-sm);
  transition: all var(--transition);
}
.page-btn:hover:not(:disabled) {
  border-color: var(--color-accent);
  color: var(--color-accent);
}
.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.page-info {
  font-size: var(--fs-sm);
}
</style>
