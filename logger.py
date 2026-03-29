"""
日志记录器模块 - 记录运行日志
"""
import json
from datetime import datetime
from typing import Any, Dict, Optional

from config import LOG_DIR


class RunLogger:
    """运行日志记录器"""

    def __init__(self):
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = LOG_DIR / f"run_{self.run_id}.jsonl"

    def log(self, stage: str, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """记录日志"""
        payload = {
            "time": datetime.now().isoformat(timespec="seconds"),
            "stage": stage,
            "message": message,
            "extra": extra or {},
        }
        with self.log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        print(f"[{stage}] {message}")
