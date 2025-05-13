# Newro AI 虚拟主播系统

Newro是一个基于WebSocket的AI虚拟主播系统，支持文本和语音双向交互，能够实时生成文本和语音回复。

## 功能特点

- 💬 文本交互：接收文本输入并生成AI回复
- 🎤 语音识别：接收音频输入并转换为文本
- 🔊 语音合成：将AI回复转换为自然语音
- 🧠 上下文记忆：基于会话ID保持对话连贯性
- 🔄 实时通信：使用WebSocket实现低延迟交互

## 快速开始

### 环境要求

- Python 3.10
- 必要的依赖包（见requirements.txt）

### 安装步骤

1. 克隆项目代码
```bash
git clone [项目仓库地址]
cd newroBackend
```

2. 安装依赖
```bash
pip install -r requirements.txt
```
3. 调整设置，见 config/settings_example.py 文件，仿照格式设置 settings.py 并且放置于config目录下

4. 启动后端服务
```bash
python main.py
```

### 简单测试
测试服务是否正常运行
```bash
python demo.py
```

使用命令行工具直接与虚拟主播交互：
```bash
python demo2.py
```

## 项目结构

newroBackend/
├── config/               # 配置文件
│   ├── settings.py       # 项目配置
│   └── settings_example.py # 示例配置
├── core/                 # 核心功能
│   ├── websocket/        # WebSocket通信协议和处理器
│   └── message/          # 消息处理
├── services/             # 服务实现
│   ├── llm/              # 大语言模型服务
│   ├── tts/              # 语音合成服务
│   ├── stt/              # 语音识别服务
│   └── base.py           # 服务基类
├── tests/                # 测试代码（都是独立运行的单元测试脚本）
│   └── test_data/        # 测试数据
├── utils/                # 实用工具
│   └── helpers.py        # 辅助函数
├── README.md             # 项目说明
├── LICENSE               # 许可证
├── requirements.txt      # 依赖包
├── main.py               # 主程序入口
├── demo.py               # 演示脚本
└── demo2.py              # 命令行交互演示


## 文档

- [API文档](API.md)
- [前端集成指南](FRONTEND_INTEGRATION.md) (coming soon)

## 许可证

本项目采用MIT许可证。详见[LICENSE](LICENSE)文件。


## todo
- [x] 支持多客户端并发的 websocket 服务器
- [x] 添加 whisper 作为基础 stt 服务 
- [x] 适配 GPTsoVITS api_v2 提供基础 tts 服务
- [x] 适配 openai api 作为基础 llm 服务
- [ ] 实现 live2d 的口型同步算法 
- [ ] 实现简单的RAG
- [ ] 添加自定义大（小）模型的服务端API，使用 fastAPI 构建
- [ ] 支持多语言交互
- [ ] 添加更多语音模型选择
- [ ] 增加更加详细错误处理和恢复机制
