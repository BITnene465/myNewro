import asyncio
import logging
import websockets
from typing import Optional
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed, ConnectionClosedOK, ConnectionClosedError

from .protocol import create_message, MessageType
from ..broker import ServiceBroker

logger = logging.getLogger(__name__)

class WebSocketServer:
    """
    WebSocket服务器类，用于处理客户端连接和消息。
    """
    def __init__(self, host: str, port: int, broker: ServiceBroker):
        self.host = host
        self.port = port
        self.broker = broker
        self.server: Optional[websockets.WebSocketServer] = None

    async def _send_message(self, websocket: WebSocketServerProtocol, message: str):
        """通过指定的WebSocket连接发送消息。"""
        try:
            await websocket.send(message)
        except ConnectionClosed:
            logger.warning(f"Attempted to send message to a closed connection: {websocket.remote_address}")
        except Exception as e:
            logger.error(f"Error sending message to {websocket.remote_address}: {e}", exc_info=True)


    async def handler(self, websocket: WebSocketServerProtocol):
        """
        处理单个WebSocket连接。
        为每个连接的生命周期调用。
        """
        logger.info(f"Client connected: {websocket.remote_address}")
        self.broker.register_connection(websocket, self._send_message)
        
        try:
            # 发送连接成功消息
            welcome_message = create_message(MessageType.SYSTEM_STATUS, {"message": "Connected to AI Virtual Anchor server."})
            await websocket.send(welcome_message)  # send 只负责把消息送到网络信道上
            # todo: Broker可以处理更通用的系统消息

            async for message_str in websocket:
                if not isinstance(message_str, str): # 二进制消息暂不处理
                    logger.warning(f"Received non-text message from {websocket.remote_address}, ignoring.")
                    continue
                logger.debug(f"Received message from {websocket.remote_address}: {message_str[:200]}") # 打印部分消息
                await self.broker.handle_message(websocket, message_str)
        
        except (ConnectionClosedOK, ConnectionClosedError):
            logger.info(f"Client disconnected: {websocket.remote_address}")
        except ConnectionClosed as e: # 其他关闭异常
            logger.warning(f"Connection closed with error for {websocket.remote_address}: {e}")
        except Exception as e:
            logger.error(f"Error in WebSocket handler for {websocket.remote_address}: {e}", exc_info=True)
        finally:
            self.broker.unregister_connection(websocket)
            logger.info(f"Cleaned up connection for {websocket.remote_address}")


    async def start(self):
        """
        启动WebSocket服务器。
        """
        logger.info(f"Starting WebSocket server on ws://{self.host}:{self.port}")
        try:
            self.server = await websockets.serve(
                self.handler,
                self.host,
                self.port,
                ping_interval=60, # 保持连接活跃
                ping_timeout=60,
                max_size= 50 * 1024 * 1024,
            )
            logger.info("WebSocket server started successfully.")
           #  await self.server.wait_closed() # 保持服务器运行直到被关闭
        except OSError as e:
            logger.error(f"Failed to start WebSocket server: {e} (Port {self.port} might be in use)")
        except Exception as e:
            logger.error(f"An unexpected error occurred while starting or running the WebSocket server: {e}", exc_info=True)

    async def stop(self):
        """
        停止WebSocket服务器。
        """
        if self.server:
            logger.info("Stopping WebSocket server...")
            self.server.close()
            await self.server.wait_closed() # 等待服务器完全关闭
            self.server = None # 清理服务器实例
            logger.info("WebSocket server stopped.")
        else:
            logger.info("WebSocket server is not running or already stopped.")
