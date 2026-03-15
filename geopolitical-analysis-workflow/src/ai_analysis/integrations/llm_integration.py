"""
大语言模型集成模块
提供统一的LLM接口，支持Anthropic Claude和OpenAI GPT系列
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import hashlib
import pickle
from enum import Enum

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    import openai
except ImportError:
    openai = None

from src.api.config import settings

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """LLM提供商"""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    LOCAL = "local"


class LLMModel(Enum):
    """支持的LLM模型"""
    # Anthropic Claude系列
    CLAUDE_3_OPUS = "claude-3-opus-20240229"
    CLAUDE_3_SONNET = "claude-3-sonnet-20240229"
    CLAUDE_3_HAIKU = "claude-3-haiku-20240307"
    CLAUDE_3_5_SONNET = "claude-3-5-sonnet-20240620"

    # OpenAI GPT系列
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_3_5_TURBO = "gpt-3.5-turbo"

    # 本地模型（如有）
    LLAMA_3_70B = "llama-3-70b"
    MIXTRAL_8x7B = "mixtral-8x7b"


@dataclass
class LLMResponse:
    """LLM响应"""
    content: str
    raw_response: Any
    model: str
    provider: LLMProvider
    usage: Dict[str, int] = field(default_factory=dict)  # tokens使用情况
    latency: float = 0.0  # 响应延迟（秒）
    cached: bool = False  # 是否来自缓存


@dataclass
class LLMRequest:
    """LLM请求"""
    prompt: str
    system_prompt: Optional[str] = None
    model: Union[str, LLMModel] = LLMModel.CLAUDE_3_SONNET
    provider: LLMProvider = LLMProvider.ANTHROPIC
    temperature: float = 0.1
    max_tokens: int = 4000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_sequences: Optional[List[str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class LLMError(Exception):
    """LLM错误"""
    pass


class BaseLLMClient(ABC):
    """LLM客户端基类"""

    def __init__(self, provider: LLMProvider):
        self.provider = provider
        self._cache: Dict[str, tuple[LLMResponse, datetime]] = {}
        self._cache_ttl = timedelta(hours=1)  # 缓存1小时
        self._total_requests = 0
        self._total_errors = 0
        self.logger = logging.getLogger(f"{__name__}.{provider.value}")

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """生成文本"""
        pass

    async def generate_stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """流式生成文本"""
        # 默认实现：非流式生成然后返回
        response = await self.generate(request)
        yield response.content

    def _get_cache_key(self, request: LLMRequest) -> str:
        """生成缓存键"""
        cache_data = {
            "prompt": request.prompt,
            "system_prompt": request.system_prompt,
            "model": request.model.value if isinstance(request.model, LLMModel) else request.model,
            "provider": request.provider.value,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_str.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[LLMResponse]:
        """从缓存获取响应"""
        if cache_key in self._cache:
            response, timestamp = self._cache[cache_key]
            if datetime.now() - timestamp < self._cache_ttl:
                response.cached = True
                self.logger.debug(f"从缓存获取响应: {cache_key[:16]}...")
                return response
            else:
                # 缓存过期
                del self._cache[cache_key]
        return None

    def _save_to_cache(self, cache_key: str, response: LLMResponse):
        """保存响应到缓存"""
        self._cache[cache_key] = (response, datetime.now())
        # 限制缓存大小
        if len(self._cache) > 1000:
            # 删除最早的缓存
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]

    async def generate_with_cache(self, request: LLMRequest) -> LLMResponse:
        """带缓存的文本生成"""
        cache_key = self._get_cache_key(request)

        # 检查缓存
        cached_response = self._get_from_cache(cache_key)
        if cached_response and request.metadata.get("use_cache", True):
            return cached_response

        # 调用LLM
        start_time = datetime.now()
        try:
            response = await self.generate(request)
            response.latency = (datetime.now() - start_time).total_seconds()

            # 保存到缓存
            self._save_to_cache(cache_key, response)
            self._total_requests += 1

            return response

        except Exception as e:
            self._total_errors += 1
            self.logger.error(f"LLM生成失败: {str(e)}")
            raise LLMError(f"{self.provider.value} 生成失败: {str(e)}")

    def get_stats(self) -> Dict[str, Any]:
        """获取客户端统计信息"""
        return {
            "provider": self.provider.value,
            "total_requests": self._total_requests,
            "total_errors": self._total_errors,
            "cache_size": len(self._cache),
            "error_rate": self._total_errors / max(self._total_requests, 1)
        }


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude客户端"""

    def __init__(self):
        super().__init__(LLMProvider.ANTHROPIC)

        if anthropic is None:
            raise ImportError("anthropic包未安装，请运行: pip install anthropic")

        api_key = settings.ANTHROPIC_API_KEY
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY未配置，请在.env文件中设置")

        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.logger.info("Anthropic客户端初始化完成")

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """生成文本（Anthropic Claude）"""
        try:
            # 构建消息
            messages = []
            if request.system_prompt:
                messages.append({
                    "role": "system",
                    "content": request.system_prompt
                })

            messages.append({
                "role": "user",
                "content": request.prompt
            })

            # 调用API
            model_name = request.model.value if isinstance(request.model, LLMModel) else request.model

            response = await self.client.messages.create(
                model=model_name,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                top_p=request.top_p,
                stop_sequences=request.stop_sequences
            )

            # 解析响应
            content = ""
            for content_block in response.content:
                if content_block.type == "text":
                    content += content_block.text

            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            }

            return LLMResponse(
                content=content,
                raw_response=response,
                model=model_name,
                provider=self.provider,
                usage=usage
            )

        except anthropic.APIConnectionError as e:
            raise LLMError(f"Anthropic API连接失败: {str(e)}")
        except anthropic.RateLimitError as e:
            raise LLMError(f"Anthropic API速率限制: {str(e)}")
        except anthropic.APIStatusError as e:
            raise LLMError(f"Anthropic API状态错误: {str(e)}")
        except Exception as e:
            raise LLMError(f"Anthropic API调用失败: {str(e)}")


