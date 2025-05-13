import os
import json
import asyncio
from typing import Dict, Any, List, Optional, Union, Iterator
from pathlib import Path
from openai import AsyncOpenAI, APIError, APIConnectionError, RateLimitError

from ..base import BaseService

class OpenaiService(BaseService):
    """
    支持 Openai API 的 LLM 服务
    """
    
    def __init__(self, service_name: str = "openaiLLM", config: Dict[str, Any] = None):
        """
        初始化LLM服务
        
        Args:
            service_name: 服务名称
            config: 配置字典，包含：
                - api_key: API密钥
                - api_base: API基础URL (DeepSeek或OpenAI)
                - model: 模型名称
                - system_prompt: 系统提示词
                - system_prompt_file: 系统提示词文件路径（如果提供，将覆盖system_prompt）
                - temperature: 温度参数，控制随机性
                - max_tokens: 最大生成token数
                - top_p: top-p采样参数
                - stream: 是否使用流式响应
        """
        config_default = {
                "api_key": os.environ.get("OPENAI_API_KEY", ""),
                "api_base_url": "https://api.deepseek.com/v1",
                "model": "deepseek-chat",  # DeepSeek默认模型
                "temperature": 0.8,
                "max_tokens": 2000,
                "top_p": 0.9,
                "stream": False
            }
        if config is None:
            config = {}
        config = {**config_default, **config} 
        super().__init__(service_name, config)
        self.client = None
        self.system_prompt = self._load_system_prompt()
        self.history_messages = {}  # 根据 session_id 为key索引的历史消息
        
        # print(self.config)
        self.logger.info(f"LLM Service created with model: {self.config.get('model')}")
    
    def _load_system_prompt(self) -> str:
        """加载系统提示词"""
        # 检查是否有提示词文件
        sys_prompt = self.config.get("system_prompt")
        if sys_prompt is not None:
            return sys_prompt
        
        sys_prompt_file = self.config.get("system_prompt_file")
        if sys_prompt_file is not None and os.path.exists(sys_prompt_file):
            with open(sys_prompt_file, "r", encoding="utf-8") as f:
                return f.read().strip()
    
        return "你是虚拟主播小田，是一个新人出道的虚拟up主。"
    
    def _get_history_messages(self, session_id: str, new_text=None) -> List[Dict[str, str]]:
        """
        Args:
            session_id: 会话ID
            new_text: 新的用户输入文本（可选）
        Returns:
            List[Dict[str, str]]: 历史消息列表
        """
        if session_id not in self.history_messages:
            if self.system_prompt:
                self.history_messages[session_id] = [{"role": "system", "content": self.system_prompt}]
            else: 
                self.history_messages[session_id] = []
        if new_text is not None:
            # 添加用户消息
            self.history_messages[session_id].append({"role": "user", "content": new_text})
        return self.history_messages[session_id]
            
        
    
    async def initialize(self):
        """
        初始化LLM服务，创建OpenAI客户端
        """
        self.logger.info("Initializing LLM service...")
        
        try:
            # 创建OpenAI客户端，配置为使用DeepSeek API
            api_key = self.config.get("api_key")
            api_base_url = self.config.get("api_base_url")
            if not api_key:
                self.logger.warning("No API key provided. API calls may fail.")
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url=api_base_url
            )
            # 测试API连接
            result = await self.test_connection()
            if result:
                self.logger.info("Successfully connected to LLM API.")
                self.set_ready()
            else:
                self.logger.error("Failed to connect to LLM API.")
                raise ConnectionError("Could not connect to LLM API. Check your API key and URL.")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize LLM service: {e}")
            raise
    
    async def test_connection(self) -> bool:
        """
        测试API连接
        
        Returns:
            bool: 连接是否成功
        """
        try:
            # 使用OpenAI客户端的models.list方法测试连接
            models = await self.client.models.list()
            return True
        except APIConnectionError as e:
            self.logger.error(f"API connection error: {e}")
            return False
        except APIError as e:
            self.logger.error(f"API error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error testing API connection: {e}")
            return False
    
    async def process(self, text: str, session_id: str, **kwargs) -> str:
        """
        处理用户文本并返回AI响应
        
        Args:
            text: 用户输入文本
            **kwargs: 额外参数，可覆盖默认配置

        Returns:
            str: AI生成的回复文本
        """
        if not self.is_ready():
            self.logger.error("LLM service not initialized")
            raise RuntimeError("LLM service not initialized")
        
        self.logger.info(f"Processing text with LLM: '{text[:50]}...'")
        
        try:
            # 合并配置和请求特定参数
            model = kwargs.get("model", self.config.get("model"))
            temperature = kwargs.get("temperature", self.config.get("temperature", 0.7))
            max_tokens = kwargs.get("max_tokens", self.config.get("max_tokens", 2000))
            top_p = kwargs.get("top_p", self.config.get("top_p", 0.9))
            stream_mode = kwargs.get("stream", self.config.get("stream", False))
            # 构建消息
            messages = self._get_history_messages(session_id, text)
            # 使用OpenAI客户端调用API
            if stream_mode:
                # todo: 目前流式有 bug，还是不要使用
                response_content = await self._process_stream(model, messages, temperature, max_tokens, top_p)
            else:
                response_content = await self._process_normal(model, messages, temperature, max_tokens, top_p)
            
            # 将AI的回复添加到历史消息中
            if session_id in self.history_messages and response_content is not None:
                self.history_messages[session_id].append({"role": "assistant", "content": response_content})
            return response_content
                
        except RateLimitError as e:
            self.logger.error(f"Rate limit exceeded: {e}")
            raise RuntimeError(f"API rate limit exceeded: {e}")
        except APIError as e:
            self.logger.error(f"API error: {e}")
            raise RuntimeError(f"API error: {e}")
        except Exception as e:
            self.logger.error(f"Error calling LLM API: {e}")
            raise
    
    async def _process_normal(self, model: str, messages: List[Dict[str, str]], 
                             temperature: float, max_tokens: int, top_p: float) -> str:
        """
        处理普通（非流式）API请求
        
        Args:
            model: 模型名称
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大生成令牌数
            top_p: Top-p采样参数
            
        Returns:
            str: AI生成的文本
        """
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p
        )
        
        content = response.choices[0].message.content
        self.logger.info(f"Successfully got response from LLM API: '{content[:50]}...'")
        return content
    
    async def _process_stream(self, model: str, messages: List[Dict[str, str]], 
                             temperature: float, max_tokens: int, top_p: float) -> str:
        """
        处理流式API请求
        
        Args:
            model: 模型名称
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大生成令牌数
            top_p: Top-p采样参数
            
        Returns:
            str: 完整的AI生成文本
        """
        response_stream = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stream=True
        )
        
        full_response = []
        async for chunk in response_stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response.append(content)
        
        final_response = "".join(full_response)
        self.logger.info(f"Successfully completed stream from LLM API: '{final_response[:50]}...'")
        return final_response
    
    async def shutdown(self):
        """释放资源"""
        await super().shutdown()
        self.logger.info("shutting down the llm client session")
        if self.client is not None:
            await self.client.close()
            self.client = None
