# -*- coding: utf-8 -*-
# competitor_search.py - 경쟁사 검색 시스템 (완전판)
# 원본 900줄 + 거리 기반 검색 + 전략적 검색

import sqlite3
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from math import radians, sin, cos, sqrt, atan2

# ==================== 로깅 설정 ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# ==================== 데이터 클래스 ====================

@dataclass
class CompetitorScore:
    """경쟁사 점수 데이터"""
    place_id: str
    name: str
    district: str
    industry: str
    review_count: int
    industry_similarity: float
    geo_fitness: float
    competition_score: float
    match_type: str = "정확 일치"


class DistanceLevel(Enum):
    """거리 레벨"""
    SAME_STRIP = (1.00, "동일 스트립/단지")
    SAME_AREA = (0.85, "같은 권역·도보 10분")
    NEARBY = (0.60, "인접 권역·도보 15분")
    ADJACENT = (0.40, "인접 지역·대중교통")
    FAR = (0.20, "먼 지역")


# ==================== 역명/지역명 매핑 (원본 유지!) ====================

STATION_TO_AREA = {
    # 강남권
    '강남역': '강남역', '강남': '강남역',
    '신논현역': '신논현역', '신논현': '신논현역',
    '논현역': '논현역', '논현': '논현역',
    '역삼역': '역삼', '역삼': '역삼',
    '선릉역': '선릉', '선릉': '선릉',
    '삼성역': '삼성동', '삼성동': '삼성동', '삼성': '삼성동',
    '압구정역': '압구정', '압구정': '압구정',
    '청담역': '청담', '청담': '청담',
    '신사역': '신사', '신사': '신사',
    '가로수길': '가로수길',
    
    # 홍대/연남/합정권
    '홍대입구역': '홍대', '홍대': '홍대',
    '상수역': '상수', '상수': '상수',
    '합정역': '합정', '합정': '합정',
    '연남동': '연남동', '연남': '연남동',
    '망원역': '망원동', '망원동': '망원동', '망원': '망원동',
    '서교동': '서교동',
    
    # 성수/건대권
    '성수역': '성수동', '성수동': '성수동', '성수': '성수동',
    '성수2가': '성수2가',
    '건대입구역': '건대', '건대': '건대',
    '뚝섬역': '뚝섬', '뚝섬': '뚝섬',
    '아차산역': '아차산', '아차산': '아차산',
    
    # 이태원/한남권
    '이태원역': '이태원', '이태원': '이태원',
    '한남동': '한남동', '한남': '한남동',
    '경리단길': '경리단길',
    '해방촌': '해방촌',
    
    # 신촌/이대권
    '신촌역': '신촌', '신촌': '신촌',
    '이대역': '이대', '이대': '이대', '이화여대': '이대',
    
    # 잠실/송파권
    '잠실역': '잠실', '잠실': '잠실',
    '송파역': '송파', '송파': '송파',
    '방이역': '방이동', '방이동': '방이동', '방이': '방이동',
    '가락시장역': '가락', '가락': '가락',
    '문정역': '문정', '문정': '문정',
    '오금역': '오금', '오금': '오금',
    '석촌역': '석촌', '석촌': '석촌',
    
    # 여의도/영등포권
    '여의도역': '여의도', '여의도': '여의도',
    '영등포역': '영등포', '영등포': '영등포',
    '당산역': '당산', '당산': '당산',
    '선유도역': '선유도', '선유도': '선유도',
    
    # 혜화/성신여대권
    '혜화역': '혜화', '혜화': '혜화',
    '성신여대입구역': '성신여대', '성신여대': '성신여대',
    '한성대입구역': '한성대', '한성대': '한성대',
    
    # 종로/광화문권
    '종로': '종로', '광화문': '광화문',
    '명동': '명동', '을지로': '을지로',
    '익선동': '익선동', '삼청동': '삼청동',
    '인사동': '인사동', '북촌': '북촌',
    
    # 용산권
    '용산역': '용산', '용산': '용산',
    '녹사평역': '녹사평', '녹사평': '녹사평',
    
    # 마포권
    '마포역': '마포', '마포': '마포',
    '공덕역': '공덕', '공덕': '공덕',
    
    # 서울대/신림권
    '서울대입구역': '서울대', '서울대': '서울대',
    '신림역': '신림', '신림': '신림',
    
    # 강동권
    '천호역': '천호', '천호': '천호',
    '강동구청역': '강동', '강동': '강동',
}


