# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 用清华 pip 镜像(国内服务器最稳定)
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple/ \
    && pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn

# 装依赖(超时拉长,带重试,防止网络抖动)
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 120 --retries 5 -r requirements.txt

# 复制项目代码
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

EXPOSE 8000

# 启动:先跑迁移,再起服务
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]