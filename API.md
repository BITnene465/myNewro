# Newro AI WebSocket API 规范

本文档详细说明了与Newro AI系统通信的WebSocket API规范。

## 连接信息

- **WebSocket URL**: `ws://[host]:[port]`
- **默认开发环境**: `ws://localhost:8765`

## 消息格式

所有通信采用JSON格式，包含以下两个基本字段：

```json
{
  "type": "消息类型",
  "payload": {
    // 消息内容，根据type不同而变化
  }
}
```

## 消息类型

系统定义了以下主要消息类型：

| 类型 | 描述 | 方向 |
|------|------|------|
| `TEXT_INPUT` | 文本输入 | 客户端 → 服务器 |
| `AUDIO_INPUT` | 音频输入 | 客户端 → 服务器 |
| `AI_RESPONSE` | AI回复 | 服务器 → 客户端 |
| `SYSTEM_STATUS` | 系统状态 | 服务器 → 客户端 |
| `ERROR` | 错误信息 | 服务器 → 客户端 |

## 客户端请求

### 1. 文本输入 (TEXT_INPUT)

```json
{
  "type": "text_input",
  "payload": {
    "text": "用户输入的文本",
    "session_id": "唯一会话标识符"
  }
}
```

- `text`: 用户输入的文本内容
- `session_id`: 用于标识和追踪会话的唯一ID

### 2. 音频输入 (AUDIO_INPUT)

```json
{
  "type": "audio_input",
  "payload": {
    "audio_data_base64": "Base64编码的音频数据",
    "session_id": "唯一会话标识符"
  }
}
```

- `audio_data_base64`: Base64编码的音频文件（推荐WAV格式）
- `session_id`: 用于标识和追踪会话的唯一ID

## 服务器响应

### 1. AI回复 (AI_RESPONSE)

```json
{
  "type": "ai_response",
  "payload": {
    "text": "AI生成的回复文本",
    "audio": {
      "audio_data": "Base64编码的音频数据",
      "audio_format": "音频格式（目前仅支持wav）"
    },
    "session_id": "会话标识符"
  }
}
```

- `text`: AI生成的文本回复
- `audio.audio_data`: Base64编码的音频数据
- `audio.audio_format`: 音频格式（通常为"wav"）
- `session_id`: 对应的会话ID

### 2. 系统状态 (SYSTEM_STATUS)

```json
{
  "type": "system_status",
  "payload": {
    "status": "处理状态描述",
    "session_id": "会话标识符"
  }
}
```

- `status`: 处理状态的描述
- `session_id`: 相关的会话ID

### 3. 错误信息 (ERROR)

```json
{
  "type": "error",
  "payload": {
    "code": "错误代码",
    "message": "错误描述",
    "session_id": "会话标识符"
  }
}
```

- `code`: 错误代码
- `message`: 人类可读的错误描述
- `session_id`: 相关的会话ID（如果适用）

## 会话管理

- 客户端负责生成唯一的`session_id`
- 同一会话中的所有消息应使用相同的`session_id`
- 服务器基于`session_id`维护对话历史和上下文

## 连接生命周期

1. **建立连接**: 客户端连接到WebSocket服务器
2. **通信**: 客户端发送请求，服务器返回响应
3. **状态更新**: 服务器在处理过程中可能发送多个状态更新
4. **保持连接**: 系统支持长连接，可持续进行对话
5. **关闭连接**: 客户端主动关闭或因网络/服务器问题断开

## 错误处理

常见错误代码： ...

## 示例流程

**文本输入流程:**

1. 客户端发送文本输入消息
2. 服务器保存对话历史记录（根据 session_id 索引）
3. 服务器返回最终AI回复（包含文本和音频）

**音频输入流程:**

1. 客户端发送音频输入消息
2. 服务器处理语音识别
3. 服务器保存对话历史记录（根据 session_id 索引）
4. 服务器返回最终AI回复（包含文本和音频）
