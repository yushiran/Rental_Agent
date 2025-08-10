FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install uv

COPY . /app

# 使用uv同步依赖
RUN uv sync

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uv", "run", "fastapi", "run", "app/api_service/main.py", "--host", "0.0.0.0", "--port", "8000"]