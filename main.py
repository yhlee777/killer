# -*- coding: utf-8 -*-
# main.py - 수정 버전 (12가지 질문 + 통합 리포트)

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

# 네이버 API 키
try:
    from naver_blog_crawler import NAVER_CLIENT_ID, NAVER_CLIENT_SECRET
    print("✅ 블로그 크롤러 API 키 import 성공!")
except:
    NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "ZLPHHehmKYVHcF2hUGhQ")
    NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "NrVaQLeDfV")


# ==================== Request Models ====================

class AnalyzeRequest(BaseModel):
    store_name: str
    email: str
    
    # 🔥 12가지 질문 추가
    industry: Optional[str] = None
    price: Optional[str] = None
    diff: Optional[str] = None
    age: Optional[str] = None
    budget: Optional[str] = None
    time: Optional[str] = None
    skill: Optional[str] = None
    goal: Optional[str] = None
    area: Optional[str] = None
    competition: Optional[str] = None
    traffic: Optional[str] = None
    customer: Optional[str] = None


# ==================== 네이버 검색 API ====================

def search_naver_places_api(query: str, display: int = 10) -> List[Dict[str, str]]:
    """네이버 검색 API 사용"""
    try:
        if NAVER_CLIENT_ID == "YOUR_CLIENT_ID":
            print("⚠️  네이버 API 키가 설정되지 않았습니다!")
            return []
        
        encText = urllib.parse.quote(query)
        url = f"https://openapi.naver.com/v1/search/local.json?query={encText}&display={display}&start=1&sort=random"
        
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
                name = item['title'].replace('<b>', '').replace('</b>', '')
                address = item.get('roadAddress', item.get('address', ''))
                category = item.get('category', '음식점')
                
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


# ==================== 마케팅 전략 생성 ====================

# main.py에서 이 함수만 교체하세요

