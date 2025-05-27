# services/factory.py
import importlib
from typing import Type, cast
from services.base import BaseService
from config import settings 
import logging

logger = logging.getLogger(__name__)

def get_service_instance(service_category: str) -> BaseService:
    """
    根据配置创建并返回指定服务类别的实例 (例如 "stt", "llm", "tts").
    """
    if not hasattr(settings, "SERVICES") or service_category not in settings.SERVICES:
        raise ValueError(f"服务类别 '{service_category}' 未在 settings.SERVICES 中配置。")

    category_config = settings.SERVICES[service_category]
    active_provider_name = category_config.get("active_provider")

    if not active_provider_name:
        raise ValueError(f"服务类别 '{service_category}' 未指定 'active_provider'。")

    if active_provider_name not in category_config.get("providers", {}):
        raise ValueError(f"提供商 '{active_provider_name}' 未在服务类别 '{service_category}' 的 'providers' 中配置。")

    provider_config = category_config["providers"][active_provider_name]
    class_path = provider_config.get("class")
    specific_config = provider_config.get("config", {})
    service_name = provider_config.get("service_name", f"{service_category.upper()}_{active_provider_name.upper()}")

    if not class_path:
        raise ValueError(f"提供商 '{active_provider_name}' (服务类别 '{service_category}') 未指定 'class' 路径。")

    try:
        module_path, class_name = class_path.rsplit('.', 1)
        module = importlib.import_module(module_path)
        service_class = cast(Type[BaseService], getattr(module, class_name))
    except (ImportError, AttributeError, ValueError) as e:
        logger.error(f"无法导入服务类 '{class_path}': {e}", exc_info=True)
        raise ImportError(f"无法导入服务类 '{class_path}': {e}")

    logger.info(f"为服务类别 '{service_category}' 创建提供商 '{active_provider_name}' (类: {class_path}) 的实例。")
    return service_class(service_name=service_name, config=specific_config)