class OpenAIClient(BaseLLMClient):
    """OpenAI GPT客户端"""

    def __init__(self):
        super().__init__(LLMProvider.OPENAI)

        if openai is None:
            raise ImportError("openai包未安装，请运行: pip install openai")

        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OPENAI_API_KEY未配置，请在.env文件中设置")

        self.client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=settings.OPENAI_BASE_URL
        )
        self.logger.info("OpenAI客户端初始化完成")

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """生成文本（OpenAI GPT）"""
        try:
            # 构建消息
            messages = []
            if request.system_prompt:
                messages.append({
                    "role": "system",
                    "content": request.system_prompt
                })

            messages.append({
                "role": "user",
                "content": request.prompt
            })

            # 调用API
            model_name = request.model.value if isinstance(request.model, LLMModel) else request.model

            response = await self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                top_p=request.top_p,
                frequency_penalty=request.frequency_penalty,
                presence_penalty=request.presence_penalty,
                stop=request.stop_sequences
            )

            # 解析响应
            content = response.choices[0].message.content or ""

            usage = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0
            }

            return LLMResponse(
                content=content,
                raw_response=response,
                model=model_name,
                provider=self.provider,
                usage=usage
            )

        except openai.APIConnectionError as e:
            raise LLMError(f"OpenAI API连接失败: {str(e)}")
        except openai.RateLimitError as e:
            raise LLMError(f"OpenAI API速率限制: {str(e)}")
        except openai.APIStatusError as e:
            raise LLMError(f"OpenAI API状态错误: {str(e)}")
        except Exception as e:
            raise LLMError(f"OpenAI API调用失败: {str(e)}")


class LLMManager:
    """LLM管理器（工厂模式）"""

    _instances: Dict[LLMProvider, BaseLLMClient] = {}

    @classmethod
    async def get_client(cls, provider: LLMProvider = LLMProvider.ANTHROPIC) -> BaseLLMClient:
        """获取LLM客户端实例"""
        if provider not in cls._instances:
            try:
                if provider == LLMProvider.ANTHROPIC:
                    cls._instances[provider] = AnthropicClient()
                elif provider == LLMProvider.OPENAI:
                    cls._instances[provider] = OpenAIClient()
                else:
                    raise ValueError(f"不支持的LLM提供商: {provider}")

                logger.info(f"创建LLM客户端: {provider.value}")
            except Exception as e:
                logger.error(f"创建LLM客户端失败: {provider.value}, 错误: {str(e)}")
                # 尝试回退到其他提供商
                if provider == LLMProvider.ANTHROPIC:
                    return await cls.get_client(LLMProvider.OPENAI)
                elif provider == LLMProvider.OPENAI:
                    return await cls.get_client(LLMProvider.ANTHROPIC)
                else:
                    raise LLMError(f"无法创建任何LLM客户端: {str(e)}")

        return cls._instances[provider]

    @classmethod
    async def generate_text(
        cls,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Union[str, LLMModel] = LLMModel.CLAUDE_3_SONNET,
        provider: LLMProvider = LLMProvider.ANTHROPIC,
        **kwargs
    ) -> str:
        """生成文本（简化接口）"""
        request = LLMRequest(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            provider=provider,
            **kwargs
        )

        client = await cls.get_client(provider)
        response = await client.generate_with_cache(request)

        return response.content

    @classmethod
    async def generate_structured(
        cls,
        prompt: str,
        output_schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        model: Union[str, LLMModel] = LLMModel.CLAUDE_3_SONNET,
        provider: LLMProvider = LLMProvider.ANTHROPIC,
        **kwargs
    ) -> Dict[str, Any]:
        """生成结构化输出"""
        # 在提示中添加输出格式要求
        format_prompt = f"""{prompt}

请严格按照以下JSON格式输出：
```json
{json.dumps(output_schema, indent=2, ensure_ascii=False)}
```

请只输出JSON，不要包含其他内容。"""

        request = LLMRequest(
            prompt=format_prompt,
            system_prompt=system_prompt,
            model=model,
            provider=provider,
            **kwargs
        )

        client = await cls.get_client(provider)
        response = await client.generate_with_cache(request)

        # 尝试解析JSON
        try:
            # 提取JSON部分（可能包含markdown代码块）
            content = response.content.strip()
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
            else:
                json_str = content

            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {response.content[:200]}...")
            raise LLMError(f"无法解析LLM响应为JSON: {str(e)}")

    @classmethod
    def get_all_stats(cls) -> Dict[str, Any]:
        """获取所有LLM客户端的统计信息"""
        stats = {}
        for provider, client in cls._instances.items():
            stats[provider.value] = client.get_stats()
        return stats


# 全局LLM管理器实例
_llm_manager: Optional[LLMManager] = None


async def get_llm_manager() -> LLMManager:
    """获取LLM管理器实例"""
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMManager()
    return _llm_manager