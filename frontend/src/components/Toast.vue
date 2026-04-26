<template>
  <div class="toast-container">
    <transition-group name="toast">
      <div
        v-for="msg in toastStore.messages"
        :key="msg.id"
        class="toast"
        :class="`toast-${msg.type}`"
      >
        {{ msg.text }}
      </div>
    </transition-group>
  </div>
</template>

<script setup>
import { useToastStore } from "../stores/toast";
const toastStore = useToastStore();
</script>

<style scoped>
.toast-container {
  position: fixed;
  top: var(--space-6);
  left: 50%;
  transform: translateX(-50%);
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  pointer-events: none;
}
.toast {
  padding: var(--space-3) var(--space-5);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  font-size: var(--fs-sm);
  color: var(--color-text);
  min-width: 200px;
  text-align: center;
}
.toast-error {
  color: var(--color-error);
  border-color: var(--color-error);
}
.toast-success {
  color: var(--color-success);
  border-color: var(--color-success);
}

.toast-enter-active,
.toast-leave-active {
  transition: all 300ms ease;
}
.toast-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}
.toast-leave-to {
  opacity: 0;
}
</style>
