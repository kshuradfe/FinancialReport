# -*- coding: utf-8 -*-
"""FinScope 一键启动。

安装缺失的依赖 -> 构建前端 -> 启动服务 -> 打开浏览器。

    python run_finscope.py           # 单端口模式：后端同时托管前端页面
    python run_finscope.py --dev     # 开发模式：另开 Vite，带热更新
    python run_finscope.py --port 9000
    python run_finscope.py --skip-install --no-browser

Windows 上直接双击 start.bat 即可。
"""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
VENV = os.path.join(ROOT, ".venv")
FRONTEND = os.path.join(ROOT, "frontend")
DIST = os.path.join(FRONTEND, "dist")
NODE_MODULES = os.path.join(FRONTEND, "node_modules")
REQUIREMENTS = os.path.join(ROOT, "backend", "requirements.txt")

DEFAULT_PORT = 8787
VITE_PORT = 5173
BACKEND_PACKAGES = ("fastapi", "uvicorn", "pydantic", "pandas", "openpyxl", "yfinance")

IS_WINDOWS = os.name == "nt"

def _enable_utf8_console() -> None:
    """cmd.exe defaults to a legacy code page; switch it here rather than in
    the .bat, where a mid-file chcp corrupts batch parsing."""
    if IS_WINDOWS:
        try:
            import ctypes

            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
            ctypes.windll.kernel32.SetConsoleCP(65001)
        except Exception:  # noqa: BLE001 - cosmetic only
            pass
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


_enable_utf8_console()


# --------------------------------------------------------------------- output

_STEP = 0


def step(text: str) -> None:
    global _STEP
    _STEP += 1
    print(f"\n[{_STEP}] {text}")


def ok(text: str) -> None:
    print(f"    OK  {text}")


def info(text: str) -> None:
    print(f"        {text}")


def fail(text: str) -> None:
    print(f"    !!  {text}")


# ----------------------------------------------------------------- python env

def venv_python() -> str | None:
    exe = os.path.join(VENV, "Scripts", "python.exe") if IS_WINDOWS \
        else os.path.join(VENV, "bin", "python")
    return exe if os.path.exists(exe) else None


def ensure_venv() -> str:
    """Return the interpreter to run the server with, creating .venv if needed."""
    existing = venv_python()
    if existing:
        ok(f"虚拟环境 {os.path.relpath(existing, ROOT)}")
        return existing

    if sys.prefix != sys.base_prefix:      # already inside some venv
        ok(f"使用当前虚拟环境 {sys.prefix}")
        return sys.executable

    info("未找到 .venv，正在创建…")
    try:
        subprocess.run([sys.executable, "-m", "venv", VENV], check=True, cwd=ROOT)
    except subprocess.CalledProcessError:
        fail("创建虚拟环境失败，将直接使用系统 Python")
        return sys.executable
    created = venv_python()
    if created:
        ok("已创建 .venv")
        return created
    return sys.executable


def missing_packages(python: str) -> list[str]:
    probe = (
        "import importlib.util,sys;"
        "print(' '.join(n for n in sys.argv[1:] "
        "if importlib.util.find_spec(n.replace('-','_')) is None))"
    )
    result = subprocess.run([python, "-c", probe, *BACKEND_PACKAGES],
                            capture_output=True, text=True, cwd=ROOT)
    return result.stdout.split()


def ensure_backend_deps(python: str, skip: bool) -> bool:
    missing = missing_packages(python)
    if not missing:
        ok("后端依赖齐全")
        return True
    if skip:
        fail(f"缺少 {', '.join(missing)}，但指定了 --skip-install")
        return False

    info(f"缺少 {', '.join(missing)}，正在安装…")
    cmd = [python, "-m", "pip", "install", "-r", REQUIREMENTS]
    if subprocess.run(cmd, cwd=ROOT).returncode != 0:
        fail("依赖安装失败。可以手动执行：")
        info(f"{python} -m pip install -r backend/requirements.txt")
        return False

    still = missing_packages(python)
    if still:
        fail(f"安装后仍缺少 {', '.join(still)}")
        return False
    ok("后端依赖安装完成")
    return True


# -------------------------------------------------------------------- node js

def find_npm() -> str | None:
    return shutil.which("npm") or shutil.which("npm.cmd")


def newest_mtime(*paths: str) -> float:
    newest = 0.0
    for path in paths:
        if os.path.isfile(path):
            newest = max(newest, os.path.getmtime(path))
        elif os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if d != "node_modules"]
                for name in files:
                    try:
                        newest = max(newest, os.path.getmtime(os.path.join(root, name)))
                    except OSError:
                        pass
    return newest


