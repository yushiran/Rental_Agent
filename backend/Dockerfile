# -----------------------------------------------------------------------------
# Stage 1: Builder - Install uv and lock/install all dependencies
# -----------------------------------------------------------------------------
# Choose a lightweight Python base image as the starting point for the build stage
# python:3.13-slim-bookworm provides Python 3.13 and Debian Bookworm OS
FROM python:3.13-slim-bookworm AS builder

# Set the working directory inside the container. Subsequent instructions (like COPY, RUN) will execute relative to this directory
WORKDIR /app

# Copy the pre-compiled uv binary from the official uv Docker image to /usr/local/bin
# This is faster than compiling uv inside the container and avoids installing Rust compiler and other additional tools
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project dependency configuration files.
# Placing them here allows leveraging Docker's build cache: if these files don't change, the RUN instruction below can be skipped
COPY pyproject.toml uv.lock ./

# Run uv sync dependencies.
# --mount=type=cache,target=/root/.cache/uv: Mount a cache volume to accelerate repeated uv builds
# --frozen: 强制 uv 严格按照 uv.lock 的版本安装，确保可复现性
# --no-install-project: 不安装当前项目本身 (如果你的项目只是一个脚本集合，不是一个可安装的 Python 包)
# --no-dev: 不安装开发依赖 (如 pytest, ruff 等)，只安装生产环境所需依赖
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# -----------------------------------------------------------------------------
# Stage 2: Runtime - 复制依赖和应用代码，构建最终的生产镜像
# -----------------------------------------------------------------------------
# 选择与 builder 阶段相同的轻量级 Python 基础镜像作为最终运行环境
FROM python:3.13-slim-bookworm AS runtime

# 再次设置工作目录，与 builder 阶段保持一致
WORKDIR /app

# 从 builder 阶段复制已经安装好的虚拟环境 (.venv 目录)
# 这样最终的镜像中只包含必要的 Python 解释器和依赖，没有构建工具
COPY --from=builder /app/.venv /app/.venv

# 设置 PATH 环境变量，使虚拟环境中的可执行文件可以直接运行
# 例如，可以直接运行 `python` 而不是 `/app/.venv/bin/python`
ENV PATH="/app/.venv/bin:$PATH"

# 复制你的应用代码。
# 放在最后，因为应用代码可能频繁改动，这样可以最大限度地利用 Docker 缓存
COPY . .
RUN chmod +x init.sh # <-- 确保这一行存在！

# 暴露应用程序监听的端口 (如果你的应用是一个 Web 服务，例如监听 8000 端口)
EXPOSE 8000

# 定义容器启动时默认执行的命令。
# 这里假设你的主程序是 main.py。请根据你的实际应用修改
# CMD ["python", "main.py"]
CMD ["bash", "./init.sh"]

# 如果是 Web 应用，例如使用 uvicorn:
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]