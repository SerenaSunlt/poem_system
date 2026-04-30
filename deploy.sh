#!/bin/bash
set -e

cd /opt/poem_system

echo "当前目录："
pwd

echo "项目文件："
ls -la

echo "Compose 服务列表："
docker compose config --services

echo "部署前容器状态："
docker compose ps

echo "开始部署 poem_system..."
docker compose up -d --build

echo "部署后容器状态："
docker compose ps

echo "简单健康检查："
sleep 5
curl -I http://localhost:8080 || true

echo "部署完成"