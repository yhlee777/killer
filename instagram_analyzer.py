# -*- coding: utf-8 -*-
# instagram_analyzer.py - Instagram & Naver Place 진단 (스티브 잡스 톤)

import os
import requests
from typing import Dict, List, Optional
from datetime import datetime
import re
from collections import Counter
import statistics
import sqlite3


class InstagramDiagnostics:
    """Instagram Business Discovery API"""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://graph.facebook.com/v21.0"
    
    def get_account_data(self, ig_username: str, user_id: str) -> Optional[Dict]:
        """계정 데이터 가져오기"""
        try:
            url = f"{self.base_url}/{user_id}"
            params = {
                "fields": f"business_discovery.username({ig_username})"
                          "{followers_count,media_count,"
                          "media.limit(30){caption,like_count,comments_count,"
                          "media_type,timestamp}}",
                "access_token": self.access_token
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            return response.json().get('business_discovery')
        
        except Exception as e:
            print(f"❌ Instagram API 오류: {e}")
            return None
    
    def extract_data_for_diagnosis(self, account_data: Dict) -> Dict:
        """진단용 데이터 추출"""
        media_list = account_data.get('media', {}).get('data', [])
        
        # 최근 30일 필터링
        now = datetime.now()
        recent_30d = []
        post_dates = []
        
        for m in media_list:
            try:
                ts = m.get('timestamp')
                if ts:
                    dt = datetime.strptime(ts, '%Y-%m-%dT%H:%M:%S%z')
                    days_ago = (now - dt.replace(tzinfo=None)).days
                    
                    if days_ago <= 30:
                        recent_30d.append(m)
                    
                    post_dates.append(dt.replace(tzinfo=None))
            except:
                continue
        
        # 릴스 개수
        recent_30d_posts = len(recent_30d)
        recent_30d_reels = sum(1 for m in recent_30d if m.get('media_type') == 'VIDEO')
        
        return {
            'followers': account_data.get('followers_count', 0),
            'media_count': account_data.get('media_count', 0),
            'recent_30d_posts': recent_30d_posts,
            'recent_30d_reels': recent_30d_reels,
            'post_dates': sorted(post_dates)
        }


def calculate_consistency(post_dates: List[datetime]) -> str:
    """일관성 계산 (표준편차 기반)"""
    if len(post_dates) < 3:
        return 'unknown'
    
    intervals = [(post_dates[i+1] - post_dates[i]).days 
                 for i in range(len(post_dates)-1)]
    
    if not intervals:
        return 'unknown'
    
    std_dev = statistics.stdev(intervals) if len(intervals) > 1 else 0
    
    # 표준편차 7일 이내 = 일관적
    return 'consistent' if std_dev < 7 else 'inconsistent'


def diagnose_instagram(data: Dict, open_period: str) -> Dict:
    """
    Instagram 진단 (스티브 잡스 톤)
    
    Args:
        data: {
            'followers': 247,
            'media_count': 45,
            'recent_30d_posts': 8,
            'recent_30d_reels': 2,
            'post_dates': [datetime, ...]
        }
        open_period: '0-6' / '6-24' / '24+'
    """
    
    # 1. 최소 데이터 체크
    if data['media_count'] < 10:
        return {
            'status': 'insufficient_data',
            'message': """
게시물이 10개 미만입니다.
데이터가 부족하여 분석이 불가능합니다.

당장:
주 3회 포스팅을 2개월 유지하십시오.
"""
        }
    
    # 2. 포스팅 빈도
    weekly_posts = data['recent_30d_posts'] / 4.3
    
    if weekly_posts < 1:
        frequency_status = "활동이 거의 없습니다"
        frequency_action = "주 3회로 시작하십시오"
    elif weekly_posts < 3:
        frequency_status = "부족합니다"
        frequency_action = "주 3-5회가 필요합니다"
    else:
        frequency_status = "좋습니다"
        frequency_action = "유지하십시오"
    
    # 3. 릴스 빈도
    weekly_reels = data['recent_30d_reels'] / 4.3
    
    if weekly_reels == 0:
        reels_status = "릴스가 없습니다"
        reels_action = "즉시 시작하십시오"
        reels_urgency = "🔴 긴급"
    elif weekly_reels < 2:
        reels_status = "릴스가 부족합니다"
        reels_action = "주 2-3개 필요합니다"
        reels_urgency = "🟡"
    else:
        reels_status = "릴스가 좋습니다"
        reels_action = "유지하십시오"
        reels_urgency = "✅"
    
    # 4. 일관성
    consistency = calculate_consistency(data['post_dates'])
    
    if consistency == 'consistent':
        consistency_msg = "일관성이 있습니다. 좋습니다."
    else:
        consistency_msg = "들쭉날쭉합니다. 일정하게 하십시오."
    
    # 5. 오픈 기간별 톤 조정
    if open_period == '0-6':
        tone = "초기 단계입니다."
        expectation = "일단 꾸준함이 중요합니다."
    elif open_period == '6-24':
        tone = "1년 넘었습니다."
        expectation = "이제 가속화가 필요합니다."
    else:  # 24+
        tone = "2년 넘었습니다."
        expectation = "지금까지 뭘 했습니까?"
    
    # 6. 최종 메시지 조합
    return {
        'status': 'success',
        'message': f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{reels_urgency} Instagram

최근 30일 게시물 {data['recent_30d_posts']}개입니다.
주 {weekly_posts:.1f}회입니다.
{frequency_status}

릴스 {data['recent_30d_reels']}개입니다.
{reels_status}

{consistency_msg}

{tone}
{expectation}

액션:
- {frequency_action}
- {reels_action}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    }


class NaverPlaceDiagnostics:
    """Naver Place 리뷰 분석"""
    
    def __init__(self, db_path: str = 'seoul_industry_reviews.db'):
        self.db_path = db_path
    
    def get_reviews_from_db(self, place_id: str) -> List[Dict]:
        """DB에서 리뷰 가져오기"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT date, content, crawled_at 
                FROM reviews 
                WHERE place_id = ? 
                ORDER BY date DESC
            """, (place_id,))
            
            reviews = []
            for row in cursor.fetchall():
                reviews.append({
                    'date': row[0],
                    'content': row[1],
                    'crawled_at': row[2]
                })
            
            conn.close()
            return reviews
        
        except Exception as e:
            print(f"❌ DB 오류: {e}")
            return []
    
    def extract_data_for_diagnosis(self, reviews: List[Dict]) -> Dict:
        """진단용 데이터 추출 (날짜 없는 버전)"""
        
        # 사진 리뷰 개수 (길이 50자 이상으로 추정)
        photo_reviews = sum(1 for r in reviews if len(r.get('content', '')) > 50)
        
        # 사장님 답글 응답률
        owner_replies = sum(1 for r in reviews if self.is_owner_reply(r.get('content', '')))
        reply_rate = owner_replies / len(reviews) if reviews else 0
        
        return {
            'total_reviews': len(reviews),
            'photo_reviews': photo_reviews,
            'reply_rate': reply_rate
        }
    
    def is_owner_reply(self, text: str) -> bool:
        """사장님 답글 감지"""
        if not text:
            return False
        
        strong_signals = ['리뷰 감사', '진심으로 감사', '찾아주셔서', '보답하겠습니다']
        return any(s in text for s in strong_signals) or \
               sum(1 for k in ['감사드립니다', '감사합니다'] if k in text) >= 2


