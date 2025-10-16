# -*- coding: utf-8 -*-
# main.py - 13번째 질문 + 스티브 잡스 톤 + 리뷰 교차 분석 완전 통합

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
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "nqgpfqlpfuijioua")

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
    
    # 12가지 질문
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
    
    # 🔥 13번째 질문 (가중치 50%)
    current_marketing: Optional[List[str]] = []
    marketing_details: Optional[Dict[str, Dict[str, str]]] = {}


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


# ==================== 🔥 후킹 문장 생성 (스티브 잡스 톤) ====================

def generate_hook_sentence(
    review_data: Dict,
    statistical_comparison: Dict,
    questions: Dict,
    current_marketing: List[str]
) -> str:
    """
    스티브 잡스 톤 후킹 문장 생성
    
    템플릿 5가지:
    1. 강점 낭비: "당신의 {강점}은 경쟁사보다 {배수}배 우수합니다. 그런데 왜 {채널}이 없습니까?"
    2. 약점 방치: "{약점}에 고객이 불만입니다. 경쟁사는 해결했습니다. 당신은 언제 하실 겁니까?"
    3. 순서 지적: "오픈 {개월}개월. Instagram 팔로워 0명. 인플루언서부터 하십시오. 순서가 틀렸습니다."
    4. 현실 직시: "{강점}은 좋습니다. {약점}이 문제입니다. {본질적 진실}"
    5. 선택 강요: "두 가지 길이 있습니다. {A} 아니면 {B}. 선택하십시오."
    """
    try:
        from openai import OpenAI
        
        # 가장 큰 격차 찾기
        biggest_strength = None
        biggest_weakness = None
        
        if statistical_comparison:
            # 강점 중 최대
            if '우리의_강점' in statistical_comparison:
                strengths = statistical_comparison['우리의_강점']
                if strengths:
                    topic = list(strengths.keys())[0]
                    stat = strengths[topic]
                    biggest_strength = {
                        'topic': topic,
                        'our_rate': stat['our']['rate'] * 100,
                        'comp_rate': stat['comp']['rate'] * 100,
                        'gap': stat['gap'] * 100
                    }
            
            # 약점 중 최대
            if '우리의_약점' in statistical_comparison:
                weaknesses = statistical_comparison['우리의_약점']
                if weaknesses:
                    topic = list(weaknesses.keys())[0]
                    stat = weaknesses[topic]
                    biggest_weakness = {
                        'topic': topic,
                        'our_rate': stat['our']['rate'] * 100,
                        'comp_rate': stat['comp']['rate'] * 100,
                        'gap': stat['gap'] * 100
                    }
        
        # 사장님 상황
        open_period = questions.get('age', '정보 없음')
        budget = questions.get('budget', '0')
        has_instagram = 'instagram' in current_marketing
        has_nothing = 'none' in current_marketing or len(current_marketing) == 0
        
        # GPT-4o로 후킹 문장 생성
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        prompt = f"""
당신은 스티브 잡스입니다. 짧고 강렬하게 핵심을 찌릅니다.

**데이터:**
- 오픈 기간: {open_period}
- 예산: {budget}
- 현재 마케팅: {', '.join(current_marketing) if current_marketing else '없음'}
- 가장 큰 강점: {biggest_strength}
- 가장 큰 약점: {biggest_weakness}

**규칙:**
- 3문장 이내
- 각 문장 10단어 이내
- 질문 형태로 찌르기
- 숫자로 사실 제시
- 이모지 제거

**패턴 예시:**

패턴 1 (강점 낭비):
"당신의 [강점]은 경쟁사보다 [배수]배 우수합니다. 그런데 왜 [채널]이 없습니까?"

패턴 2 (약점 방치):
"[약점]에 고객이 불만입니다. 경쟁사는 해결했습니다. 당신은 언제 하실 겁니까?"

패턴 3 (순서 지적):
"오픈 [개월]개월. Instagram 팔로워 0명. 인플루언서부터 하십시오. 순서가 틀렸습니다."

패턴 4 (현실 직시):
"[강점]은 좋습니다. [약점]이 문제입니다. [본질적 진실]"

패턴 5 (선택 강요):
"두 가지 길이 있습니다. [A] 아니면 [B]. 선택하십시오."

가장 적합한 패턴을 선택하여 3문장으로 작성하세요.
"""
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "당신은 스티브 잡스입니다. 짧고 강렬하게 핵심을 찌릅니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=200
        )
        
        hook = response.choices[0].message.content.strip()
        print(f"✅ 후킹 문장 생성: {hook[:50]}...")
        return hook
        
    except Exception as e:
        print(f"⚠️ 후킹 문장 생성 실패: {e}")
        return "당신의 가게는 잠재력이 있습니다.\n지금이 기회입니다.\n시작하십시오."


