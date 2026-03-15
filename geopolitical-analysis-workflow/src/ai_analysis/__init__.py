"""
地缘政治分析AI分析模块
提供多源数据智能分析功能
"""

from .core.base_analyzer import (
    BaseAnalyzer,
    AnalyzerConfig,
    AnalysisResult,
    AnalysisError
)

from .analyzers.ais_analyzer import AISAnalyzer
from .analyzers.adsb_analyzer import ADS_BAnalyzer
from .analyzers.military_analyzer import MilitaryAnalyzer
from .analyzers.fusion_analyzer import FusionAnalyzer

from .integrations.llm_integration import (
    LLMManager,
    LLMProvider,
    LLMModel,
    LLMRequest,
    LLMResponse
)

from .core.analysis_manager import (
    AnalysisManager,
    AnalysisType,
    AnalysisRequest,
    get_analysis_manager,
    start_analysis,
    stop_analysis,
    analyze_data,
    analyze_multimodal_data,
    get_analysis_status
)

__version__ = "0.1.0"
__all__ = [
    # 基础类
    "BaseAnalyzer",
    "AnalyzerConfig",
    "AnalysisResult",
    "AnalysisError",

    # 分析器
    "AISAnalyzer",
    "ADS_BAnalyzer",
    "MilitaryAnalyzer",
    "FusionAnalyzer",

    # LLM集成
    "LLMManager",
    "LLMProvider",
    "LLMModel",
    "LLMRequest",
    "LLMResponse",

    # 分析管理器
    "AnalysisManager",
    "AnalysisType",
    "AnalysisRequest",
    "get_analysis_manager",
    "start_analysis",
    "stop_analysis",
    "analyze_data",
    "analyze_multimodal_data",
    "get_analysis_status"
]