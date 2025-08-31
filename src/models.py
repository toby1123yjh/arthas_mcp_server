"""
Arthas MCP Server 数据模型
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class ArthasConnection(BaseModel):
    """Arthas 连接配置"""
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )
    
    host: str = Field(default="localhost", description="Arthas WebConsole 主机")
    port: int = Field(default=8563, description="Arthas WebConsole 端口")
    session_id: Optional[str] = Field(default=None, description="会话 ID")
    is_connected: bool = Field(default=False, description="连接状态")
    connected_at: Optional[datetime] = Field(default=None, description="连接时间")

class JVMInfo(BaseModel):
    """JVM 信息模型"""
    name: str = Field(description="JVM 名称")
    version: str = Field(description="Java 版本")
    vendor: str = Field(description="供应商")
    uptime: str = Field(description="运行时间")
    heap_used: str = Field(description="已使用堆内存")
    heap_max: str = Field(description="最大堆内存")
    non_heap_used: str = Field(description="已使用非堆内存")
    non_heap_max: str = Field(description="最大非堆内存")
    gc_count: Optional[int] = Field(default=None, description="GC 次数")
    gc_time: Optional[str] = Field(default=None, description="GC 总时间")

class ThreadInfo(BaseModel):
    """线程信息模型"""
    thread_id: int = Field(description="线程 ID")
    thread_name: str = Field(description="线程名称")
    state: str = Field(description="线程状态")
    cpu_time: str = Field(description="CPU 时间")
    user_time: str = Field(description="用户时间")
    priority: Optional[int] = Field(default=None, description="线程优先级")
    daemon: Optional[bool] = Field(default=None, description="是否守护线程")

class MemoryInfo(BaseModel):
    """内存信息模型"""
    heap_memory: Dict[str, Any] = Field(description="堆内存信息")
    non_heap_memory: Dict[str, Any] = Field(description="非堆内存信息")
    memory_pools: List[Dict[str, Any]] = Field(description="内存池信息")
    garbage_collectors: List[Dict[str, Any]] = Field(description="垃圾收集器信息")

class ClassLoadInfo(BaseModel):
    """类加载信息模型"""
    loaded_class_count: int = Field(description="已加载类数量")
    total_loaded_class_count: int = Field(description="总共已加载类数量")
    unloaded_class_count: int = Field(description="已卸载类数量")
    is_verbose: bool = Field(description="是否启用详细输出")

class ArthasCommand(BaseModel):
    """Arthas 命令模型"""
    command: str = Field(description="命令内容")
    args: Optional[List[str]] = Field(default=None, description="命令参数")
    session_id: Optional[str] = Field(default=None, description="会话 ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="执行时间")

class ArthasResponse(BaseModel):
    """Arthas 响应模型"""
    status: str = Field(description="响应状态")
    message: Optional[str] = Field(default=None, description="响应消息")
    data: Optional[Dict[str, Any]] = Field(default=None, description="响应数据")
    error: Optional[str] = Field(default=None, description="错误信息")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间")

class DiagnosticResult(BaseModel):
    """诊断结果模型"""
    type: str = Field(description="诊断类型")
    title: str = Field(description="诊断标题")
    summary: str = Field(description="诊断摘要")
    details: Dict[str, Any] = Field(description="详细信息")
    severity: str = Field(description="严重程度", pattern="^(low|medium|high|critical)$")
    suggestions: List[str] = Field(description="建议解决方案")