"""
服务协调器 (Broker)
负责在WebSocket连接和后端服务之间路由和处理消息。
"""
import asyncio
import logging
import base64
from typing import Any, Dict, Callable, Coroutine, Set, Optional
from enum import Enum

from services.base import BaseService
from .websocket.protocol import MessageType, create_message, parse_message

logger = logging.getLogger(__name__)

# 定义回调函数类型，用于将消息发送回WebSocket客户端
# 参数：websocket连接对象，消息内容(str)
SendMessageCallback = Callable[[Any, str], Coroutine[Any, Any, None]]


class ServiceBroker:
    """
    服务协调器，管理AI服务并将它们连接到WebSocket通信。
    """
    def __init__(self,
                 stt_service: BaseService,
                 llm_service: BaseService,
                 tts_service: BaseService
                 ):
        # 使用字典存储所有服务
        self.services = {
            'stt': stt_service,
            'llm': llm_service,
            'tts': tts_service,
        }
        
        self.active_connections: Set[Any] = set() # 存储活跃的WebSocket连接对象
        self.send_message_callback: Optional[SendMessageCallback] = None

    def get_service(self, service_name: str) -> Any:
        """获取指定名称的服务实例"""
        if service_name not in self.services:
            raise KeyError(f"Service '{service_name}' not found")
        return self.services[service_name]

    def register_service(self, service_name: str, service_instance: Any) -> None:
        """注册新服务或替换现有服务"""
        self.services[service_name] = service_instance
        logger.info(f"Service '{service_name}' registered")

    def remove_service(self, service_name: str) -> Any:
        """移除并返回服务实例"""
        if service_name not in self.services:
            raise KeyError(f"Service '{service_name}' not found")
        service = self.services.pop(service_name)
        logger.info(f"Service '{service_name}' removed")
        return service

    def has_service(self, service_name: str) -> bool:
        """检查服务是否存在"""
        return service_name in self.services

    async def initialize_services(self):
        """初始化所有服务。"""
        logger.info("Initializing all services...")
        initialization_tasks = []
        for name, service in self.services.items():
            if hasattr(service, 'initialize') and callable(service.initialize):
                logger.debug(f"Scheduling initialization of service '{name}'")
                initialization_tasks.append(service.initialize())
            else:
                logger.warning(f"Service '{name}' doesn't have an initialize method")
        
        if initialization_tasks:
            await asyncio.gather(*initialization_tasks)
        logger.info("All services initialized.")

    async def shutdown_services(self):
        """关闭所有服务。"""
        logger.info("Shutting down all services...")
        shutdown_tasks = []
        for name, service in self.services.items():
            if hasattr(service, 'shutdown') and callable(service.shutdown):
                logger.debug(f"Scheduling shutdown of service '{name}'")
                shutdown_tasks.append(service.shutdown())
            else:
                logger.warning(f"Service '{name}' doesn't have a shutdown method")
        
        if shutdown_tasks:
            await asyncio.gather(*shutdown_tasks)
        logger.info("All services shut down.")

    def register_connection(self, websocket: Any, send_callback: SendMessageCallback):
        """注册一个新的WebSocket连接及其发送回调。"""
        self.active_connections.add(websocket)
        if self.send_message_callback is None: 
            self.send_message_callback = send_callback
        logger.info(f"New connection registered: {websocket}. Total connections: {len(self.active_connections)}")

    def unregister_connection(self, websocket: Any):
        """注销一个WebSocket连接。"""
        self.active_connections.discard(websocket)
        logger.info(f"Connection unregistered: {websocket}. Total connections: {len(self.active_connections)}")
        # If no connections, we might not need to clear send_message_callback if it's generic enough
        # or if the server manages its lifecycle.

    async def handle_message(self, websocket: Any, message_str: str):
        """
        处理从WebSocket客户端接收到的消息。
        """
        try:
            message_data = parse_message(message_str)
            msg_type_str = message_data.get("type")
            msg_type  = MessageType(msg_type_str)
            payload = message_data.get("payload", {})
            request_id = message_data.get("request_id") # todo: 用于跟踪请求（目前不打算实现）
            
            session_id = payload.get("session_id")
            if session_id is None:
                logger.error("No session_id in payload")
                await self._send_error_response(websocket, "Missing session_id, no response for this request", request_id)
                return
            
            logger.debug(f"Broker received message: Type='{msg_type_str}', Payload='{payload}', RequestID='{request_id}'")

            if msg_type == MessageType.AUDIO_INPUT:
                # 需要 payload 包含 {"audio_data_base64": "...", "format": "wav"}
                audio_data_base64 = payload.get("audio_data_base64")
                if not audio_data_base64:
                    logger.error("No audio_data_base64 in AUDIO_INPUT payload")
                    await self._send_error_response(websocket, "Missing audio_data_base64", request_id)
                    return
                # 解码 base64 音频数据
                try:
                    audio_bytes = base64.b64decode(audio_data_base64)
                except Exception as e:
                    logger.error(f"Failed to decode base64 audio data: {e}")
                    await self._send_error_response(websocket, f"Invalid base64 audio data: {e}", request_id)
                    return

                await self._process_audio_pipeline(websocket, audio_bytes, session_id, request_id)

            elif msg_type == MessageType.TEXT_INPUT:
                user_text = payload.get("text")
                if not user_text:
                    logger.error("No text in TEXT_INPUT payload")
                    await self._send_error_response(websocket, "Missing text in payload", request_id)
                    return
                await self._process_text_pipeline(websocket, user_text, session_id, request_id)

            elif msg_type == MessageType.MIXED_INPUT:
                logger.info(f"Received MIXED_INPUT (Request ID: {request_id}). Processing not yet implemented.")
                # 在这里添加对混合输入的处理逻辑，例如提取文本和图像数据
                # user_text = payload.get("text")
                # image_data_base64 = payload.get("image_data_base64")
                # ... 调用相应的多模态LLM服务 ...
                # 这是一个占位符，暂时返回一个提示信息
                await self._send_to_client(websocket, MessageType.AI_RESPONSE, {
                    "text": "混合输入处理功能尚未实现。",
                    "audio": None,
                    "emotion": None,
                    "recognized_text": payload.get("text", "") # 如果有文本部分
                }, request_id)

            else:
                logger.warning(f"Received unhandled message type: {msg_type_str}")
                await self._send_error_response(websocket, f"Unhandled message type: {msg_type_str}", request_id)

        except ValueError as e: # 来自 parse_message
            logger.error(f"Invalid message format: {e}")
            await self._send_error_response(websocket, f"Invalid message format: {e}", None) # request_id可能无法解析
        except Exception as e:
            logger.error(f"Error handling message in Broker: {e}", exc_info=True)
            await self._send_error_response(websocket, f"Internal server error: {e}", message_data.get("request_id") if 'message_data' in locals() else None)

    async def _process_audio_pipeline(self, websocket: Any, audio_bytes: bytes, session_id: str, request_id: Optional[str]):
        """完整的音频处理流程：STT -> LLM -> Emotion -> TTS  -> AI_RESPONSE"""
        recognized_text = ""
        ai_response_text = ""
        tts_output = {}

        try:
            # 1. STT: 音频转文本
            stt_service = self.get_service('stt')
            recognized_text = await stt_service.process(audio_bytes)
            logger.info(f"STT result: '{recognized_text}' (Request ID: {request_id})")
            
            # 2. LLM: 文本生成回复
            llm_service = self.get_service('llm')
            ai_response_text = await llm_service.process(recognized_text, session_id=session_id)
            logger.info(f"LLM response: '{ai_response_text}' (Request ID: {request_id})")
            
            # 2.5 提取 emotion，清洗文本
            extract_result = text_extractor(ai_response_text)
            emotion = extract_result.get("emotion", EmotionType.CALM)
            res_text = extract_result.get("res_text", "")
            tts_text = extract_result.get("tts_text", "") 
            
            # 3. TTS: 文本转语音
            tts_service = self.get_service('tts')
            tts_output = await tts_service.process(tts_text)
            logger.info(f"TTS result generated. Format: {tts_output.get('audio_format')} (Request ID: {request_id})")
                
            # 4. 组合并发送单一 AI_RESPONSE 消息
            final_payload = {
                "emotion": emotion.value, # 情感类型
                "text": res_text,
                "audio": tts_output, # 包含 audio_data, audio_format
                "recognized_text": recognized_text # 用户通过STT识别的文本
            }
            await self._send_to_client(websocket, MessageType.AI_RESPONSE, final_payload, request_id)

        except Exception as e:
            logger.error(f"Error in audio processing pipeline (Request ID: {request_id}): {e}", exc_info=True)
            await self._send_error_response(websocket, f"Error in audio processing pipeline: {e}", request_id)

    async def _process_text_pipeline(self, websocket: Any, user_text: str, session_id: str, request_id: Optional[str]):
        """文本输入处理流程：LLM -> Emotion -> TTS -> AI_RESPONSE"""
        ai_response_text = ""
        tts_output = {}
        try:
            logger.info(f"Processing text input: '{user_text}' (Request ID: {request_id})")
            
            # 1. LLM: 文本生成回复
            llm_service = self.get_service('llm')
            ai_response_text = await llm_service.process(user_text, session_id=session_id)
            logger.info(f"LLM response: '{ai_response_text}' (Request ID: {request_id})")
            
            # 1.5 提取 emotion，清洗文本
            extract_result = text_extractor(ai_response_text)
            emotion = extract_result.get("emotion", EmotionType.CALM)
            res_text = extract_result.get("res_text", "")
            tts_text = extract_result.get("tts_text", "")  
            
            # 2. TTS: 文本转语音
            tts_service = self.get_service('tts')
            tts_output = await tts_service.process(tts_text)
            logger.info(f"TTS result generated. Format: {tts_output.get('audio_format')} (Request ID: {request_id})")

            # 3. 组合并发送单一 AI_RESPONSE 消息
            final_payload = {
                "emotion": emotion.value, # 情感类型
                "text": res_text, # AI生成的回复文本
                "audio": tts_output,
                "recognized_text": user_text # 用户直接输入的文本
            }
            await self._send_to_client(websocket, MessageType.AI_RESPONSE, final_payload, request_id)

        except Exception as e:
            logger.error(f"Error in text processing pipeline (Request ID: {request_id}): {e}", exc_info=True)
            await self._send_error_response(websocket, f"Error in text processing pipeline: {e}", request_id)

    async def _send_to_client(self, websocket: Any, msg_type: MessageType, payload: Dict, request_id: Optional[str]):
        """Helper to send a message to a specific client."""
        if self.send_message_callback:
            message_str = create_message(msg_type, payload, request_id)
            await self.send_message_callback(websocket, message_str)
        else:
            logger.error("send_message_callback not set in Broker. Cannot send message.")
            
    async def _send_error_response(self, websocket: Any, error_message: str, request_id: Optional[str]):
        """向客户端发送错误消息。"""
        logger.error(f"Sending error to client (Request ID: {request_id}): {error_message}")
        error_payload = {"message": error_message, "code": "INTERNAL_ERROR"}
        await self._send_to_client(websocket, MessageType.ERROR, error_payload, request_id)


