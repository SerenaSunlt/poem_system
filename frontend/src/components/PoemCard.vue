<template>
  <article class="poem-card" :class="`mode-${mode}`">
    <header class="card-header">
      <h2 class="card-title font-kaiti">{{ poem.title }}</h2>
      <p class="card-meta text-soft">
        <span>{{ poem.author || "佚名" }}</span>
        <span v-if="poem.dynasty"> · {{ poem.dynasty }}</span>
      </p>
    </header>

    <div class="card-content">
      <p v-for="(line, idx) in poemLines" :key="idx" class="card-line">
        {{ line }}
      </p>
    </div>

    <!-- 列表模式:展示用户标签和备注 -->
    <div v-if="mode === 'list' && (userTags.length || note)" class="card-extra">
      <div v-if="userTags.length" class="user-tags">
        <span v-for="t in userTags" :key="t" class="user-tag">{{ t }}</span>
      </div>
      <p v-if="note" class="note text-soft">{{ note }}</p>
    </div>
  </article>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  poem: { type: Object, required: true },
  mode: {
    type: String,
    default: "list", // 'list' | 'hero'(详情/推荐用大字号)
  },
  userTags: { type: Array, default: () => [] },
  note: { type: String, default: "" },
});

const poemLines = computed(() => {
  if (!props.poem?.content) return [];
  return props.poem.content
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);
});
</script>

<style scoped>
.poem-card {
  text-align: center;
}

/* === list 模式:列表卡片,中等尺寸 === */
.mode-list {
  padding: var(--space-5) var(--space-4);
  border: 1px solid var(--color-border);
  background: var(--color-bg-card);
  transition: border-color var(--transition);
  cursor: pointer;
}
.mode-list:hover {
  border-color: var(--color-accent);
}
.mode-list .card-title {
  font-size: var(--fs-xl);
  letter-spacing: 4px;
  margin-bottom: var(--space-2);
}
.mode-list .card-meta {
  font-size: var(--fs-sm);
  margin-bottom: var(--space-4);
}
.mode-list .card-content {
  font-family: var(--font-kaiti);
  line-height: 2;
  margin-bottom: var(--space-3);
}
.mode-list .card-line {
  font-size: var(--fs-base);
  letter-spacing: 2px;
}

/* === hero 模式:沉浸大字号(详情、推荐用) === */
.mode-hero {
  padding: var(--space-7) 0;
}
.mode-hero .card-title {
  font-size: var(--fs-3xl);
  letter-spacing: 6px;
  margin-bottom: var(--space-3);
}
.mode-hero .card-meta {
  font-size: var(--fs-base);
  letter-spacing: 2px;
  margin-bottom: var(--space-6);
}
.mode-hero .card-content {
  font-family: var(--font-kaiti);
  line-height: 2.4;
}
.mode-hero .card-line {
  font-size: var(--fs-xl);
  letter-spacing: 4px;
}

/* 用户标签和备注(只在 list 模式出现) */
.card-extra {
  margin-top: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px dashed var(--color-border-soft);
  text-align: left;
}
.user-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}
.user-tag {
  font-size: var(--fs-xs);
  padding: 1px var(--space-2);
  background: var(--color-border-soft);
  color: var(--color-text-soft);
}
.note {
  font-size: var(--fs-sm);
  font-style: italic;
}
</style>
