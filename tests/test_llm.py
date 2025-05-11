import os
import sys
import asyncio
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from services.llm import LLMService
from config import settings

async def test_llm_service():
    """测试LLM服务"""
    # 创建输出目录
    output_dir = Path(__file__).parent / "test_output"
    os.makedirs(output_dir, exist_ok=True)
    # 初始化LLM服务
    print("初始化DeepSeek LLM服务...")
    start_time = time.time()
    # 创建LLM服务实例
    llm_service = LLMService(config=settings.LLM_SERVICE)
    
    try:
        await llm_service.initialize()
        print(f"LLM服务初始化完成，耗时: {time.time() - start_time:.2f} 秒")
        
        # 测试查询
        test_queries = [
            "你好，请介绍一下你自己",
            "你就是neuro吗？那个大名鼎鼎的v",
            "我感觉很沮丧，有什么建议吗?"
        ]
        
        for i, query in enumerate(test_queries):
            print(f"\n测试查询 {i+1}: '{query}'")
            start_time = time.time()
            response = await llm_service.process(query)
            print(f"生成回复，耗时: {time.time() - start_time:.2f} 秒")
            print(f"回复: {response}\n")
            # 保存响应
            output_file = output_dir / f"llm_response_{i+1}.txt"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(f"查询: {query}\n\n回复: {response}")
            print(f"响应已保存到: {output_file}")
        
        # 测试流式响应
        print("\n测试流式响应...")
        start_time = time.time()
        stream_query = "你能用简单的语言解释量子力学吗？"
        print(f"流式查询: '{stream_query}'")
        response = await llm_service.process(
            stream_query,
            stream=True
        )
        print(f"流式生成完成，耗时: {time.time() - start_time:.2f} 秒")
        print(f"流式回复: {response}")
    except ConnectionError as e:
        print(f"\n连接错误: {e}")
        print("请确保提供了正确的API密钥，并且API服务可用。")
    except Exception as e:
        print(f"\n发生错误: {e}")
    finally:
        # 关闭服务
        if 'llm_service' in locals() and llm_service.is_ready():
            await llm_service.shutdown()
        print("\n测试完成")

if __name__ == "__main__":
    asyncio.run(test_llm_service())