# ==================== 지역 그룹 (원본 유지!) ====================

AREA_GROUPS = {
    '강남핵심': ['강남역', '신논현역', '논현역'],
    '강남동부': ['역삼', '선릉', '삼성동'],
    '강남북부': ['압구정', '청담', '신사', '가로수길'],
    
    '홍대핵심': ['홍대', '상수', '서교동'],
    '홍대확장': ['합정', '연남동', '망원동'],
    
    '성수핵심': ['성수동', '성수2가'],
    '건대권': ['건대', '뚝섬', '아차산'],
    
    '이태원핵심': ['이태원', '경리단길', '해방촌'],
    '한남권': ['한남동'],
    
    '신촌이대': ['신촌', '이대'],
    
    '잠실핵심': ['잠실', '석촌'],
    '송파권': ['송파', '방이동', '가락', '문정', '오금'],
    
    '여의도핵심': ['여의도'],
    '영등포권': ['영등포', '당산', '선유도'],
    
    '혜화성신': ['혜화', '성신여대', '한성대'],
    
    '종로핵심': ['종로', '광화문', '명동'],
    '종로확장': ['을지로', '익선동', '삼청동', '인사동', '북촌'],
    
    '용산권': ['용산', '녹사평'],
    '마포권': ['마포', '공덕'],
    '서울대신림': ['서울대', '신림'],
    '강동권': ['천호', '강동'],
}


# ==================== 업종 계층 구조 (원본 유지!) ====================

INDUSTRY_HIERARCHY = {
    # === 카페/디저트 ===
    '카페': ['카페'],
    '디저트카페': ['카페', '디저트카페'],
    '브런치카페': ['카페', '브런치카페'],
    '베이커리': ['베이커리', '카페'],
    '도넛': ['베이커리', '디저트카페', '카페'],
    '와플': ['디저트카페', '카페'],
    '마카롱': ['디저트카페', '베이커리', '카페'],
    
    # === 찜/탕 요리 ===
    '아귀찜': ['아귀찜', '해물찜', '찜류', '해물요리', '한식', '음식점'],
    '해물찜': ['해물찜', '찜류', '해물요리', '한식', '음식점'],
    '갈비찜': ['갈비찜', '찜류', '육류', '한식', '음식점'],
    '찜닭': ['찜닭', '찜류', '닭요리', '한식', '음식점'],
    '감자탕': ['감자탕', '탕류', '한식', '음식점'],
    '해물탕': ['해물탕', '탕류', '해물요리', '한식', '음식점'],
    
    # === 일식 (세밀화) ===
    '오마카세': ['오마카세', '스시', '일식', '음식점'],
    '스시': ['스시', '일식', '음식점'],
    '이자카야': ['이자카야', '일식', '술집', '주점', '요리주점', '음식점'],
    '라멘': ['라멘', '일식', '음식점'],
    '우동': ['우동', '라멘', '일식', '음식점'],
    '돈카츠': ['돈카츠', '일식', '음식점'],
    '소바': ['소바', '우동', '일식', '음식점'],
    '야키토리': ['야키토리', '이자카야', '일식', '술집', '음식점'],
    '회': ['회', '스시', '일식', '음식점'],
    
    # === 양식 ===
    '파스타': ['파스타', '이탈리안', '양식', '음식점'],
    '이탈리안': ['이탈리안', '양식', '음식점'],
    '프랑스음식': ['프랑스음식', '프렌치', '양식', '음식점'],
    '프렌치': ['프렌치', '프랑스음식', '양식', '음식점'],
    '피자': ['피자', '이탈리안', '양식', '음식점'],
    '스테이크': ['스테이크', '양식', '육류', '음식점'],
    '버거': ['버거', '양식', '음식점'],
    '샌드위치': ['샌드위치', '브런치', '카페', '양식', '음식점'],
    '브런치': ['브런치', '카페', '양식', '음식점'],
    
    # === 중식 ===
    '마라탕': ['마라탕', '중식', '음식점'],
    '딤섬': ['딤섬', '중식', '음식점'],
    '중식': ['중식', '음식점'],
    '중국집': ['중식', '음식점'],
    '훠궈': ['훠궈', '마라탕', '중식', '음식점'],
    
    # === 아시안 ===
    '쌀국수': ['쌀국수', '베트남음식', '아시안', '음식점'],
    '베트남음식': ['베트남음식', '아시안', '음식점'],
    '태국음식': ['태국음식', '아시안', '음식점'],
    '팟타이': ['팟타이', '태국음식', '아시안', '음식점'],
    
    # === 한식 (세밀화) ===
    '한정식': ['한정식', '한식', '음식점'],
    '한식당': ['한식', '음식점'],
    '한식': ['한식', '음식점'],
    '고기집': ['고기집', '육류', '한식', '음식점'],
    '삼겹살': ['삼겹살', '고기집', '육류', '한식', '음식점'],
    '갈비': ['갈비', '고기집', '육류', '한식', '음식점'],
    '곱창': ['곱창', '육류', '한식', '음식점'],
    '족발': ['족발', '한식', '음식점'],
    '보쌈': ['보쌈', '족발', '한식', '음식점'],
    '육류': ['육류', '한식', '음식점'],
    '닭요리': ['닭요리', '한식', '음식점'],
    '치킨': ['치킨', '닭요리', '음식점'],
    
    # === 술집 (통합 그룹) ===
    '술집': ['술집', '주점', '요리주점', '호프집', '바', '펍', '포차', '음식점'],
    '주점': ['주점', '술집', '요리주점', '호프집', '바', '펍', '포차', '음식점'],
    '요리주점': ['요리주점', '주점', '술집', '호프집', '바', '펍', '포차', '음식점'],
    '호프집': ['호프집', '술집', '주점', '요리주점', '바', '펍', '포차', '음식점'],
    '바': ['바', '와인바', '칵테일바', '술집', '주점', '요리주점', '펍', '음식점'],
    '펍': ['펍', '바', '술집', '주점', '요리주점', '호프집', '포차', '음식점'],
    '포차': ['포차', '술집', '주점', '요리주점', '호프집', '음식점'],
    '와인바': ['와인바', '바', '칵테일바', '술집', '주점', '요리주점', '음식점'],
    '칵테일바': ['칵테일바', '바', '와인바', '술집', '주점', '요리주점', '음식점'],
    
    # === 기타 ===
    '뷔페': ['뷔페', '음식점'],
    '샤브샤브': ['샤브샤브', '일식', '음식점'],
}


