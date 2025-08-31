"""
Arthas MCP Server 核心服务器实现
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

from .client import ArthasClient
from .models import ArthasConnection, JVMInfo, ThreadInfo, ArthasResponse

# 获取日志器
logger = logging.getLogger(__name__)
# 确保中文日志消息正确编码
logger.setLevel(logging.INFO)

class ArthasMCPServer:
    """Arthas MCP Server - Java Performance Analysis & Diagnostics

    A Java application performance analysis and system diagnostics server designed for LLMs.
    It supports real-time performance monitoring, memory analysis, thread analysis, method tracing, and other core diagnostic capabilities.
    It can diagnose business issues by inspecting method call inputs and outputs, exceptions, monitoring method execution time, and class loading information.
    """
    
    def __init__(self, name: str = "Java Performance Analysis & Diagnostics (Arthas)"):
        """
        初始化 MCP 服务器
        
        Args:
            name: 服务器名称
        """
        self.mcp = FastMCP(name)
        self.client: Optional[ArthasClient] = None
        self._setup_tools()
    
    def _setup_tools(self) -> None:
        """设置 MCP 工具"""
        
        @self.mcp.tool()
        async def connect_arthas(url: str = "http://localhost:8563") -> Dict[str, Any]:
            """
            连接到 Arthas http api
            
            Args:
                url: Arthas http api 完整URL地址 (例如: http://localhost:8563)
            
            Returns:
                连接结果信息
            """
            try:
                if self.client:
                    await self.client.disconnect()
                
                self.client = ArthasClient(url=url)
                result = await self.client.connect()
                
                return {
                    "status": result.status,
                    "message": result.message,
                    "data": result.data,
                    "connection": self.client.get_connection_info()
                }
            except Exception as e:
                logger.error(f"Failed to connect to Arthas: {str(e)}")
                return {
                    "status": "error",
                    "message": f"连接失败: {str(e)}"
                }

        @self.mcp.tool()
        async def get_connection_status() -> Dict[str, Any]:
            """
            获取当前连接状态
            
            Returns:
                连接状态信息
            """
            if not self.client:
                return {
                    "status": "error",
                    "message": "客户端未初始化"
                }
                
            return {
                "status": "success",
                "connection": self.client.get_connection_info(),
                "is_connected": self.client.is_connected
            }

        @self.mcp.tool()
        async def disconnect_arthas() -> Dict[str, Any]:
            """
            断开 Arthas 连接
            
            Returns:
                断开连接结果
            """
            if not self.client:
                return {
                    "status": "error",
                    "message": "客户端未初始化"
                }
            
            try:
                result = await self.client.disconnect()
                return {
                    "status": result.status,
                    "message": result.message
                }
            except Exception as e:
                logger.error(f"Failed to disconnect: {str(e)}")
                return {
                    "status": "error",
                    "message": f"断开连接失败: {str(e)}"
                }

        @self.mcp.tool()
        async def execute_arthas_custom_command(command: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
            """
            执行自定义性能分析命令 - 灵活执行各种Arthas性能诊断命令
            
            当专用性能分析工具不能满足需求时，可使用此工具执行任意Arthas命令。
            支持高级性能分析、系统诊断、自定义性能监控等场景。
            
            常用性能分析命令：
            - dashboard: 系统性能概览
            - vmtool: 虚拟机工具
            - logger: 日志分析
            
            Args:
                command: 要执行的 Arthas 性能分析命令
                args: 命令参数列表
                
            Returns:
                性能分析命令执行结果
            """
            if not self.client or not self.client.is_connected:
                return {
                    "status": "error",
                    "message": "未连接到 Arthas，请先调用 connect_arthas"
                }
            
            try:
                result = await self.client.execute_command(command, args)
                return {
                    "status": result.status,
                    "message": result.message,
                    "data": result.data,
                    "error": result.error
                }
            except Exception as e:
                logger.error(f"Command execution failed: {str(e)}")
                return {
                    "status": "error",
                    "message": f"命令执行失败: {str(e)}"
                }

        @self.mcp.tool()
        async def get_jvm_info() -> Dict[str, Any]:
            """
            获取JVM性能信息和系统状态 - Java应用性能分析基础
            
            提供JVM运行时信息，包括版本、配置参数、运行状态等，
            是进行Java应用性能分析和系统诊断的基础数据。
            
            Returns:
                JVM性能信息和系统状态数据
            """
            if not self.client or not self.client.is_connected:
                return {
                    "status": "error",
                    "message": "未连接到 Arthas，请先调用 connect_arthas"
                }
            
            try:
                result = await self.client.get_jvm_info()
                return {
                    "status": result.status,
                    "message": result.message,
                    "data": result.data,
                    "error": result.error
                }
            except Exception as e:
                logger.error(f"Failed to get JVM info: {str(e)}")
                return {
                    "status": "error",
                    "message": f"获取 JVM 信息失败: {str(e)}"
                }

        @self.mcp.tool()
        async def get_thread_info(thread_id: Optional[int] = None, count: int = 10) -> Dict[str, Any]:
            """
            线程性能分析 - 诊断线程阻塞、死锁、CPU占用等性能问题
            
            分析线程状态、CPU使用率、阻塞情况，识别性能瓶颈和并发问题。
            适用于解决高CPU使用率、响应缓慢、死锁等性能问题。
            
            注意：thread_id指定时返回该线程详情，否则返回前count个线程
            
            Args:
                thread_id: 指定线程ID进行深度性能分析 (可选)
                count: 返回的线程数量限制，用于性能概览
                
            Returns:
                线程性能分析数据，包括CPU占用、状态、阻塞信息
            """
            if not self.client or not self.client.is_connected:
                return {
                    "status": "error",
                    "message": "未连接到 Arthas，请先调用 connect_arthas"
                }
            
            try:
                result = await self.client.get_thread_info(thread_id=thread_id, count=count)
                return {
                    "status": result.status,
                    "message": result.message,
                    "data": result.data,
                    "error": result.error
                }
            except Exception as e:
                logger.error(f"Failed to get thread info: {str(e)}")
                return {
                    "status": "error",
                    "message": f"获取线程信息失败: {str(e)}"
                }

        @self.mcp.tool()
        async def get_memory_info() -> Dict[str, Any]:
            """
            内存性能分析 - 诊断内存泄漏、OOM、GC压力等性能问题
            
            分析堆内存、非堆内存、GC情况，识别内存性能瓶颈。
            适用于解决内存溢出、内存泄漏、GC频繁等性能问题。
            
            Returns:
                内存性能分析数据，包括堆使用率、GC统计、内存分布
            """
            if not self.client or not self.client.is_connected:
                return {
                    "status": "error",
                    "message": "未连接到 Arthas，请先调用 connect_arthas"
                }
            
            try:
                result = await self.client.get_memory_info()
                return {
                    "status": result.status,
                    "message": result.message,
                    "data": result.data,
                    "error": result.error
                }
            except Exception as e:
                logger.error(f"Failed to get memory info: {str(e)}")
                return {
                    "status": "error",
                    "message": f"获取内存信息失败: {str(e)}"
                }


        @self.mcp.tool()
        async def trace_method(class_pattern: str, method_pattern: str, count: int = 3,
                             async_mode: bool = True) -> Dict[str, Any]:
            """
            方法性能追踪 - 分析方法调用链和执行耗时，定位性能瓶颈
            
            深度追踪方法调用路径和执行时间，识别慢方法和性能热点。
            适用于分析接口响应慢、方法执行耗时、调用链复杂等性能问题。
            
            性能分析场景：
            - API响应时间分析
            - 方法执行性能优化  
            - 调用链路性能瓶颈定位
            
            Args:
                class_pattern: 类名模式 (支持通配符 *, 如: com.example.*)
                method_pattern: 方法名模式 (支持通配符 *, 如: get*)
                count: 追踪次数 (默认3次，推荐3次)
                async_mode: 异步模式 (推荐false，超时后停止追踪)
                
            Returns:
                方法性能追踪结果，包含调用链路和执行耗时数据
            """
            if not self.client or not self.client.is_connected:
                return {
                    "status": "error",
                    "message": "未连接到 Arthas，请先调用 connect_arthas"
                }
            
            try:
                result = await self.client.trace_method(class_pattern, method_pattern, count, async_mode)
                return {
                    "status": result.status,
                    "message": result.message,
                    "data": result.data,
                    "error": result.error
                }
            except Exception as e:
                logger.error(f"Method trace failed: {str(e)}")
                return {
                    "status": "error",
                    "message": f"方法追踪失败: {str(e)}"
                }

        @self.mcp.tool()
        async def decompile_class(class_name: str) -> Dict[str, Any]:
            """
            反编译类
            
            Args:
                class_name: 类名
                
            Returns:
                反编译结果
            """
            if not self.client or not self.client.is_connected:
                return {
                    "status": "error",
                    "message": "未连接到 Arthas，请先调用 connect_arthas"
                }
            
            try:
                result = await self.client.decompile_class(class_name)
                return {
                    "status": result.status,
                    "message": result.message,
                    "data": result.data,
                    "error": result.error
                }
            except Exception as e:
                logger.error(f"Class decompilation failed: {str(e)}")
                return {
                    "status": "error",
                    "message": f"类反编译失败: {str(e)}"
                }

        @self.mcp.tool()
        async def search_class(class_pattern: str) -> Dict[str, Any]:
            """
            搜索类
            
            Args:
                class_pattern: 类名模式
                
            Returns:
                搜索结果
            """
            if not self.client or not self.client.is_connected:
                return {
                    "status": "error",
                    "message": "未连接到 Arthas，请先调用 connect_arthas"
                }
            
            try:
                result = await self.client.search_class(class_pattern)
                return {
                    "status": result.status,
                    "message": result.message,
                    "data": result.data,
                    "error": result.error
                }
            except Exception as e:
                logger.error(f"Class search failed: {str(e)}")
                return {
                    "status": "error",
                    "message": f"类搜索失败: {str(e)}"
                }

        @self.mcp.tool()
        async def search_method(class_pattern: str, method_pattern: Optional[str] = None) -> Dict[str, Any]:
            """
            搜索方法
            
            Args:
                class_pattern: 类名模式
                method_pattern: 方法名模式 (可选)
                
            Returns:
                搜索结果
            """
            if not self.client or not self.client.is_connected:
                return {
                    "status": "error",
                    "message": "未连接到 Arthas，请先调用 connect_arthas"
                }
            
            try:
                result = await self.client.search_method(class_pattern, method_pattern)
                return {
                    "status": result.status,
                    "message": result.message,
                    "data": result.data,
                    "error": result.error
                }
            except Exception as e:
                logger.error(f"Method search failed: {str(e)}")
                return {
                    "status": "error",
                    "message": f"方法搜索失败: {str(e)}"
                }

        @self.mcp.tool()
        async def get_gc_info() -> Dict[str, Any]:
            """
            GC性能分析 - 分析垃圾收集器性能，优化内存管理
            
            分析GC频率、耗时、回收效果，识别GC性能瓶颈。
            适用于解决GC暂停时间长、Full GC频繁、内存回收效率低等性能问题。
            
            Returns:
                GC性能分析数据，包括GC统计、暂停时间、回收效率
            """
            if not self.client or not self.client.is_connected:
                return {
                    "status": "error",
                    "message": "未连接到 Arthas，请先调用 connect_arthas"
                }
            
            try:
                result = await self.client.get_gc_info()
                return {
                    "status": result.status,
                    "message": result.message,
                    "data": result.data,
                    "error": result.error
                }
            except Exception as e:
                logger.error(f"Failed to get GC info: {str(e)}")
                return {
                    "status": "error",
                    "message": f"获取 GC 信息失败: {str(e)}"
                }

        @self.mcp.tool()
        async def get_system_env() -> Dict[str, Any]:
            """
            获取系统环境变量
            
            Returns:
                系统环境变量信息
            """
            if not self.client or not self.client.is_connected:
                return {
                    "status": "error",
                    "message": "未连接到 Arthas，请先调用 connect_arthas"
                }
            
            try:
                result = await self.client.get_system_env()
                return {
                    "status": result.status,
                    "message": result.message,
                    "data": result.data,
                    "error": result.error
                }
            except Exception as e:
                logger.error(f"Failed to get system environment variables: {str(e)}")
                return {
                    "status": "error",
                    "message": f"获取系统环境变量失败: {str(e)}"
                }

        @self.mcp.tool()
        async def watch_method(class_pattern: str, method_pattern: str, 
                              expression: str = "returnObj", count: int = 3,
                              async_mode: bool = True) -> Dict[str, Any]:
            """
            方法实时性能监控 - 监控方法执行过程，分析性能数据和异常情况

            
            性能监控场景：
            - 接口性能实时监控
            - 业务逻辑执行分析
            - 异常和错误监控
            - 数据流转跟踪
            
            Args:
                    class_pattern: 类名模式 (支持通配符 *, 如: com.example.*)
                    method_pattern: 方法名模式 (支持通配符 *, 如: get*)
                    expression: 观察表达式，常用: "returnObj"(返回值), "params"(参数), "{params,returnObj}"(都观察)
                    count: 观察次数 (默认3次,推荐3次)
                    async_mode: 异步模式 （推荐false，超时后停止观察）
                    
            Returns:
                方法性能监控结果，包含执行数据和性能指标
            
            实用示例：
            - 性能监控: watch_method("com.example.OrderService", "createOrder", "returnObj", 5) 
            - 异常监控: watch_method("*.PaymentService", "*", "throwExp", 5)
            - 全面监控: watch_method("com.example.UserController", "register", "{params,returnObj,throwExp}", 3)
            """
            if not self.client or not self.client.is_connected:
                return {
                    "status": "error",
                    "message": "未连接到 Arthas，请先调用 connect_arthas"
                }
            
            try:
                result = await self.client.watch_method(class_pattern, method_pattern, expression, count, async_mode)
                return {
                    "status": result.status,
                    "message": result.message,
                    "data": result.data,
                    "error": result.error
                }
            except Exception as e:
                logger.error(f"Method watch failed: {str(e)}")
                return {
                    "status": "error",
                    "message": f"方法观察失败: {str(e)}"
                }

        @self.mcp.tool()
        async def analyze_system_performance() -> Dict[str, Any]:
            """
            系统性能综合分析，整体分析时使用
            
            综合分析CPU使用率、内存分布、线程状态、GC性能等关键指标，
            快速识别系统性能瓶颈和优化建议，适用于性能问题排查的第一步。
            
            性能分析维度：
            - CPU使用率和线程分析
            - 内存使用和GC性能
            - 系统负载和资源状况
            - 关键性能指标汇总
            
            Returns:
                系统性能分析报告，包含性能指标和优化建议
            """
            if not self.client or not self.client.is_connected:
                return {
                    "status": "error",
                    "message": "未连接到 Arthas，请先调用 connect_arthas"
                }
            
            try:
                # 使用dashboard命令获取系统性能概览
                result = await self.client.execute_command("dashboard", ["-n", "1"])
                return {
                    "status": result.status,
                    "message": "系统性能分析完成",
                    "data": result.data,
                    "analysis_type": "comprehensive_system_performance",
                    "error": result.error
                }
            except Exception as e:
                logger.error(f"System performance analysis failed: {str(e)}")
                return {
                    "status": "error",
                    "message": f"系统性能分析失败: {str(e)}"
                }

        @self.mcp.tool()
        async def profile_performance_hotspots(duration: int = 15, event: str = "cpu") -> Dict[str, Any]:
            """
            全局性能热点分析，整体分析时使用
            
            使用profiler生成火焰图，深度分析性能热点和资源消耗，
            精确定位高CPU占用的方法和内存分配热点。
            
            适用场景：
            - CPU使用率过高分析
            - 方法执行性能优化
            - 内存分配热点识别
            - 性能回归分析
            
            Args:
                duration: 分析持续时间(秒)，推荐15秒
                event: 分析事件类型 ('cpu', 'alloc', 'lock', 'cache-misses')
                
            Returns:
                性能热点分析结果和火焰图数据
            """
            if not self.client or not self.client.is_connected:
                return {
                    "status": "error",
                    "message": "未连接到 Arthas，请先调用 connect_arthas"
                }
            
            try:
                # 启动profiler
                start_result = await self.client.execute_command("profiler", ["start", "--event", event])
                if start_result.status != "success":
                    return {
                        "status": "error",
                        "message": f"启动性能分析失败: {start_result.message}"
                    }
                
                # 等待指定时间
                await asyncio.sleep(duration)
                
                # 生成报告
                result = await self.client.execute_command("profiler", ["stop", "--format", "html"])
                return {
                    "status": result.status,
                    "message": f"性能热点分析完成 - {event}事件，持续{duration}秒",
                    "data": result.data,
                    "analysis_type": f"performance_hotspots_{event}",
                    "duration": duration,
                    "error": result.error
                }
            except Exception as e:
                logger.error(f"Performance hotspots analysis failed: {str(e)}")
                return {
                    "status": "error",
                    "message": f"性能热点分析失败: {str(e)}"
                }

    def run_stdio(self) -> None:
        """通过 stdio 启动 MCP 服务器"""
        logger.info("Starting Arthas MCP Server...")
        try:
            # FastMCP 会自己处理事件循环
            self.mcp.run()
        except Exception as e:
            logger.error(f"Server run failed: {str(e)}")
            raise
    
    async def run(self) -> None:
        """启动 MCP 服务器（异步版本）"""
        logger.info("Starting Arthas MCP Server...")
        try:
            await self.mcp.run()
        except Exception as e:
            logger.error(f"Server run failed: {str(e)}")
            raise
        finally:
            # 清理资源
            if self.client:
                await self.client.disconnect()

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.client:
            await self.client.disconnect()

# 主函数
async def main():
    """服务器主函数"""
    async with ArthasMCPServer() as server:
        await server.run()

def run_mcp_server():
    """MCP 服务器启动函数，兼容不同环境的事件循环"""
    try:
        # 尝试获取当前事件循环
        loop = asyncio.get_running_loop()
        # 如果已有运行的事件循环，创建任务
        return asyncio.create_task(main())
    except RuntimeError:
        # 没有运行的事件循环，使用 asyncio.run
        return asyncio.run(main())

if __name__ == "__main__":
    run_mcp_server()