import os
import tempfile
import asyncio
from pathlib import Path
from typing import Any, Dict, Optional, Union
import torch
import torchaudio
import numpy as np
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor, AutoFeatureExtractor

from ..base import BaseService

class Wav2vecService(BaseService):
    """
    基于Hugging Face的Wav2Vec2模型
    """
    DEFAULT_MODEL_NAME = "jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn"
    DEFAULT_SAMPLE_RATE = 16000
    
    def __init__(self, service_name: str = "stt", config: Dict[str, Any] = None):
        """
        初始化STT服务
        Args:
            service_name: 服务名称
            config: 配置字典，可包含以下键：
                - model_name: Wav2Vec2模型名称
                - device: 计算设备 (cpu, cuda)
                - local_models_path: 本地模型存储路径
        """
        config_default = config = {
                "model_name": self.DEFAULT_MODEL_NAME,  
                "device": "cuda" if torch.cuda.is_available() else "cpu",  # 优先使用GPU
                "local_models_path": "models" 
            }
        if config is None:
            config = {}
        config = {**config_default, **config} 
        super().__init__(service_name, config)
        self.model = None
        self.processor = None
        self.device = torch.device(self.config["device"])
        self.logger.info(f"STT Service created with config: {config}")
    
    async def initialize(self):
        """
        初始化STT服务，加载Wav2Vec2模型和处理器
        首次运行时将模型下载到本地models文件夹中
        """
        self.logger.info("Initializing STT service with Wav2Vec2 model...")
        
        # 创建本地模型目录
        local_models_path = Path(self.config["local_models_path"]) / self.config["model_name"].split("/")[-1]
        os.makedirs(local_models_path, exist_ok=True)
        
        self.logger.info(f"Local models directory: {local_models_path}")
        
        try:
            # 获取当前运行的事件循环
            # 为什么要采用这种方式？因为模型加载相关函数使用huggingfac接口，只能同步运行，直接当作异步函数运行会阻塞主线程。所以采用多线程执行的方式（通过 run_in_executor() 让线程池调度相关的同步代码）
            loop = asyncio.get_running_loop()
            model_load_result = await loop.run_in_executor(
                None,
                lambda: self._load_model_and_processor(local_models_path)
            )
            
            self.model, self.processor = model_load_result
            self.model.to(self.device)
            
            self.logger.info(f"Wav2Vec2 model loaded successfully and moved to {self.device}")
            self._is_ready = True
        except Exception as e:
            self.logger.error(f"Failed to load Wav2Vec2 model: {e}")
            raise
    
    def _load_model_and_processor(self, local_path):
        """
        加载模型和处理器，如果本地存在则从本地加载，否则从Hugging Face下载
        Args:
            local_path: 本地模型存储路径

        Returns:
            元组: (model, processor)
        """
        try:
            # 尝试从本地加载
            self.logger.info(f"Attempting to load model from local path: {local_path}")
            if os.path.exists(local_path) and len(os.listdir(local_path)) > 0:
                self.logger.info("Loading model from local cache...")
                model = Wav2Vec2ForCTC.from_pretrained(local_path)
                processor = Wav2Vec2Processor.from_pretrained(local_path)
                self.logger.info("Model loaded from local cache successfully")
            else:
                # 从Hugging Face下载并保存到本地
                self.logger.info(f"Downloading model from Hugging Face: {self.config['model_name']}")
                model = Wav2Vec2ForCTC.from_pretrained(self.config["model_name"])
                processor = Wav2Vec2Processor.from_pretrained(self.config["model_name"])
                self.logger.info("Saving model to local cache...")
                model.save_pretrained(local_path)
                processor.save_pretrained(local_path)
                self.logger.info(f"Model saved to local cache: {local_path}")
            
            return model, processor
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            raise
    
    async def process(self, audio_data: Union[bytes, np.ndarray], **kwargs) -> str:
        """
        处理音频数据并返回识别的文本
        
        Args:
            audio_data: 音频数据，可以是原始字节或numpy数组
            kwargs: 额外参数，可包含：
                - sample_rate: 采样率（默认16000）
                
        Returns:
            识别的文本字符串
        """
        if not self.is_ready():
            self.logger.error("STT service not initialized")
            raise RuntimeError("STT service not initialized")
            
        self.logger.info("Processing audio data for speech recognition")
        try:
            # 获取当前运行的事件循环
            loop = asyncio.get_running_loop()
            # 处理音频数据
            if isinstance(audio_data, bytes): # 如果是字节流
                # 保存为临时文件
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    temp_path = temp_file.name
                    temp_file.write(audio_data)
                
                try:
                    # 读取音频文件
                    waveform, sample_rate = await loop.run_in_executor(
                        None, lambda: torchaudio.load(temp_path)
                    )
                finally:
                    # 删除临时文件
                    os.unlink(temp_path)
            else:
                # 如果是numpy数组，转换为PyTorch张量
                # 假设数据是单通道、16kHz采样率
                sample_rate = kwargs.get('sample_rate', self.DEFAULT_SAMPLE_RATE)
                waveform = torch.from_numpy(audio_data).float().unsqueeze(0)
            
            # 重采样到16kHz（如果需要）
            if sample_rate != self.DEFAULT_SAMPLE_RATE:
                self.logger.info(f"Resampling audio from {sample_rate}Hz to {self.DEFAULT_SAMPLE_RATE}Hz")
                resampler = torchaudio.transforms.Resample(orig_freq=sample_rate, new_freq=self.DEFAULT_SAMPLE_RATE)
                waveform = resampler(waveform)
            
            # 归一化音频（如果不是范围在-1到1之间）
            if waveform.abs().max() > 1.0:
                waveform = waveform / waveform.abs().max()
                
            # 在异步线程中处理推理
            result = await loop.run_in_executor(
                None,
                lambda: self._recognize_audio(waveform)
            )
            
            self.logger.info(f"Successfully recognized audio: '{result[:50]}...' (truncated)")
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing audio data: {e}")
            raise
    
    def _recognize_audio(self, waveform):
        """
        使用Wav2Vec2模型识别音频
        Args:
            waveform: PyTorch张量格式的音频波形 [channels, time]
        
        Returns:
            识别的文本字符串
        """
        # 确保在正确的设备上
        self.model.to(self.device)
        
        # 处理输入
        input_values = self.processor(waveform[0], return_tensors="pt", sampling_rate=self.DEFAULT_SAMPLE_RATE).input_values
        input_values = input_values.to(self.device)
        
        # 推理
        with torch.no_grad():
            logits = self.model(input_values).logits
        
        # 解码
        predicted_ids = torch.argmax(logits, dim=-1)
        transcription = self.processor.decode(predicted_ids[0])
        
        return transcription.strip()
    
    async def shutdown(self):
        """释放资源"""
        self.logger.info("Shutting down STT service")
        self.model = None
        self.processor = None
        self._is_ready = False
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        await super().shutdown()