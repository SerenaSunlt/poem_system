// src/api/client.js
import axios from "axios";
import { useUserStore } from "../stores/user";
import { useToastStore } from "../stores/toast";
import router from "../router";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '',  // 留空,使用同源
  timeout: 15000,
})

// 请求拦截器:自动加 Authorization
client.interceptors.request.use(
  (config) => {
    const userStore = useUserStore();
    if (userStore.token) {
      config.headers.Authorization = `Bearer ${userStore.token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// 响应拦截器:统一处理业务码 + HTTP 错误
client.interceptors.response.use(
  (response) => {
    const data = response.data;
    // 业务成功
    if (data.code === 0) {
      return data.data;
    }
    // 业务错误,弹 Toast 并 reject
    const toastStore = useToastStore();
    toastStore.error(data.message || "请求失败");
    return Promise.reject(new Error(data.message || `code=${data.code}`));
  },
  (error) => {
    const toastStore = useToastStore();

    if (error.response) {
      const status = error.response.status;
      if (status === 401) {
        // token 过期或无效
        const userStore = useUserStore();
        userStore.logout();
        toastStore.error("请先登录");
        router.push({
          name: "login",
          query: { redirect: router.currentRoute.value.fullPath },
        });
      } else if (status === 422) {
        toastStore.error("参数有误");
      } else {
        toastStore.error(`服务异常 (${status})`);
      }
    } else if (error.code === "ECONNABORTED") {
      toastStore.error("请求超时");
    } else {
      toastStore.error("网络错误");
    }
    return Promise.reject(error);
  },
);

export default client;
