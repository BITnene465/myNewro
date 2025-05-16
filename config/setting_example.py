"""
项目配置文件(example)
"""
import logging
import torch.cuda
from pathlib import Path

# 项目相关设置
PROJECT_NAME = "Newro"
PROJECT_VERSION = "0.1.0"
PROJECT_ROOT = Path(__file__).parent.parent  # 项目根目录(settings.py路径不更改的情况下)

# WebSocket 服务器配置
WEBSOCKET_HOST = "localhost"
WEBSOCKET_PORT = 8765

# 日志配置
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

#  服务配置

## 语音识别服务配置
STT_MODEL_TYPE = "whisper"  # 可选值: "whisper", "wav2vec"

if STT_MODEL_TYPE == "whisper":
    STT_SERVICE_NAME = "WhisperSTT"
    STT_SERVICE = {
        "model_size": "medium",  # 可选值: "tiny", "base", "small", "medium", "large"
        "language": "zh",  # 语言代码，"zh"表示中文
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        }

elif STT_MODEL_TYPE == "wav2vec":
    STT_SERVICE_NAME = "Wav2vecSTT"
    STT_SERVICE = {
        "model_name": "jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn",
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "local_models_path": Path(__file__).parent.parent / "models"
        }

## TTS 服务配置
TTS_MODEL_TYPE = "gpt_sovits"  # 可选值: "gpt_sovits", "fish speech"

if TTS_MODEL_TYPE == "gpt_sovits":
    TTS_SERVICE_NAME = "GPTsoVITS"
    TTS_SERVICE ={
        "api_base_url": "http://localhost:9880",  # 确保GPTsoVITS服务正在运行
        "speed": 1.0,
        "audio_format": "wav",
        "ref_audio_path": "G:\\GPT-SoVITS-DockerTest\\SoVITS_weights\\ref_audio\\dxl1.wav",  # 默认参考音频路径
        "prompt_text": "你好，这里是我的频道，欢迎大家来和我聊天！",  # 默认提示文本
        "prompt_language": "zh", 
        "text_language": "zh",
        "top_k": 20,
        "top_p": 0.9,
        "temperature": 0.9,
        "text_split_method": "cut0",  # 文本分割方法，详情参考 GPTsoVITS 文档 
        }

elif TTS_MODEL_TYPE == "fish speech":
    TTS_SERVICE_NAME = "FishSpeech TTS"
    TTS_SERVICE = {}


# ## 唇形同步服务配置
# LIPSYNC_SERVICE_NAME = "Lipsync"
# LIPSYNC_SERVICE = {
#     "model_path": PROJECT_ROOT / "models" / "xxx.pth"   # 占位符
# }

## llm 服务配置
SYSTEM_PROMPT = ""
try:
    with open(PROJECT_ROOT / "config" / "system_prompt.txt", "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read().strip()  # 读取系统提示词
except FileNotFoundError:
    print("系统提示词文件未找到，使用默认值。")
except Exception as e:
    print(f"读取系统提示词时发生错误: {e}")

LLM_MODEL_TYPE = "openai_like"   # 可选值: "openai_like", "local", "ollama"

if LLM_MODEL_TYPE == "openai_like":
    LLM_SERVICE_NAME = "DeepSeek"  # 根据模型商来自行设置
    LLM_SERVICE = {
        "api_base_url": "https://api.deepseek.com/v1",
        "api_key": "your-api-key", 
        "model": "deepseek-chat",
        "temperature": 0.9,
        "max_tokens": 60,
        "system_prompt": SYSTEM_PROMPT,
        "top_p": 0.9,
        "stream": False
    }
    
elif LLM_MODEL_TYPE == "local":
    LLM_SERVICE_NAME = "Llama2" # 根据模型商来自行设置
    LLM_SERVICE = {
        "model_path": PROJECT_ROOT / "models" / "llama2-7b-chat.gguf",
        "system_prompt": SYSTEM_PROMPT,
        "temperature": 0.7,
        "max_tokens": 100,
        "top_p": 0.9,
        "stream": False
    }
    
elif LLM_MODEL_TYPE == "ollama":
    LLM_SERVICE_NAME = "Ollama" # 根据模型商来自行设置
    LLM_SERVICE = {}
