"""
服务模块的基类定义
"""
import asyncio
import logging
from abc import ABC, abstractmethod  # 用来实现抽象类
from typing import Any, Dict

class BaseService(ABC):
    """
    所有服务的抽象基类。
    """
    def __init__(self, service_name: str, config: Dict[str, Any]):
        self.service_name = service_name
        self.config = config
        self.logger = logging.getLogger(f"service.{self.service_name}")
        self.logger.info(f"Initializing service: {self.service_name} with config: {config}")
        self._is_ready = False

    @abstractmethod
    async def initialize(self):
        """
        异步初始化服务，例如加载模型、连接外部API等。
        """
        self.logger.info(f"Service {self.service_name} initialized.")
        self._is_ready = True

    @abstractmethod
    async def process(self, data: Any, **kwargs) -> Any:
        """
        处理输入数据并返回结果。
        具体的输入输出类型由子类定义。
        """
        if not self.is_ready():
            self.logger.error(f"Service {self.service_name} is not ready. Call initialize() first.")
            raise RuntimeError(f"Service {self.service_name} not initialized.")
        pass

    async def shutdown(self):
        """
        关闭服务，释放资源。
        """
        self.logger.info(f"Shutting down service: {self.service_name}")
        self._is_ready = False

    def is_ready(self) -> bool:
        """
        检查服务是否已准备好处理请求。
        """
        return self._is_ready
    
    def set_ready(self) -> None:
        self._is_ready = True
    
    def set_not_ready(self) -> None:
        self._is_ready = False
    

    def get_status(self) -> Dict[str, Any]:
        """
        获取服务的当前状态。
        """
        return {
            "service_name": self.service_name,
            "is_ready": self._is_ready,
            "config": self.config
        }
