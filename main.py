# -*- coding: utf-8 -*-
# main.py - 네이버 검색 API 사용 (초고속 버전!)

import sys
import asyncio

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import asyncio
import uuid
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
from pathlib import Path
import urllib.request
import json

from master_analyzer import run_master_analysis

app = FastAPI(title="Review Intelligence API")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 작업 상태 저장소
jobs: Dict[str, Dict[str, Any]] = {}

# 환경변수
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "friends292198@gmail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "nqgpfqlpfuijioua ")

# 🔥 네이버 API 키 (블로그 크롤러에서 재사용!)
try:
    from naver_blog_crawler import NAVER_CLIENT_ID, NAVER_CLIENT_SECRET
    print("✅ 블로그 크롤러 API 키 import 성공!")
except:
    # 폴백: 환경변수 또는 직접 입력
    NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "ZLPHHehmKYVHcF2hUGhQ")
    NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "NrVaQLeDfV")


# ==================== Request Models ====================

class AnalyzeRequest(BaseModel):
    store_name: str
    email: str


# ==================== 🚀 네이버 검색 API (초고속!) ====================

def search_naver_places_api(query: str, display: int = 10) -> List[Dict[str, str]]:
    """
    네이버 검색 API 사용 (Local Search)
    
    속도: 0.1-0.5초 ⚡
    제한: 일 25,000건
    
    반환 형식:
    [
        {
            "name": "스케줄청담",
            "address": "서울특별시 강남구 청담동",
            "category": "양식>프랑스음식"
        },
        ...
    ]
    """
    try:
        # API 키 체크
        if NAVER_CLIENT_ID == "YOUR_CLIENT_ID":
            print("⚠️  네이버 API 키가 설정되지 않았습니다!")
            return []
        
        # URL 인코딩
        encText = urllib.parse.quote(query)
        url = f"https://openapi.naver.com/v1/search/local.json?query={encText}&display={display}&start=1&sort=random"
        
        # API 요청
        request = urllib.request.Request(url)
        request.add_header("X-Naver-Client-Id", NAVER_CLIENT_ID)
        request.add_header("X-Naver-Client-Secret", NAVER_CLIENT_SECRET)
        
        response = urllib.request.urlopen(request)
        rescode = response.getcode()
        
        if rescode == 200:
            response_body = response.read()
            data = json.loads(response_body.decode('utf-8'))
            
            results = []
            for item in data.get('items', []):
                # HTML 태그 제거
                name = item['title'].replace('<b>', '').replace('</b>', '')
                address = item.get('roadAddress', item.get('address', ''))
                category = item.get('category', '음식점')
                
                # 카테고리 정제 (예: "음식점>한식>육류,고기요리" → "육류,고기요리")
                if '>' in category:
                    category = category.split('>')[-1]
                
                results.append({
                    "name": name,
                    "address": address,
                    "category": category
                })
            
            print(f"✅ 네이버 API 검색 성공: {len(results)}개")
            return results
        else:
            print(f"❌ API 오류 코드: {rescode}")
            return []
    
    except Exception as e:
        print(f"❌ 네이버 API 오류: {e}")
        return []


# ==================== Email Function ====================

def send_email_with_report(to_email: str, store_name: str, html_file: str) -> bool:
    """HTML 리포트를 이메일로 전송"""
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_EMAIL
        msg['To'] = to_email
        msg['Subject'] = f"[Review Intelligence] {store_name} 분석 리포트"
        
        body = f"""
안녕하세요!

{store_name}의 리뷰 분석이 완료되었습니다.

📊 리포트 내용:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 네이버 플레이스 리뷰 수집 및 분석
✅ 위치/업종 기반 경쟁사 자동 분석
✅ AI 인사이트 (GPT + Claude 하이브리드)
✅ 장점/단점 키워드 추출
✅ 실행 가능한 체크리스트
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📎 첨부된 HTML 파일을 브라우저로 열어서
   상세한 분석 결과를 확인하세요!

💡 차트와 그래프가 포함된 인터랙티브 리포트입니다.

감사합니다,
Review Intelligence 팀
        """
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # HTML 파일 첨부
        if os.path.exists(html_file):
            with open(html_file, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                filename = os.path.basename(html_file)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{filename}"'
                )
                msg.attach(part)
        
        # 전송
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
        
        print(f"✅ 이메일 전송 완료: {to_email}")
        return True
    
    except Exception as e:
        print(f"❌ 이메일 전송 실패: {e}")
        return False


# ==================== Background Task ====================

