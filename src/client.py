"""
Arthas HTTP 客户端模块
提供与 Arthas WebConsole 的 HTTP/WebSocket 连接
"""

import asyncio
import logging
from typing import Any, Dict, Optional, List

import httpx

from .models import ArthasConnection, ArthasCommand, ArthasResponse

logger = logging.getLogger(__name__)

class ArthasClient:
    """Arthas WebConsole HTTP 客户端"""
    
    # 持续命令列表：需要限制执行次数的命令
    PERSISTENT_COMMANDS = {
        "watch", "trace", "tt", "stack", "jfr"
    }
    
    # 默认执行次数配置
    DEFAULT_COUNTS = {
        "watch": 5,
        "trace": 3, 
        "tt": 10,
        "stack": 3,
        "jfr": 1
    }

    def __init__(self, url: str = "http://localhost:8563", timeout: int = 30):
        """
        初始化 Arthas 客户端
        
        Args:
            url: Arthas WebConsole 完整URL地址
            timeout: 请求超时时间(秒)
        """
        # 从URL中解析host和port用于连接信息显示
        from urllib.parse import urlparse
        parsed = urlparse(url)
        
        self.connection = ArthasConnection(
            host=parsed.hostname or "localhost", 
            port=parsed.port or 8563
        )
        self.base_url = url.rstrip('/')  # 确保没有尾部斜杠
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.disconnect()
    
    async def connect(self) -> ArthasResponse:
        """
        连接到 Arthas WebConsole
        
        Returns:
            连接结果响应
        """
        try:
            if self._client:
                await self.disconnect()
                
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
            
            # 使用正确的Arthas API格式进行健康检查
            # 发送一个简单的version命令来测试连接
            test_payload = {
                "action": "exec",
                "requestId": "health_check",
                "command": "version",
                "execTimeout": "5000"
            }
            
            response = await self._client.post("/api", json=test_payload)
            
            if response.status_code == 200:
                self.connection.is_connected = True
                logger.info(f"Connected to Arthas WebConsole: {self.connection.host}:{self.connection.port}")
                
                return ArthasResponse(
                    status="success",
                    message=f"Connected to Arthas WebConsole: {self.connection.host}:{self.connection.port}",
                    data={"response": response.json() if response.content else {}}
                )
            else:
                raise httpx.HTTPStatusError(
                    f"HTTP {response.status_code}", 
                    request=response.request, 
                    response=response
                )
                
        except Exception as e:
            # 改进连接错误日志记录
            error_msg = str(e) if str(e).strip() else repr(e)
            error_type = type(e).__name__
            logger.error(f"Failed to connect to Arthas [{error_type}]: {error_msg}")
            
            self.connection.is_connected = False
            return ArthasResponse(
                status="error",
                error=f"Connection failed [{error_type}]: {error_msg if error_msg else 'Unknown connection error'}"
            )
    
    async def disconnect(self) -> ArthasResponse:
        """
        断开 Arthas 连接
        
        Returns:
            断开连接响应
        """
        try:
            if self._client:
                await self._client.aclose()
                self._client = None
                
            self.connection.is_connected = False
            self.connection.session_id = None
            
            logger.info("Disconnected from Arthas")
            return ArthasResponse(
                status="success",
                message="Disconnected from Arthas"
            )
            
        except Exception as e:
            # 改进断开连接错误日志记录
            error_msg = str(e) if str(e).strip() else repr(e)
            error_type = type(e).__name__
            logger.error(f"Failed to disconnect [{error_type}]: {error_msg}")
            
            return ArthasResponse(
                status="error",
                error=f"Failed to disconnect [{error_type}]: {error_msg if error_msg else 'Unknown disconnection error'}"
            )
    
    async def execute_command(self, command: str, args: Optional[List[str]] = None) -> ArthasResponse:
        """
        执行 Arthas 命令
        
        Args:
            command: 要执行的命令
            args: 命令参数
            
        Returns:
            命令执行结果
        """
        if not self.connection.is_connected or not self._client:
            return ArthasResponse(
                status="error",
                error="Not connected to Arthas, please call connect first"
            )
        
        try:
            # 构建完整的命令字符串
            full_command = command
            if args:
                # 过滤空参数
                filtered_args = [arg for arg in args if arg is not None and str(arg).strip()]
                if filtered_args:
                    full_command += " " + " ".join(filtered_args)
            
            # 智能处理持续命令：自动添加-n参数限制执行次数
            full_command = self._ensure_persistent_command_limits(full_command)
            
            # 构造正确的Arthas API请求格式
            payload = {
                "action": "exec",
                "requestId": f"cmd_{hash(full_command)}_{int(asyncio.get_event_loop().time())}",
                "command": full_command,
                "execTimeout": "30000"  # 30秒超时
            }
            
            # 如果有会话ID，添加到请求中
            if self.connection.session_id:
                payload["sessionId"] = self.connection.session_id
            
            # 发送命令执行请求
            response = await self._client.post("/api", json=payload)
            
            if response.status_code == 200:
                try:
                    result_data = response.json() if response.content else {}
                except Exception as json_error:
                    logger.warning(f"Failed to parse JSON response: {json_error}")
                    try:
                        result_data = {"raw_text": response.text}
                    except:
                        result_data = {"error": "Failed to parse response"}
                
                logger.info(f"Command executed successfully: {full_command}")
                
                return ArthasResponse(
                    status="success",
                    message=f"Command '{full_command}' executed successfully",
                    data=result_data
                )
            else:
                raise httpx.HTTPStatusError(
                    f"HTTP {response.status_code}",
                    request=response.request,
                    response=response
                )
                
        except Exception as e:
            # 改进错误日志记录，包含更多调试信息
            error_msg = str(e) if str(e).strip() else repr(e)
            error_type = type(e).__name__
            logger.error(f"Command execution failed [{error_type}]: {error_msg}")
            
            # 如果是HTTP状态错误，记录更多细节
            if hasattr(e, 'response'):
                try:
                    response_text = e.response.text if hasattr(e.response, 'text') else str(e.response)
                    logger.error(f"HTTP Response: {response_text[:500]}...")  # 限制长度
                except:
                    logger.error(f"HTTP Response: Unable to get response text")
            
            return ArthasResponse(
                status="error",
                error=f"Command execution failed [{error_type}]: {error_msg if error_msg else 'Unknown error'}"
            )
    
    def _ensure_persistent_command_limits(self, command: str) -> str:
        """
        确保持续命令有执行次数限制，避免无限等待
        
        Args:
            command: 原始命令字符串
            
        Returns:
            处理后的命令字符串
        """
        parts = command.strip().split()
        if not parts:
            return command
            
        cmd_name = parts[0]
        
        # 只处理持续命令
        if cmd_name not in self.PERSISTENT_COMMANDS:
            return command
        
        # 如果已经有-n参数，不做修改
        if "-n" in parts:
            return command
            
        # 获取默认执行次数
        default_count = self.DEFAULT_COUNTS.get(cmd_name, 3)
        
        # 添加-n参数
        # 对于不同命令，-n参数位置可能不同，统一放在命令名后面
        new_parts = [cmd_name, "-n", str(default_count)] + parts[1:]
        
        logger.info(f"Auto-limited persistent command: {command} -> {' '.join(new_parts)}")
        return " ".join(new_parts)
    
    async def execute_persistent_command_async(self, command: str, 
                                          pull_timeout: int = 5, 
                                          max_pulls: int = 4) -> ArthasResponse:
        """
        异步执行持续命令，避免长时间等待
        
        Args:
            command: 要执行的命令
            pull_timeout: 每次拉取结果的等待时间（秒）
            max_pulls: 最大拉取次数
            
        Returns:
            命令执行结果
        """
        if not self.connection.is_connected or not self._client:
            return ArthasResponse(
                status="error",
                error="Not connected to Arthas, please call connect first"
            )
        
        try:
            # 1. 创建临时会话
            init_payload = {"action": "init_session"}
            init_response = await self._client.post("/api", json=init_payload)
            
            if init_response.status_code != 200:
                raise Exception(f"Failed to create session: HTTP {init_response.status_code}")
                
            session_data = init_response.json()
            session_id = session_data.get("sessionId")
            consumer_id = session_data.get("consumerId")
            
            if not session_id or not consumer_id:
                raise Exception("Failed to get session info")
            
            # 2. 异步执行命令
            exec_payload = {
                "action": "async_exec",
                "command": command,
                "sessionId": session_id
            }
            
            exec_response = await self._client.post("/api", json=exec_payload)
            if exec_response.status_code != 200:
                raise Exception(f"Failed to execute command: HTTP {exec_response.status_code}")
                
            exec_data = exec_response.json()
            if exec_data.get("state") != "SCHEDULED":
                raise Exception(f"Command not scheduled: {exec_data}")
            
            job_id = exec_data.get("body", {}).get("jobId")
            logger.info(f"Async command scheduled with job ID: {job_id}")
            
            # 3. 拉取结果（限制次数和时间）
            all_results = []
            pull_count = 0
            
            while pull_count < max_pulls:
                pull_payload = {
                    "action": "pull_results",
                    "sessionId": session_id,
                    "consumerId": consumer_id
                }
                
                try:
                    # 设置较短的超时时间
                    pull_response = await asyncio.wait_for(
                        self._client.post("/api", json=pull_payload),
                        timeout=pull_timeout
                    )
                    
                    if pull_response.status_code == 200:
                        pull_data = pull_response.json()
                        results = pull_data.get("body", {}).get("results", [])
                        
                        if results:
                            all_results.extend(results)
                            # 检查是否有完成状态
                            for result in results:
                                if (result.get("type") == "status" and 
                                    result.get("statusCode") == 0):
                                    logger.info("Command completed successfully")
                                    break
                            else:
                                # 如果没有完成状态，继续拉取
                                pull_count += 1
                                continue
                            break
                        else:
                            pull_count += 1
                            
                except asyncio.TimeoutError:
                    logger.warning(f"Pull timeout after {pull_timeout}s, attempt {pull_count + 1}")
                    pull_count += 1
                    
            # 4. 中断命令（清理）
            try:
                interrupt_payload = {
                    "action": "interrupt_job",
                    "sessionId": session_id
                }
                await self._client.post("/api", json=interrupt_payload)
                logger.info("Command interrupted for cleanup")
            except Exception as e:
                logger.warning(f"Failed to interrupt command: {e}")
            
            # 5. 关闭会话
            try:
                close_payload = {
                    "action": "close_session",
                    "sessionId": session_id
                }
                await self._client.post("/api", json=close_payload)
                logger.info("Session closed")
            except Exception as e:
                logger.warning(f"Failed to close session: {e}")
            
            # 6. 返回结果
            if all_results:
                return ArthasResponse(
                    status="success",
                    message=f"Command '{command}' executed with {len(all_results)} results (async mode)",
                    data={"results": all_results, "async_execution": True}
                )
            else:
                return ArthasResponse(
                    status="warning", 
                    message=f"Command '{command}' executed but no results received (possibly no matching calls)",
                    data={"results": [], "async_execution": True}
                )
                
        except Exception as e:
            error_msg = str(e) if str(e).strip() else repr(e)
            error_type = type(e).__name__
            logger.error(f"Async command execution failed [{error_type}]: {error_msg}")
            
            return ArthasResponse(
                status="error",
                error=f"Async command execution failed [{error_type}]: {error_msg}"
            )
    
    async def get_jvm_info(self) -> ArthasResponse:
        """
        获取 JVM 信息
        
        Returns:
            JVM 信息响应
        """
        return await self.execute_command("jvm")
    
    async def get_system_env(self) -> ArthasResponse:
        """
        获取系统环境信息
        
        Returns:
            系统环境响应
        """
        return await self.execute_command("sysenv")
    
    async def get_thread_info(self, thread_id: Optional[int] = None, count: int = 10) -> ArthasResponse:
        """
        获取线程信息
        
        Args:
            thread_id: 指定线程ID
            count: 返回线程数量
            
        Returns:
            线程信息响应
        """
        args = []
        if thread_id is not None:
            # 根据文档，直接指定线程ID，不使用-id参数
            args.append(str(thread_id))
        else:
            # 如果没有指定线程ID，使用-n参数显示前N个线程
            if count > 0:
                args.extend(["-n", str(count)])
            
        return await self.execute_command("thread", args)
    
    
    async def trace_method(self, class_pattern: str, method_pattern: str, count: int = 3,
                          async_mode: bool = True) -> ArthasResponse:
        """
        追踪方法调用路径
        
        Args:
            class_pattern: 类名模式
            method_pattern: 方法名模式
            count: 追踪次数
            async_mode: 是否使用异步模式（推荐）
            
        Returns:
            追踪结果响应
        """
        # 根据文档，trace命令语法: trace [-E] [-n:] class-pattern method-pattern [condition-express]
        # 修复参数顺序：正确的Arthas trace命令格式为 trace class-pattern method-pattern -n count
        args = [class_pattern, method_pattern, "-n", str(count)]
        command = "trace " + " ".join(args)
        
        if async_mode:
            return await self.execute_persistent_command_async(command, pull_timeout=5, max_pulls=4)
        else:
            return await self.execute_command("trace", args)
    
    async def watch_method(self, class_pattern: str, method_pattern: str, 
                          expression: str = "returnObj", count: int = 5,
                          async_mode: bool = True) -> ArthasResponse:
        """
        观察方法调用
        
        Args:
            class_pattern: 类名模式
            method_pattern: 方法名模式
            expression: 观察表达式，默认观察返回值
            count: 观察次数
            async_mode: 是否使用异步模式（推荐）
            
        Returns:
            观察结果响应
        """
        # 表达式预处理：处理复杂表达式的引号
        processed_expression = expression
        if '{' in expression and '}' in expression:
            # 确保复杂表达式被正确引用
            if not (expression.startswith('"') and expression.endswith('"')):
                processed_expression = f'"{expression}"'
        
        # 正确的Arthas watch命令格式：watch class-pattern method-pattern expression -n count
        args = [class_pattern, method_pattern, processed_expression, "-n", str(count)]
        command = "watch " + " ".join(args)
        
        if async_mode:
            return await self.execute_persistent_command_async(command, pull_timeout=5, max_pulls=4)
        else:
            return await self.execute_command("watch", args)
    
    async def get_memory_info(self) -> ArthasResponse:
        """
        获取内存使用信息
        
        Returns:
            内存信息响应
        """
        return await self.execute_command("memory")
    
    async def get_gc_info(self) -> ArthasResponse:
        """
        获取 GC 信息
        
        Returns:
            GC 信息响应
        """
        return await self.execute_command("gc")
    
    async def decompile_class(self, class_name: str) -> ArthasResponse:
        """
        反编译类
        
        Args:
            class_name: 类名
            
        Returns:
            反编译结果响应
        """
        return await self.execute_command("jad", [class_name])
    
    async def search_class(self, class_pattern: str) -> ArthasResponse:
        """
        搜索类
        
        Args:
            class_pattern: 类名模式
            
        Returns:
            搜索结果响应
        """
        return await self.execute_command("sc", [class_pattern])
    
    async def search_method(self, class_pattern: str, method_pattern: Optional[str] = None) -> ArthasResponse:
        """
        搜索方法
        
        Args:
            class_pattern: 类名模式
            method_pattern: 方法名模式
            
        Returns:
            搜索结果响应
        """
        args = [class_pattern]
        if method_pattern:
            args.append(method_pattern)
        return await self.execute_command("sm", args)
    
    def get_connection_info(self) -> Dict[str, Any]:
        """
        获取连接信息
        
        Returns:
            连接信息字典
        """
        return self.connection.model_dump()
    
    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.connection.is_connected