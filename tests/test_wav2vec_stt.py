import os
import sys
import asyncio
import time
from pathlib import Path
import torch

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import PROJECT_ROOT
from services.stt import Wav2vecService

async def test_stt_service():
    """测试STT服务的语音识别功能"""
    audio_path = Path(__file__).parent / "test_data" / "exp2.wav"
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
    STT_SERVICE_CONFIG = {
        "model_name": "jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn",
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "local_models_path": PROJECT_ROOT / "models"   # 就是根目录下的 models 文件夹
        }
    
    stt_service = Wav2vecService(config=STT_SERVICE_CONFIG)
    
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
    asyncio.run(test_stt_service())