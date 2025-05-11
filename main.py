import asyncio
import logging
import signal
import os

from config import settings
from core.websocket.server import WebSocketServer
from core.broker import ServiceBroker

# 配置日志
logging.basicConfig(level=settings.LOG_LEVEL, format=settings.LOG_FORMAT)
logger = logging.getLogger(__name__)

# 全局变量，用于优雅关闭
shutdown_event = asyncio.Event()

def choose_services():
    """根据settings.py 中的配置选择服务"""
    if settings.STT_MODEL_TYPE == "whisper":
        from services.stt import WhisperService
        stt_service = WhisperService(service_name=settings.STT_SERVICE_NAME, config=settings.STT_SERVICE)
    elif settings.STT_MODEL_TYPE == "wav2vec":
        from services.stt import Wav2vecService
        stt_service = Wav2vecService(service_name=settings.STT_SERVICE_NAME, config=settings.STT_SERVICE)
    else:
        raise ValueError(f"Unsupported STT service: {settings.STT_SERVICE}")
    
    if settings.TTS_MODEL_TYPE == "gpt_sovits":
        from services.tts import GPTsovitsService
        tts_service = GPTsovitsService(service_name=settings.TTS_SERVICE_NAME, config=settings.TTS_SERVICE)
    elif settings.TTS_MODEL_TYPE == "fish_speech":
        from services.tts import FishSpeechService
        tts_service = FishSpeechService(service_name=settings.TTS_SERVICE_NAME, config=settings.TTS_SERVICE)
    else:
        raise ValueError(f"Unsupported TTS service: {settings.TTS_SERVICE}")
    
    if settings.LLM_MODEL_TYPE == "openai_like":
        from services.llm import OpenaiService
        llm_service = OpenaiService(service_name=settings.LLM_SERVICE_NAME, config=settings.LLM_SERVICE)
    elif settings.LLM_MODEL_TYPE == "local":
        from services.llm import LocalModelService
        llm_service = LocalModelService(service_name=settings.LLM_SERVICE_NAME, config=settings.LLM_SERVICE)
    elif settings.LLM_MODEL_TYPE == "ollama":
        from services.llm import LlamaService
        llm_service = LlamaService(service_name=settings.LLM_SERVICE_NAME, config=settings.LLM_SERVICE)
    else:
        raise ValueError(f"Unsupported LLM service: {settings.LLM_MODEL_TYPE}")
    
    from services.lips import LipSyncService
    lipsync_service = LipSyncService(service_name=settings.LIPSYNC_SERVICE_NAME, config=settings.LIPSYNC_SERVICE)
    
    return stt_service, llm_service, tts_service, lipsync_service
    

async def main():
    """
    主异步函数，初始化并运行应用程序。
    """
    logger.info("Starting AI Virtual Anchor Backend...")

    # 1. 初始化服务
    stt_service, llm_service, tts_service, lipsync_service = choose_services()

    # 2. 初始化服务协调器 (Broker)
    broker = ServiceBroker(
        stt_service=stt_service,
        llm_service=llm_service,
        tts_service=tts_service,
        lipsync_service=lipsync_service,
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
