import asyncio
import logging
import signal
import os

from config import settings
from core.websocket.server import WebSocketServer
from core.broker import ServiceBroker
from services.factory import get_service_instance

# 配置日志
logging.basicConfig(level=settings.LOG_LEVEL, format=settings.LOG_FORMAT)
logger = logging.getLogger(__name__)

# 全局变量，用于优雅关闭
shutdown_event = asyncio.Event()


async def main():
    """
    主异步函数，初始化并运行应用程序。
    """
    logger.info("Starting AI Virtual Anchor Backend...")
    
    try:
        # 1. 使用环境变量获取服务实例
        stt_service = get_service_instance("stt")
        llm_service = get_service_instance("llm")
        tts_service = get_service_instance("tts")
        
        # 如果需要RAG服务，可以取消注释以下行
        # rag_service = get_service_instance("rag")
    except (ValueError, ImportError) as e:
        logger.error(f"初始化服务失败: {e}", exc_info=True)
        return

    # 2. 初始化服务协调器 (Broker)
    broker = ServiceBroker(
        stt_service=stt_service,
        llm_service=llm_service,
        tts_service=tts_service,
        # rag_service=rag_service  # 如果需要RAG服务，可以取消注释此行
    )
    
    try:
        await broker.initialize_services()
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}", exc_info=True)
        return # 初始化失败则不启动服务器

    # 3. 初始化并启动WebSocket服务器
    ws_server = WebSocketServer(
        host=settings.WEBSOCKET_HOST,
        port=settings.WEBSOCKET_PORT,
        broker=broker
    )

    # 启动WebSocket服务器的任务
    server_task = asyncio.create_task(ws_server.start())
    
    logger.info(f"Application started. Listening on ws://{settings.WEBSOCKET_HOST}:{settings.WEBSOCKET_PORT}")
    logger.info("Press Ctrl+C to stop the server.")

    # 等待关闭信号
    await shutdown_event.wait()

    # 执行关闭操作
    logger.info("Shutdown signal received. Cleaning up...")
    
    # 停止WebSocket服务器 (这会解除 ws_server.start() 中的 wait_closed)
    if ws_server.server and not ws_server.server.is_serving(): # 检查服务器是否仍在运行
         logger.info("WebSocket server already stopped or not started.")
    else:
        await ws_server.stop()

    # 关闭服务
    await broker.shutdown_services()
    
    # 等待服务器任务完成 (如果它还没有因为stop()而结束)
    if not server_task.done():
        try:
            await asyncio.wait_for(server_task, timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("Server task did not finish in time. Forcing cancellation.")
            server_task.cancel()
            try:
                await server_task # 等待取消完成
            except asyncio.CancelledError:
                logger.info("Server task was cancelled.")
        except Exception as e:
            logger.error(f"Error during server task completion: {e}")


    logger.info("Application shut down gracefully.")


def signal_handler(sig, frame):
    """处理SIGINT (Ctrl+C) 和 SIGTERM信号。"""
    logger.info(f"Received signal {sig}, initiating shutdown...")
    shutdown_event.set()


if __name__ == "__main__":
    os.chdir(settings.PROJECT_ROOT)
    # 设置信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # 理论上 signal_handler 会处理，这里作为备用
        logger.info("KeyboardInterrupt caught in __main__, shutting down.")
        # 确保 shutdown_event 被设置，以防 signal_handler 未完全执行
        if not shutdown_event.is_set():
            shutdown_event.set()
            # 可能需要手动调用 asyncio.run(cleanup_logic()) 如果 main() 已经退出
    except Exception as e:
        logger.critical(f"Unhandled exception in main execution: {e}", exc_info=True)
    finally:
        logger.info("Application exiting.")
