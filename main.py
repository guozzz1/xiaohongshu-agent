"""
主入口文件 - 程序入口点
"""
import asyncio

from agent import XhsAgent


if __name__ == "__main__":
    # 立即执行每日管道
    asyncio.run(XhsAgent().run_daily_pipeline())
