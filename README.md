<div align="center">

# Dockerfile Generator Ai MCP

**MCP server for dockerfile generator ai mcp operations**

[![PyPI](https://img.shields.io/pypi/v/meok-dockerfile-generator-ai-mcp)](https://pypi.org/project/meok-dockerfile-generator-ai-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MEOK AI Labs](https://img.shields.io/badge/MEOK_AI_Labs-MCP_Server-purple)](https://meok.ai)

</div>

## Overview

Dockerfile Generator Ai MCP provides AI-powered tools via the Model Context Protocol (MCP).

## Tools

| Tool | Description |
|------|-------------|
| `generate_dockerfile` | Generate an optimized Dockerfile for the specified language and framework. |
| `optimize_layers` | Analyze a Dockerfile and suggest layer optimizations for faster builds and small |
| `validate_dockerfile` | Validate a Dockerfile for syntax errors, security issues, and best practice viol |
| `suggest_base_image` | Suggest the best base Docker image for a given language and use case. |

## Installation

```bash
pip install meok-dockerfile-generator-ai-mcp
```

## Usage with Claude Desktop

Add to your Claude Desktop MCP config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "dockerfile-generator-ai": {
      "command": "python",
      "args": ["-m", "meok_dockerfile_generator_ai_mcp.server"]
    }
  }
}
```

## Usage with FastMCP

```python
from mcp.server.fastmcp import FastMCP

# This server exposes 4 tool(s) via MCP
# See server.py for full implementation
```

## License

MIT © [MEOK AI Labs](https://meok.ai)
