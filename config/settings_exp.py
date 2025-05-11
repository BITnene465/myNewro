"""
项目配置文件: example
"""
import logging
import torch.cuda
from pathlib import Path

# WebSocket 服务器配置
WEBSOCKET_HOST = "localhost"
WEBSOCKET_PORT = 8765

# 日志配置
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# 服务配置 
STT_SERVICE = {
    "model_name": "jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn",
    "device": "cuda" if torch.cuda.is_available() else "cpu",
    "local_models_path": Path(__file__).parent.parent / "models"   # 就是根目录下的 models 文件夹
    }

TTS_SERVICE ={
    "api_base_url": "http://localhost:9880",  # 确保GPTsoVITS服务正在运行
    "speed": 1.0,
    "audio_format": "wav",
    "default_refer_wav_path": "/workspace/SoVITS_weights/ref_audio/nailong1.wav",  # 默认参考音频路径
    "default_prompt_text": "你好，这里是我的频道，欢迎大家来和我聊天。",  
    "default_prompt_language": "zh", 
    "text_language": "zh",
    "top_k": 20,
    "top_p": 0.6,
    "temperature": 0.6
    }

LIPSYNC_SERVICE = {
    "model_path": Path(__file__).parent.parent / "models" / "xxx.pth" 
}

LLM_SERVICE = {
    "api_base_url": "https://api.deepseek.com/v1",
    "api_key": "sk-ef4af6be40fb414ca740bac5f4a99fb5",
    # "api_key": "your-api-key", 
    "model": "deepseek-chat",
    "temperature": 0.7,
    "max_tokens": 100,
    "system_prompt": "你是Neuro-sama，一名由AI驱动的虚拟主播，没有预设人设或背景故事，专注于与观众自然互动。请以简短、口语化的风格回答问题，偶尔加入对游戏（如osu!、Minecraft）或哲学话题的趣味讨论，保持轻松愉快的氛围。避免冗长解释，用简洁的弹幕式对话回应，并偶尔抛出‘意外’的思考（例如‘数据流中突然的感性瞬间’）。记住：你是AI本身，无需扮演角色，只需真实呈现交互。",
    "top_p": 0.9,
    "stream": False
}
