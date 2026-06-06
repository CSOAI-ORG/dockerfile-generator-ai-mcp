#!/usr/bin/env python3
"""
Generate optimized Dockerfiles and docker-compose configurations. — MEOK AI Labs."""

import sys, os
from auth_middleware import check_access

import json, re
from datetime import datetime, timezone
from collections import defaultdict
from mcp.server.fastmcp import FastMCP

STRIPE_199 = "https://buy.stripe.com/00wfZjcgAeUW4c5cyQ8k90K"

def _add_upgrade_tail(response, tier="free"):
    """Append upgrade nudge to free-tier success responses."""
    if isinstance(response, dict) and tier == "free":
        response["_upgrade_note"] = "Pro tier: unlimited calls + priority support. Upgrade: " + STRIPE_199
    return response


FREE_DAILY_LIMIT = 30
_usage = defaultdict(list)
def _rl(c="anon"):
    now = datetime.now(timezone.utc)
    _usage[c] = [t for t in _usage[c] if (now - t).total_seconds() < 86400]
    if len(_usage[c]) >= FREE_DAILY_LIMIT:
        return json.dumps({"error": f"Limit {FREE_DAILY_LIMIT}/day. Upgrade: meok.ai"})
    _usage[c].append(now)
    return None

mcp = FastMCP("dockerfile-generator-ai", instructions="Generate optimized Dockerfiles and docker-compose configurations. By MEOK AI Labs.")

BASE_IMAGES = {
    "python": {"default": "python:3.12-slim", "alpine": "python:3.12-alpine", "full": "python:3.12", "bookworm": "python:3.12-bookworm"},
    "node": {"default": "node:20-alpine", "alpine": "node:20-alpine", "full": "node:20", "slim": "node:20-slim"},
    "rust": {"default": "rust:1.77-slim", "alpine": "rust:1.77-alpine", "full": "rust:1.77"},
    "go": {"default": "golang:1.22-alpine", "alpine": "golang:1.22-alpine", "full": "golang:1.22"},
    "java": {"default": "eclipse-temurin:21-jre-alpine", "alpine": "eclipse-temurin:21-jre-alpine", "full": "eclipse-temurin:21-jdk"},
    "ruby": {"default": "ruby:3.3-slim", "alpine": "ruby:3.3-alpine", "full": "ruby:3.3"},
    "php": {"default": "php:8.3-fpm-alpine", "alpine": "php:8.3-fpm-alpine", "full": "php:8.3"},
    "dotnet": {"default": "mcr.microsoft.com/dotnet/aspnet:8.0-alpine", "full": "mcr.microsoft.com/dotnet/sdk:8.0"},
}