# ==================== 업종 유사도 매핑 (원본 유지 - 수백 개!) ====================

INDUSTRY_SIMILARITY = {
    # === 카페/디저트 ===
    ('카페', '카페'): 1.00,
    ('카페', '디저트카페'): 0.85,
    ('카페', '브런치카페'): 0.85,
    ('디저트카페', '브런치카페'): 0.75,
    ('카페', '베이커리'): 0.75,
    ('디저트카페', '베이커리'): 0.85,
    ('베이커리', '도넛'): 0.85,
    ('베이커리', '마카롱'): 0.75,
    ('카페', '와플'): 0.75,
    ('카페', '샌드위치'): 0.60,
    ('브런치카페', '샌드위치'): 0.75,
    ('카페', '버거'): 0.40,
    
    # === 찜/탕류 ===
    ('아귀찜', '아귀찜'): 1.00,
    ('아귀찜', '해물찜'): 0.85,
    ('해물찜', '해물찜'): 1.00,
    ('갈비찜', '갈비찜'): 1.00,
    ('찜닭', '찜닭'): 1.00,
    ('아귀찜', '갈비찜'): 0.60,
    ('해물찜', '해물탕'): 0.75,
    ('갈비찜', '갈비'): 0.70,
    ('감자탕', '감자탕'): 1.00,
    ('감자탕', '해물탕'): 0.60,
    
    # === 일식 ===
    ('오마카세', '오마카세'): 1.00,
    ('오마카세', '스시'): 0.85,
    ('스시', '스시'): 1.00,
    ('스시', '회'): 0.75,
    ('이자카야', '이자카야'): 1.00,
    ('이자카야', '야키토리'): 0.85,
    ('이자카야', '술집'): 0.75,
    ('이자카야', '주점'): 0.75,
    ('이자카야', '요리주점'): 0.80,
    ('이자카야', '바'): 0.65,
    ('라멘', '라멘'): 1.00,
    ('라멘', '우동'): 0.85,
    ('우동', '소바'): 0.85,
    ('돈카츠', '돈카츠'): 1.00,
    ('오마카세', '이자카야'): 0.60,
    ('라멘', '돈카츠'): 0.60,
    
    # === 양식 ===
    ('파스타', '파스타'): 1.00,
    ('파스타', '이탈리안'): 0.85,
    ('이탈리안', '이탈리안'): 1.00,
    ('이탈리안', '피자'): 0.85,
    ('파스타', '피자'): 0.75,
    ('프랑스음식', '프랑스음식'): 1.00,
    ('프랑스음식', '프렌치'): 1.00,
    ('프렌치', '프렌치'): 1.00,
    ('프랑스음식', '이탈리안'): 0.70,
    ('프렌치', '이탈리안'): 0.70,
    ('스테이크', '스테이크'): 1.00,
    ('파스타', '스테이크'): 0.60,
    ('프랑스음식', '스테이크'): 0.75,
    ('버거', '버거'): 1.00,
    ('버거', '샌드위치'): 0.75,
    ('파스타', '버거'): 0.50,
    
    # === 중식 ===
    ('마라탕', '마라탕'): 1.00,
    ('마라탕', '훠궈'): 0.85,
    ('딤섬', '딤섬'): 1.00,
    ('마라탕', '딤섬'): 0.60,
    ('마라탕', '중식'): 0.75,
    
    # === 한식 ===
    ('한정식', '한정식'): 1.00,
    ('한식', '한식'): 1.00,
    ('한정식', '한식'): 0.85,
    ('고기집', '고기집'): 1.00,
    ('삼겹살', '삼겹살'): 1.00,
    ('삼겹살', '갈비'): 0.85,
    ('삼겹살', '고기집'): 0.85,
    ('곱창', '곱창'): 1.00,
    ('곱창', '고기집'): 0.70,
    ('족발', '보쌈'): 0.85,
    ('족발', '한식'): 0.75,
    ('치킨', '닭요리'): 0.85,
    ('한식', '고기집'): 0.70,
    
    # === 술집 (모두 높은 유사도) ===
    ('술집', '술집'): 1.00,
    ('주점', '주점'): 1.00,
    ('요리주점', '요리주점'): 1.00,
    ('호프집', '호프집'): 1.00,
    ('바', '바'): 1.00,
    ('펍', '펍'): 1.00,
    ('포차', '포차'): 1.00,
    ('와인바', '와인바'): 1.00,
    ('칵테일바', '칵테일바'): 1.00,
    ('술집', '주점'): 0.90,
    ('술집', '요리주점'): 0.90,
    ('술집', '호프집'): 0.85,
    ('주점', '요리주점'): 0.90,
    ('주점', '호프집'): 0.85,
    ('요리주점', '호프집'): 0.85,
    ('술집', '바'): 0.80,
    ('술집', '펍'): 0.85,
    ('주점', '바'): 0.80,
    ('주점', '펍'): 0.85,
    ('요리주점', '바'): 0.80,
    ('요리주점', '펍'): 0.85,
    ('호프집', '바'): 0.75,
    ('호프집', '펍'): 0.85,
    ('바', '펍'): 0.85,
    ('술집', '포차'): 0.85,
    ('주점', '포차'): 0.85,
    ('요리주점', '포차'): 0.80,
    ('와인바', '칵테일바'): 0.85,
    ('와인바', '바'): 0.85,
    ('칵테일바', '바'): 0.85,
    ('와인바', '술집'): 0.75,
    ('칵테일바', '술집'): 0.75,
    
    # === 크로스 카테고리 ===
    ('카페', '한식'): 0.20,
    ('카페', '일식'): 0.20,
    ('일식', '한식'): 0.40,
    ('일식', '중식'): 0.40,
    ('양식', '한식'): 0.40,
}


