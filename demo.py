"""
Newro AI 虚拟主播后端服务集成测试脚本
用于模拟前端通过WebSocket接口向服务器发送请求

该脚本模拟以下流程：
1. 连接到WebSocket服务器
2. 发送文本输入 (chat 消息)
3. 接收并打印服务器响应
4. 发送音频输入 (speech-to-text 消息)
5. 接收并打印语音识别结果
"""
import asyncio
import json
import base64
import os
from pathlib import Path
import time
import websockets

import io
from pydub import AudioSegment
from pydub.playback import play

from core.websocket.protocol import MessageType, create_message, parse_message
from config import settings

# 服务器配置
WS_HOST = "localhost"
WS_PORT = 8765
WS_URI = f"ws://{WS_HOST}:{WS_PORT}"

# 创建全局异步播放队列和信号量
audio_queue = asyncio.Queue()
player_semaphore = asyncio.Semaphore(1)  # 限制同时只能有一个播放任务
player_task = None

# 播放器协程
async def audio_player():
    """异步音频播放器，从队列中取出音频并按顺序播放"""
    while True:
        # 获取下一个要播放的音频
        audio_data, audio_format = await audio_queue.get()
        # 使用信号量确保一次只播放一个音频
        async with player_semaphore:
            # 播放音频 (仍需使用executor因为播放是阻塞操作)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: play_audio_local(audio_data, audio_format)
            )
        # 标记任务完成
        audio_queue.task_done()

# 启动播放器任务
def ensure_player_running():
    global player_task
    if player_task is None or player_task.done():
        player_task = asyncio.create_task(audio_player())
        
# 将音频加入队列的异步方法
async def play_audio_async(audio_data, audio_format):
    # 确保播放器任务在运行
    ensure_player_running()
    # 将音频放入队列
    await audio_queue.put((audio_data, audio_format))


def play_audio_local(audio_data, audio_format):
    # 解码音频数据
    decoded_audio = base64.b64decode(audio_data)
    audio_io = io.BytesIO(decoded_audio)
    # 加载并播放
    print(f"正在播放音频...")
    sound = AudioSegment.from_file(audio_io, format=audio_format)
    play(sound)


async def test_websocket_client():
    """简单的WebSocket客户端，用于测试与服务器的连接和消息处理"""
    try:
        print(f"连接到WebSocket服务器: {WS_URI}")
        async with websockets.connect(WS_URI, max_size=50 * 1024 * 1024) as websocket:
            print("连接成功!")
            
            # 1. 测试文本输入 (text input)
            print("\n===== 测试文本输入 =====")
            text_message = {
                "type": "text_input",
                "payload": {
                    "text": "你好，请介绍一下你自己",
                    "session_id": "test-session-123",
                },
            }
            
            print(f"发送消息: {text_message}")
            await websocket.send(json.dumps(text_message))
            
            # 等待响应
            print("等待响应...")
            response_data = None
            while True:
                response = await websocket.recv()
                response_data = parse_message(response)
                msg_type = response_data.get("type")
                if msg_type == MessageType.SYSTEM_STATUS.value:
                    continue
                break
            # 处理response， 并且展示
            audio = response_data['payload']['audio']
            audio_data = audio['audio_data']
            audio_form = audio['audio_format']
            text = response_data['payload']['text']
            print(f"生成文本为： {text}")
            
            # 不要阻塞主主线程
            await play_audio_async(audio_data, audio_form)
            
            # 2. 测试音频输入 (audio input)
            print("\n===== 测试音频输入 =====")
            
            # 读取测试音频文件
            test_audio_path = Path(__file__).parent / "tests" / "test_data" / "exp.wav"
            if not test_audio_path.exists():
                print(f"测试音频文件不存在: {test_audio_path}")
                print("跳过音频测试")
            else:
                with open(test_audio_path, "rb") as audio_file:
                    audio_bytes = audio_file.read()
                
                # 将音频数据编码为base64字符串
                audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                
                # 创建音频输入消息
                audio_message = {
                    "type": "audio_input",
                    "payload": {
                        "audio_data_base64": audio_base64,
                        "session_id": "test-session-123",
                    },
                }
                
                print(f"发送音频消息...")
                await websocket.send(json.dumps(audio_message))
                
                # 等待响应
                print("等待语音识别响应...")
                response = await websocket.recv()
                response_data = parse_message(response)
                audio = response_data['payload']['audio']
                audio_data = audio['audio_data']
                audio_form = audio['audio_format']
                text = response_data['payload']['text']
                print(f"生成文本为： {text}")
                
                # 异步播放，不阻塞主线程
                await play_audio_async(audio_data, audio_form)
            
            print("\n测试完成!")
            
    except Exception as e:
        print(f"测试过程中发生错误: {e}")

# 用于测试服务器 websocket 的 keepalive机制
async def test_idle_connection():
    """测试空闲WebSocket连接是否会自动断开"""
    try:
        print(f"连接到WebSocket服务器: {WS_URI}")
        start_time = time.time()
        
        async with websockets.connect(
            WS_URI, 
            max_size=50 * 1024 * 1024,
            ping_interval=30,  # 可选：增加ping间隔(秒)
            ping_timeout=30    # 可选：增加ping超时(秒)
        ) as websocket:
            print("连接成功!")
            print("保持连接空闲，不发送任何消息...")
            
            # 接收欢迎消息
            welcome = await websocket.recv()
            print(f"收到欢迎消息: {welcome[:100]}...")
            
            # 保持连接打开但不发送任何消息
            try:
                while True:
                    # 每10秒打印一次连接持续时间
                    await asyncio.sleep(10)
                    duration = time.time() - start_time
                    print(f"连接已持续 {duration:.1f} 秒...")
            except Exception as e:
                duration = time.time() - start_time
                print(f"连接在 {duration:.1f} 秒后断开，错误: {e}")
    
    except Exception as e:
        print(f"测试过程中发生错误: {e}")


if __name__ == "__main__":
    # 检查服务器是否已启动的提示
    print("确保服务器已启动 (python main.py)")
    print("开始测试...")
    
    # 测试空闲连接
    # print("开始测试空闲连接...")
    # asyncio.run(test_idle_connection())
    
    # 运行测试
    asyncio.run(test_websocket_client())