def diagnose_naver_place(data: Dict, open_period: str) -> Dict:
    """
    Naver Place 진단 (날짜 없는 버전)
    
    Args:
        data: {
            'total_reviews': 12,
            'photo_reviews': 3,
            'reply_rate': 0.25
        }
        open_period: '0-6' / '6-24' / '24+'
    """
    
    total = data['total_reviews']
    
    # 1. 오픈 기간별 목표
    if open_period == '0-6':
        expected = 30
        timeline = "6개월입니다"
        monthly_goal = 10
    elif open_period == '6-24':
        expected = 100
        timeline = "1년 넘었습니다"
        monthly_goal = 15
    else:  # 24+
        expected = 200
        timeline = "2년 넘었습니다"
        monthly_goal = 20
    
    # 2. 평가
    if total == 0:
        status = "🔴 위험"
        message = "리뷰가 없습니다. 즉시 행동하십시오."
    elif total < expected * 0.3:
        status = "🔴 매우 부족"
        message = f"목표의 {int(total/expected*100)}%입니다. 위험합니다."
    elif total < expected * 0.7:
        status = "🟡 부족"
        message = f"목표의 {int(total/expected*100)}%입니다."
    else:
        status = "✅ 양호"
        message = f"목표 달성. 계속하십시오."
    
    # 3. 답글 응답률
    reply_rate = data['reply_rate'] * 100
    if reply_rate < 50:
        reply_msg = f"{100-reply_rate:.0f}%를 무시하고 있습니다"
        reply_urgency = "🔴"
    elif reply_rate < 80:
        reply_msg = "답글률이 부족합니다"
        reply_urgency = "🟡"
    else:
        reply_msg = "좋습니다"
        reply_urgency = "✅"
    
    # 4. 사진 리뷰 비율
    photo_rate = (data['photo_reviews'] / total * 100) if total > 0 else 0
    
    # 5. 오픈 기간별 특별 메시지
    if open_period == '24+' and total < 100:
        special_msg = """
⚠️ 2년이 넘었는데 100개 미만입니다.
무엇을 했습니까?
"""
    elif open_period == '6-24' and total < 50:
        special_msg = """
⚠️ 1년이 지났는데 50개 미만입니다.
가속화가 시급합니다.
"""
    else:
        special_msg = ""
    
    # 6. 최종 메시지
    return {
        'status': 'success',
        'message': f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{status} Naver Place

총 리뷰: {total}개
{timeline}
예상 목표: {expected}개
{message}

{reply_urgency} 답글 응답률: {reply_rate:.0f}%
{reply_msg}

사진 리뷰: {photo_rate:.0f}%
{special_msg}

목표:
월 +{monthly_goal}개

액션:
1. 모든 리뷰 24시간 내 답변
2. 영수증 리뷰 이벤트 (5천원 할인)
3. 사진 리뷰 추가 (3천원)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    }


