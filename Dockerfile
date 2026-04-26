# Dockerfile
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 用阿里云 pip 镜像加速(服务器在国内,装包飞快)
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

# 系统依赖(pymysql 在某些场景需要)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 先复制 requirements 装依赖(利用 Docker 层缓存)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再复制项目代码
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

# 暴露端口
EXPOSE 8000

# 启动命令:先跑迁移,再起服务
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]