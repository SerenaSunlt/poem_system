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
      <p v-for="(line, idx) in displayLines" :key="idx" class="card-line">
        {{ line }}
      </p>
      <!-- 列表模式:被截断时,显示"读全篇" -->
      <p v-if="mode === 'list' && isTruncated" class="more-hint text-faint">
        读全篇
      </p>
    </div>

    <!-- 列表模式:展示用户标签(备注不在列表显示,详情页才显示) -->
    <div v-if="mode === 'list' && userTags.length" class="card-extra">
      <div class="user-tags">
        <span v-for="t in userTags" :key="t" class="user-tag">{{ t }}</span>
      </div>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  poem: { type: Object, required: true },
  mode: {
    type: String,
    default: 'list',
  },
  userTags: { type: Array, default: () => [] },
  note: { type: String, default: '' },
})

// 列表模式:超过这个分句数就截断,显示"读全篇"
const LIST_MAX_LINES = 2

// 把诗词正文拆成"分句"数组(同样的长短句逻辑)
const poemLines = computed(() => {
  if (!props.poem?.content) return []

  const rawLines = props.poem.content
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

// 实际显示的行(列表模式可能截断,hero 模式全显)
const displayLines = computed(() => {
  if (props.mode === 'list' && poemLines.value.length > LIST_MAX_LINES) {
    return poemLines.value.slice(0, LIST_MAX_LINES)
  }
  return poemLines.value
})

// 是否被截断(用来决定要不要显示"读全篇")
const isTruncated = computed(() => {
  return props.mode === 'list' && poemLines.value.length > LIST_MAX_LINES
})
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
.mode-list .more-hint {
  margin-top: var(--space-3);
  font-size: var(--fs-xs);
  letter-spacing: 2px;
  font-family: var(--font-kaiti);
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

/* 用户标签(只在 list 模式出现) */
.card-extra {
  margin-top: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px dashed var(--color-border-soft);
}
.user-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  justify-content: center;
}
.user-tag {
  font-size: var(--fs-xs);
  padding: 1px var(--space-2);
  background: var(--color-border-soft);
  color: var(--color-text-soft);
}

/* === 移动端:每个分句独占一行 === */
@media (max-width: 640px) {
  .mode-hero .card-line {
    font-size: var(--fs-lg);
    letter-spacing: 2px;
    line-height: 2.2;
  }

  .mode-list .card-line {
    font-size: var(--fs-sm);
    letter-spacing: 1px;
    line-height: 2;
  }
}
</style>