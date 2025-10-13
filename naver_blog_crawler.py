# -*- coding: utf-8 -*-
# naver_blog_crawler.py - 네이버 블로그 크롤링 + 가게 분석 (500개 수집)

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


# ==================== 네이버 블로그 검색 (500개 수집) ====================

def search_naver_blog(query: str, total_count: int = 500) -> List[Dict]:
    """
    네이버 블로그 검색 API (최대 500개, 중복 제거)
    
    Args:
        query: 검색어 (가게명)
        total_count: 가져올 총 개수 (기본 500개)
    
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
        "친절", "불친절", "빠르다", "느리다", "세심", "불편"
    ]
    
    found_keywords = []
    text_lower = text.lower()
    
    for keyword in industry_keywords + concept_keywords + taste_keywords + service_keywords:
        if keyword in text_lower:
            found_keywords.append(keyword)
    
    return found_keywords


# ==================== 감정 분석 (간단 버전) ====================

def analyze_sentiment(text: str) -> str:
    """
    간단한 감정 분석
    """
    positive_words = ["좋", "최고", "맛있", "친절", "깨끗", "추천"]
    negative_words = ["나쁘", "별로", "맛없", "불친절", "더럽", "비추"]
    
    pos_count = sum(1 for word in positive_words if word in text)
    neg_count = sum(1 for word in negative_words if word in text)
    
    if pos_count > neg_count:
        return "긍정"
    elif neg_count > pos_count:
        return "부정"
    else:
        return "중립"


# ==================== 가게 프로필 분석 (블로그에서) ====================

def analyze_store_from_blog(store_name: str, max_blogs: int = 500) -> StoreProfile:
    """
    블로그 데이터로부터 가게 프로필 자동 추출
    
    Args:
        store_name: 가게명
        max_blogs: 분석할 최대 블로그 수
    
    Returns:
        StoreProfile 객체
    """
    print(f"\n{'='*60}")
    print(f"📱 블로그 분석 시작: {store_name}")
    print(f"{'='*60}")
    
    # 블로그 검색
    blogs = search_naver_blog(store_name, total_count=max_blogs)
    
    if not blogs:
        raise Exception("블로그 검색 결과 없음")
    
    print(f"\n   🔍 총 {len(blogs)}개 블로그 분석 중...")
    
    # 키워드 카운터
    all_keywords = []
    sentiments = []
    visit_purposes = []
    
    for blog in blogs:
        title = blog.get('title', '')
        description = blog.get('description', '')
        combined_text = title + " " + description
        
        # HTML 태그 제거
        combined_text = re.sub(r'<[^>]+>', '', combined_text)
        
        # 키워드 추출
        keywords = extract_keywords(combined_text)
        all_keywords.extend(keywords)
        
        # 감정 분석
        sentiment = analyze_sentiment(combined_text)
        sentiments.append(sentiment)
        
        # 방문 목적 추출
        if "데이트" in combined_text or "소개팅" in combined_text:
            visit_purposes.append("데이트")
        elif "회식" in combined_text or "단체" in combined_text:
            visit_purposes.append("회식")
        elif "혼술" in combined_text:
            visit_purposes.append("혼술")
        elif "친목" in combined_text or "친구" in combined_text:
            visit_purposes.append("친목")
    
    # 통계 집계
    keyword_counter = Counter(all_keywords)
    purpose_counter = Counter(visit_purposes)
    
    # 업종 추정
    industry_candidates = ["요리주점", "술집", "카페", "이자카야", "바"]
    industry = "일반"
    for candidate in industry_candidates:
        if keyword_counter.get(candidate, 0) > 0:
            industry = candidate
            break
    
    # 컨셉 추정
    concept_candidates = ["헌팅포차", "데이트", "혼술집", "회식"]
    concept = "일반"
    for candidate in concept_candidates:
        if keyword_counter.get(candidate, 0) > 2:
            concept = candidate
            break
    
    # 지역 추정 (간단 버전)
    area = "미상"
    area_keywords = ["건대", "홍대", "강남", "신촌", "이태원", "명동"]
    for area_kw in area_keywords:
        if any(area_kw in blog.get('title', '') + blog.get('description', '') for blog in blogs[:10]):
            area = area_kw
            break
    
    # 긍정 비율
    positive_count = sentiments.count("긍정")
    positive_ratio = positive_count / len(sentiments) if sentiments else 0.0
    
    # 평균 평점 (간단 추정)
    avg_rating = 3.0 + (positive_ratio * 2.0)  # 3.0 ~ 5.0
    
    # StoreProfile 생성
    profile = StoreProfile(
        name=store_name,
        industry=industry,
        area=area,
        concept=concept,
        target_customers=["20대", "대학생"],  # 간단 추정
        signature_menus=[],
        price_range="2-3만원대",
        atmosphere_keywords=[kw for kw, _ in keyword_counter.most_common(5)],
        visit_purposes=dict(purpose_counter),
        peak_times=["금요일 저녁", "주말"],
        foot_traffic="중",
        competition_level="높음",
        total_blog_posts=len(blogs),
        positive_ratio=positive_ratio,
        avg_rating=avg_rating
    )
    
    print(f"   ✅ 분석 완료!")
    print(f"      업종: {profile.industry}")
    print(f"      컨셉: {profile.concept}")
    print(f"      긍정 비율: {profile.positive_ratio:.1%}")
    
    return profile


# ==================== 메인 실행 ====================

if __name__ == "__main__":
    # 테스트
    store_name = input("가게 이름을 입력하세요: ").strip()
    
    if store_name:
        profile = analyze_store_from_blog(store_name, max_blogs=500)
        print(f"\n{'='*60}")
        print(json.dumps(profile.__dict__, ensure_ascii=False, indent=2))
        print(f"{'='*60}")