def frontend_is_stale() -> bool:
    built = os.path.join(DIST, "index.html")
    if not os.path.exists(built):
        return True
    sources = newest_mtime(
        os.path.join(FRONTEND, "src"),
        os.path.join(FRONTEND, "index.html"),
        os.path.join(FRONTEND, "vite.config.ts"),
        os.path.join(FRONTEND, "package.json"),
    )
    return sources > os.path.getmtime(built)


def ensure_node_modules(npm: str, skip: bool) -> bool:
    fresh = os.path.exists(NODE_MODULES) and \
        os.path.getmtime(NODE_MODULES) >= os.path.getmtime(os.path.join(FRONTEND, "package.json"))
    if fresh:
        ok("前端依赖齐全")
        return True
    if skip:
        fail("node_modules 缺失或过期，但指定了 --skip-install")
        return False

    info("正在安装前端依赖（首次约需 1 分钟）…")
    if subprocess.run([npm, "install"], cwd=FRONTEND).returncode != 0:
        fail("npm install 失败")
        return False
    ok("前端依赖安装完成")
    return True


def build_frontend(npm: str) -> bool:
    if not frontend_is_stale():
        ok("前端已是最新构建")
        return True
    info("正在构建前端…")
    if subprocess.run([npm, "run", "build"], cwd=FRONTEND).returncode != 0:
        fail("前端构建失败（上面是 tsc / vite 的报错）")
        return False
    ok("前端构建完成")
    return True


# ----------------------------------------------------------------------- port

def port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def pick_port(preferred: int) -> int | None:
    if port_is_free(preferred):
        return preferred
    info(f"端口 {preferred} 已被占用，正在寻找可用端口…")
    for candidate in range(preferred + 1, preferred + 20):
        if port_is_free(candidate):
            return candidate
    return None


def wait_for_health(port: int, timeout: float = 60.0) -> bool:
    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{port}/api/health"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2):
                return True
        except (urllib.error.URLError, OSError):
            time.sleep(0.4)
    return False


# ----------------------------------------------------------------------- main

def main() -> int:
    parser = argparse.ArgumentParser(description="FinScope 一键启动")
    parser.add_argument("--dev", action="store_true", help="开发模式：另起 Vite 热更新服务")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="后端端口")
    parser.add_argument("--skip-install", action="store_true", help="跳过依赖检查与安装")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args()

    print("=" * 58)
    print("  FinScope · 全球财报数据采集台")
    print("=" * 58)

    # ---------------------------------------------------------- dependencies
    step("检查 Python 环境")
    python = ensure_venv()
    if not ensure_backend_deps(python, args.skip_install):
        return 1

    step("检查前端")
    npm = find_npm()
    serve_static = not args.dev

    if npm is None:
        if os.path.exists(os.path.join(DIST, "index.html")):
            fail("未找到 npm，使用已有的前端构建产物")
        else:
            fail("未找到 npm，且没有已构建的前端页面。")
            info("请先安装 Node.js（https://nodejs.org），再重新运行本脚本。")
            return 1
    else:
        if not ensure_node_modules(npm, args.skip_install):
            return 1
        if serve_static and not build_frontend(npm):
            return 1

    # ------------------------------------------------------------ start them
    step("启动服务")
    port = pick_port(args.port)
    if port is None:
        fail(f"{args.port} 起连续 20 个端口都被占用了")
        return 1
    if port != args.port:
        ok(f"改用端口 {port}")

    procs: list[subprocess.Popen] = []
    api = subprocess.Popen(
        [python, "-m", "uvicorn", "backend.app.main:app",
         "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT,
    )
    procs.append(api)

    if not wait_for_health(port):
        fail("后端启动超时，请查看上方日志")
        api.terminate()
        return 1
    ok(f"后端已就绪  http://127.0.0.1:{port}")

    url = f"http://127.0.0.1:{port}"
    if args.dev and npm:
        env = dict(os.environ, FINSCOPE_API=f"http://127.0.0.1:{port}")
        procs.append(subprocess.Popen([npm, "run", "dev"], cwd=FRONTEND, env=env))
        url = f"http://localhost:{VITE_PORT}"
        time.sleep(2.5)
        ok(f"Vite 开发服务器已启动  {url}")

    print("\n" + "-" * 58)
    print(f"  打开:  {url}")
    print("  按 Ctrl+C 停止")
    print("-" * 58 + "\n")

    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    # -------------------------------------------------------------- run loop
    try:
        while all(p.poll() is None for p in procs):
            time.sleep(0.5)
        for p in procs:
            if p.poll() not in (None, 0):
                fail("有服务意外退出，正在关闭其余进程")
                break
    except KeyboardInterrupt:
        print("\n正在停止…")
    finally:
        for p in procs:
            if p.poll() is None:
                p.terminate()
        for p in procs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
    print("已停止。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
