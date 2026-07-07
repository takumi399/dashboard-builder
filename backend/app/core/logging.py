"""
结构化日志配置 —— 使用 structlog 输出 JSON 格式日志。

日志字段：timestamp, level, module, message, 以及自定义上下文。
"""

import logging
import structlog
from typing import Any


def setup_logging() -> None:
    """配置 structlog + 标准 logging 集成，输出 JSON 格式。"""
    # ── 标准 logging 桥接到 structlog ──
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # 设置标准 logging 的 handler，让 uvicorn 等也输出结构化日志
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter('{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(name)s", "message": "%(message)s"}')
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)


def get_logger(name: str) -> Any:
    """返回结构化日志 logger。"""
    return structlog.get_logger(name)