# ==================== 통합 실행 함수 ====================

async def run_instagram_diagnosis(
    ig_username: str,
    open_period: str,
    access_token: str,
    user_id: str
) -> Optional[Dict]:
    """Instagram 진단 실행"""
    print(f"\n{'='*60}")
    print(f"📱 Instagram 진단: @{ig_username}")
    print(f"{'='*60}")
    
    analyzer = InstagramDiagnostics(access_token)
    account_data = analyzer.get_account_data(ig_username, user_id)
    
    if not account_data:
        return None
    
    data = analyzer.extract_data_for_diagnosis(account_data)
    result = diagnose_instagram(data, open_period)
    
    return result


def run_naver_place_diagnosis(
    place_id: str,
    open_period: str,
    db_path: str = 'seoul_industry_reviews.db'
) -> Optional[Dict]:
    """Naver Place 진단 실행"""
    print(f"\n{'='*60}")
    print(f"📍 Naver Place 진단: {place_id}")
    print(f"{'='*60}")
    
    analyzer = NaverPlaceDiagnostics(db_path)
    reviews = analyzer.get_reviews_from_db(place_id)
    
    if not reviews:
        print("❌ 리뷰 데이터 없음")
        return None
    
    data = analyzer.extract_data_for_diagnosis(reviews)
    result = diagnose_naver_place(data, open_period)
    
    return result


# ==================== 메타 태그 버전 (DB 대신 사용) ====================

