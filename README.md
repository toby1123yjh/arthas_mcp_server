# Arthas MCP Server

[![中文](https://img.shields.io/badge/lang-中文-blue.svg)](README.zh-CN.md)

Java diagnostics MCP server

## Overview

Arthas MCP Server is an MCP-based diagnostic toolkit for Java applications, designed for LLM integration. It integrates with Alibaba Arthas so AI assistants can analyze and diagnose Java apps.

## Use Cases

### Example: Performance Analysis with AI Assistant

![Use Case Example](./usecase/case1.jpg)

The screenshot demonstrates how to use AI assistants (like Claude) to intelligently diagnose Java application performance issues through natural language interactions. Simply describe your problem, and the AI assistant will automatically:

- Connect to the Arthas server
- Execute appropriate diagnostic commands
- Analyze performance metrics
- Provide actionable insights and recommendations

This eliminates the need to manually remember Arthas command syntax and parameters.

## Features

- 🔍 **Intelligent diagnostics** via LLM-friendly tools
- 🚀 **Real-time monitoring**: JVM, threads, memory
- 📊 **Performance analysis**: CPU usage, call tracing, bottlenecks
- 🔧 **Runtime operations**: dynamic class/method tools

## Quick Start

### Requirements
- Python 3.13+
- A running Java application
- Arthas 3.6.7+

### Install
```bash
uv sync
```

### Run
```bash
python main.py
```

## MCP Tools

- connect_arthas: connect to Arthas WebConsole
- get_connection_status: get current status
- disconnect_arthas: disconnect
- get_jvm_info: JVM info
- get_thread_info: thread status and performance
- get_memory_info: memory usage and GC
- execute_arthas_command: run custom Arthas command
- analyze_performance: performance analysis
- trace_method_calls: method call tracing

## Config

### Add to Cursor / Claude Code

macOS: `~/.cursor/mcp.json`
Windows: `C:\Users\{username}\.cursor\mcp.json`

```json
{
  "mcpServers": {
    "arthas": {
      "command": "uv",
      "args": ["--directory", "F:\\path\\to\\arthas_mcp_server", "run", "python", "main.py"],
      "env": { "ARTHAS_URL": "http://localhost:8563" }
    }
  }
}
```

### Start Arthas

There are multiple deployment methods: either attach mode or agent mode. Both approaches ultimately result in listening for HTTP requests (Arthas commands) on port 8563.


## Project Structure

```
arthas_mcp_server/
├── src/
│   ├── __init__.py
│   ├── models.py
│   ├── server.py
│   └── client.py
├── main.py
├── pyproject.toml
└── README.md
```

## Development

```bash
uv sync --extra dev
```
