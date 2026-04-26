<template>
  <div class="skeleton" :class="`mode-${mode}`">
    <div class="sk-title"></div>
    <div class="sk-meta"></div>
    <div class="sk-line"></div>
    <div class="sk-line"></div>
    <div class="sk-line short"></div>
  </div>
</template>

<script setup>
defineProps({
  mode: { type: String, default: "hero" },
});
</script>

<style scoped>
.skeleton {
  text-align: center;
  padding: var(--space-7) 0;
  animation: skeleton-pulse 1.4s ease-in-out infinite;
}
.sk-title,
.sk-meta,
.sk-line {
  background: var(--color-border-soft);
  margin: var(--space-3) auto;
  border-radius: 2px;
}
.sk-title {
  width: 200px;
  height: 32px;
  margin-bottom: var(--space-4);
}
.sk-meta {
  width: 120px;
  height: 14px;
  margin-bottom: var(--space-6);
}
.sk-line {
  width: 360px;
  height: 22px;
}
.sk-line.short {
  width: 280px;
}

.mode-list .sk-title {
  width: 140px;
  height: 24px;
}
.mode-list .sk-meta {
  width: 80px;
  height: 12px;
  margin-bottom: var(--space-3);
}
.mode-list .sk-line {
  width: 280px;
  height: 18px;
}
.mode-list .sk-line.short {
  width: 200px;
}

@keyframes skeleton-pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}
</style>