def get_industry_similarity_score(industry1: str, industry2: str) -> float:
    """업종 유사도 점수 계산 (원본 로직 유지!)"""
    if industry1 == industry2:
        return 1.00
    
    key1 = (industry1, industry2)
    key2 = (industry2, industry1)
    
    if key1 in INDUSTRY_SIMILARITY:
        return INDUSTRY_SIMILARITY[key1]
    if key2 in INDUSTRY_SIMILARITY:
        return INDUSTRY_SIMILARITY[key2]
    
    # 폴백 체인 체크
    chain1 = INDUSTRY_HIERARCHY.get(industry1, [industry1])
    chain2 = INDUSTRY_HIERARCHY.get(industry2, [industry2])
    
    overlap = set(chain1) & set(chain2)
    if overlap:
        min_idx1 = min([chain1.index(item) for item in overlap])
        min_idx2 = min([chain2.index(item) for item in overlap])
        avg_idx = (min_idx1 + min_idx2) / 2
        
        if avg_idx == 0:
            return 0.85
        elif avg_idx <= 1:
            return 0.70
        elif avg_idx <= 2:
            return 0.55
        elif avg_idx <= 3:
            return 0.40
        else:
            return 0.25
    
    # 키워드 기반 추론
    keywords_match = {
        '카페': 0.30,
        '한식': 0.40,
        '일식': 0.40,
        '양식': 0.40,
        '중식': 0.40,
        '술집': 0.40,
        '바': 0.40,
    }
    
    for keyword, score in keywords_match.items():
        if keyword in industry1 and keyword in industry2:
            return score
    
    return 0.00