async def analyze_and_send(job_id: str, store_name: str, email: str):
    """백그라운드 분석 작업"""
    try:
        print(f"\n{'='*70}")
        print(f"🚀 분석 시작")
        print(f"{'='*70}")
        print(f"   가게명: {store_name}")
        print(f"   이메일: {email}")
        print(f"{'='*70}\n")
        
        jobs[job_id]['status'] = 'processing'
        jobs[job_id]['progress'] = '🔍 네이버 플레이스에서 가게 검색 중...'
        
        jobs[job_id]['progress'] = '🕷️ 리뷰 크롤링 중... (1-2분 소요)'
        
        result = await run_master_analysis(store_name, store_name)
        
        if not result:
            jobs[job_id]['status'] = 'failed'
            jobs[job_id]['error'] = f'"{store_name}" 가게를 찾을 수 없습니다. 정확한 가게명을 입력해주세요.'
            print(f"❌ 가게를 찾을 수 없음: {store_name}")
            return
        
        jobs[job_id]['progress'] = '🏪 경쟁사 분석 중...'
        await asyncio.sleep(2)
        
        jobs[job_id]['progress'] = '🤖 AI 인사이트 생성 중... (GPT + Claude)'
        await asyncio.sleep(3)
        
        jobs[job_id]['progress'] = '📊 HTML 리포트 생성 중...'
        
        # HTML 파일 찾기
        timestamp = datetime.now().strftime('%Y%m%d')
        store_name_clean = store_name.replace(' ', '_')
        
        patterns = [
            f'report_{store_name_clean}*{timestamp}*.html',
            f'hybrid_report_{store_name_clean}*{timestamp}*.html',
            f'unified_report_{store_name_clean}*{timestamp}*.html',
            f'ultimate_report_{store_name_clean}*{timestamp}*.html',
            f'*{store_name_clean}*.html'
        ]
        
        html_file = None
        for pattern in patterns:
            files = sorted(
                Path('.').glob(pattern),
                key=os.path.getmtime,
                reverse=True
            )
            if files:
                html_file = str(files[0])
                print(f"✅ HTML 리포트 발견: {html_file}")
                break
        
        if not html_file:
            jobs[job_id]['status'] = 'failed'
            jobs[job_id]['error'] = 'HTML 리포트 생성에 실패했습니다.'
            print(f"❌ HTML 파일을 찾을 수 없음")
            return
        
        jobs[job_id]['progress'] = '📧 이메일 전송 중...'
        
        success = send_email_with_report(email, store_name, html_file)
        
        if success:
            jobs[job_id]['status'] = 'completed'
            jobs[job_id]['progress'] = '완료! 이메일을 확인하세요.'
            jobs[job_id]['result'] = {
                'email': email,
                'html_file': html_file,
                'message': f'{email}로 리포트를 전송했습니다!'
            }
            print(f"\n{'='*70}")
            print(f"✅ 전체 프로세스 완료!")
            print(f"{'='*70}\n")
        else:
            jobs[job_id]['status'] = 'failed'
            jobs[job_id]['error'] = '리포트는 생성되었으나 이메일 전송에 실패했습니다.'
    
    except Exception as e:
        print(f"\n{'='*70}")
        print(f"❌ 오류 발생: {e}")
        print(f"{'='*70}\n")
        import traceback
        traceback.print_exc()
        
        jobs[job_id]['status'] = 'failed'
        jobs[job_id]['error'] = f'분석 중 오류 발생: {str(e)}'


# ==================== API Endpoints ====================

@app.get("/")
async def root():
    """API 상태 확인"""
    return {
        "service": "Review Intelligence API",
        "version": "2.0.0",
        "status": "running",
        "description": "네이버 플레이스 리뷰 AI 분석 시스템",
        "features": [
            "🚀 네이버 검색 API 직접 연동 (초고속!)",
            "🕷️ 리뷰 자동 크롤링",
            "🏪 경쟁사 자동 분석",
            "🤖 AI 인사이트 (GPT + Claude)",
            "📊 HTML 리포트 생성",
            "📧 이메일 전송"
        ],
        "api_status": {
            "naver_api": "✅ 활성화" if NAVER_CLIENT_ID != "YOUR_CLIENT_ID" else "⚠️ API 키 필요"
        },
        "endpoints": {
            "search": "GET /api/search-stores?q=가게명",
            "analyze": "POST /api/analyze",
            "job_status": "GET /api/job/{job_id}",
            "all_jobs": "GET /api/jobs"
        }
    }


@app.get("/api/search-stores")
async def search_stores(q: str):
    """
    🚀 네이버 검색 API 사용 (초고속!)
    
    Parameters:
    - q: 검색어 (최소 2글자)
    
    Returns:
    - results: 가게 목록 (최대 10개)
    
    Example:
    /api/search-stores?q=스케줄청담
    
    Response:
    {
        "query": "스케줄청담",
        "count": 5,
        "results": [
            {
                "name": "스케줄청담",
                "address": "서울 강남구 청담동",
                "category": "프랑스음식"
            },
            ...
        ],
        "elapsed": "0.23초"
    }
    """
    # 입력 검증
    if not q or len(q) < 2:
        return {
            "query": q,
            "count": 0,
            "results": [],
            "message": "검색어는 최소 2글자 이상이어야 합니다."
        }
    
    try:
        import time
        start_time = time.time()
        
        print(f"🔍 네이버 API 검색: {q}")
        
        # 네이버 검색 API 호출 (초고속!)
        results = search_naver_places_api(q, display=10)
        
        elapsed = time.time() - start_time
        
        print(f"✅ 검색 완료: {len(results)}개 ({elapsed:.2f}초)")
        
        return {
            "query": q,
            "count": len(results),
            "results": results,
            "elapsed": f"{elapsed:.2f}초"
        }
    
    except Exception as e:
        print(f"❌ 검색 실패: {e}")
        return {
            "query": q,
            "count": 0,
            "results": [],
            "error": str(e)
        }


