import os
import sys
import asyncio
import time
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from services.tts import TTSService

async def test_tts_service():
    """测试GPTsoVITS TTS服务"""
    # 创建输出目录
    output_dir = Path(__file__).parent / "test_output"
    os.makedirs(output_dir, exist_ok=True)
    
    # 初始化TTS服务
    print("初始化GPTsoVITS TTS服务...")
    start_time = time.time()
    
    # 创建TTS服务实例
    tts_service = TTSService(service_name="GPTsoVITS", config={
        "api_base_url": "http://localhost:9880",  # 确保GPTsoVITS服务正在运行
        "speed": 1.0,
        "audio_format": "wav",
        "default_refer_wav_path": "/workspace/SoVITS_weights/ref_audio/nailong1.wav",  # 默认参考音频路径
        "default_prompt_text": "你好，这里是我的频道，欢迎大家来和我聊天。",  
        "default_prompt_language": "zh", 
        "text_language": "zh",
        "top_k": 20,
        "top_p": 0.6,
        "temperature": 0.6
    })
    
    try:
        await tts_service.initialize()
        print(f"TTS服务初始化完成，耗时: {time.time() - start_time:.2f} 秒")
        
        # 测试文本
        test_text = "你好，这是使用GPTsoVITS生成的测试语音，语音合成质量如何呢？"
        
        # 测试1: 不指定参考音频 (使用API默认参考音频)
        print(f"\n测试1: 使用API默认参考音频合成文本: '{test_text}'")
        start_time = time.time()
        
        try:
            result = await tts_service.process(
                test_text,
                text_language="zh",
                format="wav",
            )
            
            audio_data = result["audio_data"]
            audio_format = result.get("audio_format", "wav")
            
            print(f"语音合成完成，耗时: {time.time() - start_time:.2f} 秒")
            print(f"音频大小: {len(audio_data)/1024:.2f} KB, 格式: {audio_format}")
            
            # 保存音频文件
            output_file = output_dir / f"gptsoVITS_default.{audio_format}"
            with open(output_file, "wb") as f:
                f.write(audio_data)
            
            print(f"语音文件已保存到: {output_file}")
        except Exception as e:
            print(f"测试1失败: {e}")
            print("API可能没有设置默认参考音频，请继续下一个测试")
        
        # 测试4: 测试不同参数组合
        print("\n测试4: 测试不同参数组合")
        
        # 测试文本切分
        try:
            print("测试文本切分功能...")
            long_text = "这是一段较长的文本，包含了多个句子。GPTsoVITS可以根据标点符号切分文本。这样生成的语音会更加自然，停顿更加合理。"
            
            result = await tts_service.process(
                long_text,
                cut_punc="，。",  # 使用逗号和句号作为切分符号
                speed=0.9,        # 较慢的语速
                format="wav",
            )
            
            audio_data = result["audio_data"]
            
            print(f"带切分的语音合成完成，大小: {len(audio_data)/1024:.2f} KB")
            
            # 保存音频文件
            output_file = output_dir / "gptsoVITS_cut_punc.wav"
            with open(output_file, "wb") as f:
                f.write(audio_data)
            
            print(f"语音文件已保存到: {output_file}")
        
        except Exception as e:
            print(f"切分测试失败: {e}")
    
    except ConnectionError as e:
        print(f"\n连接错误: {e}")
        print("请确保GPTsoVITS服务正在运行，并且API地址配置正确。")
        print("默认GPTsoVITS地址是 http://localhost:9880")
    
    except Exception as e:
        print(f"\n发生错误: {e}")
    
    finally:
        # 关闭服务
        if 'tts_service' in locals() and tts_service.is_ready():
            await tts_service.shutdown()
        print("测试完成")

if __name__ == "__main__":
    asyncio.run(test_tts_service())
