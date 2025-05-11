# Newro AI 虚拟主播后端服务

这是一个基于Python的AI虚拟主播后端服务系统，提供语音识别(STT)、大语言模型(LLM)对话、文本转语音(TTS)及唇形同步等功能，可用于创建交互式AI虚拟主播或数字人应用。

## 项目架构

```
newroBackend/
├── config/              # 配置文件目录
│   ├── settings.py      # 主配置文件
│   └── system_prompt.txt# LLM系统提示词
├── core/                # 核心功能模块
│   ├── broker.py        # 服务协调器
│   └── websocket/       # WebSocket服务器
│       ├── protocol.py  # 通信协议定义
│       └── server.py    # WebSocket服务器实现
├── models/              # 本地模型文件
│   └── wav2vec2-large-xlsr-53-chinese-zh-cn/  # 语音识别模型
├── services/            # 服务模块
│   ├── base.py          # 服务基类
│   ├── llm.py           # 大语言模型服务
│   ├── stt.py           # 语音识别服务
│   ├── tts.py           # 语音合成服务
│   └── lips.py          # 唇形同步服务
├── tests/               # 测试模块
│   ├── test_llm.py      # LLM服务测试
│   ├── test_stt.py      # STT服务测试
│   └── test_tts.py      # TTS服务测试
└── main.py              # 主程序入口
```

## 主要功能

### 1. 语音识别服务 (STT)

使用Hugging Face的Wav2Vec2模型进行中文语音识别，支持本地模型加载与推理。

- 模型：`jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn`
- 支持音频文件和字节流输入
- 自动采样率转换

### 2. 大语言模型服务 (LLM)

基于DeepSeek API的大语言模型服务，支持对话生成和流式输出。

- 使用OpenAI兼容接口
- 支持自定义系统提示词
- 可配置温度、最大token数等参数
- 支持普通和流式响应

### 3. 文本转语音服务 (TTS)

基于GPTsoVITS的文本转语音服务，支持自然、情感化的语音合成。

- 支持多种音色
- 可调节语速和情感参数
- 支持WAV、MP3等音频格式输出

### 4. 唇形同步服务

提供语音与唇形动作同步功能，用于虚拟形象动画。

### 5. 服务协调器 (Broker)

管理各服务模块间的通信和协作，提供统一接口。

### 6. WebSocket服务器

提供WebSocket接口，使前端应用能实时与后端交互。

## 安装与配置

### 环境要求

- Python 3.8+
- PyTorch 1.10+
- CUDA 11.3+（推荐GPU加速）

### 依赖安装

```bash
pip install -r requirements.txt
```

### 配置说明

在`config/settings.py`中可以配置各服务参数：

- WebSocket服务器配置（主机、端口）
- LLM服务配置（API密钥、模型等）
- STT服务配置（模型路径、设备等）
- TTS服务配置（API基础URL、合成参数等）

## 运行

启动主服务：

```bash
python main.py
```

## 测试

测试语音识别：

```bash
python tests/test_stt.py
```

测试大语言模型：

```bash
python tests/test_llm.py
```

测试语音合成：

```bash
python tests/test_tts.py
```

## WebSocket API

客户端可通过WebSocket接口发送以下类型的请求：

- `audio_input`: 语音请求
- `text_input`: 纯文本对话请求
- `mixed_input`: 多模态的输入请求

详细协议格式请参考`core/websocket/protocol.py`文件。

## 许可证

[MIT License](LICENSE)