# ==================== 🔥 리뷰 교차 분석 인사이트 ====================

def generate_review_insights(
    review_data: Dict,
    statistical_comparison: Dict
) -> str:
    """
    리뷰 교차 분석 인사이트 (10가지 패턴)
    
    패턴:
    1. 맛↑ 서비스↓ → "식사는 경험입니다"
    2. 분위기↑ 대기↓ → "기다림은 기대를 죽입니다"
    3. 가성비↑ 청결↓ → "싸도 더러우면 안 옵니다"
    4. 디저트↑ 메인↓ → "순서가 틀렸습니다"
    5. 분위기↑ 음식↓ → "Instagram은 한 번, 재방문은 맛"
    6. 직원↑ 사장↓ → "고객은 사장을 기억합니다"
    7. 평일↑ 주말↓ → "매출보다 품질입니다"
    8. 가격↓ 양↓ → "둘 다 아니면 화납니다"
    9. 혼자↑ 단체↓ → "타겟을 정하십시오"
    10. 재방문율 낮음 → "특별함이 없습니다"
    """
    try:
        from openai import OpenAI
        
        # 키워드 통계 정리
        keyword_stats = review_data.get('keyword_stats', {})
        
        # 경쟁사 비교에서 강점/약점 추출
        strengths_text = ""
        weaknesses_text = ""
        
        if statistical_comparison:
            if '우리의_강점' in statistical_comparison:
                strengths = list(statistical_comparison['우리의_강점'].items())[:3]
                strengths_text = ", ".join([topic for topic, _ in strengths])
            
            if '우리의_약점' in statistical_comparison:
                weaknesses = list(statistical_comparison['우리의_약점'].items())[:3]
                weaknesses_text = ", ".join([topic for topic, _ in weaknesses])
        
        # GPT-4o로 인사이트 생성
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        prompt = f"""
당신은 리뷰 분석 전문가입니다. 스티브 잡스의 톤으로 직설적으로 말합니다.

**데이터:**
- 강점: {strengths_text}
- 약점: {weaknesses_text}
- 키워드 통계: {list(keyword_stats.keys())[:10] if keyword_stats else '없음'}

**요구사항:**
10가지 패턴 중 2-3개를 선택하여 인사이트를 작성하세요.

**구조:**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 인사이트 #1

[강점]은/는 좋습니다.
[약점]이/가 문제입니다.

[본질을 꿰뚫는 한 문장]

개선:
[구체적 액션]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**톤:** 
- 짧은 문장
- 단도직입
- 본질 지적
- 이모지 없음
"""
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "스티브 잡스 톤. 본질을 찌릅니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        insights = response.choices[0].message.content.strip()
        print(f"✅ 리뷰 교차 분석 인사이트 생성 완료")
        return insights
        
    except Exception as e:
        print(f"⚠️ 리뷰 인사이트 생성 실패: {e}")
        return ""


# ==================== 🔥 13번째 질문 분석 ====================

