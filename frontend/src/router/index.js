import { createRouter, createWebHistory } from "vue-router";
import { useUserStore } from "../stores/user";

const routes = [
  { path: "/", redirect: "/recommend" },
  {
    path: "/login",
    name: "login",
    component: () => import("../views/LoginView.vue"),
    meta: { guestOnly: true },
  },
  {
    path: "/register",
    name: "register",
    component: () => import("../views/RegisterView.vue"),
    meta: { guestOnly: true },
  },
  {
    path: "/recommend",
    name: "recommend",
    component: () => import("../views/RecommendView.vue"),
    // 不加 requiresAuth,游客可访问
  },
  {
    path: "/favorites",
    name: "favorites",
    component: () => import("../views/FavoritesView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/poem/:id",
    name: "poem-detail",
    component: () => import("../views/PoemDetailView.vue"),
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// 路由守卫
router.beforeEach((to, from, next) => {
  const userStore = useUserStore();

  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    next({ name: "login", query: { redirect: to.fullPath } });
    return;
  }

  if (to.meta.guestOnly && userStore.isLoggedIn) {
    next({ name: "recommend" });
    return;
  }

  next();
});

export default router;