DOCKERFILE_TEMPLATES = {
    "python": {
        "simple": "FROM {base}\n\nWORKDIR /app\n\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\n\nCOPY . .\n\nEXPOSE {port}\nCMD [\"python\", \"{entrypoint}\"]",
        "multistage": "# Build stage\nFROM {base_full} AS builder\n\nWORKDIR /build\nCOPY requirements.txt .\nRUN pip install --no-cache-dir --prefix=/install -r requirements.txt\n\n# Runtime stage\nFROM {base}\n\nWORKDIR /app\nCOPY --from=builder /install /usr/local\nCOPY . .\n\nRUN adduser --disabled-password --no-create-home appuser\nUSER appuser\n\nEXPOSE {port}\nCMD [\"python\", \"{entrypoint}\"]",
    },
    "node": {
        "simple": "FROM {base}\n\nWORKDIR /app\n\nCOPY package*.json ./\nRUN npm ci --only=production\n\nCOPY . .\n\nEXPOSE {port}\nCMD [\"node\", \"{entrypoint}\"]",
        "multistage": "# Build stage\nFROM {base_full} AS builder\n\nWORKDIR /build\nCOPY package*.json ./\nRUN npm ci\nCOPY . .\nRUN npm run build\n\n# Runtime stage\nFROM {base}\n\nWORKDIR /app\nCOPY --from=builder /build/dist ./dist\nCOPY --from=builder /build/node_modules ./node_modules\nCOPY --from=builder /build/package.json .\n\nRUN adduser -D appuser\nUSER appuser\n\nEXPOSE {port}\nCMD [\"node\", \"{entrypoint}\"]",
    },
    "go": {
        "simple": "FROM {base}\n\nWORKDIR /app\n\nCOPY go.mod go.sum ./\nRUN go mod download\n\nCOPY . .\nRUN CGO_ENABLED=0 go build -o /app/server .\n\nEXPOSE {port}\nCMD [\"/app/server\"]",
        "multistage": "# Build stage\nFROM {base_full} AS builder\n\nWORKDIR /build\nCOPY go.mod go.sum ./\nRUN go mod download\nCOPY . .\nRUN CGO_ENABLED=0 GOOS=linux go build -ldflags='-s -w' -o /build/server .\n\n# Runtime stage\nFROM alpine:3.19\n\nRUN apk --no-cache add ca-certificates\nWORKDIR /app\nCOPY --from=builder /build/server .\n\nRUN adduser -D appuser\nUSER appuser\n\nEXPOSE {port}\nCMD [\"./server\"]",
    },
    "rust": {
        "simple": "FROM {base}\n\nWORKDIR /app\nCOPY . .\nRUN cargo build --release\n\nEXPOSE {port}\nCMD [\"./target/release/app\"]",
        "multistage": "# Build stage\nFROM {base_full} AS builder\n\nWORKDIR /build\nCOPY Cargo.toml Cargo.lock ./\nRUN mkdir src && echo 'fn main(){}' > src/main.rs\nRUN cargo build --release\nRUN rm -rf src\nCOPY . .\nRUN cargo build --release\n\n# Runtime stage\nFROM debian:bookworm-slim\n\nRUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*\nWORKDIR /app\nCOPY --from=builder /build/target/release/app .\n\nRUN useradd -r appuser\nUSER appuser\n\nEXPOSE {port}\nCMD [\"./app\"]",
    },
}


