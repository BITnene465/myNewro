# -*- coding: utf-8 -*-
import os
import asyncio
import aiohttp
import base64
from pathlib import Path
from typing import Dict, Any, Union, List, Optional

from ..base import BaseService

class GPTsovitsService(BaseService):
    """
    基于GPTsoVITS的文本转语音服务，适配api_v2.py接口
    """
    def __init__(self, service_name: str = "tts", config: Dict[str, Any] = None):
        """
        初始化GPTsoVITS TTS服务
        
        Args:
            service_name: 服务名称
            config: 配置字典，包含：
                - api_base_url: GPTsoVITS API基础URL
                - text_language: 默认文本语言 (zh, en, ja等)
                - prompt_language: 默认参考音频语言
                - ref_audio_path: 默认参考音频路径
                - prompt_text: 默认参考音频文本
                - speed_factor: 语速 (0.5-2.0之间)
                - audio_format: 输出音频格式 (wav, mp3, ogg, aac)
                - top_k: GPT参数
                - top_p: GPT参数
                - temperature: GPT参数
                - text_split_method: 文本分割方法
        """
       
        config_default = {
            "api_base_url": "http://localhost:9880",          
            "text_language": "zh",                           
            "prompt_language": "zh",                   
            "ref_audio_path": "",                   
            "prompt_text": "",                       
            "speed_factor": 1.0,
            "audio_format": "wav",                             
            "top_k": 5,                                       
            "top_p": 0.7,                                      
            "temperature": 0.8,
            "text_split_method": "cut5",
            "batch_size": 8,
            "repetition_penalty": 1.35,
        }
        # 合并默认配置和用户提供的配置
        if config is None:
            config = {}
        config = {**config_default, **config}  # 保证用户config的优先级更高
        super().__init__(service_name, config)
        self.api_session = None
        self.logger.info(f"GPTsoVITS TTS Service created with config: {config}")
    
    async def initialize(self):
        """
        初始化TTS服务，连接GPTsoVITS API
        """
        self.logger.info("Initializing GPTsoVITS TTS service...")
        
        try:
            # 创建API会话
            self.api_session = aiohttp.ClientSession()
            # 测试API连接 ( important！ 需要在原本 api_v2.py 中手动添加 /health 路由)
            base_url = self.config.get("api_base_url")
            async with self.api_session.get(f"{base_url}/health") as response:
                if response.status != 200:
                    raise RuntimeError(f"Failed to connect to GPTsoVITS API: {response.status}")
                # 检查API是否准备就绪
                health_info = await response.json()
                if not health_info.get("ready", False):
                    raise RuntimeError("GPTsoVITS API is not ready")
                self.logger.info("GPTsoVITS TTS service initialized successfully")
            self.set_ready()
                
        except aiohttp.ClientError as e:
            self.logger.error(f"Network error during initialization: {e}")
            if self.api_session:
                await self.api_session.close()
                self.api_session = None
            raise
                
        except Exception as e:
            self.logger.error(f"Failed to initialize GPTsoVITS TTS service: {e}")
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
            "text_lang": kwargs.get("text_language", self.config.get("text_language", "zh")),
            "ref_audio_path": kwargs.get("ref_audio_path", self.config.get("ref_audio_path")),
            "prompt_lang": kwargs.get("prompt_language", self.config.get("prompt_language", "zh")),
            "prompt_text": kwargs.get("prompt_text", self.config.get("prompt_text", "")),
            "speed_factor": kwargs.get("speed_factor", self.config.get("speed_factor", 1.0)),
            "top_k": kwargs.get("top_k", self.config.get("top_k", 5)),
            "top_p": kwargs.get("top_p", self.config.get("top_p", 0.7)),
            "temperature": kwargs.get("temperature", self.config.get("temperature", 0.6)),
            "text_split_method": kwargs.get("text_split_method", self.config.get("text_split_method", "cut5")),
            "batch_size": kwargs.get("batch_size", self.config.get("batch_size", 1)),
            "repetition_penalty": kwargs.get("repetition_penalty", self.config.get("repetition_penalty", 1.35)),
            "media_type": kwargs.get("audio_format", self.config.get("audio_format", "wav")),
        }
        # 添加辅助参考音频
        aux_ref_audio_paths = kwargs.get("aux_ref_audio_paths")
        if aux_ref_audio_paths:
            params["aux_ref_audio_paths"] = aux_ref_audio_paths
        # 添加流式响应参数
        if kwargs.get("streaming", False):
            params["streaming_mode"] = True
            
        return params
    
    async def process(self, text: str, **kwargs) -> Union[bytes, Dict[str, Any]]:
        """
        将文本转换为语音
        
        Args:
            text: 要转换为语音的文本
            **kwargs: 额外参数，可包含：
                - ref_audio_path: 参考音频路径
                - prompt_text: 参考音频文本
                - prompt_language: 参考音频语种
                - text_language: 合成文本语种
                - speed_factor: 语速 (0.5-2.0)
                - top_k: GPT参数
                - top_p: GPT参数
                - temperature: GPT参数
                - audio_format: 输出格式 (wav, ogg, aac)
                - streaming: 是否启用流式响应
                - text_split_method: 文本分割方法
                - aux_ref_audio_paths: 辅助参考音频列表
        
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
            self.logger.debug(f"Sending TTS request to {base_url}/tts with params: {params}")
            # 使用POST请求
            async with self.api_session.post(
                f"{base_url}/tts",
                json=params,
                timeout=60  # 合成时间可能较长
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"API request failed with status {response.status}: {error_text}")
                
                # 读取音频数据
                audio_data = await response.read()  # 此处为 wav 音频流
                result = {
                    "audio_data":  base64.b64encode(audio_data).decode('utf-8'),  # base64编码，方便转化为json格式
                    "audio_format": audio_format,
                    # "text_source": text  # 去掉text_source字段
                }
                self.logger.info(f"Successfully synthesized speech: {len(result['audio_data'])/1024:.2f} KB")
                return result
        
        except aiohttp.ClientError as e:    
            self.logger.error(f"Network error during TTS request: {e}")
            raise ConnectionError(f"Network error during TTS request: {e}")
                
        except Exception as e:
            self.logger.error(f"Error synthesizing speech: {e}")
            raise
    
    async def set_gpt_weights(self, weights_path: str) -> bool:
        """
        设置GPT模型权重
        
        Args:
            weights_path: 权重文件路径
            
        Returns:
            bool: 是否成功设置
        """
        if not self.is_ready():
            self.logger.error("GPTsoVITS TTS service not initialized")
            raise RuntimeError("GPTsoVITS TTS service not initialized")
            
        try:
            # 发送请求
            base_url = self.config.get("api_base_url")
            async with self.api_session.get(
                f"{base_url}/set_gpt_weights",
                params={"weights_path": weights_path},
                timeout=30
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"Failed to set GPT weights: {error_text}")
                
                self.logger.info(f"Successfully set GPT weights to {weights_path}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error setting GPT weights: {e}")
            raise
    
    async def set_sovits_weights(self, weights_path: str) -> bool:
        """
        设置SoVITS模型权重
        
        Args:
            weights_path: 权重文件路径
            
        Returns:
            bool: 是否成功设置
        """
        if not self.is_ready():
            self.logger.error("GPTsoVITS TTS service not initialized")
            raise RuntimeError("GPTsoVITS TTS service not initialized")
            
        try:
            # 发送请求
            base_url = self.config.get("api_base_url")
            async with self.api_session.get(
                f"{base_url}/set_sovits_weights",
                params={"weights_path": weights_path},
                timeout=30
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"Failed to set SoVITS weights: {error_text}")
                
                self.logger.info(f"Successfully set SoVITS weights to {weights_path}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error setting SoVITS weights: {e}")
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
            async with self.api_session.get(
                f"{base_url}/control",
                params={"command": "restart"},
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
        await super().shutdown()
        # 关闭API会话
        self.logger("shuting down the api session...")
        if self.api_session:
            await self.api_session.close()
            self.api_session = None
