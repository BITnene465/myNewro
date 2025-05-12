import asyncio
import json
import base64
import io
import sys
import os
from pathlib import Path
import websockets
from pydub import AudioSegment
from pydub.playback import play

from core.websocket.protocol import MessageType, create_message, parse_message
from config import settings

# 服务器配置
WS_HOST = "localhost"
WS_PORT = 8765
WS_URI = f"ws://{WS_HOST}:{WS_PORT}"
session_id = f"test-session-0721"

# 创建全局异步播放队列和信号量
audio_queue = asyncio.Queue()
player_semaphore = asyncio.Semaphore(1)
player_task = None

# 播放器协程
async def audio_player():
    """异步音频播放器，从队列中取出音频并按顺序播放"""
    while True:
        audio_data, audio_format = await audio_queue.get()
        async with player_semaphore:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: play_audio_local(audio_data, audio_format)
            )
        audio_queue.task_done()

def ensure_player_running():
    global player_task
    if player_task is None or player_task.done():
        player_task = asyncio.create_task(audio_player())
        
async def play_audio_async(audio_data, audio_format):
    ensure_player_running()
    await audio_queue.put((audio_data, audio_format))

def play_audio_local(audio_data, audio_format):
    try:
        decoded_audio = base64.b64decode(audio_data)
        audio_io = io.BytesIO(decoded_audio)
        sound = AudioSegment.from_file(audio_io, format=audio_format)
        play(sound)
    except Exception as e:
        print(f"播放音频时出错: {e}")

async def send_text_to_server(websocket, text_input):
    """发送文本到服务器并处理响应"""
    text_message = {
        "type": MessageType.TEXT_INPUT.value,
        "payload": {
            "text": text_input,
            "session_id": session_id,
        },
    }
    
    print("🔄 发送到服务器，请稍候...")
    await websocket.send(json.dumps(text_message))
    
    # 等待响应
    while True:
        response = await websocket.recv()
        response_data = parse_message(response)
        msg_type = response_data.get("type")
        if msg_type == MessageType.AI_RESPONSE.value:
            break
    
    # 处理回复
    audio = response_data['payload']['audio']
    audio_data = audio['audio_data']   # 此时是 base64 编码
    audio_format = audio['audio_format']
    text = response_data['payload']['text']    
    print(f"🤖 虚拟主播: {text}")
    await play_audio_async(audio_data, audio_format)

async def get_user_input(prompt):
    """在线程池中运行input()函数，避免阻塞事件循环"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: input(prompt).strip())


async def interactive_session():
    """交互式会话主函数"""
    print("=" * 60)
    print("🎙️ Newro AI 虚拟主播命令行交互客户端")
    print("=" * 60)
    print("连接到服务器...", end="")
    sys.stdout.flush()
    
    try:
        async with websockets.connect(WS_URI, max_size=50 * 1024 * 1024) as websocket:
            print(" 已连接!")
            print("💡 开始对话 (输入 'exit' 或 'quit' 退出)")
            print("-" * 60)
            
            # 启动播放器
            ensure_player_running()
            while True:
                user_input = await get_user_input("👤 你: ")
                
                # 检查是否退出
                if user_input.lower() in ['exit', 'quit']:
                    print("再见! 👋")
                    break
                if user_input.lower() in ['cls', 'clear']:
                    os.system('cls' if os.name == 'nt' else 'clear')
                    continue
                if not user_input:
                    continue
                
                # 发送用户输入到服务器
                await send_text_to_server(websocket, user_input)
                print("-" * 60)
    
    except websockets.exceptions.ConnectionClosed:
        print("\n⚠️ 连接已关闭")
    except Exception as e:
        print(f"\n❌ 错误: {e}")

if __name__ == "__main__":
    try:
        # 检查服务器是否已启动的提示
        print("确保服务器已启动 (python main.py)")
        asyncio.run(interactive_session())
    except KeyboardInterrupt:
        print("\n用户中断，退出程序")
