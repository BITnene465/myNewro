import os
import sys
import asyncio
import time
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from services.stt import STTService

async def test_stt_service():
    """测试STT服务的语音识别功能"""
    audio_path = Path(__file__).parent / "test_data" / "exp2.wav"
    # 如果data目录不存在，创建它
    os.makedirs(audio_path.parent, exist_ok=True)
    
    if not audio_path.exists():
        print(f"警告: 音频文件 {audio_path} 不存在！")
        return
    
    print(f"正在读取音频文件: {audio_path}")
    
    # 读取音频文件
    with open(audio_path, "rb") as f:
        audio_data = f.read()
    
    print(f"音频文件大小: {len(audio_data)/1024:.2f} KB")
    
    # 初始化STT服务
    print("初始化STT服务中...")
    start_time = time.time()
    
    # 创建STT服务实例
    stt_service = STTService(config={
        "model_name": "jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn",
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "local_models_path": Path(__file__).parent.parent / "models"
    })
    
    await stt_service.initialize()
    print(f"STT服务初始化完成，耗时: {time.time() - start_time:.2f} 秒")
    
    # 识别音频
    print("开始进行语音识别...")
    start_time = time.time()
    
    text = await stt_service.process(audio_data)
    
    print(f"语音识别完成，耗时: {time.time() - start_time:.2f} 秒")
    print(f"识别结果: {text}")
    
    # 关闭服务
    await stt_service.shutdown()
    print("测试完成")

if __name__ == "__main__":
    try:
        import torch
        asyncio.run(test_stt_service())
    except RuntimeError as e:
        if "CUDA" in str(e):
            print("\n错误: CUDA初始化失败。请确保您的系统支持CUDA并已正确安装驱动。")
            print("您可以通过运行时自动判断使用CPU模式运行。")
        else:
            print(f"\n运行时错误: {e}")
    except Exception as e:
        print(f"\n发生错误: {e}")
