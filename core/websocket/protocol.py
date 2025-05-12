"""
WebSocket 消息协议定义
"""
import json
from enum import Enum
from typing import Dict, Any, Optional

class MessageType(Enum):
    """消息类型枚举"""
    # 一般是输入
    AUDIO_INPUT = "audio_input"          # 客户端发送的音频数据
    TEXT_INPUT = "text_input"            # 客户端发送的文本数据 
    MIXED_INPUT = "mixed_input"          # 客户端发送的混合输入 (文本+图像 或 音频+图像)
    
    # 一般是输出
    AI_RESPONSE = "ai_response"         # 后端生成的回复： 文本 + 音频 + 唇形同步 + 情感分类（对应动作）

    # 系统消息
    SYSTEM_STATUS = "system_status"      # 系统状态消息
    ERROR = "error"                      # 错误消息
    
    
def create_message(msg_type: MessageType, payload: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None) -> str:
    """
    创建标准格式的WebSocket消息。

    Args:
        msg_type: 消息类型 (MessageType枚举)。
        payload: 消息内容。
        request_id: 可选的请求ID，用于跟踪请求响应。

    Returns:
        JSON格式的消息字符串。
    """
    message = {
        "type": msg_type.value,
        "payload": payload if payload is not None else {},
    }
    if request_id is not None:
        message["request_id"] = request_id
    return json.dumps(message)

def parse_message(message_str: str) -> Dict[str, Any]:
    """
    解析JSON格式的WebSocket消息。

    Args:
        message_str: JSON消息字符串。

    Returns:
        解析后的消息字典。
    
    Raises:
        ValueError: 如果消息不是有效的JSON。
    """
    try:
        return json.loads(message_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON message: {e}")
    
