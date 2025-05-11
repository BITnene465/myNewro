import os
import asyncio
import aiohttp
import base64
from pathlib import Path
from typing import Dict, Any, Union, List, Optional

from .base import BaseService

class TTSService(BaseService):
    """
    基于GPTsoVITS的文本转语音服务
    """
    def __init__(self, service_name: str = "tts", config: Dict[str, Any] = None):
        """
        初始化GPTsoVITS TTS服务
        
        Args:
            service_name: 服务名称
            config: 配置字典，包含：
                - api_base_url: GPTsoVITS API基础URL
                - speaker_id: 默认说话人ID
                - emotion: 情感参数 (0-1之间)
                - speed: 语速 (0.5-2.0之间)
                - audio_format: 输出音频格式 (wav, mp3)
                - default_refer_wav_path: 默认参考音频路径
                - default_prompt_text: 默认参考音频文本
                - default_prompt_language: 默认参考音频语种
                - text_language: 默认合成文本语种
                - top_k: GPT参数
                - top_p: GPT参数
                - temperature: GPT参数
                - cut_punc: 切分符号
        """
        if config is None:
            config = {
                "api_base_url": "http://localhost:9880",          
                "speed": 1.0,                                      # 默认语速
                "audio_format": "wav",                             
                "default_refer_wav_path": None,                   
                "default_prompt_text": None,                       
                "default_prompt_language": "zh",                   
                "text_language": "zh",                           
                "top_k": 20,                                       
                "top_p": 0.7,                                      
                "temperature": 0.6,                               
                "cut_punc": None,                                 
            }
        super().__init__(service_name, config)
        print(self.config)
        self.api_session = None
        self.logger.info(f"GPTsoVITS TTS Service created with config: {config}")
    
    
    
    async def initialize(self):
        """
        初始化TTS服务，连接GPTsoVITS API并设置默认参考音频
        """
        self.logger.info("Initializing GPTsoVITS TTS service...")
        
        try:
            # 创建API会话
            self.api_session = aiohttp.ClientSession()
            self._is_ready = True
                
        except aiohttp.ClientError as e:
            self.logger.error(f"Network error during initialization: {e}")
            # 关闭会话以防资源泄露
            if self.api_session:
                await self.api_session.close()
                self.api_session = None
            raise
                
        except Exception as e:
            self.logger.error(f"Failed to initialize GPTsoVITS TTS service: {e}")
            # 关闭会话以防资源泄露
            if self.api_session:
                await self.api_session.close()
                self.api_session = None
            raise
    
    def _build_tts_params(self, text: str, **kwargs) -> Dict[str, Any]:
        """
        构建TTS请求参数
        
        Args:
            text: 要合成的文本
            **kwargs: 额外参数
            
        Returns:
            Dict[str, Any]: 构建好的参数字典
        """
        # 基础参数
        params = {
            "text": text,
            "text_language": kwargs.get("text_language", self.config.get("text_language", "zh")),
            "speed": kwargs.get("speed", self.config.get("speed", 1.0)),
        }
        # 添加参考音频相关参数
        refer_wav_path = kwargs.get("refer_wav_path", self.config.get("default_refer_wav_path"))
        if refer_wav_path:
            params["refer_wav_path"] = refer_wav_path
            params["prompt_text"] = kwargs.get("prompt_text", self.config.get("default_prompt_text"))
            params["prompt_language"] = kwargs.get("prompt_language", self.config.get("default_prompt_language", "zh"))
        # 添加GPT参数
        top_k = kwargs.get("top_k", self.config.get("top_k"))
        if top_k is not None:
            params["top_k"] = top_k
        top_p = kwargs.get("top_p", self.config.get("top_p"))
        if top_p is not None:
            params["top_p"] = top_p
        temperature = kwargs.get("temperature", self.config.get("temperature"))
        if temperature is not None:
            params["temperature"] = temperature
        # 添加切分符号
        cut_punc = kwargs.get("cut_punc", self.config.get("cut_punc"))
        if cut_punc:
            params["cut_punc"] = cut_punc
        # 添加额外参考音频
        inp_refs = kwargs.get("inp_refs")
        if inp_refs:
            params["inp_refs"] = inp_refs
        return params
    
    async def process(self, text: str, **kwargs) -> Union[bytes, Dict[str, Any]]:
        """
        将文本转换为语音
        
        Args:
            text: 要转换为语音的文本
            **kwargs: 额外参数，可包含：
                - refer_wav_path: 参考音频路径
                - prompt_text: 参考音频文本
                - prompt_language: 参考音频语种
                - text_language: 合成文本语种
                - speed: 语速 (0.5-2.0)
                - top_k: GPT参数
                - top_p: GPT参数
                - temperature: GPT参数
                - format: 输出格式 (wav, ogg, aac)
                - cut_punc: 切分符号
                - inp_refs: 额外参考音频列表
        
        Returns:
            音频数据（字节流）或包含音频数据和元信息的字典
        """
        if not self.is_ready():
            self.logger.error("GPTsoVITS TTS service not initialized")
            raise RuntimeError("GPTsoVITS TTS service not initialized")
        
        self.logger.info(f"Processing text for speech synthesis: '{text[:50]}...'")
        
        try:
            base_url = self.config.get("api_base_url")
            # 构建请求参数
            params = self._build_tts_params(text, **kwargs)
            
            audio_format = kwargs.get("audio_format", self.config.get("audio_format", "wav"))
            # 发送请求
            self.logger.debug(f"Sending TTS request to {base_url} with params: {params}")
            
            async with self.api_session.post(
                base_url,
                json=params,
                timeout=50  # 合成时间要久一点
            ) as response:
                if response.status == 400:
                    error_message = await response.json().get("message", "Unknown error")
                    raise RuntimeError(f"API request failed with status {response.status}: {error_message}")
                
                elif response.status == 200:
                    # 读取音频数据
                    audio_data = await response.read()
                    result = {
                        "audio_data": audio_data,
                        "audio_format": audio_format,
                        "text_source": text
                    }
                    self.logger.info(f"Successfully synthesized speech: {len(result['audio_data'])/1024:.2f} KB")
                    return result
                
                else:
                    error_text = await response.text()
                    raise RuntimeError(f"API request failed with status {response.status}: {error_text}")
        
        except aiohttp.ClientError as e:    
            self.logger.error(f"Network error during TTS request: {e}")
            raise ConnectionError(f"Network error during TTS request: {e}")
                
        except Exception as e:
            self.logger.error(f"Error synthesizing speech: {e}")
            raise
    
    async def change_default_refer(self, refer_wav_path: str, prompt_text: str, prompt_language: str = "zh") -> bool:
        """
        更改默认参考音频设置
        Args:
            refer_wav_path: 参考音频路径
            prompt_text: 参考音频文本
            prompt_language: 参考音频语种
            
        Returns:
            bool: 是否成功更改
        """
        if not self.is_ready():
            self.logger.error("GPTsoVITS TTS service not initialized")
            raise RuntimeError("GPTsoVITS TTS service not initialized")
            
        try:
            # 构建请求参数
            params = {
                "refer_wav_path": refer_wav_path,
                "prompt_text": prompt_text,
                "prompt_language": prompt_language
            }
            
            # 发送请求
            base_url = self.config.get("api_base_url")
            async with self.api_session.post(
                f"{base_url}/change_refer",
                json=params,
                timeout=20
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"Failed to change default refer: {error_text}")
                
                # 更新本地配置
                self.config["default_refer_wav_path"] = refer_wav_path
                self.config["default_prompt_text"] = prompt_text
                self.config["default_prompt_language"] = prompt_language
                
                self.logger.info(f"Successfully changed default refer to {refer_wav_path}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error changing default refer: {e}")
            raise
    
    async def restart_service(self) -> bool:
        """
        重启GPTsoVITS服务
        
        Returns:
            bool: 是否成功发送重启命令
        """
        if not self.is_ready():
            self.logger.error("GPTsoVITS TTS service not initialized")
            raise RuntimeError("GPTsoVITS TTS service not initialized")
            
        try:
            # 发送重启命令
            base_url = self.config.get("api_base_url")
            async with self.api_session.post(
                f"{base_url}/control",
                json={"command": "restart"},
                timeout=5
            ) as response:
                # 不检查响应，因为服务可能会立即重启导致连接关闭
                self.logger.info("Restart command sent to GPTsoVITS service")
                return True
                
        except Exception as e:
            self.logger.error(f"Error sending restart command: {e}")
            return False
    
    async def shutdown(self):
        """释放资源"""
        self.logger.info("Shutting down GPTsoVITS TTS service") 
        # 关闭API会话
        if self.api_session:
            await self.api_session.close()
            self.api_session = None
        self._is_ready = False
        await super().shutdown()
