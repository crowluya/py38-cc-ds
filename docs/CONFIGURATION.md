# Claude Code Python MVP - 配置指南

本文档详细说明 Claude Code Python MVP 的配置选项。

## 目录

- [环境变量](#环境变量)
- [配置文件](#配置文件)
- [DeepSeek 配置](#deepseek-配置)
- [权限配置](#权限配置)
- [Windows 7 配置](#windows-7-配置)
- [内网部署配置](#内网部署配置)

---

## 环境变量

### 快速开始

1. 复制示例配置文件：
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，填入你的配置

### 环境变量列表

| 变量名 | 必需 | 默认值 | 说明 |
|--------|------|--------|------|
| `DEEPSEEK_API_KEY` | ✅ | - | DeepSeek API 密钥 |
| `DEEPSEEK_BASE_URL` | ❌ | `https://api.deepseek.com/v1` | API 端点 |
| `DEEPSEEK_MODEL` | ❌ | `deepseek-chat` | 默认模型 |
| `LOG_LEVEL` | ❌ | `INFO` | 日志级别 |
| `DEFAULT_PERMISSION_MODE` | ❌ | `ask` | 权限策略 |
| `VERIFY_SSL` | ❌ | `true` | SSL 证书验证 |

---

## 配置文件

### 配置优先级

配置按以下优先级加载（高到低）：

1. **CLI 参数** - 最高优先级
2. `.pycc/settings.local.json` - 项目本地配置
3. `.pycc/settings.json` - 项目共享配置
4. `~/.pycc/settings.json` - 用户全局配置

说明：本仓库的 `.claude/` 目录用于外部工具（例如 Claude Code IDE 集成）的配置，不由本 Python 项目读取。

### 配置文件结构

```json
{
  "llm": {
    "api_key": "sk-xxx",
    "base_url": "https://api.deepseek.com/v1",
    "model": "deepseek-chat",
    "timeout": 120,
    "max_tokens": 4096,
    "temperature": 0.7
  },
  "permissions": {
    "default_mode": "ask",
    "file_read": "ask",
    "file_write": "ask",
    "command": "ask",
    "network": "deny"
  },
  "hooks": {
    "enabled": true,
    "directory": ".pycc/hooks"
  },
  "output": {
    "format": "text",
    "stream": true
  }
}
```

---

## DeepSeek 配置

### 获取 API 密钥

1. 访问 [DeepSeek 开放平台](https://platform.deepseek.com/)
2. 注册并登录
3. 进入 API Keys 页面
4. 创建新的 API 密钥

### 基础配置

#### 方式一：环境变量（推荐）

```bash
export DEEPSEEK_API_KEY="sk-your-api-key"
export DEEPSEEK_BASE_URL="https://api.deepseek.com/v1"
```

#### 方式二：配置文件

创建 `~/.pycc/settings.json`：

```json
{
  "llm": {
    "api_key": "sk-your-api-key",
    "base_url": "https://api.deepseek.com/v1",
    "model": "deepseek-chat"
  }
}
```

### 模型选择

| 模型 | 说明 | 上下文 |
|------|------|--------|
| `deepseek-chat` | 通用对话模型 | 16K |
| `deepseek-coder` | 代码专用模型 | 16K |

---

## 权限配置

### 权限模式

| 模式 | 说明 |
|------|------|
| `dontAsk` | 自动允许所有操作 |
| `ask` | 危险操作需要确认 |
| `deny` | 拒绝所有危险操作 |

### 权限规则

在 `.pycc/settings.json` 中配置权限规则：

```json
{
  "permissions": {
    "default_mode": "ask",
    "rules": [
      {
        "domain": "file_read",
        "action": "allow",
        "pattern": "*.py"
      },
      {
        "domain": "file_write",
        "action": "deny",
        "pattern": "*.py"
      },
      {
        "domain": "command",
        "action": "allow",
        "pattern": "git *"
      },
      {
        "domain": "command",
        "action": "ask",
        "pattern": "rm *"
      }
    ]
  }
}
```

---

## Windows 7 配置

### PowerShell 2.0 支持

Windows 7 默认使用 PowerShell 2.0，需要以下配置：

```json
{
  "executor": {
    "shell": "powershell.exe",
    "args": ["-ExecutionPolicy", "Bypass", "-Command"]
  }
}
```

### 路径处理

Claude Code 使用 `pathlib.Path` 处理路径，自动适配：

```python
# Windows 7
C:\Users\Username\project\file.py

# Unix
/home/username/project/file.py
```

### 编码设置

确保所有文件操作使用 UTF-8 编码：

```bash
# Windows 7 控制台
chcp 65001
```

---

## 内网部署配置

### 自定义 API 端点

如果使用内网部署的 DeepSeek 模型：

```bash
# 环境变量
export DEEPSEEK_BASE_URL="http://internal-api.company.com:8080/v1"
```

或通过配置文件：

```json
{
  "llm": {
    "base_url": "http://internal-api.company.com:8080/v1",
    "verify_ssl": false,
    "ca_cert_path": "/path/to/company-ca.crt"
  }
}
```

### 离线安装

在有网络的环境中下载依赖：

```bash
pip download -r requirements.txt -d wheels/
```

在目标环境中安装：

```bash
pip install --no-index --find-links=wheels/ -r requirements.txt
```

### 代理配置

如需通过代理访问：

```bash
export HTTP_PROXY="http://proxy.company.com:8080"
export HTTPS_PROXY="http://proxy.company.com:8080"
```

---

## 故障排查

### API 连接失败

```bash
# 检查 API 密钥
echo $DEEPSEEK_API_KEY

# 测试连接
curl -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  https://api.deepseek.com/v1/models
```

### PowerShell 权限错误

```powershell
# 设置执行策略
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 编码问题

```python
# 确保文件读取时指定编码
with open("file.txt", "r", encoding="utf-8") as f:
    content = f.read()
```