def analyze_current_marketing(
    current_marketing: List[str],
    marketing_details: Dict[str, Dict[str, str]],
    questions: Dict[str, str]
) -> str:
    """
    현재 마케팅 활동 분석 (스티브 잡스 톤)
    """
    try:
        from openai import OpenAI
        
        if not current_marketing or 'none' in current_marketing:
            return """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 현재 마케팅 활동: 없음

아무것도 하지 않고 있습니다.
온라인에 존재하지 않습니다.

2024년입니다.
온라인 없이는 생존할 수 없습니다.

지금 시작하십시오.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        # GPT-4o로 분석
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        channels_info = []
        for channel_id in current_marketing:
            details = marketing_details.get(channel_id, {})
            channels_info.append(f"- {channel_id}: {details}")
        
        prompt = f"""
현재 마케팅 활동을 분석하고 진단하세요.

**현재 하고 있는 것:**
{chr(10).join(channels_info)}

**규칙:**
- 각 채널별로 진단
- 현재 하고 있는 것 인정
- 하지만 문제 지적
- 개선 방향 제시
- "할 수 있냐" 질문으로 마무리
- 스티브 잡스 톤

**예시 (Instagram):**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Instagram (팔로워 50명, 릴스 없음)

팔로워 50명입니다. 거의 없습니다.
릴스가 없습니다.
2024년에 릴스 없는 Instagram은 죽은 것입니다.

개선:
1. 릴스 주 3개 시작
2. 인플루언서 1명 협업

할 수 있습니까?
없으면 Instagram 접으십시오.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

