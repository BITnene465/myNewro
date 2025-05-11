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
import websockets

# 服务器配置
WS_HOST = "localhost"
WS_PORT = 8765
WS_URI = f"ws://{WS_HOST}:{WS_PORT}"

async def test_websocket_client():
    """简单的WebSocket客户端，用于测试与服务器的连接和消息处理"""
    try:
        print(f"连接到WebSocket服务器: {WS_URI}")
        async with websockets.connect(WS_URI) as websocket:
            print("连接成功!")
            
            # 1. 测试文本输入 (chat)
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
            response = await websocket.recv()
            response_data = json.loads(response)
            print(f"收到响应: {response_data}")
            
            # 2. 测试音频输入 (speech-to-text)
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
                response_data = json.loads(response)
                print(f"收到语音识别响应: {response_data}")
            
            print("\n测试完成!")
            
    except Exception as e:
        print(f"测试过程中发生错误: {e}")

if __name__ == "__main__":
    # 检查服务器是否已启动的提示
    print("确保服务器已启动 (python main.py)")
    print("开始测试...")
    
    # 运行测试
    asyncio.run(test_websocket_client())