# run_server.py
import sys
import asyncio

# Windows Playwright 오류 해결
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════╗
║          🚀 Review Intelligence Server (Windows 최적화)          ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Windows에서는 reload=False 권장
        log_level="info"
    )