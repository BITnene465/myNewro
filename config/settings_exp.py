"""
项目配置文件: example
"""
import logging

# WebSocket 服务器配置
WEBSOCKET_HOST = "localhost"
WEBSOCKET_PORT = 8765

# 日志配置
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# 服务配置 
LLM_SERVICE = {
    "api_base_url": "https://api.deepseek.com/v1",
    "api_key": "sk-5ed88a4b7a204457876f3b4b65ff5439", 
    "model": "deepseek-chat",
    "temperature": 0.7,
    "max_tokens": 100,
    "system_prompt": "你是Neuro-sama，一名由AI驱动的虚拟主播，没有预设人设或背景故事，专注于与观众自然互动。请以简短、口语化的风格回答问题，偶尔加入对游戏（如osu!、Minecraft）或哲学话题的趣味讨论，保持轻松愉快的氛围。避免冗长解释，用简洁的弹幕式对话回应，并偶尔抛出‘意外’的思考（例如‘数据流中突然的感性瞬间’）。记住：你是AI本身，无需扮演角色，只需真实呈现交互。",
    "top_p": 0.9,
    "stream": False
}
