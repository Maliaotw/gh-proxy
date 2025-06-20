# 通用文件加速代理 (gh-proxy)

一个使用 FastAPI 和 httpx 构建的高性能代理服务，用于加速各种网络资源的下载，特别适合 GitHub 等访问受限的网站。

## 📋 项目概述

本项目借鉴了 [gh-proxy](https://github.com/hunshcn/gh-proxy)，将原本基于 Flask 的实现改造为使用 FastAPI 框架，并扩展了其功能，使其成为一个通用的文件加速代理。

通用文件加速代理是一项旨在解决网络资源访问缓慢或受限问题的服务。它不仅适用于 GitHub，还可用于加速其他各种网站的资源下载。该服务提供：

- 高性能的通用代理，支持各类网站资源的加速下载
- 智能文件缓存系统，显著提高重复请求的响应速度
- 完整支持 Git 操作，包括克隆、拉取等（自动转换为 ZIP 文件下载）
- 简洁易用的网页界面和灵活的命令行调用方式

## 🛠️ 技术栈

- **FastAPI**：用于构建 API 的现代、快速的 Web 框架
- **httpx**：用于发送代理请求的异步 HTTP 客户端
- **uvicorn**：用于运行 FastAPI 应用程序的 ASGI 服务器
- **Docker**：用于容器化和简化部署
- **GitHub Actions**：用于 CI/CD 和部署到 Google Cloud Run

## 🚀 安装和设置

### 前提条件

- Python 3.11 或更高版本
- [uv](https://github.com/astral-sh/uv)（推荐）或 pip

### 使用 uv 安装（推荐）

1. 如果尚未安装 uv，请先安装：
   ```bash
   pip install uv
   ```

2. 克隆仓库：
   ```bash
   git clone https://github.com/yourusername/gh-proxy.git
   cd gh-proxy
   ```

3. 创建虚拟环境并安装依赖：
   ```bash
   uv venv
   uv sync
   ```

### 使用 pip 安装

1. 克隆仓库：
   ```bash
   git clone https://github.com/yourusername/gh-proxy.git
   cd gh-proxy
   ```

2. 创建虚拟环境并安装依赖：
   ```bash
   python -m venv venv
   source venv/bin/activate  # 在 Windows 上：venv\Scripts\activate
   pip install -r requirements.txt
   ```

## ⚙️ 配置

应用程序可以使用环境变量或 `.env` 文件进行配置。

### 环境变量

- `PROXY_HOST`：服务器绑定的主机（默认：127.0.0.1）
- `PROXY_PORT`：服务器绑定的端口（默认：8080）

### .env 文件

在项目根目录创建一个包含以下内容的 `.env` 文件：

```
PROXY_HOST=0.0.0.0
PROXY_PORT=8080
```

## 🏃‍♂️ 运行应用程序

### 本地开发

1. 启动应用程序：
   ```bash
   cd app
   python main.py
   ```

   或直接使用 uvicorn：
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload
   ```

2. 在 http://127.0.0.1:8080 访问 Web 界面

### Docker

1. 使用 Docker 构建和运行：
   ```bash
   docker build -t gh-proxy .
   docker run -p 8080:80 gh-proxy
   ```

2. 在 http://localhost:8080 访问 Web 界面

### Docker Compose

1. 使用 Docker Compose 运行：
   ```bash
   docker-compose up -d
   ```

2. 在 http://localhost:8080 访问 Web 界面

## 🧪 测试

项目包含测试以确保功能正常。使用以下命令运行测试：

```bash
pytest tests/ -v
```

### 代码格式化和检查

安装开发依赖并使用 black 和 isort 进行代码格式化：

```bash
uv install --dev
black .
isort .
```

### 手动测试

您可以通过以下方式手动测试代理：

#### 通过 Web 界面测试

1. 启动应用程序
2. 打开 Web 界面
3. 输入 GitHub URL（例如，https://github.com/username/project/archive/master.zip）
4. 点击"加速下载"

#### 通过命令行测试

假设代理服务运行在 `http://127.0.0.1:8080`，您可以使用以下命令测试：

##### 使用 Git 克隆

```bash
git clone http://127.0.0.1:8080/https://github.com/cookiecutter/cookiecutter-django.git
```

##### 使用 wget 下载

```bash
wget http://127.0.0.1:8080/https://github.com/twbs/bootstrap/releases/download/v5.3.7/bootstrap-5.3.7-examples.zip
```

##### 使用 curl 下载

```bash
curl -O http://127.0.0.1:8080/https://github.com/twbs/bootstrap/releases/download/v5.3.7/bootstrap-5.3.7-examples.zip
```

> **注意**：在上述命令中，代理 URL (`http://127.0.0.1:8080/`) 后面直接跟着目标 URL，无需额外参数。

## 🚢 部署

### Google Cloud Run

项目包含用于自动部署到 Google Cloud Run 的 GitHub Actions 工作流。设置步骤：

1. Fork 此仓库
2. 在您的 GitHub 仓库中设置以下密钥：
   - `GCP_PROJECT_ID`：您的 Google Cloud 项目 ID
   - `GCP_SA_KEY`：您的 Google Cloud 服务账号密钥（JSON）
   - `GCP_RUN_VARS`：Cloud Run 的环境变量（逗号分隔的 KEY=VALUE 对）

3. 推送到主分支以触发部署

## 📝 许可证

本项目采用 MIT 许可证 - 详情请参阅 LICENSE 文件。

## 🤝 贡献

欢迎贡献！请随时提交 Pull Request。
