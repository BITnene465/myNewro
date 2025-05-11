import whisper
import soundfile as sf
import os
import tempfile
import asyncio
from pathlib import Path
from typing import Any, Dict, Optional, Union
import torch
import numpy as np

from ..base import BaseService

class WhisperService(BaseService):
    """
    基于OpenAI的Whisper模型的语音识别服务
    """
    DEFAULT_MODEL_SIZE = "medium"  # tiny, base, small, medium, large
    DEFAULT_SAMPLE_RATE = 16000
    
    def __init__(self, service_name: str = "stt_whisper", config: Dict[str, Any] = None):
        """
        初始化Whisper STT服务
        Args:
            service_name: 服务名称
            config: 配置字典，可包含以下键：
                - model_size: Whisper模型大小 (tiny, base, small, medium, large)
                - device: 计算设备 (cpu, cuda)
                - language: 语言代码，如'zh'表示中文 
        """
        if config is None:
            config = {
                "model_size": self.DEFAULT_MODEL_SIZE,
                "device": "cuda" if torch.cuda.is_available() else "cpu",
                "language": "zh"  # 默认中文
            }
        super().__init__(service_name, config)
        self.model = None
        self.device = torch.device(self.config["device"])
        self.logger.info(f"Whisper STT Service created with config: {config}")
    
    async def initialize(self):
        """初始化Whisper模型"""
        self.logger.info(f"Initializing Whisper STT service with model size: {self.config['model_size']}")
        
        # 在事件循环中运行模型加载
        loop = asyncio.get_running_loop()
        self.model = await loop.run_in_executor(
            None,
            lambda: whisper.load_model(self.config["model_size"], device=self.config["device"])
        )
        
        self.logger.info(f"Whisper model loaded successfully on {self.device}")
        self._is_ready = True
    
    async def process(self, audio_data: Union[bytes, np.ndarray], **kwargs) -> str:
        """
        处理音频数据并返回识别的文本
        
        Args:
            audio_data: 音频数据，可以是原始字节或numpy数组
            kwargs: 额外参数，可包含：
                - language: 覆盖默认语言设置
                
        Returns:
            识别的文本字符串
        """
        if not self.is_ready():
            raise RuntimeError("Whisper STT service not initialized")
            
        self.logger.info("Processing audio data with Whisper")
        loop = asyncio.get_running_loop()
        
        # 处理不同格式的音频输入
        if isinstance(audio_data, bytes):
            # 保存为临时文件
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(audio_data)
            
            # 使用Whisper处理音频文件
            language = kwargs.get('language', self.config.get('language'))
            result = await loop.run_in_executor(
                None,
                lambda: self._transcribe_audio(temp_path, language)
            )
            os.unlink(temp_path)
            
        else: 
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
                sample_rate = kwargs.get('sample_rate', self.DEFAULT_SAMPLE_RATE)
                sf.write(temp_path, audio_data, sample_rate)
            # 使用Whisper处理音频文件
            language = kwargs.get('language', self.config.get('language'))
            result = await loop.run_in_executor(
                None,
                lambda: self._transcribe_audio(temp_path, language)
            )
            os.unlink(temp_path)
        
        self.logger.info(f"Successfully recognized audio with Whisper: '{result[:50]}...' (truncated)")
        return result
    
    def _transcribe_audio(self, audio_path, language=None):
        """
        使用Whisper模型转录音频
        
        Args:
            audio_path: 音频文件路径
            language: 语言代码，如'zh'表示中文
            
        Returns:
            识别的文本字符串
        """
        # 转录选项
        options = {}
        if language:
            options["language"] = language
        
        # 执行转录
        result = self.model.transcribe(audio_path, **options)
        
        # 返回转录文本
        return result["text"].strip()
    
    async def shutdown(self):
        """释放资源"""
        self.logger.info("Shutting down Whisper STT service")
        self.model = None
        self._is_ready = False
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        await super().shutdown()