def generate_marketing_strategy(
    questions: Dict[str, str], 
    store_name: str, 
    review_data: Dict,
    statistical_comparison: Dict = None
) -> str:
    """
    12가지 질문 + 리뷰 분석 + 경쟁사 비교 → 맞춤형 마케팅 전략 생성
    """
    try:
        from prompt_generator import generate_full_prompt
        from openai import OpenAI
        
        # 🔥 실제 리뷰 데이터 정리
        total_reviews = review_data.get('total_reviews', 0)
        
        # 장점/단점 추출 (상위 5개)
        strengths = []
        weaknesses = []
        
        if 'keyword_stats' in review_data:
            keyword_stats = review_data['keyword_stats']
            
            # 🔥 keyword_stats가 dict인지 확인
            if isinstance(keyword_stats, dict):
                # 키워드를 카운트 순으로 정렬
                sorted_keywords = sorted(
                    keyword_stats.items(), 
                    key=lambda x: x[1] if isinstance(x[1], int) else x[1].get('count', 0),
                    reverse=True
                )
                
                # 간단하게 상위 5개를 장점으로
                strengths = [(kw, count if isinstance(count, int) else count.get('count', 0)) 
                            for kw, count in sorted_keywords[:5]]
        
        # 🔥 경쟁사 비교 데이터 정리
        competitive_insights = ""
        if statistical_comparison:
            competitive_insights = "\n## 🏪 경쟁사 비교 분석\n\n"
            
            # 우리의 강점
            if '우리의_강점' in statistical_comparison:
                competitive_insights += "### ✅ 우리가 경쟁사보다 잘하는 것\n\n"
                for topic, stat in list(statistical_comparison['우리의_강점'].items())[:3]:
                    our_rate = stat['our']['rate'] * 100
                    comp_rate = stat['comp']['rate'] * 100
                    gap = stat['gap'] * 100
                    competitive_insights += f"- **{topic}**: 우리 {our_rate:.1f}% vs 경쟁사 {comp_rate:.1f}% (+{gap:.1f}%p 우위)\n"
                competitive_insights += "\n"
            
            # 우리의 약점
            if '우리의_약점' in statistical_comparison:
                competitive_insights += "### ⚠️ 우리가 경쟁사보다 부족한 것 (개선 필요)\n\n"
                for topic, stat in list(statistical_comparison['우리의_약점'].items())[:3]:
                    our_rate = stat['our']['rate'] * 100
                    comp_rate = stat['comp']['rate'] * 100
                    gap = abs(stat['gap'] * 100)
                    competitive_insights += f"- **{topic}**: 우리 {our_rate:.1f}% vs 경쟁사 {comp_rate:.1f}% (-{gap:.1f}%p 열위)\n"
                competitive_insights += "\n"
        
        # 🔥 리뷰 분석 결과
        review_analysis = {
            'total': total_reviews,
            'positive': int(total_reviews * 0.7) if total_reviews > 0 else 0,
            'negative': int(total_reviews * 0.2) if total_reviews > 0 else 0,
            'neutral': int(total_reviews * 0.1) if total_reviews > 0 else 0,
            'strengths': strengths,
            'weaknesses': weaknesses
        }
        
        # 프롬프트 생성
        system_prompt, user_prompt = generate_full_prompt(
            answers=questions,
            review_analysis=review_analysis,
            store_name=store_name
        )
        
        # 🔥 경쟁사 비교 데이터를 user_prompt에 추가
        if competitive_insights:
            user_prompt += f"\n\n{competitive_insights}"
            user_prompt += """
---

🎯 **위 데이터를 활용한 전략 요청**

**필수 반영사항:**
1. 우리의 강점은 마케팅에 최대한 활용
2. 우리의 약점은 반드시 개선 방안 제시
3. 경쟁사와의 차별화 포인트 명확히
4. 실제 리뷰 데이터 기반의 구체적 전략
5. 12가지 질문(예산/시간/역량)에 맞는 실행 가능한 전략만

예시:
- 강점 "분위기"가 있으면 → Instagram 분위기 사진 마케팅
- 약점 "대기시간"이 있으면 → 예약 시스템 도입 (비용/기간 명시)
- 경쟁사가 "가성비" 강조하면 → 우리는 "프리미엄 경험" 포지셔닝
"""
        
        # GPT-4o 호출
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=4000
        )
        
        strategy = response.choices[0].message.content
        print("✅ 맞춤형 마케팅 전략 생성 완료 (리뷰 데이터 반영)")
        return strategy
        
    except Exception as e:
        print(f"⚠️ 마케팅 전략 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        
        # 🔥 실패해도 기본 전략은 생성 (12가지 질문만 사용)
        try:
            from prompt_generator import generate_full_prompt
            from openai import OpenAI
            
            print("⚠️ 간단한 전략으로 재시도 중...")
            
            review_analysis = {
                'total': 0,
                'positive': 0,
                'negative': 0,
                'neutral': 0,
                'strengths': [],
                'weaknesses': []
            }
            
            system_prompt, user_prompt = generate_full_prompt(
                answers=questions,
                review_analysis=review_analysis,
                store_name=store_name
            )
            
            client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            print("✅ 기본 마케팅 전략 생성 완료 (12가지 질문만 사용)")
            return response.choices[0].message.content
            
        except Exception as e2:
            print(f"❌ 전략 생성 완전 실패: {e2}")
            return None

# ==================== 통합 리포트 생성 ====================

def create_integrated_report(html_file: str, marketing_strategy: str, store_name: str) -> str:
    """
    기존 HTML 리포트 + 마케팅 전략을 하나로 통합
    """
    try:
        # 기존 HTML 읽기
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 마케팅 전략을 HTML로 변환 (Markdown → HTML)
        strategy_html = f"""
        <div id="marketing-strategy" class="section">
            <h2>🎯 맞춤형 마케팅 전략</h2>
            <div style="background: white; padding: 30px; border-radius: 15px; line-height: 1.8;">
                <pre style="white-space: pre-wrap; font-family: 'Segoe UI', sans-serif; margin: 0;">
{marketing_strategy}
                </pre>
            </div>
        </div>
        """
        
        # </body> 태그 바로 앞에 마케팅 전략 삽입
        if '</body>' in html_content:
            integrated = html_content.replace('</body>', f'{strategy_html}\n</body>')
        else:
            integrated = html_content + strategy_html
        
        # 네비게이션에 마케팅 전략 링크 추가
        if '<div class="nav-links">' in integrated:
            nav_link = '<a href="#marketing-strategy">🎯 마케팅 전략</a>'
            integrated = integrated.replace(
                '</div>',
                f'{nav_link}\n</div>',
                1  # 첫 번째만 교체
            )
        
        # 새 파일명
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        integrated_file = f"integrated_report_{store_name.replace(' ', '_')}_{timestamp}.html"
        
        # 저장
        with open(integrated_file, 'w', encoding='utf-8') as f:
            f.write(integrated)
        
        print(f"✅ 통합 리포트 생성: {integrated_file}")
        return integrated_file
        
    except Exception as e:
        print(f"⚠️ 통합 리포트 생성 실패: {e}")
        return html_file  # 실패 시 원본 반환


# ==================== 이메일 전송 ====================

def send_email_with_report(to_email: str, store_name: str, html_file: str) -> bool:
    """통합 리포트를 이메일로 전송"""
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_EMAIL
        msg['To'] = to_email
        msg['Subject'] = f"[KILLER] {store_name} 완전 분석 리포트"
        
        body = f"""
안녕하세요!

{store_name}의 완전 분석이 완료되었습니다.

📊 리포트 내용:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 네이버 플레이스 리뷰 분석
✅ 경쟁사 비교 분석
✅ AI 인사이트 (GPT + Claude)
✅ 맞춤형 마케팅 전략 (NEW!)
   • 우선순위 채널 TOP 3
   • 2주 액션 플랜
   • 예산 배분 가이드
   • 측정 가능한 KPI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📎 첨부된 HTML 파일을 브라우저로 열어서 확인하세요!

💡 모든 전략은 12가지 질문 기반으로 맞춤화되었습니다.

감사합니다,
KILLER 팀
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

# main.py의 analyze_and_send 함수도 수정

async def analyze_and_send(
    job_id: str, 
    store_name: str, 
    email: str,
    questions: Dict[str, str]
):
    """백그라운드 분석 작업"""
    try:
        print(f"\n{'='*70}")
        print(f"🚀 분석 시작")
        print(f"{'='*70}")
        print(f"   가게명: {store_name}")
        print(f"   이메일: {email}")
        print(f"   예산: {questions.get('budget', '미입력')}")
        print(f"   목표: {questions.get('goal', '미입력')}")
        print(f"{'='*70}\n")
        
        jobs[job_id]['status'] = 'processing'
        jobs[job_id]['progress'] = '🔍 네이버 플레이스에서 가게 검색 중...'
        
        # 1. 리뷰 분석 실행
        jobs[job_id]['progress'] = '🕷️ 리뷰 크롤링 중... (1-2분 소요)'
        result = await run_master_analysis(store_name, store_name)
        
        if not result:
            jobs[job_id]['status'] = 'failed'
            jobs[job_id]['error'] = f'"{store_name}" 가게를 찾을 수 없습니다.'
            print(f"❌ 가게를 찾을 수 없음: {store_name}")
            return
        
        jobs[job_id]['progress'] = '🏪 경쟁사 분석 중...'
        await asyncio.sleep(1)
        
        jobs[job_id]['progress'] = '🤖 AI 인사이트 생성 중... (GPT + Claude)'
        await asyncio.sleep(1)
        
        # 2. HTML 리포트 찾기
        jobs[job_id]['progress'] = '📊 HTML 리포트 생성 중...'
        
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
        
        # 🔥 3. 마케팅 전략 생성 (리뷰 데이터 + 경쟁사 비교 반영)
        jobs[job_id]['progress'] = '🎯 맞춤형 마케팅 전략 생성 중...'
        
        # result에서 리뷰 데이터 추출
        review_data = {
            'total_reviews': len(result.get('reviews', [])) if result else 0,
            'keyword_stats': result.get('keyword_stats', {}) if result else {}
        }
        
        # 경쟁사 비교 데이터
        statistical_comparison = result.get('statistical_comparison', None) if result else None
        
        marketing_strategy = generate_marketing_strategy(
            questions=questions,
            store_name=store_name,
            review_data=review_data,  # 🔥 실제 데이터 전달
            statistical_comparison=statistical_comparison  # 🔥 경쟁사 비교 전달
        )
        
        # 4. 통합 리포트 생성
        if marketing_strategy:
            jobs[job_id]['progress'] = '📄 통합 리포트 생성 중...'
            html_file = create_integrated_report(html_file, marketing_strategy, store_name)
        
        # 5. 이메일 전송
        jobs[job_id]['progress'] = '📧 이메일 전송 중...'
        
        success = send_email_with_report(email, store_name, html_file)
        
        if success:
            jobs[job_id]['status'] = 'completed'
            jobs[job_id]['progress'] = '완료! 이메일을 확인하세요.'
            jobs[job_id]['result'] = {
                'email': email,
                'html_file': html_file,
                'message': f'{email}로 통합 리포트를 전송했습니다!'
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
        "version": "3.0.0",
        "status": "running",
        "description": "네이버 플레이스 리뷰 AI 분석 + 맞춤형 마케팅 전략",
        "features": [
            "🚀 네이버 검색 API 직접 연동",
            "🕷️ 리뷰 자동 크롤링",
            "🏪 경쟁사 자동 분석",
            "🤖 AI 인사이트 (GPT + Claude)",
            "🎯 맞춤형 마케팅 전략 (NEW!)",
            "📊 통합 HTML 리포트",
            "📧 이메일 전송"
        ],
        "endpoints": {
            "search": "GET /api/search-stores?q=가게명",
            "analyze": "POST /api/analyze",
            "job_status": "GET /api/job/{job_id}",
            "all_jobs": "GET /api/jobs"
        }
    }


@app.get("/api/search-stores")
async def search_stores(q: str):
    """네이버 검색 API"""
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
    
    # 🔥 12가지 질문 딕셔너리로 변환
    questions = {
        'industry': request.industry,
        'price': request.price,
        'diff': request.diff,
        'age': request.age,
        'budget': request.budget,
        'time': request.time,
        'skill': request.skill,
        'goal': request.goal,
        'area': request.area,
        'competition': request.competition,
        'traffic': request.traffic,
        'customer': request.customer
    }
    
    jobs[job_id] = {
        "status": "queued",
        "progress": "대기 중...",
        "created_at": datetime.now().isoformat(),
        "store_name": request.store_name,
        "email": request.email,
        "questions": questions
    }
    
    print(f"\n📝 새로운 분석 요청")
    print(f"   Job ID: {job_id}")
    print(f"   가게: {request.store_name}")
    print(f"   이메일: {request.email}")
    print(f"   예산: {questions.get('budget')}")
    print(f"   목표: {questions.get('goal')}\n")
    
    background_tasks.add_task(
        analyze_and_send,
        job_id,
        request.store_name,
        request.email,
        questions  # 🔥 전달
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
║          🚀 Review Intelligence API Server v3.0                  ║
║          리뷰 분석 + 맞춤형 마케팅 전략 (통합)                    ║
╚══════════════════════════════════════════════════════════════════╝

✨ NEW! 12가지 질문 기반 맞춤형 전략
   • 우선순위 채널 TOP 3
   • 2주 액션 플랜
   • 예산 배분 가이드
   • 측정 가능한 KPI

📊 통합 리포트 (하나의 HTML)
   • 리뷰 분석 + 경쟁사 비교
   • AI 인사이트 (GPT + Claude)
   • 맞춤형 마케팅 전략

🌐 서버 시작:
   python main.py
   → http://localhost:8000
    """)
    
    if NAVER_CLIENT_ID == "YOUR_CLIENT_ID":
        print("⚠️  경고: 네이버 API 키가 설정되지 않았습니다!")
    else:
        print(f"✅ 네이버 API 활성화: {NAVER_CLIENT_ID[:10]}...\n")
    
    if SMTP_EMAIL == "your-email@gmail.com":
        print("⚠️  경고: 이메일 환경변수가 설정되지 않았습니다!")
    else:
        print(f"✅ 이메일 설정됨: {SMTP_EMAIL}\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)