"""
API路由模块
"""

from . import data, system

# 尝试导入可选路由
try:
    from . import prediction
    PREDICTION_AVAILABLE = True
except ImportError:
    PREDICTION_AVAILABLE = False
    prediction = None

try:
    from . import analysis
    ANALYSIS_AVAILABLE = True
except ImportError:
    ANALYSIS_AVAILABLE = False
    analysis = None

try:
    from . import workflow
    WORKFLOW_AVAILABLE = True
except ImportError:
    WORKFLOW_AVAILABLE = False
    workflow = None

# 导出所有路由
__all__ = ["data", "system"]

if PREDICTION_AVAILABLE:
    __all__.append("prediction")

if ANALYSIS_AVAILABLE:
    __all__.append("analysis")

if WORKFLOW_AVAILABLE:
    __all__.append("workflow")