@app.post("/api/analyze")
async def analyze(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """가게 분석 시작"""
    job_id = str(uuid.uuid4())
    
    jobs[job_id] = {
        "status": "queued",
        "progress": "대기 중...",
        "created_at": datetime.now().isoformat(),
        "store_name": request.store_name,
        "email": request.email
    }
    
    print(f"\n📝 새로운 분석 요청")
    print(f"   Job ID: {job_id}")
    print(f"   가게: {request.store_name}")
    print(f"   이메일: {request.email}\n")
    
    background_tasks.add_task(
        analyze_and_send,
        job_id,
        request.store_name,
        request.email
    )
    
    return {
        "success": True,
        "job_id": job_id,
        "message": "분석이 시작되었습니다. 2-3분 후 이메일을 확인하세요."
    }


@app.get("/api/job/{job_id}")
async def get_job_status(job_id: str):
    """작업 상태 확인"""
    if job_id not in jobs:
        return {
            "error": "작업을 찾을 수 없습니다.",
            "job_id": job_id
        }
    
    job = jobs[job_id]
    return {
        "job_id": job_id,
        "status": job['status'],
        "progress": job.get('progress', ''),
        "error": job.get('error'),
        "result": job.get('result')
    }


@app.get("/api/jobs")
async def get_all_jobs():
    """모든 작업 목록"""
    return {
        "total": len(jobs),
        "jobs": [
            {
                "job_id": jid,
                "store_name": job.get('store_name'),
                "email": job.get('email'),
                "status": job['status'],
                "created_at": job.get('created_at')
            }
            for jid, job in list(jobs.items())[-10:]
        ]
    }


# ==================== Main ====================

if __name__ == "__main__":
    import uvicorn
    
    print("""
╔══════════════════════════════════════════════════════════════════╗
║          🚀 Review Intelligence API Server v2.0                  ║
║          네이버 검색 API 직접 연동 (초고속!)                       ║
╚══════════════════════════════════════════════════════════════════╝

✨ NEW! 네이버 검색 API 사용 (크롤링 → API)
   속도: 2-3초 → 0.1-0.5초 ⚡
   안정성: 불안정 → 매우 안정
   제한: 일 25,000건 (무료)

📂 설정 방법:
   1. https://developers.naver.com/ 접속
   2. 애플리케이션 등록 (1분)
   3. 환경변수 설정:
      Windows CMD:
      setx NAVER_CLIENT_ID "YOUR_CLIENT_ID"
      setx NAVER_CLIENT_SECRET "YOUR_CLIENT_SECRET"
      
      또는 코드에 직접 입력:
      NAVER_CLIENT_ID = "YOUR_CLIENT_ID"
      NAVER_CLIENT_SECRET = "YOUR_CLIENT_SECRET"

📂 사용하는 기존 파일들:
   ✅ master_analyzer.py          - 메인 오케스트레이터
   ✅ mvp_analyzer.py              - 네이버 플레이스 크롤링
   ✅ competitor_search.py         - 경쟁사 자동 검색
   ✅ hybrid_insight_engine.py     - GPT + Claude AI 분석
   ✅ seoul_industry_reviews.db    - 데이터베이스

🌐 서버 시작:
   python run_server.py
   → http://localhost:8000
    """)
    
    # API 키 확인
    if NAVER_CLIENT_ID == "YOUR_CLIENT_ID":
        print("⚠️  경고: 네이버 API 키가 설정되지 않았습니다!")
        print("   자동완성 기능이 작동하지 않습니다.")
        print("   https://developers.naver.com/ 에서 발급받으세요!\n")
    else:
        print(f"✅ 네이버 API 활성화: {NAVER_CLIENT_ID[:10]}...\n")
    
    # 이메일 확인
    if SMTP_EMAIL == "your-email@gmail.com":
        print("⚠️  경고: 이메일 환경변수가 설정되지 않았습니다!")
        print("   setx SMTP_EMAIL \"your-email@gmail.com\"")
        print("   setx SMTP_PASSWORD \"your-app-password\"\n")
    else:
        print(f"✅ 이메일 설정됨: {SMTP_EMAIL}\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)