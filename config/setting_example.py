"""
项目配置文件
"""
import logging
import torch.cuda
from pathlib import Path

# 项目相关设置
PROJECT_NAME = "Newro"
PROJECT_VERSION = "0.1.0"
PROJECT_ROOT = Path(__file__).parent.parent  # 项目根目录(settings.py路径不更改的情况下)

# WebSocket 服务器配置
WEBSOCKET_HOST = "localhost"
WEBSOCKET_PORT = 8765

# 日志配置
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# 系统提示词加载
SYSTEM_PROMPT = ""
try:
    # 确保 system_prompt.txt 文件与 settings.py 在同一 config 目录下，或者调整路径
    with open(PROJECT_ROOT / "config" / "system_prompt.txt", "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read().strip()
except FileNotFoundError:
    print("系统提示词文件 'config/system_prompt.txt' 未找到，LLM 将使用默认或无系统提示词。")
except Exception as e:
    print(f"读取系统提示词时发生错误: {e}")


# 服务配置
SERVICES = {
    "stt": {
        "active_provider": "whisper",  # 可选值: "whisper", "wav2vec"
        "providers": {
            "whisper": {
                "class": "services.stt.WhisperService",  # 类路径
                "service_name": "WhisperSTT",
                "config": {
                    "model_size": "medium",  # 可选值: "tiny", "base", "small", "medium", "large"
                    "language": "zh",
                    "device": "cuda" if torch.cuda.is_available() else "cpu",
                }
            },
            "wav2vec": {
                "class": "services.stt.Wav2vecService", 
                "service_name": "Wav2vecSTT",
                "config": {
                    "model_name": "jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn",
                    "device": "cuda" if torch.cuda.is_available() else "cpu",
                    "local_models_path": PROJECT_ROOT / "models" # 确保模型在此路径下
                }
            }
        }
    },
    "llm": {
        "active_provider": "openai_like",  # 可选值: "openai_like", "local", "ollama"
        "providers": {
            "openai_like": {
                "class": "services.llm.OpenaiService",
                "service_name": "DeepSeekLLM",  # 例如 DeepSeek
                "config": {
                    "api_base_url": "https://api.deepseek.com/v1",
                    "api_key": "your-api-key", # 替换为你的 DeepSeek 密钥
                    "model": "deepseek-chat",
                    "temperature": 0.8,
                    "max_tokens": 200,
                    "system_prompt": SYSTEM_PROMPT,
                    "top_p": 0.8,
                    "stream": False
                }
            },
            "local": {
                "class": "services.llm.LocalModelService", # 类路径
                "service_name": "LocalLLM",
                "config": {
                    "api_base_url": "http://localhost:10721", # NewroLLMServer 或其他本地服务地址
                    "api_key": "",  # 不需要可以留空
                    "model_name": "Qwen3-1.7B-xin-lora", # 确保与本地服务中的模型名一致
                    "temperature": 0.9,
                    "max_tokens": 200,
                    "system_prompt": SYSTEM_PROMPT,
                    "top_p": 0.8,
                    "enable_thinking": False, # 特定于你的 LocalModelService 的配置
                }
            },
            "ollama": {
                "class": "services.llm.OllamaService", # 类路径
                "service_name": "OllamaLLM",
                "config": {
                    # "host": "http://localhost:11434", # Ollama 默认地址
                    # "model": "llama3", # 在Ollama中已下载的模型
                    # "system_prompt": SYSTEM_PROMPT,
                    # "options": {
                    #     "temperature": 0.8,
                    #     "top_p": 0.9
                    # }
                }
            }
        }
    },
    "tts": {
        "active_provider": "gpt_sovits",  # 可选值: "gpt_sovits", "fish_speech"
        "providers": {
            "gpt_sovits": {
                "class": "services.tts.GPTsovitsService", 
                "service_name": "GPTsoVITS_TTS",
                "config": {
                    "api_base_url": "http://localhost:9880",
                    "speed": 1.0, 
                    "audio_format": "wav",
                    "ref_audio_path": "G:\\codeSpace\\NewroProject\\asset\\ref_audios\\ref1.wav",
                    "prompt_text": "就是客人的重要度划分，分为胡、桃、竹、木四级，往往级别越高，往来就越密切",
                    "prompt_language": "zh",
                    "text_language": "zh",
                    "top_k": 20,
                    "top_p": 0.9,
                    "temperature": 0.9,
                    "text_split_method": "cut0",  # 文本切割方式，根据 GPT-SoVITS 的文档按需填写
                }
            },
            "fish_speech": {
                "class": "services.tts.FishSpeechService", 
                "service_name": "FishSpeechTTS",
                "config": {
                    # 根据 FishSpeech 服务的要求填写配置
                }
            }
        }
    },
    "rag": {
        "active_provider": "simple_rag",  # 可选值: "simple_rag"
        "providers": {
            "simple_rag": {
                "class": "services.rag.SimpleRAGService",  # 类路径
                "service_name": "SimpleRAG",
                "config": {
                    "knowledge_base_path": PROJECT_ROOT / "data" / "knowledge_test.txt",  # 知识库文件路径
                    "chroma_db_path": PROJECT_ROOT / "data" / "chroma_db",  # Chroma向量数据库路径
                    "collection_name": "knowledge_test",   # 向量数据库集合名称
                    "embedding_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",  # 嵌入模型
                    "chunk_size": 300,  # 文本分块大小
                    "chunk_overlap": 50,  # 分块重叠大小
                    "top_k": 3,  # 检索返回的相关文档数量
                    "similarity_threshold": 0.6  # 相似度阈值，低于此值的文档不会被返回
                }
            },
        }
    }
}