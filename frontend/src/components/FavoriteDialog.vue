<template>
  <Teleport to="body">
    <div v-if="modelValue" class="dialog-mask" @click.self="close">
      <div class="dialog-box">
        <h3 class="dialog-title font-kaiti">
          {{ isEdit ? "编辑收藏" : "收藏这首诗" }}
        </h3>

        <div class="poem-summary text-soft">
          <span class="font-kaiti">《{{ poem?.title }}》</span>
          <span> · {{ poem?.author }}</span>
        </div>

        <div class="field">
          <label class="field-label">标签</label>
          <div class="tags-input">
            <span v-for="(tag, idx) in tags" :key="idx" class="tag-chip">
              {{ tag }}
              <button class="tag-remove" @click="removeTag(idx)">×</button>
            </span>
            <input
              v-model="tagDraft"
              class="tag-input"
              placeholder="输入标签后回车"
              @keydown.enter.prevent="addTag"
              @keydown.backspace="onBackspace"
              maxlength="20"
            />
          </div>
          <p v-if="suggestedTags.length > 0" class="suggested">
            <span class="text-faint">常用:</span>
            <button
              v-for="t in suggestedTags"
              :key="t"
              class="suggested-tag"
              @click="addSuggestedTag(t)"
            >
              {{ t }}
            </button>
          </p>
        </div>

        <div class="field">
          <label class="field-label">备注(可选)</label>
          <textarea
            v-model="note"
            class="input note-input"
            rows="3"
            maxlength="500"
            placeholder="比如:2026 五一杭州行"
          ></textarea>
        </div>

        <div class="dialog-actions">
          <button class="btn-ghost" @click="close">取消</button>
          <button class="btn" :disabled="loading" @click="submit">
            {{ loading ? "保存中..." : "保存" }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch, computed } from "vue";
import * as favoriteApi from "../api/favorite";
import { useToastStore } from "../stores/toast";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  poem: { type: Object, default: null },
  isEdit: { type: Boolean, default: false },
  initialTags: { type: Array, default: () => [] },
  initialNote: { type: String, default: "" },
  myTags: { type: Array, default: () => [] }, // 用户已有的标签
});

const emit = defineEmits(["update:modelValue", "success"]);

const toastStore = useToastStore();

const tags = ref([]);
const tagDraft = ref("");
const note = ref("");
const loading = ref(false);

// 弹窗打开时初始化数据
watch(
  () => props.modelValue,
  (val) => {
    if (val) {
      tags.value = [...props.initialTags];
      note.value = props.initialNote || "";
      tagDraft.value = "";
    }
  },
  { immediate: true },
);

// 推荐已有标签:用户用过的标签里,当前没选的前几个
const suggestedTags = computed(() => {
  return props.myTags.filter((t) => !tags.value.includes(t)).slice(0, 5);
});

function addTag() {
  const v = tagDraft.value.trim();
  if (!v) return;
  if (tags.value.includes(v)) {
    tagDraft.value = "";
    return;
  }
  if (tags.value.length >= 10) {
    toastStore.error("最多 10 个标签");
    return;
  }
  tags.value.push(v);
  tagDraft.value = "";
}

function addSuggestedTag(t) {
  if (!tags.value.includes(t) && tags.value.length < 10) {
    tags.value.push(t);
  }
}

function removeTag(idx) {
  tags.value.splice(idx, 1);
}

// 在空输入框上按 backspace 删除最后一个标签
function onBackspace(e) {
  if (!tagDraft.value && tags.value.length > 0) {
    tags.value.pop();
  }
}

function close() {
  emit("update:modelValue", false);
}

async function submit() {
  if (loading.value) return;
  loading.value = true;
  try {
    if (props.isEdit) {
      await favoriteApi.updateFavorite(props.poem.id, {
        userTags: tags.value,
        note: note.value || null,
      });
      toastStore.success("已更新");
    } else {
      await favoriteApi.addFavorite(
        props.poem.id,
        tags.value,
        note.value || null,
      );
      toastStore.success("已收藏");
    }
    emit("success");
    close();
  } catch (e) {
    // 拦截器已弹 toast
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.dialog-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: var(--space-5);
}
.dialog-box {
  width: 100%;
  max-width: 480px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  padding: var(--space-6);
}
.dialog-title {
  font-size: var(--fs-xl);
  letter-spacing: 4px;
  margin-bottom: var(--space-3);
}
.poem-summary {
  font-size: var(--fs-sm);
  margin-bottom: var(--space-5);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border-soft);
}
.field {
  margin-bottom: var(--space-5);
}
.field-label {
  display: block;
  font-size: var(--fs-sm);
  color: var(--color-text-soft);
  margin-bottom: var(--space-2);
}
.tags-input {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  min-height: 48px;
}
.tag-chip {
  display: inline-flex;
  align-items: center;
  padding: 2px var(--space-2);
  background: var(--color-border-soft);
  font-size: var(--fs-sm);
  color: var(--color-text);
}
.tag-remove {
  margin-left: 4px;
  font-size: var(--fs-base);
  color: var(--color-text-soft);
  line-height: 1;
}
.tag-remove:hover {
  color: var(--color-error);
}
.tag-input {
  flex: 1;
  min-width: 100px;
  border: none;
  background: transparent;
  padding: 4px 0;
  font-size: var(--fs-sm);
}
.suggested {
  margin-top: var(--space-2);
  font-size: var(--fs-xs);
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
}
.suggested-tag {
  font-size: var(--fs-xs);
  color: var(--color-accent);
  border: 1px dashed var(--color-border);
  padding: 1px var(--space-2);
}
.suggested-tag:hover {
  background: var(--color-border-soft);
}
.note-input {
  resize: vertical;
  min-height: 60px;
  font-family: var(--font-sans);
}
.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  margin-top: var(--space-5);
}
</style>
