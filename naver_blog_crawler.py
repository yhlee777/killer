# -*- coding: utf-8 -*-
# naver_blog_crawler.py - 네이버 블로그 크롤링 + 가게 분석 (200개 수집)

import requests
import json
import time
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from dataclasses import dataclass
from collections import Counter
import re
from datetime import datetime

# ==================== 네이버 API 설정 ====================

NAVER_CLIENT_ID = "ZLPHHehmKYVHcF2hUGhQ"  # 네이버 개발자센터에서 발급
NAVER_CLIENT_SECRET = "NrVaQLeDfV"


# ==================== 데이터 클래스 ====================

@dataclass
class BlogPost:
    """블로그 포스트"""
    title: str
    link: str
    description: str
    blogger_name: str
    post_date: str
    
    # 추출된 정보
    keywords: List[str]
    sentiment: str  # "긍정", "중립", "부정"
    visit_purpose: Optional[str]  # "데이트", "친목", "혼술" 등
    price_mentioned: Optional[int]
    menu_mentioned: List[str]


@dataclass
class StoreProfile:
    """가게 프로필 (블로그에서 자동 추출)"""
    name: str
    
    # 자동 추출된 정보
    industry: str  # "요리주점", "이자카야", "카페" 등
    area: str  # "건대", "홍대" 등
    concept: str  # "헌팅포차", "혼술집", "데이트" 등
    
    # 상세 분석
    target_customers: List[str]  # ["20대", "대학생", "커플"]
    signature_menus: List[str]  # 시그니처 메뉴
    price_range: str  # "1-2만원대", "3-5만원대"
    atmosphere_keywords: List[str]  # ["시끄러움", "아늑함", "넓음"]
    visit_purposes: Dict[str, int]  # {"데이트": 15, "친목": 30}
    
    # 상권 분석
    peak_times: List[str]  # ["금요일 저녁", "주말"]
    foot_traffic: str  # "상", "중", "하"
    competition_level: str  # "높음", "보통", "낮음"
    
    # 통계
    total_blog_posts: int
    positive_ratio: float
    avg_rating: float


# ==================== 네이버 블로그 검색 (200개 수집) ====================