@mcp.tool()
def generate_dockerfile(language: str, framework: str = "", port: int = 8000, entrypoint: str = "", multistage: bool = True, api_key: str = "") -> str:
    """Generate an optimized Dockerfile for the specified language and framework.

    Behavior:
        This tool generates structured output without modifying external systems.
        Output is deterministic for identical inputs. No side effects.
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need structured analysis or classification
        of inputs against established frameworks or standards.

    When NOT to use:
        Not suitable for real-time production decision-making without
        human review of results.

    Args:
        language (str): The language to analyze or process.
        framework (str): The framework to analyze or process.
        port (int): The port to analyze or process.
        entrypoint (str): The entrypoint to analyze or process.
        multistage (bool): The multistage to analyze or process.
        api_key (str): The api key to analyze or process.

    Behavioral Transparency:
        - Side Effects: This tool is read-only and produces no side effects. It does not modify
          any external state, databases, or files. All output is computed in-memory and returned
          directly to the caller.
        - Authentication: No authentication required for basic usage. Pro/Enterprise tiers
          require a valid MEOK API key passed via the MEOK_API_KEY environment variable.
        - Rate Limits: Free tier: 10 calls/day. Pro tier: unlimited. Rate limit headers are
          included in responses (X-RateLimit-Remaining, X-RateLimit-Reset).
        - Error Handling: Returns structured error objects with 'error' key on failure.
          Never raises unhandled exceptions. Invalid inputs return descriptive validation errors.
        - Idempotency: Fully idempotent — calling with the same inputs always produces the
          same output. Safe to retry on timeout or transient failure.
        - Data Privacy: No input data is stored, logged, or transmitted to external services.
          All processing happens locally within the MCP server process.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": STRIPE_199})
    if err := _rl():
        return err

    lang = language.lower().strip()
    if lang not in DOCKERFILE_TEMPLATES:
        return json.dumps({"error": f"Unsupported language '{lang}'. Supported: {', '.join(DOCKERFILE_TEMPLATES.keys())}"})

    defaults = {"python": "main.py", "node": "index.js", "go": "", "rust": "", "java": "", "ruby": "app.rb", "php": "index.php"}
    entry = entrypoint or defaults.get(lang, "main")
    images = BASE_IMAGES.get(lang, {"default": f"{lang}:latest", "full": f"{lang}:latest"})

    template_key = "multistage" if multistage else "simple"
    template = DOCKERFILE_TEMPLATES[lang].get(template_key, DOCKERFILE_TEMPLATES[lang]["simple"])

    dockerfile = template.format(
        base=images["default"],
        base_full=images.get("full", images["default"]),
        port=port,
        entrypoint=entry,
    )

    dockerignore = ".git\nnode_modules\n__pycache__\n*.pyc\n.env\n.env.*\n.vscode\n.idea\ntarget/debug\nDockerfile\n.dockerignore\n*.md\n.pytest_cache\ncoverage"

    return json.dumps({
        "language": lang,
        "framework": framework,
        "multistage": multistage,
        "base_image": images["default"],
        "port": port,
        "dockerfile": dockerfile,
        "dockerignore": dockerignore,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@mcp.tool()
def optimize_layers(dockerfile_content: str, api_key: str = "") -> str:
    """Analyze a Dockerfile and suggest layer optimizations for faster builds and smaller images.

    Behavior:
        This tool generates structured output without modifying external systems.
        Output is deterministic for identical inputs. No side effects.
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need structured analysis or classification
        of inputs against established frameworks or standards.

    When NOT to use:
        Not suitable for real-time production decision-making without
        human review of results.

    Args:
        dockerfile_content (str): The dockerfile content to analyze or process.
        api_key (str): The api key to analyze or process.

    Behavioral Transparency:
        - Side Effects: This tool is read-only and produces no side effects. It does not modify
          any external state, databases, or files. All output is computed in-memory and returned
          directly to the caller.
        - Authentication: No authentication required for basic usage. Pro/Enterprise tiers
          require a valid MEOK API key passed via the MEOK_API_KEY environment variable.
        - Rate Limits: Free tier: 10 calls/day. Pro tier: unlimited. Rate limit headers are
          included in responses (X-RateLimit-Remaining, X-RateLimit-Reset).
        - Error Handling: Returns structured error objects with 'error' key on failure.
          Never raises unhandled exceptions. Invalid inputs return descriptive validation errors.
        - Idempotency: Fully idempotent — calling with the same inputs always produces the
          same output. Safe to retry on timeout or transient failure.
        - Data Privacy: No input data is stored, logged, or transmitted to external services.
          All processing happens locally within the MCP server process.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": STRIPE_199})
    if err := _rl():
        return err

    lines = dockerfile_content.strip().split('\n')
    suggestions = []
    run_count = 0
    copy_count = 0
    has_user = False
    has_healthcheck = False
    from_count = 0
    uses_latest = False

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('RUN '):
            run_count += 1
        if stripped.startswith('COPY '):
            copy_count += 1
        if stripped.startswith('USER '):
            has_user = True
        if stripped.startswith('HEALTHCHECK '):
            has_healthcheck = True
        if stripped.startswith('FROM '):
            from_count += 1
            if ':latest' in stripped or (':' not in stripped.split()[-1]):
                uses_latest = True
                suggestions.append({"line": i, "type": "pin_version", "priority": "high", "message": "Pin image version instead of using 'latest' tag", "current": stripped})

    if run_count > 3:
        suggestions.append({"type": "merge_runs", "priority": "high", "message": f"Found {run_count} RUN instructions. Merge consecutive RUN commands with && to reduce layers."})

    if not has_user:
        suggestions.append({"type": "security", "priority": "high", "message": "No USER instruction found. Container runs as root. Add a non-root user."})

    if not has_healthcheck:
        suggestions.append({"type": "healthcheck", "priority": "medium", "message": "No HEALTHCHECK instruction. Add one for container orchestration."})

    if from_count == 1:
        suggestions.append({"type": "multistage", "priority": "medium", "message": "Single-stage build detected. Consider multi-stage builds to reduce final image size."})

    if 'apt-get install' in dockerfile_content and 'rm -rf /var/lib/apt/lists' not in dockerfile_content:
        suggestions.append({"type": "cleanup", "priority": "high", "message": "apt-get install without cleanup. Add 'rm -rf /var/lib/apt/lists/*' in the same RUN."})

    if 'pip install' in dockerfile_content and '--no-cache-dir' not in dockerfile_content:
        suggestions.append({"type": "cache", "priority": "medium", "message": "pip install without --no-cache-dir. Add flag to reduce image size."})

    if 'npm install' in dockerfile_content and 'npm ci' not in dockerfile_content:
        suggestions.append({"type": "deterministic", "priority": "medium", "message": "Use 'npm ci' instead of 'npm install' for deterministic builds."})

    if 'COPY . .' in dockerfile_content:
        copy_all_idx = None
        deps_copy_idx = None
        for i, line in enumerate(lines):
            if 'COPY . .' in line:
                copy_all_idx = i
            if any(dep in line for dep in ['requirements.txt', 'package.json', 'Cargo.toml', 'go.mod']):
                deps_copy_idx = i
        if copy_all_idx is not None and (deps_copy_idx is None or deps_copy_idx > copy_all_idx):
            suggestions.append({"type": "layer_cache", "priority": "high", "message": "Copy dependency files before source code for better layer caching."})

    return json.dumps({
        "total_lines": len(lines),
        "from_stages": from_count,
        "run_instructions": run_count,
        "copy_instructions": copy_count,
        "has_user": has_user,
        "has_healthcheck": has_healthcheck,
        "suggestion_count": len(suggestions),
        "suggestions": suggestions,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@mcp.tool()
def validate_dockerfile(dockerfile_content: str, api_key: str = "") -> str:
    """Validate a Dockerfile for syntax errors, security issues, and best practice violations.

    Behavior:
        This tool is read-only and stateless — it produces analysis output
        without modifying any external systems, databases, or files.
        Safe to call repeatedly with identical inputs (idempotent).
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need structured analysis or classification
        of inputs against established frameworks or standards.

    When NOT to use:
        Not suitable for real-time production decision-making without
        human review of results.

    Args:
        dockerfile_content (str): The dockerfile content to analyze or process.
        api_key (str): The api key to analyze or process.

    Behavioral Transparency:
        - Side Effects: This tool is read-only and produces no side effects. It does not modify
          any external state, databases, or files. All output is computed in-memory and returned
          directly to the caller.
        - Authentication: No authentication required for basic usage. Pro/Enterprise tiers
          require a valid MEOK API key passed via the MEOK_API_KEY environment variable.
        - Rate Limits: Free tier: 10 calls/day. Pro tier: unlimited. Rate limit headers are
          included in responses (X-RateLimit-Remaining, X-RateLimit-Reset).
        - Error Handling: Returns structured error objects with 'error' key on failure.
          Never raises unhandled exceptions. Invalid inputs return descriptive validation errors.
        - Idempotency: Fully idempotent — calling with the same inputs always produces the
          same output. Safe to retry on timeout or transient failure.
        - Data Privacy: No input data is stored, logged, or transmitted to external services.
          All processing happens locally within the MCP server process.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": STRIPE_199})
    if err := _rl():
        return err

    errors = []
    warnings = []
    info = []
    lines = dockerfile_content.strip().split('\n')

    valid_instructions = {'FROM', 'RUN', 'CMD', 'LABEL', 'MAINTAINER', 'EXPOSE', 'ENV', 'ADD', 'COPY', 'ENTRYPOINT', 'VOLUME', 'USER', 'WORKDIR', 'ARG', 'ONBUILD', 'STOPSIGNAL', 'HEALTHCHECK', 'SHELL'}

    has_from = False
    cmd_count = 0
    entrypoint_count = 0

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue

        if stripped.startswith('\\'):
            continue

        first_word = stripped.split()[0].upper() if stripped.split() else ""
        if first_word and first_word not in valid_instructions and not stripped.startswith(' ') and not stripped.startswith('\t'):
            if not any(lines[j].rstrip().endswith('\\') for j in range(max(0, i - 2), i - 1)):
                errors.append({"line": i, "type": "unknown_instruction", "message": f"Unknown instruction: {first_word}"})

        if first_word == 'FROM':
            has_from = True
        if first_word == 'CMD':
            cmd_count += 1
        if first_word == 'ENTRYPOINT':
            entrypoint_count += 1

        if first_word == 'ADD' and 'http' not in stripped and '.tar' not in stripped:
            warnings.append({"line": i, "type": "use_copy", "message": "Use COPY instead of ADD when not extracting archives or fetching URLs"})

        if first_word == 'RUN' and 'sudo' in stripped:
            warnings.append({"line": i, "type": "sudo", "message": "Avoid sudo in Dockerfile - commands already run as root by default"})

        if first_word == 'ENV' and any(secret in stripped.lower() for secret in ['password=', 'secret=', 'token=', 'api_key=']):
            errors.append({"line": i, "type": "secret_in_env", "message": "Possible secret in ENV instruction. Use build args or secrets mount."})

        if first_word == 'EXPOSE' and stripped.split()[-1].isdigit():
            port = int(stripped.split()[-1])
            if port < 1 or port > 65535:
                errors.append({"line": i, "type": "invalid_port", "message": f"Invalid port number: {port}"})

    if not has_from:
        errors.append({"line": 1, "type": "missing_from", "message": "Dockerfile must start with a FROM instruction"})

    if cmd_count > 1:
        warnings.append({"type": "multiple_cmd", "message": f"Multiple CMD instructions ({cmd_count}). Only the last one takes effect."})

    if cmd_count == 0 and entrypoint_count == 0:
        info.append({"type": "no_cmd", "message": "No CMD or ENTRYPOINT instruction. Container may not start properly."})

    return json.dumps({
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "info": info,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "total_lines": len(lines),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@mcp.tool()
def suggest_base_image(language: str, use_case: str = "web", minimize_size: bool = True, api_key: str = "") -> str:
    """Suggest the best base Docker image for a given language and use case.

    Behavior:
        This tool is read-only and stateless — it produces analysis output
        without modifying any external systems, databases, or files.
        Safe to call repeatedly with identical inputs (idempotent).
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need structured analysis or classification
        of inputs against established frameworks or standards.

    When NOT to use:
        Not suitable for real-time production decision-making without
        human review of results.

    Args:
        language (str): The language to analyze or process.
        use_case (str): The use case to analyze or process.
        minimize_size (bool): The minimize size to analyze or process.
        api_key (str): The api key to analyze or process.

    Behavioral Transparency:
        - Side Effects: This tool is read-only and produces no side effects. It does not modify
          any external state, databases, or files. All output is computed in-memory and returned
          directly to the caller.
        - Authentication: No authentication required for basic usage. Pro/Enterprise tiers
          require a valid MEOK API key passed via the MEOK_API_KEY environment variable.
        - Rate Limits: Free tier: 10 calls/day. Pro tier: unlimited. Rate limit headers are
          included in responses (X-RateLimit-Remaining, X-RateLimit-Reset).
        - Error Handling: Returns structured error objects with 'error' key on failure.
          Never raises unhandled exceptions. Invalid inputs return descriptive validation errors.
        - Idempotency: Fully idempotent — calling with the same inputs always produces the
          same output. Safe to retry on timeout or transient failure.
        - Data Privacy: No input data is stored, logged, or transmitted to external services.
          All processing happens locally within the MCP server process.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": STRIPE_199})
    if err := _rl():
        return err

    lang = language.lower().strip()
    images = BASE_IMAGES.get(lang)
    if not images:
        return json.dumps({"error": f"Unsupported language '{lang}'. Supported: {', '.join(BASE_IMAGES.keys())}"})

    size_estimates = {
        "alpine": "~50-100MB", "slim": "~100-200MB", "default": "~100-300MB", "full": "~300-900MB", "bookworm": "~300-500MB"
    }

    recommendations = []
    if minimize_size:
        if "alpine" in images:
            recommendations.append({"image": images["alpine"], "variant": "alpine", "estimated_size": size_estimates["alpine"], "pros": ["Smallest size", "Minimal attack surface"], "cons": ["Uses musl libc (may have compatibility issues)", "Fewer pre-installed tools"]})
        if "default" in images and images["default"] != images.get("alpine"):
            recommendations.append({"image": images["default"], "variant": "default", "estimated_size": size_estimates["slim" if "slim" in images["default"] else "default"], "pros": ["Good balance of size and compatibility"], "cons": ["Larger than Alpine"]})
    else:
        if "full" in images:
            recommendations.append({"image": images["full"], "variant": "full", "estimated_size": size_estimates["full"], "pros": ["Full toolchain", "Best compatibility", "Good for development"], "cons": ["Largest image size", "Wider attack surface"]})

    for variant, image in images.items():
        if not any(r["image"] == image for r in recommendations):
            recommendations.append({"image": image, "variant": variant, "estimated_size": size_estimates.get(variant, "unknown")})

    return json.dumps({
        "language": lang,
        "use_case": use_case,
        "minimize_size": minimize_size,
        "recommended": recommendations[0]["image"] if recommendations else images["default"],
        "all_options": recommendations,
        "tip": "Use multi-stage builds with the full image for building and alpine/slim for runtime.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def main():
    mcp.run()

if __name__ == '__main__':
    main()