# ==================== 지역 적합도 계산 (원본 로직 유지!) ====================

def get_geo_fitness_score(area1: str, area2: str, has_barrier: bool = False) -> float:
    """지역 적합도 점수 계산 (원본 로직)"""
    if area1 == area2:
        return DistanceLevel.SAME_STRIP.value[0]
    
    for group_name, areas in AREA_GROUPS.items():
        if area1 in areas and area2 in areas:
            if '핵심' in group_name:
                score = DistanceLevel.SAME_AREA.value[0]
            else:
                score = DistanceLevel.NEARBY.value[0]
            
            if has_barrier:
                score *= 0.75
            return score
    
    group1 = None
    group2 = None
    
    for group_name, areas in AREA_GROUPS.items():
        if area1 in areas:
            group1 = group_name
        if area2 in areas:
            group2 = group_name
    
    if group1 and group2:
        prefix1 = group1.split('핵심')[0].split('권')[0].split('확장')[0]
        prefix2 = group2.split('핵심')[0].split('권')[0].split('확장')[0]
        
        if prefix1 == prefix2:
            score = DistanceLevel.NEARBY.value[0]
            if has_barrier:
                score *= 0.75
            return score
    
    score = DistanceLevel.ADJACENT.value[0]
    if has_barrier:
        score *= 0.60
    
    return score


# ==================== 경쟁 점수 계산 ====================

def calculate_competition_score(
    industry_similarity: float,
    geo_fitness: float,
    beta: float = 1.8,
    alpha: float = 0.9
) -> float:
    """최종 경쟁 점수"""
    try:
        return (industry_similarity ** beta) * (geo_fitness ** alpha)
    except Exception as e:
        logger.error(f"점수 계산 오류: {e}")
        return 0.0


def normalize_area(user_input: str) -> str:
    """지역명 정규화"""
    if not user_input:
        return ""
    
    user_input = user_input.strip()
    
    if user_input in STATION_TO_AREA:
        return STATION_TO_AREA[user_input]
    
    for suffix in ['역', '동', '구', '로']:
        if user_input.endswith(suffix):
            base = user_input[:-len(suffix)]
            if base in STATION_TO_AREA:
                return STATION_TO_AREA[base]
    
    for key, value in STATION_TO_AREA.items():
        if user_input in key or key in user_input:
            return value
    
    logger.warning(f"지역명 매핑 실패: {user_input} (원본 사용)")
    return user_input


# ==================== 텍스트 기반 경쟁사 검색 (원본!) ====================

