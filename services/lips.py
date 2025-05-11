import os
import json
import asyncio
from typing import Dict, Any, List, Optional, Union, Iterator
from pathlib import Path

from .base import BaseService

class LipSyncService(BaseService):
    """ 唇形同步的计算服务 """
    def __init__(self, service_name: str="lips", config: Dict[str, Any]=None):
        super().__init__(service_name, config)
        self.model = self._load_model(config['model_path'])
        
    async def _load_model(self, model_path: str):
        return None
        
    async def initialize(self):
        # 加载本地模型即可，不使用 http 连接
        return super().initialize()
    
    async def process(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        super().process(data, **kwargs)
        return None
    
    async def shutdown(self):
        # 释放资源
        super().shutdown()
        self.model = None 
        return self._is_ready
        