이런 형식으로 각 채널을 분석하세요.
"""
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "스티브 잡스 톤. 직설적이고 강렬하게."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        
        analysis = response.choices[0].message.content.strip()
        print(f"✅ 13번째 질문 분석 완료")
        return analysis
        
    except Exception as e:
        print(f"⚠️ 13번째 질문 분석 실패: {e}")
        return ""


# ==================== 🔥 WHY-WHAT-HOW 전략 생성 ====================

def generate_why_what_how_strategy(
    questions: Dict[str, str],
    store_name: str,
    review_data: Dict,
    statistical_comparison: Dict,
    current_marketing: List[str],
    marketing_details: Dict[str, Dict[str, str]]
) -> str:
    """
    WHY-WHAT-HOW 구조의 전략 제시
    """
    try:
        from prompt_generator import generate_full_prompt
        from openai import OpenAI
        
        # 리뷰 분석 결과
        total_reviews = review_data.get('total_reviews', 0)
        keyword_stats = review_data.get('keyword_stats', {})
        
        strengths = []
        if isinstance(keyword_stats, dict):
            sorted_keywords = sorted(
                keyword_stats.items(),
                key=lambda x: x[1] if isinstance(x[1], int) else x[1].get('count', 0),
                reverse=True
            )
            strengths = [(kw, count if isinstance(count, int) else count.get('count', 0))
                        for kw, count in sorted_keywords[:5]]
        
        review_analysis = {
            'total': total_reviews,
            'positive': int(total_reviews * 0.7) if total_reviews > 0 else 0,
            'negative': int(total_reviews * 0.2) if total_reviews > 0 else 0,
            'neutral': int(total_reviews * 0.1) if total_reviews > 0 else 0,
            'strengths': strengths,
            'weaknesses': []
        }
        
        # 기본 프롬프트 생성 (🔥 13번째 질문 포함)
        system_prompt, user_prompt = generate_full_prompt(
            answers=questions,
            review_analysis=review_analysis,
            store_name=store_name,
            current_marketing=current_marketing,  # 🔥 추가
            marketing_details=marketing_details   # 🔥 추가
        )
        
        # GPT-4o 호출 (🔥 prompt_generator에서 WHY-WHAT-HOW 구조 포함됨)
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
        print("✅ WHY-WHAT-HOW 전략 생성 완료")
        return strategy
        
    except Exception as e:
        print(f"⚠️ 전략 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return "전략 생성에 실패했습니다."


# ==================== 통합 리포트 생성 (잡스 톤 적용) ====================

def create_professional_dashboard(
    html_file: str,
    hook_sentence: str,
    review_insights: str,
    marketing_analysis: str,
    strategy: str,
    store_name: str
) -> str:
    """
    스티브 잡스 톤이 적용된 전문 대시보드 생성
    """
    try:
        # 기존 HTML 읽기
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 🔥 진정성 헤더
        authenticity_header = """
        <div style="background: #f8f9fa; padding: 30px; margin: 20px 0; border-left: 4px solid #FF7A59;">
            <div style="font-size: 18px; font-weight: 600; color: #2d3748; margin-bottom: 15px;">
                먼저 말씀드립니다.
            </div>
            <div style="font-size: 15px; line-height: 1.8; color: #4a5568;">
                나는 당신의 서포터입니다.<br>
                주인공은 당신입니다.<br><br>
                
                마케팅은 도구입니다.<br>
                본질은 당신의 음식과 서비스입니다.<br><br>
                
                좋은 가게는 마케팅 없이도 살아남습니다.<br>
                다만 3년이 걸립니다.<br><br>
                
                빨리 가고 싶다면 이 도구를 쓰십시오.<br>
                천천히 가고 싶다면 무시하십시오.<br><br>
                
                둘 다 정답입니다.
            </div>
        </div>
        """
        
        # 🔥 후킹 문장 (빨간 배너)
        hook_banner = f"""
        <div style="background: linear-gradient(135deg, #FF6B6B 0%, #FF8E53 100%); 
                    padding: 30px; margin: 20px 0; border-radius: 12px; color: white; text-align: center; box-shadow: 0 4px 15px rgba(255,107,107,0.3);">
            <div style="font-size: 22px; font-weight: 700; line-height: 1.6;">
                {hook_sentence.replace(chr(10), '<br>')}
            </div>
        </div>
        """
        
        # 🔥 핵심 인사이트
        insights_section = f"""
        <div id="core-insights" class="section" style="background: white; padding: 40px; margin: 20px 0; border-radius: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h2 style="color: #2d3748; border-bottom: 3px solid #FF7A59; padding-bottom: 15px; margin-bottom: 30px;">
                🔍 핵심 인사이트 (리뷰 교차 분석)
            </h2>
            <div style="font-size: 15px; line-height: 1.9; color: #2d3748; white-space: pre-wrap; font-family: 'Segoe UI', sans-serif;">
{review_insights}
            </div>
        </div>
        """
        
        # 🔥 13번째 질문 분석
        marketing_section = f"""
        <div id="marketing-analysis" class="section" style="background: white; padding: 40px; margin: 20px 0; border-radius: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h2 style="color: #2d3748; border-bottom: 3px solid #FF7A59; padding-bottom: 15px; margin-bottom: 30px;">
                📊 현재 마케팅 활동 분석 (가중치 50%)
            </h2>
            <div style="font-size: 15px; line-height: 1.9; color: #2d3748; white-space: pre-wrap; font-family: 'Segoe UI', sans-serif;">
{marketing_analysis}
            </div>
        </div>
        """
        
        # 🔥 전략 제시
        strategy_section = f"""
        <div id="strategy" class="section" style="background: white; padding: 40px; margin: 20px 0; border-radius: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h2 style="color: #2d3748; border-bottom: 3px solid #FF7A59; padding-bottom: 15px; margin-bottom: 30px;">
                🎯 전략 제시 (WHY-WHAT-HOW)
            </h2>
            <div style="font-size: 15px; line-height: 1.9; color: #2d3748; white-space: pre-wrap; font-family: 'Segoe UI', sans-serif;">
{strategy}
            </div>
        </div>
        """
        
        # 🔥 푸터
        footer = """
        <div style="background: #f8f9fa; padding: 30px; margin: 40px 0 20px 0; border-top: 3px solid #FF7A59; text-align: center;">
            <div style="font-size: 18px; font-weight: 600; color: #2d3748; margin-bottom: 20px;">
                마지막으로 정리하겠습니다.
            </div>
            <div style="font-size: 15px; line-height: 2; color: #4a5568; text-align: left; max-width: 600px; margin: 0 auto;">
                1. 진짜 승부는 맛과 서비스에서 납니다.<br>
                2. 마케팅은 그것을 알리는 도구일 뿐입니다.<br>
                3. 좋은 음식 + 마케팅 = 빠른 성장<br>
                4. 나는 지름길을 알려줄 뿐입니다. 가는 것은 당신입니다.<br><br>
                
                귀찮다는 것 압니다.<br>
                하지만 경쟁사는 하고 있습니다.<br>
                당신은 어떻게 하시겠습니까?
            </div>
        </div>
        """
        
        # 통합
        integrated = html_content.replace(
            '</body>',
            f'{authenticity_header}\n{hook_banner}\n{insights_section}\n{marketing_section}\n{strategy_section}\n{footer}\n</body>'
        )
        
        # 저장
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        integrated_file = f"killer_report_{store_name.replace(' ', '_')}_{timestamp}.html"
        
        with open(integrated_file, 'w', encoding='utf-8') as f:
            f.write(integrated)
        
        print(f"✅ KILLER 대시보드 생성: {integrated_file}")
        return integrated_file
        
    except Exception as e:
        print(f"⚠️ 대시보드 생성 실패: {e}")
        return html_file


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
✅ 스티브 잡스 톤 후킹 문장
✅ 리뷰 교차 분석 인사이트
✅ 현재 마케팅 활동 진단 (가중치 50%)
✅ WHY-WHAT-HOW 전략 제시
✅ 경쟁사 비교 분석
✅ AI 인사이트 (GPT + Claude)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📎 첨부된 HTML 파일을 브라우저로 열어서 확인하세요!

💡 모든 전략은 13가지 질문 기반으로 맞춤화되었습니다.

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

async def analyze_and_send(
    job_id: str,
    store_name: str,
    email: str,
    questions: Dict[str, str],
    current_marketing: List[str],
    marketing_details: Dict[str, Dict[str, str]]
):
    """백그라운드 분석 작업 (13번째 질문 포함)"""
    try:
        print(f"\n{'='*70}")
        print(f"🚀 KILLER 분석 시작")
        print(f"{'='*70}")
        print(f"   가게명: {store_name}")
        print(f"   이메일: {email}")
        print(f"   예산: {questions.get('budget', '미입력')}")
        print(f"   현재 마케팅: {', '.join(current_marketing) if current_marketing else '없음'}")
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
            f'*{store_name_clean}*{timestamp}*.html',
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
        
        # 3. 데이터 준비
        review_data = {
            'total_reviews': len(result.get('reviews', [])) if result else 0,
            'keyword_stats': result.get('keyword_stats', {}) if result else {}
        }
        statistical_comparison = result.get('statistical_comparison', None) if result else None
        
        # 🔥 4. 후킹 문장 생성
        jobs[job_id]['progress'] = '🎯 스티브 잡스 톤 후킹 문장 생성 중...'
        hook_sentence = generate_hook_sentence(
            review_data, statistical_comparison, questions, current_marketing
        )
        
        # 🔥 5. 리뷰 교차 분석 인사이트
        jobs[job_id]['progress'] = '🔍 리뷰 교차 분석 인사이트 생성 중...'
        review_insights = generate_review_insights(review_data, statistical_comparison)
        
        # 🔥 6. 13번째 질문 분석
        jobs[job_id]['progress'] = '📊 현재 마케팅 활동 분석 중... (가중치 50%)'
        marketing_analysis = analyze_current_marketing(
            current_marketing, marketing_details, questions
        )
        
        # 🔥 7. WHY-WHAT-HOW 전략 생성
        jobs[job_id]['progress'] = '🎯 WHY-WHAT-HOW 전략 생성 중...'
        strategy = generate_why_what_how_strategy(
            questions, store_name, review_data, statistical_comparison,
            current_marketing, marketing_details
        )
        
        # 🔥 8. 통합 대시보드 생성
        jobs[job_id]['progress'] = '📄 KILLER 대시보드 생성 중...'
        final_html = create_professional_dashboard(
            html_file, hook_sentence, review_insights,
            marketing_analysis, strategy, store_name,
            current_marketing, marketing_details  # 🔥 13번째 질문 데이터 전달
        )
        
        # 9. 이메일 전송
        jobs[job_id]['progress'] = '📧 이메일 전송 중...'
        success = send_email_with_report(email, store_name, final_html)
        
        if success:
            jobs[job_id]['status'] = 'completed'
            jobs[job_id]['progress'] = '완료! 이메일을 확인하세요.'
            jobs[job_id]['result'] = {
                'email': email,
                'html_file': final_html,
                'message': f'{email}로 KILLER 리포트를 전송했습니다!'
            }
            print(f"\n{'='*70}")
            print(f"✅ KILLER 프로세스 완료!")
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
        "service": "KILLER API",
        "version": "4.0.0",
        "status": "running",
        "description": "13가지 질문 기반 맞춤형 마케팅 전략 + 스티브 잡스 톤",
        "features": [
            "🔥 13번째 질문 (가중치 50%)",
            "💬 스티브 잡스 톤 후킹 문장",
            "🔍 리뷰 교차 분석 인사이트",
            "🎯 WHY-WHAT-HOW 전략 구조",
            "🤖 AI 인사이트 (GPT + Claude)",
            "📊 통합 대시보드",
            "📧 이메일 전송"
        ]
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
    """가게 분석 시작 (13번째 질문 포함)"""
    job_id = str(uuid.uuid4())
    
    # 12가지 질문
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
    
    # 🔥 13번째 질문
    current_marketing = request.current_marketing or []
    marketing_details = request.marketing_details or {}
    
    jobs[job_id] = {
        "status": "queued",
        "progress": "대기 중...",
        "created_at": datetime.now().isoformat(),
        "store_name": request.store_name,
        "email": request.email,
        "questions": questions,
        "current_marketing": current_marketing
    }
    
    print(f"\n📝 새로운 KILLER 분석 요청")
    print(f"   Job ID: {job_id}")
    print(f"   가게: {request.store_name}")
    print(f"   현재 마케팅: {', '.join(current_marketing) if current_marketing else '없음'}\n")
    
    background_tasks.add_task(
        analyze_and_send,
        job_id,
        request.store_name,
        request.email,
        questions,
        current_marketing,  # 🔥 전달
        marketing_details   # 🔥 전달
    )
    
    return {
        "success": True,
        "job_id": job_id,
        "message": "KILLER 분석이 시작되었습니다. 3-4분 후 이메일을 확인하세요."
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
║                  🔥 KILLER API Server v4.0                       ║
║          13가지 질문 + 스티브 잡스 톤 + 교차 분석               ║
╚══════════════════════════════════════════════════════════════════╝

🔥 NEW! 13번째 질문 (가중치 50%)
   • 현재 마케팅 활동 진단
   • 채널별 구체적 분석

💬 스티브 잡스 톤
   • 후킹 문장 (3문장)
   • 짧고 강렬하게
   • 본질을 찌름

🔍 리뷰 교차 분석
   • 10가지 패턴 인사이트
   • 맛↑ 서비스↓ 등

🎯 WHY-WHAT-HOW 전략
   • 우선순위 명확
   • 실행 가능한 액션

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