def diagnose_naver_place_from_counts(
    total_reviews: int,
    blog_reviews: int,
    open_period: str
) -> Dict:
    """
    mvp_analyzer에서 추출한 리뷰 개수로 진단
    
    Args:
        total_reviews: 네이버 플레이스 리뷰 수 (메타 태그)
        blog_reviews: 블로그 리뷰 수 (메타 태그)
        open_period: '0-6' / '6-24' / '24+'
    """
    
    # 오픈 기간별 목표
    if open_period == '0-6':
        expected_place = 30
        expected_blog = 20
        timeline = "6개월입니다"
    elif open_period == '6-24':
        expected_place = 100
        expected_blog = 50
        timeline = "1년 넘었습니다"
    else:  # 24+
        expected_place = 200
        expected_blog = 100
        timeline = "2년 넘었습니다"
    
    # 플레이스 리뷰 평가
    if total_reviews < expected_place * 0.3:
        place_status = "🔴"
        place_msg = f"플레이스: {total_reviews}개 (목표의 {int(total_reviews/expected_place*100)}%)"
    elif total_reviews < expected_place * 0.7:
        place_status = "🟡"
        place_msg = f"플레이스: {total_reviews}개 (목표의 {int(total_reviews/expected_place*100)}%)"
    else:
        place_status = "✅"
        place_msg = f"플레이스: {total_reviews}개 (목표 달성)"
    
    # 블로그 평가
    if blog_reviews < expected_blog * 0.3:
        blog_status = "🔴"
        blog_msg = f"블로그: {blog_reviews}개 (목표의 {int(blog_reviews/expected_blog*100)}%)"
    elif blog_reviews < expected_blog * 0.7:
        blog_status = "🟡"
        blog_msg = f"블로그: {blog_reviews}개 (목표의 {int(blog_reviews/expected_blog*100)}%)"
    else:
        blog_status = "✅"
        blog_msg = f"블로그: {blog_reviews}개 (목표 달성)"
    
    # 종합 평가
    total_score = total_reviews + blog_reviews
    if open_period == '24+' and total_score < 150:
        overall = "2년 넘었는데 이 정도입니까?"
    elif open_period == '6-24' and total_score < 75:
        overall = "1년이 지났습니다. 가속화하십시오."
    elif open_period == '0-6' and total_score < 30:
        overall = "초기입니다. 더 빠르게 움직이십시오."
    else:
        overall = "진행 중입니다. 만족하지 마십시오."
    
    return {
        'status': 'success',
        'message': f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{place_status} {blog_status} Naver 종합

{timeline}

{place_msg}
{blog_msg}

{overall}

액션:
1. 영수증 리뷰 이벤트
2. 블로거 체험단 월 2회
3. 모든 리뷰 24시간 내 답변
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    }


# ==================== CLI 테스트 ====================

if __name__ == "__main__":
    import asyncio
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║          Instagram & Naver Place 진단 (스티브 잡스 톤)       ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    choice = input("1: Instagram / 2: Naver Place / 3: 메타 태그 진단: ").strip()
    open_period = input("오픈 기간 (0-6 / 6-24 / 24+): ").strip()
    
    if choice == "1":
        ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
        USER_ID = os.getenv("INSTAGRAM_USER_ID", "")
        
        if not ACCESS_TOKEN or not USER_ID:
            print("❌ .env 파일에 Instagram API 키 필요")
        else:
            username = input("Instagram 계정명: ").strip()
            result = asyncio.run(run_instagram_diagnosis(
                username, open_period, ACCESS_TOKEN, USER_ID
            ))
            
            if result:
                print(result['message'])
    
    elif choice == "2":
        place_id = input("Place ID: ").strip()
        result = run_naver_place_diagnosis(place_id, open_period)
        
        if result:
            print(result['message'])
    
    elif choice == "3":
        total = int(input("네이버 플레이스 리뷰 수: "))
        blog = int(input("블로그 리뷰 수: "))
        result = diagnose_naver_place_from_counts(total, blog, open_period)
        print(result['message'])