from typing import Dict, Any ,Optional, List, Union
from pathlib import Path
import aiohttp
import os

from ..base import BaseService

class LocalModelService(BaseService):
    """
    基于本地模型服务器或者远程模型服务器的服务。api 适配 NewroLLMServer 
    """
    def __init__(self, service_name: str = "NewroLLMService", config: Dict[str, Any] = None):
        super().__init__(service_name, config)
        config_default = {
                "api_key": "",   # 目前暂时没有加入身份验证
                "api_base_url": "http://localhost:10721",
                "model_name": "Qwen3-1.7B",  
                "temperature": 0.8,
                "max_tokens": 2000,
                "top_p": 0.9,
                "enable_thinking": False,
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
        初始化LLM服务，与 Newro LLM server建立 http session并且测试连接
        """
        self.logger.info("Initializing LLM service...")
        try:
            api_base = self.config.get("api_base_url")
            api_key = self.config.get("api_key")
            # 创建客户端
            self.client = NewroLLMClient(api_base, api_key)
            # 测试连接
            ready = await self.client.check_health()
            if not ready:
                raise RuntimeError("LLM Server is not ready")
            self.set_ready()
            
            # 选择初始模型
            model_name = self.config.get("model_name")
            if not model_name:
                raise ValueError("initial Model name is required")
            model_name = await self.client.switch_model(model_name)   # 没写 await，查bug查半天
            self.logger.info(f"LLM service initialized with model: {model_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize LLM service: {e}")
            if self.client:
                await self.client.close()
                self.client = None
            raise
        finally:
            self.logger.info("LLM service initialized successfully")
    
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
            enable_thinking = kwargs.get("enable_thinking", self.config.get("enable_thinking", False))
            # 构建消息
            messages = self._get_history_messages(session_id, text)
            # ai 生成
            response_content = await self._process_normal(model, messages, temperature, max_tokens, top_p, enable_thinking)
            # 将AI的回复添加到历史消息中
            if session_id in self.history_messages and response_content is not None:
                self.history_messages[session_id].append({"role": "assistant", "content": response_content})
            return response_content
        except Exception as e:
            self.logger.error(msg=f"Error calling api: {e}")
            
    
    async def _process_normal(self, model: str, messages: List[Dict[str, str]], 
                             temperature: float=0.7, max_tokens: int=2000, top_p: float=0.8, enable_thinking=False) -> str:
        """
        非流式处理API请求
        
        Args:
            model: 模型名称
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大生成令牌数
            top_p: Top-p采样参数
            
        Returns:
            str: AI生成的文本
        """
        try:
            content = await self.client.chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                enable_thinking=enable_thinking,
            )
            self.logger.info(f"Successfully got response from LLM API: '{content[:50]}...'")
            return content
        except Exception as e:
            self.logger.error(f"Error in _process_normal: {e}")
            raise
    
    async def shutdown(self):
        """释放资源"""
        await super().shutdown()
        # 关闭客户端连接
        if self.client is not None:
            await self.client.close()
            self.client = None
            

class NewroLLMClient:
    """
    用于与 Newro LLM Server 进行通信的客户端
    """
    def __init__(self, api_base_url: str, api_key: Optional[str] = None):
        self.api_base_url = api_base_url
        self.api_key = api_key  # 暂时不考虑加入身份验证
        self.session = aiohttp.ClientSession()
    
    async def chat_completion(self, messages: List[Dict[str, str]], 
                              model: str, temperature: float, max_tokens: int, top_p: float, enable_thinking: bool=False) -> str:
        """
        调用聊天补全API
        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大生成令牌数
            top_p: Top-p采样参数
        Returns:
            str: AI生成的文本
        """
        url = f"{self.api_base_url}/chat/completions"
        # TODO 之后考虑加入身份验证
        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "enable_thinking": enable_thinking,
        }
        
        async with self.session.post(url, json=data) as response:
            if response.status != 200:
                raise Exception(f"Error {response.status}: {await response.text()}")
            result = await response.json()
            return result.get("content", "")
    
    async def check_health(self) -> bool:
        """
        检查服务是否可用
        Returns:
            bool: 如果服务可用，则返回True，否则返回False
        """
        url = f"{self.api_base_url}/health"
        async with self.session.get(url) as response:
            if response.status != 200:
                return False
            result = await response.json()
            return result.get("ready") == True
                
    async def switch_model(self, model_name: str):
        """
        切换模型
        Args:
            model: 模型名称
        """
        async with self.session.post(f"{self.api_base_url}/models/switch", json={"model_name": model_name}) as response:
            if response.status != 200:
                raise Exception(f"Error {response.status}: {await response.text()}")
            response_data = await response.json()
            # print("response_data", response_data)
            return response_data.get("current_model")
    
    async def get_model_list(self) -> List[str]:
        """
        获取可用模型列表
        Returns:
            List[str]: 模型名称列表
        """
        url = f"{self.api_base_url}/models/list"
        async with self.session.get(url) as response:
            if response.status != 200:
                raise Exception(f"Error {response.status}: {await response.text()}")
            result = await response.json()
            return result.get("models", [])
    
    
    async def close(self):
        await self.session.close()  # session 是需要显式关闭的资源
        self.session = None