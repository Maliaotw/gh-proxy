"""
GitHub 代理应用程序入口点。

此脚本创建并运行 GitHub 代理 FastAPI 应用程序，使用 httpx 实现高并发。
它包括基于 URL MD5 哈希的文件缓存，以提高重复请求的性能。
"""

import asyncio
import hashlib
import logging
import os
import shutil
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent.parent



# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("github-proxy")

logger.info(f'{BASE_DIR=}')

# Configuration
HOST = os.environ.get("PROXY_HOST", "127.0.0.1")
PORT = int(os.environ.get("PROXY_PORT", "8082"))

# File cache directory
CACHE_DIR = BASE_DIR / "cache"
if not CACHE_DIR.exists():
    CACHE_DIR.mkdir(parents=True)
    logger.info(f"已创建缓存目录: {CACHE_DIR}")

# Global variable to store httpx client
client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 应用程序生命周期管理器

    在应用启动时初始化资源，在关闭时清理资源
    """
    # 启动时执行
    global client
    logger.info("正在初始化应用程序...")

    try:
        # 创建 httpx 客户端
        client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )
        logger.info("已创建 httpx 客户端")

        # 这里可以添加其他初始化逻辑
        # 比如数据库连接、缓存初始化等

    except Exception as e:
        logger.error(f"初始化应用程序时出错: {e}")
        raise

    yield  # 应用程序运行期间

    # 关闭时执行
    logger.info("正在关闭应用程序...")
    try:
        if client:
            await client.aclose()
            logger.info("已关闭 httpx 客户端")
    except Exception as e:
        logger.error(f"关闭 httpx 客户端时出错: {e}")

    # 这里可以添加其他清理逻辑
    # 比如关闭数据库连接、清理临时文件等
    logger.info("应用程序已安全关闭")


# Create FastAPI app with lifespan
app = FastAPI(
    title="通用代理",
    description="使用 FastAPI 和 httpx 的高并发通用资源代理服务",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount static files directory if it exists
static_dir = Path("static")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")
    logger.info(f"已挂载静态文件目录: {static_dir}")


def get_cache_path(url: str) -> Path:
    """
    基于 URL 的 MD5 哈希生成缓存文件路径。

    参数:
        url: 要为其生成缓存路径的 URL

    返回:
        指向缓存文件位置的 Path 对象
    """
    # Create MD5 hash of the URL
    url_hash = hashlib.md5(url.encode()).hexdigest()
    return CACHE_DIR / url_hash


def is_valid_url(url: str) -> bool:
    """
    检查 URL 是否有效以进行代理

    此函数允许代理任何 URL 以实现文件加速目的。
    不再限制只能代理 GitHub URLs。

    参数:
        url: 要检查的 URL

    返回:
        始终返回 True 以允许任何 URL
    """
    # Accept any URL
    return True


@app.get("/favicon.ico")
async def favicon():
    """提供网站图标"""
    favicon_path = BASE_DIR / "static" / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(favicon_path)
    else:
        raise HTTPException(status_code=404, detail="Favicon not found")


@app.get("/")
async def root(request: Request = None):
    """根端点 - 返回欢迎消息"""
    # Check if index.html exists for HTML view
    index_path = BASE_DIR / "static" / "index.html"
    if (
        request
        and index_path.exists()
        and "text/html" in str(request.headers.get("accept", ""))
    ):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    else:
        # Return JSON response for API clients and tests
        return {"message": "通用代理服务正在运行"}


async def clone_github_repo(repo_url: str):
    """
    使用 git 命令行工具克隆 GitHub 仓库

    参数:
        repo_url: 要克隆的 GitHub 仓库 URL

    返回:
        克隆仓库的路径
    """
    logger.info(f"正在克隆 GitHub 仓库: {repo_url}")

    # Create a temporary directory for the clone
    temp_dir = tempfile.mkdtemp()
    logger.info(f"已创建临时目录: {temp_dir}")

    try:
        # Run git clone command using asyncio.subprocess
        logger.info(
            f"正在运行 git clone 命令: git clone --depth=1 {repo_url} {temp_dir}"
        )

        # Use asyncio.create_subprocess_exec for better async support
        process = await asyncio.create_subprocess_exec(
            "git",
            "clone",
            "--depth=1",
            repo_url,
            temp_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Wait for the process to complete
        stdout, stderr = await process.communicate()

        # Convert bytes to string
        stdout_str = stdout.decode() if stdout else ""
        stderr_str = stderr.decode() if stderr else ""

        logger.debug(f"Git clone 标准输出: {stdout_str}")
        logger.debug(f"Git clone 标准错误: {stderr_str}")

        if process.returncode != 0:
            logger.error(f"Git clone 失败，返回代码 {process.returncode}")
            raise Exception(f"Git clone 失败: {stderr_str}")

        logger.info(f"Git clone 成功: {temp_dir}")
        return temp_dir
    except Exception as e:
        logger.error(f"Git clone 过程中出错: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


@app.api_route(
    "/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH"]
)
async def proxy_github(request: Request, path: str):
    """
    代理请求到 GitHub

    此端点处理所有请求，并将它们转发到 GitHub（如果它们匹配预期模式）。
    它支持 Git 克隆、文件下载和其他 GitHub 操作。
    基于 URL MD5 哈希实现文件缓存，以提高性能。
    """
    # 确保 client 已经初始化
    if client is None:
        logger.error("HTTPX 客户端未初始化")
        raise HTTPException(status_code=503, detail="服务暂时不可用，请稍后重试")

    # Extract the target URL from the path
    method = request.method
    logger.info(f"请求方法: {method}")

    target_url = path

    # Ensure URL starts with http/https
    if not target_url.startswith(("http://", "https://")):
        if target_url.startswith("github.com"):
            target_url = f"https://{target_url}"
        else:
            # Handle other cases that might need URL normalization
            pass

    # No longer validating if this is a GitHub URL
    # All URLs are now accepted for file acceleration purposes
    logger.info(f"正在处理 URL: {target_url}")

    # Special handling for git clone requests
    # Git clone requests are typically to the base repository URL ending with .git
    # and don't have /info/refs, /git-upload-pack, or /git-receive-pack in the URL
    is_git_clone_request = (
        target_url.endswith(".git")
        and "/info/refs" not in target_url
        and "/git-upload-pack" not in target_url
        and "/git-receive-pack" not in target_url
        and request.method == "GET"
    )

    if is_git_clone_request:
        logger.info(f"检测到 Git clone 请求: {target_url}")
        try:
            # Check if we have a cached zip file for this repository
            cache_path = get_cache_path(target_url)
            if cache_path.with_suffix(".zip").exists():
                logger.info(f"使用缓存的仓库压缩包: {cache_path.with_suffix('.zip')}")
                return FileResponse(
                    path=str(cache_path.with_suffix(".zip")),
                    filename=os.path.basename(target_url).replace(".git", ".zip"),
                    media_type="application/zip",
                )

            # Use our dedicated git clone function
            repo_dir = await clone_github_repo(target_url)

            # Create a zip file of the repository
            zip_path = f"{repo_dir}.zip"
            logger.info(f"正在创建压缩文件: {zip_path}")

            # Run zip creation in a separate thread to avoid blocking
            def create_zip():
                try:
                    shutil.make_archive(repo_dir, "zip", repo_dir)
                    logger.info(f"压缩文件已创建: {zip_path}")
                    return True
                except Exception as e:
                    logger.error(f"创建压缩文件时出错: {str(e)}")
                    import traceback

                    logger.error(traceback.format_exc())
                    return False

            # Run the zip creation in a thread pool
            loop = asyncio.get_event_loop()
            zip_success = await loop.run_in_executor(None, create_zip)

            if not zip_success:
                raise Exception("创建压缩文件失败")

            # Clean up the repository directory
            logger.info(f"清理仓库目录: {repo_dir}")
            shutil.rmtree(repo_dir, ignore_errors=True)

            # Check if zip file exists
            if not os.path.exists(zip_path):
                raise Exception(f"未找到压缩文件: {zip_path}")

            # Cache the zip file for future use
            cache_zip_path = cache_path.with_suffix(".zip")
            logger.info(f"缓存压缩文件到: {cache_zip_path}")

            # Ensure parent directories exist
            cache_zip_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy the zip file to the cache
            shutil.copy2(zip_path, cache_zip_path)

            logger.info(f"提供压缩文件: {zip_path}")
            # Serve the zip file
            return FileResponse(
                path=zip_path,
                filename=os.path.basename(target_url).replace(".git", ".zip"),
                media_type="application/zip",
            )
        except Exception as e:
            logger.error(f"处理 git clone 请求时出错: {str(e)}")
            import traceback

            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"克隆仓库时出错: {str(e)}")

    # For other git requests or non-git requests, continue with normal proxy behavior
    is_git_request = (
        target_url.endswith(".git")
        or "/info/refs" in target_url
        or "/git-upload-pack" in target_url
        or "/git-receive-pack" in target_url
    )

    if is_git_request:
        logger.info(f"检测到 Git 请求: {target_url}")
        logger.info(f"请求方法: {request.method}")
        logger.debug(f"查询参数: {request.query_params}")

    # Get request headers and prepare them for forwarding
    headers = dict(request.headers)
    # Remove headers that might cause issues
    headers.pop("host", None)

    # Get query parameters
    params = dict(request.query_params)

    # Special handling for git requests
    if is_git_request:
        logger.info(f"检测到 Git 请求: {target_url}")
        logger.info(f"请求方法: {method}")
        logger.debug(f"查询参数: {params}")

        # For git requests, we need to ensure certain headers are set
        # But we'll keep it simple and only set headers that are essential

        # Set Git Protocol version to 2 if not already set
        if "git-protocol" not in {k.lower() for k in headers.keys()}:
            headers["Git-Protocol"] = "version=2"

        # Ensure User-Agent is set
        if "user-agent" not in {k.lower() for k in headers.keys()}:
            headers["User-Agent"] = "git/2.0.0"

        # Remove content-length header which might cause issues
        headers.pop("content-length", None)

        logger.debug(f"Git 请求的头信息: {headers}")

    # Check if we have a cached response for this URL (for GET requests only)
    if method == "GET" and not is_git_request:
        cache_path = get_cache_path(target_url)
        if cache_path.exists():
            logger.info(f"使用缓存的响应: {target_url}")

            # Read the cached file and return it
            return FileResponse(
                path=str(cache_path),
                media_type=None,  # Let the browser determine the content type
            )

    # Get request method
    method = request.method

    try:
        # Get request body for methods that support it
        body = None
        if method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                logger.debug(f"请求体大小: {len(body) if body else 0} 字节")
            except Exception as e:
                logger.error(f"读取请求体时出错: {str(e)}")
                # Continue without body if there's an error

        # Make the request to the target URL
        try:
            # Use a consistent approach for all requests
            logger.info(f"正在向目标发送请求: {target_url}")
            logger.debug(f"方法: {method}")
            logger.debug(f"头信息: {headers}")
            logger.debug(f"参数: {params}")

            response = await client.request(
                method=method,
                url=target_url,
                headers=headers,
                content=body,
                params=params,  # Include query parameters
            )

            logger.info(f"响应状态码: {response.status_code}")
            if is_git_request:
                logger.debug(f"Git 请求响应头信息: {response.headers}")
        except httpx.RequestError as e:
            logger.error(f"HTTPX 请求错误: {str(e)}")
            raise HTTPException(
                status_code=502, detail=f"向目标 URL 发送请求时出错: {str(e)}"
            )
        except Exception as e:
            logger.error(f"发送请求时发生意外错误: {str(e)}")
            import traceback

            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"发生意外错误: {str(e)}")

        # Prepare response headers
        try:
            response_headers = dict(response.headers)

            # For GET requests, cache the response if it's successful
            if method == "GET" and response.status_code == 200 and not is_git_request:
                # Get the cache path for this URL
                cache_path = get_cache_path(target_url)

                # Ensure parent directories exist
                cache_path.parent.mkdir(parents=True, exist_ok=True)

                # Save the response content to the cache
                with open(cache_path, "wb") as f:
                    f.write(response.content)
                logger.info(f"已缓存响应: {target_url}")

                # Return the response directly from the cache
                return FileResponse(
                    path=str(cache_path),
                    headers=response_headers,
                    status_code=response.status_code,
                )

            # Handle streaming response for large files
            async def stream_response():
                try:
                    async for chunk in response.aiter_bytes():
                        yield chunk
                except Exception as e:
                    logger.error(f"流式传输响应时出错: {str(e)}")
                    raise

            # Return streaming response
            return StreamingResponse(
                stream_response(),
                status_code=response.status_code,
                headers=response_headers,
                media_type=response.headers.get("content-type"),
            )
        except Exception as e:
            logger.error(f"准备响应时出错: {str(e)}")
            import traceback

            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"准备响应时出错: {str(e)}")

    except httpx.RequestError as e:
        logger.error(f"HTTPX 请求错误 (外层): {str(e)}")
        raise HTTPException(status_code=502, detail=f"代理请求时出错: {str(e)}")
    except Exception as e:
        logger.error(f"意外错误 (外层): {str(e)}")
        import traceback

        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"发生意外错误: {str(e)}")


if __name__ == "__main__":
    logger.info(f"正在启动 GitHub 代理服务器，地址: {HOST}:{PORT}")
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
