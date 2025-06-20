FROM python:3.11-slim

# 設置工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安裝 UV
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# 複製專案文件
COPY pyproject.toml uv.lock ./
COPY . .

# 安裝 Python 依賴
RUN uv sync --frozen

# 設置環境變數
ENV PYTHONPATH=/app
ENV PORT=8080

# 暴露端口
EXPOSE 8080

# 啟動命令
CMD ["uv", "run", "python", "main.py"]