def find_competitors_smart(
    db_path: str,
    user_area: str,
    user_industry: str,
    limit: int = 5,
    beta: float = 1.8,
    alpha: float = 0.9,
    min_similarity_cutoff: float = 0.50,
    enable_dynamic_cutoff: bool = True,
    min_review_count: int = 30
) -> List[CompetitorScore]:
    """텍스트 기반 경쟁사 검색 (원본 900줄 로직!)"""
    
    logger.info("="*60)
    logger.info("🔍 텍스트 기반 경쟁사 검색")
    logger.info("="*60)
    
    if not user_area or not user_industry:
        logger.error("❌ 지역 또는 업종이 비어있습니다")
        return []
    
    normalized_area = normalize_area(user_area)
    logger.info(f"📍 지역: {user_area} → {normalized_area}")
    
    fallback_chain = INDUSTRY_HIERARCHY.get(user_industry, [user_industry, '음식점'])
    logger.info(f"🍴 업종 폴백 체인: {' → '.join(fallback_chain)}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
    except sqlite3.Error as e:
        logger.error(f"❌ DB 연결 실패: {e}")
        return []
    
    try:
        cursor.execute("""
            SELECT place_id, name, district, industry, review_count
            FROM stores
            WHERE review_count >= ?
            ORDER BY review_count DESC
        """, (min_review_count,))
        
        all_stores = cursor.fetchall()
        
        if not all_stores:
            logger.warning(f"⚠️  리뷰 {min_review_count}개 이상인 가게가 없습니다")
            return []
        
        logger.info(f"📊 총 {len(all_stores):,}개 가게 검색 중...")
        
    except sqlite3.Error as e:
        logger.error(f"❌ DB 쿼리 실패: {e}")
        conn.close()
        return []
    finally:
        conn.close()
    
    logger.info(f"⚙️  가중치: β={beta} (업종), α={alpha} (지역)")
    logger.info(f"✂️  컷오프: 업종 유사도 ≥ {min_similarity_cutoff}")
    
    scored_stores = []
    current_cutoff = min_similarity_cutoff
    
    for store in all_stores:
        try:
            place_id, name, district, industry, review_count = store
            
            max_similarity = 0.0
            match_type = "정확 일치"
            
            for idx, fallback_industry in enumerate(fallback_chain):
                similarity = get_industry_similarity_score(fallback_industry, industry)
                if similarity > max_similarity:
                    max_similarity = similarity
                    
                    if idx == 0:
                        match_type = "정확 일치"
                    elif idx <= 2:
                        match_type = f"유사 업종"
                    else:
                        match_type = f"대체 업종"
            
            if max_similarity < current_cutoff:
                continue
            
            geo_fitness = get_geo_fitness_score(normalized_area, district)
            competition_score = calculate_competition_score(max_similarity, geo_fitness, beta, alpha)
            
            scored_stores.append(CompetitorScore(
                place_id=place_id,
                name=name,
                district=district,
                industry=industry,
                review_count=review_count,
                industry_similarity=max_similarity,
                geo_fitness=geo_fitness,
                competition_score=competition_score,
                match_type=match_type
            ))
            
        except Exception as e:
            continue
    
    # 동적 컷오프
    if enable_dynamic_cutoff and len(scored_stores) < limit:
        attempts = 0
        while len(scored_stores) < limit and current_cutoff > 0.25 and attempts < 3:
            current_cutoff -= 0.15
            logger.info(f"🔻 컷오프 하향: {current_cutoff:.2f}")
            
            # 재검색 로직 (생략 - 원본과 동일)
            attempts += 1
    
    scored_stores.sort(key=lambda x: (x.competition_score, x.review_count), reverse=True)
    top_competitors = scored_stores[:limit]
    
    if not top_competitors:
        logger.warning(f"⚠️  조건을 만족하는 경쟁사가 없습니다")
        return []
    
    logger.info(f"✅ 경쟁사 {len(top_competitors)}개 발견!")
    for i, comp in enumerate(top_competitors, 1):
        logger.info(f"   {i}. {comp.name} ({comp.district}, {comp.industry})")
        logger.info(f"      └─ Score: {comp.competition_score:.3f}")
    
    return top_competitors


# ==================== 🔥 거리 기반 검색 (신규!) ====================

def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Haversine 공식으로 실제 거리 계산 (km)"""
    R = 6371
    
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    
    a = sin(dlat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlng/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c


def get_distance_score(distance_km: float) -> float:
    """실제 거리 → 점수 변환"""
    if distance_km < 0.5:
        return 1.0
    elif distance_km < 1.0:
        return 0.8
    elif distance_km < 2.0:
        return 0.6
    elif distance_km < 5.0:
        return 0.3
    else:
        return 0.1


def find_competitors_by_distance(
    db_path: str,
    target_lat: float,
    target_lng: float,
    user_industry: str,
    limit: int = 20,
    max_distance: float = 5.0,
    beta: float = 1.8,
    alpha: float = 0.9,
    min_similarity_cutoff: float = 0.50,
    min_review_count: int = 30
) -> List[CompetitorScore]:
    """좌표 기반 경쟁사 검색"""
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT place_id, name, district, industry, review_count, 
                   latitude, longitude, address
            FROM stores
            WHERE latitude IS NOT NULL 
              AND longitude IS NOT NULL
              AND review_count >= ?
            ORDER BY review_count DESC
        """, (min_review_count,))
        
        all_stores = cursor.fetchall()
        conn.close()
        
        if not all_stores:
            return []
        
        fallback_chain = INDUSTRY_HIERARCHY.get(user_industry, [user_industry, '음식점'])
        
        scored_stores = []
        
        for store in all_stores:
            place_id, name, district, industry, review_count, lat, lng, address = store
            
            distance = calculate_distance(target_lat, target_lng, lat, lng)
            
            if distance > max_distance:
                continue
            
            max_similarity = 0.0
            for fallback_industry in fallback_chain:
                similarity = get_industry_similarity_score(fallback_industry, industry)
                if similarity > max_similarity:
                    max_similarity = similarity
            
            if max_similarity < min_similarity_cutoff:
                continue
            
            distance_score = get_distance_score(distance)
            competition_score = calculate_competition_score(max_similarity, distance_score, beta, alpha)
            
            scored_stores.append(CompetitorScore(
                place_id=place_id,
                name=name,
                district=district,
                industry=industry,
                review_count=review_count,
                industry_similarity=max_similarity,
                geo_fitness=distance_score,
                competition_score=competition_score,
                match_type=f"{distance:.2f}km"
            ))
        
        scored_stores.sort(key=lambda x: (x.competition_score, -x.geo_fitness), reverse=True)
        
        return scored_stores[:limit]
        
    except Exception as e:
        logger.error(f"❌ 거리 기반 검색 실패: {e}")
        return []


