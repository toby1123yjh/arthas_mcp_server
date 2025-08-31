#!/usr/bin/env python3
"""
Arthas MCP Server - Main Entry Point
An MCP server for LLM-oriented intelligent diagnostics of Java applications.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# 设置控制台编码为UTF-8（Windows兼容性）
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    # 尝试设置控制台代码页为UTF-8
    try:
        os.system('chcp 65001 > nul')
    except:
        pass

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from src.server import main

# 配置日志处理器
def setup_logging():
    """设置日志配置，解决中文乱码问题"""
    
    # 创建格式器 - 使用ASCII兼容的格式避免编码问题
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 主文件处理器 - 记录所有日志
    # 强制使用UTF-8编码，避免Windows默认编码问题
    file_handler = logging.FileHandler(
        'arthas_mcp.log', 
        encoding='utf-8', 
        mode='a'
    )
    file_handler.setFormatter(formatter)
    
    # 错误文件处理器 - 只记录ERROR级别及以上
    error_file_handler = logging.FileHandler(
        'arthas_mcp_error.log',
        encoding='utf-8',
        mode='a'
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(formatter)
    
    # 配置根日志器 - 移除控制台输出，只输出到文件
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    # 清除现有处理器，避免重复
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_file_handler)  # 添加错误日志处理器
    
    # 同时禁用FastMCP的默认日志输出
    logging.getLogger('fastmcp').setLevel(logging.WARNING)
    
    # 设置httpx日志级别，减少HTTP请求日志
    logging.getLogger('httpx').setLevel(logging.WARNING)
    
    # 设置MCP相关日志级别，减少噪音
    logging.getLogger('mcp.server.lowlevel.server').setLevel(logging.WARNING)

# 设置日志
setup_logging()

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # 重定向stderr到文件以避免FastMCP横幅干扰MCP协议
    import sys
    import contextlib
    import os
    
    # 打开错误日志文件
    error_log = open('arthas_mcp_error.log', 'a', encoding='utf-8')
    
    try:
        # 获取环境变量配置的Arthas连接信息
        arthas_url = os.getenv('ARTHAS_URL', 'http://localhost:8563')
        
        # 启动日志信息只记录到文件，不输出到stdout
        logger.info("Starting Arthas MCP Server...")
        logger.info(f"Arthas HTTP API: {arthas_url}/api")
        logger.info(f"Config: ARTHAS_URL={arthas_url}")
        logger.info("MCP Server will communicate with Arthas via HTTP API")
        
        # 重定向stderr到文件，避免FastMCP横幅输出到终端
        with contextlib.redirect_stderr(error_log):
            # 使用 FastMCP 的同步运行方法
            from src.server import ArthasMCPServer
            server = ArthasMCPServer()
            server.mcp.run()
            
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        # 改进服务器启动失败的错误日志记录
        error_msg = str(e) if str(e).strip() else repr(e)
        error_type = type(e).__name__
        logger.error(f"Server startup failed [{error_type}]: {error_msg}")
        sys.exit(1)
    finally:
        error_log.close()