class EmotionType(Enum):
    """
    情感类型枚举，用于表示情感分析结果。
    值对应前端或LLM输出的情感描述词。
    """
    CALM = "平静"
    SHY = "害羞"
    ANGRY = "生气"
    SAD = "悲伤"
    SURPRISED = "惊讶"
    EXCITED = "激动"
    EMBARRASSED = "尴尬"
    HAPPY = "高兴"

def text_extractor(ai_text: str) -> Dict[str, Any]:
    """
    从AI生成的文本中提取情感和回复文本。
    期望的格式是: "emotion" | 回复文本
    例如: "高兴" | 今天天气真好！
    """
    res_text = ai_text
    extracted_emotion = EmotionType.CALM

    try:
        if "|" in ai_text:
            parts = ai_text.split("|", 1)
            emotion_str = parts[0].strip().replace("\"", "") # 移除引号并去除首尾空格
            text_content = parts[1].strip()

            # 尝试将提取的 emotion_str 映射到 EmotionType
            found_emotion = False
            for emotion_member in EmotionType:
                if emotion_member.value == emotion_str:
                    extracted_emotion = emotion_member
                    found_emotion = True
                    break
            
            if found_emotion:
                res_text = text_content
            else:
                # 如果 emotion_str 不在 EmotionType 中，则将整个输入视为文本
                logger.warning(f"Unknown emotion tag '{emotion_str}' in LLM response. Using full text and default emotion.")
                res_text = text_content # 或者 cleaned_text = ai_text 如果希望保留无法识别的标签部分
        else:
            # 如果没有找到分隔符，则认为整个文本都是回复内容，使用默认情感
            logger.warning(f"LLM response did not contain '|' separator. Using full text and default emotion. Response: '{ai_text[:100]}...'")
            
    except Exception as e:
        logger.error(f"Error parsing emotion from LLM response: {e}. Response: '{ai_text[:100]}...'", exc_info=True)
        
    # TODO tts_text 可以进一步改进，使用特殊token来使得 TTS 更加自然
    # 为 TTS 生成更干净的文本
    tts_text_chars = []
    allowed_punctuation_for_tts = set("，。？！、；：,.?!;: ") 

    for char in res_text:
        if char.isalnum():  # 保留字母（包括中日韩等语言的字母）和数字
            tts_text_chars.append(char)
        elif char in allowed_punctuation_for_tts: # 保留指定的标点符号和空格
            # 对于空格，确保不会连续添加多个空格
            if char == ' ':
                if not tts_text_chars or tts_text_chars[-1] != ' ':
                    tts_text_chars.append(char)
            else:
                tts_text_chars.append(char)
        elif char.isspace(): # 其他空白字符（如换行符、制表符）转换成单个空格
            if not tts_text_chars or tts_text_chars[-1] != ' ':
                tts_text_chars.append(' ')
        # 其他所有字符（如特殊符号、表情符号等）将被忽略
    tts_text = "".join(tts_text_chars).strip() 
    
    return {"emotion": extracted_emotion, "res_text": res_text, "tts_text": tts_text}