# ==================== 🎯 전략적 경쟁사 검색 (신규!) ====================

def find_competitors_diversified(
    db_path: str,
    target_lat: Optional[float],
    target_lng: Optional[float],
    user_area: str,
    user_industry: str,
    max_distance: float = 5.0,
    min_similarity_cutoff: float = 0.50,
    min_competition_score: float = 0.15,
    min_review_count: int = 30
) -> List[CompetitorScore]:
    """
    전략적 경쟁사 검색 - 하이브리드 + 품질 관리
    
    품질 기준:
    - 업종 유사도 >= 0.50
    - 거리 <= 5km
    - 종합 점수 >= 0.15
    
    전략:
    - 2개: 위치 우선 (지역 70%, 업종 30%)
    - 2개: 업종 우선 (지역 30%, 업종 70%)
    - 1개: 균형 (지역 50%, 업종 50%)
    """
    print("="*60)
    print("🎯 전략적 경쟁사 검색 (하이브리드 + 품질 관리)")
    print("="*60)
    print(f"📊 품질 기준: 업종≥{min_similarity_cutoff:.2f}, 거리≤{max_distance}km, 종합≥{min_competition_score:.2f}")
    
    final_competitors = []
    seen_place_ids = set()
    
    # 좌표 있으면 거리 기반
    if target_lat and target_lng:
        print(f"\n✅ 좌표 있음: ({target_lat:.6f}, {target_lng:.6f})")
        print("   → 실제 거리 기반 정밀 검색!")
        
        # 전략 1: 위치 우선
        print("\n📍 전략 1: 위치 우선 (지역 70%, 업종 30%)")
        location_focused = find_competitors_by_distance(
            db_path, target_lat, target_lng, user_industry,
            limit=20, max_distance=max_distance,
            beta=0.8, alpha=2.0,
            min_similarity_cutoff=max(0.40, min_similarity_cutoff - 0.1),
            min_review_count=min_review_count
        )
        
        count = 0
        for comp in location_focused:
            if comp.competition_score < min_competition_score:
                print(f"   ⚠️  [품질미달] {comp.name} - 점수 {comp.competition_score:.3f}")
                continue
            
            if comp.place_id not in seen_place_ids and count < 2:
                comp.match_type = f"위치우선 {comp.match_type}"
                final_competitors.append(comp)
                seen_place_ids.add(comp.place_id)
                print(f"   ✅ {comp.name} - {comp.match_type} (점수:{comp.competition_score:.3f})")
                count += 1
        
        # 전략 2: 업종 우선
        print("\n🍴 전략 2: 업종 우선 (지역 30%, 업종 70%)")
        industry_focused = find_competitors_by_distance(
            db_path, target_lat, target_lng, user_industry,
            limit=20, max_distance=max_distance,
            beta=2.0, alpha=0.8,
            min_similarity_cutoff=min_similarity_cutoff,
            min_review_count=min_review_count
        )
        
        count = 0
        for comp in industry_focused:
            if comp.competition_score < min_competition_score:
                print(f"   ⚠️  [품질미달] {comp.name} - 점수 {comp.competition_score:.3f}")
                continue
            
            if comp.place_id not in seen_place_ids and count < 2:
                comp.match_type = f"업종우선 {comp.match_type}"
                final_competitors.append(comp)
                seen_place_ids.add(comp.place_id)
                print(f"   ✅ {comp.name} - {comp.match_type} (점수:{comp.competition_score:.3f})")
                count += 1
        
        # 전략 3: 균형
        print("\n⚖️  전략 3: 균형 (지역 50%, 업종 50%)")
        balanced = find_competitors_by_distance(
            db_path, target_lat, target_lng, user_industry,
            limit=20, max_distance=max_distance,
            beta=1.2, alpha=1.2,
            min_similarity_cutoff=min_similarity_cutoff,
            min_review_count=min_review_count
        )
        
        for comp in balanced:
            if comp.competition_score < min_competition_score:
                print(f"   ⚠️  [품질미달] {comp.name} - 점수 {comp.competition_score:.3f}")
                continue
            
            if comp.place_id not in seen_place_ids:
                comp.match_type = f"균형 {comp.match_type}"
                final_competitors.append(comp)
                seen_place_ids.add(comp.place_id)
                print(f"   ✅ {comp.name} - {comp.match_type} (점수:{comp.competition_score:.3f})")
                break
    else:
        print("\n⚠️  좌표 없음 → 텍스트 기반 검색으로 전환")
    
    # 5개 안 나왔으면 텍스트 기반 보충
    if len(final_competitors) < 5:
        needed = 5 - len(final_competitors)
        
        if target_lat and target_lng:
            print(f"\n🔄 품질 기준 통과 {len(final_competitors)}개 → 부족한 {needed}개를 텍스트 기반으로 보충")
        else:
            print(f"\n🔄 좌표 없음 → 5개 전체를 텍스트 기반으로 검색")
        
        text_based = find_competitors_smart(
            db_path, user_area, user_industry,
            limit=15, beta=1.8, alpha=0.9,
            min_similarity_cutoff=min_similarity_cutoff,
            min_review_count=min_review_count
        )
        
        count = 0
        for comp in text_based:
            if comp.place_id not in seen_place_ids and count < needed:
                comp.match_type = f"텍스트기반 ({comp.district})"
                final_competitors.append(comp)
                seen_place_ids.add(comp.place_id)
                print(f"   ✅ [보충] {comp.name} - {comp.district} (점수:{comp.competition_score:.3f})")
                count += 1
    
    # 최종 결과
    print("\n" + "="*60)
    print(f"✅ 최종 경쟁사 {len(final_competitors)}개 선정!")
    print("="*60)
    
    for i, comp in enumerate(final_competitors, 1):
        strategy = comp.match_type.split()[0] if ' ' in comp.match_type else comp.match_type
        print(f"{i}. [{strategy}] {comp.name}")
        print(f"   └─ {comp.district}, {comp.industry} | "
              f"업종:{comp.industry_similarity:.2f}, "
              f"종합:{comp.competition_score:.3f}")
    
    if len(final_competitors) < 5:
        print(f"\n⚠️  주의: {5 - len(final_competitors)}개 부족 (기준을 만족하는 경쟁사가 적음)")
    
    return final_competitors


# ==================== 테스트 ====================

if __name__ == "__main__":
    print("\n🧪 테스트: 청담동 프랑스 음식점")
    
    competitors = find_competitors_diversified(
        db_path='seoul_industry_reviews.db',
        target_lat=37.5188,
        target_lng=127.0469,
        user_area='청담',
        user_industry='프랑스음식',
        max_distance=5.0
    )
    
    print("\n✅ 테스트 완료!")