def search_naver_blog(query: str, total_count: int = 200) -> List[Dict]:
    """
    네이버 블로그 검색 API (최대 200개, 중복 제거)
    
    Args:
        query: 검색어 (가게명)
        total_count: 가져올 총 개수 (기본 200개)
    
    Returns:
        블로그 포스트 리스트 (중복 제거됨)
    """
    url = "https://openapi.naver.com/v1/search/blog.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    
    all_blogs = []
    seen_links = set()  # 중복 제거용
    
    # 1단계: 첫 요청으로 전체 개수 확인
    params = {
        "query": query,
        "display": 1,
        "sort": "sim"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        available_total = data.get("total", 0)
        
        print(f"   📊 검색 결과: 총 {available_total:,}개 블로그 발견")
        
        # 실제 가져올 개수 결정 (최소값)
        actual_count = min(total_count, available_total)
        
        if actual_count == 0:
            print("   ❌ 검색 결과 없음")
            return []
        
        print(f"   📥 수집 목표: {actual_count}개")
        
    except Exception as e:
        print(f"❌ 초기 검색 실패: {e}")
        return []
    
    # 2단계: 100개씩 나눠서 요청
    max_per_request = 100
    requests_needed = (actual_count + max_per_request - 1) // max_per_request  # 올림
    
    for page in range(requests_needed):
        start = page * max_per_request + 1
        
        # 남은 개수 계산
        remaining = actual_count - len(all_blogs)
        if remaining <= 0:
            break
        
        # 이번 요청에서 가져올 개수
        display = min(max_per_request, remaining)
        
        params = {
            "query": query,
            "display": display,
            "start": start,
            "sort": "sim"
        }
        
        try:
            print(f"   ⏳ 요청 {page + 1}/{requests_needed}: start={start}, display={display}")
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            items = data.get("items", [])
            
            # 중복 제거하면서 추가
            new_count = 0
            for item in items:
                link = item.get("link", "")
                if link and link not in seen_links:
                    seen_links.add(link)
                    all_blogs.append(item)
                    new_count += 1
                    
                    # 목표 개수 도달하면 중단
                    if len(all_blogs) >= actual_count:
                        break
            
            print(f"      ✅ 수집: {new_count}개 (누적: {len(all_blogs)}/{actual_count}개)")
            
            # 목표 개수 도달하면 루프 종료
            if len(all_blogs) >= actual_count:
                break
            
            # API 요청 간격 (과부하 방지)
            if page < requests_needed - 1:
                time.sleep(0.1)
                
        except Exception as e:
            print(f"   ⚠️  요청 {page + 1} 실패: {e}")
            continue
    
    print(f"   ✅ 최종 수집: {len(all_blogs)}개 (중복 제거 완료)")
    return all_blogs


# ==================== 블로그 내용 크롤링 ====================

def crawl_blog_content(blog_url: str) -> str:
    """
    블로그 본문 크롤링
    
    Args:
        blog_url: 블로그 URL
    
    Returns:
        본문 텍스트
    """
    try:
        # User-Agent 설정
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(blog_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 네이버 블로그 본문 추출
        # iframe 내부 접근 필요 (실제로는 더 복잡)
        content = soup.get_text(strip=True)
        
        return content
    except Exception as e:
        print(f"⚠️  크롤링 실패 ({blog_url}): {e}")
        return ""


# ==================== 키워드 추출 ====================

def extract_keywords(text: str) -> List[str]:
    """
    텍스트에서 키워드 추출
    """
    # 업종 키워드
    industry_keywords = [
        "요리주점", "술집", "주점", "호프집", "포차", "이자카야", 
        "와인바", "칵테일바", "펍", "바", "카페", "음식점"
    ]
    
    # 컨셉 키워드
    concept_keywords = [
        "헌팅", "미팅", "소개팅", "데이트", "혼술", "친목", 
        "회식", "단체", "조용한", "시끄러운", "분위기"
    ]
    
    # 맛 키워드
    taste_keywords = [
        "맛있다", "맛없다", "달다", "짜다", "매콤", "고소", 
        "신선", "바삭", "부드럽", "쫄깃"
    ]
    
    # 서비스 키워드
    service_keywords = [
        "친절", "불친절", "빠르다", "느리다", "서비스", 
        "대기", "웨이팅", "예약"
    ]
    
    keywords = []
    text_lower = text.lower()
    
    for keyword_list in [industry_keywords, concept_keywords, taste_keywords, service_keywords]:
        for kw in keyword_list:
            if kw in text_lower:
                keywords.append(kw)
    
    return keywords


# ==================== 업종/상권 자동 추출 ====================

def extract_industry_and_area(blogs: List[Dict]) -> tuple:
    """
    블로그에서 업종과 상권 자동 추출
    
    Args:
        blogs: 블로그 포스트 리스트
    
    Returns:
        (업종, 상권)
    """
    industry_counter = Counter()
    area_counter = Counter()
    
    # 업종 키워드
    industry_map = {
        "요리주점": ["요리주점", "안주집"],
        "이자카야": ["이자카야", "야키토리"],
        "술집": ["술집", "주점", "호프집"],
        "바": ["바", "와인바", "칵테일바"],
        "카페": ["카페", "디저트"],
    }
    
    # 상권 키워드
    area_keywords = [
        "건대", "홍대", "강남", "신촌", "이대", "성수", "잠실",
        "이태원", "한남", "압구정", "청담", "가로수길",
        "신사", "논현", "역삼", "선릉"
    ]
    
    for blog in blogs:
        text = (blog.get("title", "") + " " + blog.get("description", "")).lower()
        
        # 업종 추출
        for industry, keywords in industry_map.items():
            for kw in keywords:
                if kw in text:
                    industry_counter[industry] += 1
        
        # 상권 추출
        for area in area_keywords:
            if area in text:
                area_counter[area] += 1
    
    # 가장 많이 언급된 것 선택
    industry = industry_counter.most_common(1)[0][0] if industry_counter else "음식점"
    area = area_counter.most_common(1)[0][0] if area_counter else "알 수 없음"
    
    return industry, area


# ==================== 가게 프로필 생성 ====================

def create_store_profile(store_name: str, blogs: List[Dict]) -> StoreProfile:
    """
    블로그에서 가게 프로필 자동 생성
    
    Args:
        store_name: 가게명
        blogs: 블로그 포스트 리스트
    
    Returns:
        StoreProfile
    """
    print(f"\n🔍 [{store_name}] 블로그 분석 중... (총 {len(blogs)}개)")
    
    # 1. 업종/상권 추출
    industry, area = extract_industry_and_area(blogs)
    print(f"   📍 업종: {industry} | 상권: {area}")
    
    # 2. 키워드 수집
    all_keywords = []
    menu_counter = Counter()
    purpose_counter = Counter()
    atmosphere_counter = Counter()
    positive_count = 0
    
    # 최대 100개만 분석 (속도 최적화)
    analysis_limit = min(100, len(blogs))
    
    for blog in blogs[:analysis_limit]:
        text = blog.get("title", "") + " " + blog.get("description", "")
        keywords = extract_keywords(text)
        all_keywords.extend(keywords)
        
        # 메뉴 추출 (간단한 패턴)
        if "메뉴" in text or "추천" in text:
            # 실제로는 더 정교한 NER 필요
            pass
        
        # 방문 목적
        if any(kw in text for kw in ["데이트", "연인", "커플"]):
            purpose_counter["데이트"] += 1
        if any(kw in text for kw in ["친구", "친목", "모임"]):
            purpose_counter["친목"] += 1
        if any(kw in text for kw in ["혼술", "혼자"]):
            purpose_counter["혼술"] += 1
        if any(kw in text for kw in ["회식", "단체", "팀"]):
            purpose_counter["회식"] += 1
        
        # 분위기
        if "시끄럽" in text:
            atmosphere_counter["시끄러움"] += 1
        if any(kw in text for kw in ["조용", "아늑"]):
            atmosphere_counter["조용함"] += 1
        if "넓" in text:
            atmosphere_counter["넓음"] += 1
        
        # 긍정/부정
        if any(kw in text for kw in ["좋", "맛있", "추천", "최고"]):
            positive_count += 1
    
    # 3. 컨셉 추출
    keyword_freq = Counter(all_keywords)
    
    concept = "일반"
    if keyword_freq.get("헌팅", 0) > 3:
        concept = "헌팅포차"
    elif keyword_freq.get("데이트", 0) > 5:
        concept = "데이트 명소"
    elif keyword_freq.get("혼술", 0) > 3:
        concept = "혼술집"
    
    # 4. 가격대 추출 (간단한 패턴)
    price_range = "2-3만원대"  # 기본값
    
    # 5. 프로필 생성
    profile = StoreProfile(
        name=store_name,
        industry=industry,
        area=area,
        concept=concept,
        target_customers=["20대", "대학생"],  # 상권 기반 추정
        signature_menus=menu_counter.most_common(3),
        price_range=price_range,
        atmosphere_keywords=[k for k, v in atmosphere_counter.most_common(3)],
        visit_purposes=dict(purpose_counter),
        peak_times=["금요일 저녁", "주말"],
        foot_traffic="상" if "건대" in area or "홍대" in area else "중",
        competition_level="높음",
        total_blog_posts=len(blogs),
        positive_ratio=positive_count / analysis_limit if analysis_limit > 0 else 0,
        avg_rating=4.2  # 실제로는 별점 파싱 필요
    )
    
    print(f"   ✅ 프로필 생성 완료!")
    print(f"      컨셉: {concept}")
    print(f"      주요 방문 목적: {dict(purpose_counter.most_common(3))}")
    print(f"      긍정 비율: {profile.positive_ratio:.1%}")
    
    return profile


# ==================== 메인 함수 ====================

def analyze_store_from_blog(store_name: str) -> StoreProfile:
    """
    네이버 블로그에서 가게 분석
    
    Args:
        store_name: 가게명
    
    Returns:
        StoreProfile
    """
    print("="*60)
    print(f"🔍 네이버 블로그 분석 시작: {store_name}")
    print("="*60)
    
    # 1. 블로그 검색 (최대 200개, 중복 제거)
    blogs = search_naver_blog(store_name, total_count=200)
    
    if not blogs:
        print("❌ 블로그 검색 결과 없음")
        return None
    
    print(f"📊 최종 수집: {len(blogs)}개 블로그")
    
    # 2. 가게 프로필 생성
    profile = create_store_profile(store_name, blogs)
    
    return profile


# ==================== 상권 분석 (보조) ====================

def analyze_market_context(profile: StoreProfile) -> Dict:
    """
    상권 맥락 분석 (AI 보조)
    
    Args:
        profile: 가게 프로필
    
    Returns:
        상권 분석 결과
    """
    # 상권 특성 DB (간단한 룰 기반)
    market_db = {
        "건대": {
            "type": "대학가",
            "age": "20대 중심",
            "peak": "학기중 > 방학",
            "특징": "유동인구 많음, 경쟁 치열"
        },
        "홍대": {
            "type": "젊음의거리",
            "age": "20-30대",
            "peak": "주말 저녁",
            "특징": "트렌디, 높은 임대료"
        },
        "강남": {
            "type": "비즈니스 + 유흥",
            "age": "30대 중심",
            "peak": "평일 저녁",
            "특징": "고소득층, 고가격"
        }
    }
    
    context = market_db.get(profile.area, {
        "type": "일반 상권",
        "age": "다양",
        "peak": "저녁 시간대",
        "특징": "정보 부족"
    })
    
    return {
        "area": profile.area,
        "industry": profile.industry,
        "concept": profile.concept,
        "market_type": context["type"],
        "target_age": context["age"],
        "peak_season": context["peak"],
        "특징": context["특징"],
        "경쟁강도": profile.competition_level,
        "유동인구": profile.foot_traffic
    }


# ==================== 테스트 ====================

if __name__ == "__main__":
    # 테스트
    store_name = "주다방 건대점"
    
    # 블로그 분석
    profile = analyze_store_from_blog(store_name)
    
    if profile:
        print("\n" + "="*60)
        print("📊 분석 결과")
        print("="*60)
        print(f"가게명: {profile.name}")
        print(f"업종: {profile.industry}")
        print(f"상권: {profile.area}")
        print(f"컨셉: {profile.concept}")
        print(f"주요 고객: {', '.join(profile.target_customers)}")
        print(f"분위기: {', '.join(profile.atmosphere_keywords)}")
        print(f"방문 목적: {profile.visit_purposes}")
        print(f"블로그 수: {profile.total_blog_posts}개")
        print(f"긍정 비율: {profile.positive_ratio:.1%}")
        
        # 상권 분석
        print("\n" + "="*60)
        print("🗺️  상권 분석")
        print("="*60)
        market = analyze_market_context(profile)
        for k, v in market.items():
            print(f"   {k}: {v}")