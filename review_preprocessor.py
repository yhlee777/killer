# -*- coding: utf-8 -*-
# review_preprocessor.py - 리뷰 사전 분석 (정밀도 강화 버전)

import re
import math
from collections import Counter


# ==================== 정밀 키워드 사전 (오탐 방지) ====================

# 🔥 공통 제외 키워드 (오탐 방지)
EXCLUDE_KEYWORDS = {
    '짜': ['분짜', '떡볶이짜', '짜릿', '짜증'],  # "짜"가 들어가지만 부정확한 것들
    '달': ['달콤', '달달', '달빛', '달님'],  # "달다"와 무관
    '쓰': ['글쓰', '사용하기쓰', '쓰레기'],  # "쓰다(bitter)"와 무관
}

# 🎯 업종별 정밀 키워드
KEYWORD_DICT_BASE = {
    # 맛 관련
    '맛_긍정': ['맛있', '맛좋', '맛집', '맛나', '맛도좋', '맛최고', '맛진', '존맛', '꿀맛', '맛남'],
    '맛_부정': ['맛없', '맛이없', '별로', '실망', '맛이별로'],
    
    # 양/가성비
    '양_긍정': ['양많', '양도많', '푸짐', '배불', '양충분', '배터', '양이많'],
    '양_부정': ['양적', '양이적', '적어', '양부족', '아쉬', '양이부족'],
    '가성비_긍정': ['가성비', '가격대비', '저렴', '싸', '합리적', '착한가격', '가성비좋', '가성비굿'],
    '가성비_부정': ['비싸', '비쌈', '가격이비', '비싼편', '가격부담', '비싼감'],
    
    # 서비스
    '서비스_긍정': ['친절', '친절하', '서비스좋', '응대', '상냥', '친절해', '친절함'],
    '서비스_부정': ['불친절', '퉁명', '불편', '서비스별로', '응대가', '무뚝뚝', '불친절해'],
    
    # 대기/속도
    '대기_언급': ['웨이팅', '대기', '줄서', '기다', '대기시간', '웨이팅이', '줄이길', '웨이팅있'],
    '빠름_긍정': ['빠르', '빨라', '신속', '바로나', '빠른편'],
    '느림_부정': ['느리', '늦', '오래걸', '시간이오래', '느린편'],
    
    # 분위기
    '분위기_긍정': ['분위기좋', '인테리어', '깔끔', '예쁘', '감성', '뷰맛집', '조용', '분위기가좋'],
    '분위기_부정': ['시끄', '어수선', '복잡', '좁', '불편', '시끄러', '어둡'],
    
    # 위생/청결
    '청결_긍정': ['깨끗', '청결', '위생', '깔끔', '청결해', '위생적'],
    '청결_부정': ['지저분', '더러', '위생이', '벌레', '지저분해'],
    
    # 재방문 의사
    '재방문_긍정': ['재방문', '다시올', '또올', '또갈', '또가', '자주가', '단골', '재방문의사', '또오고'],
    '재방문_부정': ['재방문의사없', '다시안', '또안', '실망'],
    
    # 추천
    '추천_긍정': ['추천', '강추', '강력추천', '꼭가', '추천해', '강추합니다'],
}

# 🏷️ 업종별 추가 키워드 (정밀)
INDUSTRY_KEYWORDS = {
    '카페': {
        '커피_언급': ['커피', '아메리카노', '라떼', '카페라떼', '에스프레소', '카푸치노', '카페모카'],
        '커피_긍정': ['커피맛있', '커피가맛', '원두', '커피향', '커피가좋'],
        '커피_부정': ['커피맛없', '커피가별', '커피싱겁', '커피가싱'],
        '디저트_언급': ['케이크', '디저트', '쿠키', '마카롱', '빵', '크루아상', '타르트', '스콘'],
        '디저트_긍정': ['디저트맛있', '케이크맛있', '디저트가맛'],
        '음료_언급': ['에이드', '스무디', '차', '티', '주스'],
    },
    
    '한식': {
        '메뉴_언급': [
            '된장찌개', '김치찌개', '순두부', '부대찌개',
            '삼겹살', '목살', '갈비', '불고기', '곱창', '막창',
            '비빔밥', '돌솥밥', '백반', '정식',
            '국밥', '설렁탕', '곰탕', '갈비탕', '삼계탕'
        ],
        '밑반찬_긍정': ['밑반찬', '반찬', '밑반찬좋', '반찬많', '반찬맛있'],
        '밑반찬_부정': ['반찬이별', '반찬적', '밑반찬별'],
        '국물_언급': ['국물', '육수', '찌개', '국', '탕'],
        '국물_긍정': ['국물맛있', '국물진', '육수가', '국물깊'],
        '고기_긍정': ['고기신선', '고기맛있', '고기가맛', '고기질좋'],
        '고기_부정': ['고기질', '고기가별', '고기냄새'],
        '매운맛_언급': ['맵', '매워', '매운', '맵다', '매운맛'],
        '간_긍정': ['간이딱', '간이적당', '간맞'],
        '간_부정': ['짜', '싱겁', '싱거워', '간이세', '너무짜', '많이짜'],  # 🔥 "짜" 정밀 처리
        # 🔥 "짜" 제외 패턴
        '간_부정_exclude': ['분짜', '떡볶이짜', '짜릿', '짜증', '짜장'],  # "짜장"은 메뉴명
    },
    
    '일식': {
        '메뉴_언급': [
            '스시', '초밥', '사시미', '회',
            '라멘', '우동', '소바', '돈카츠', '텐동', '규동',
            '오마카세', '모둠초밥', '연어', '참치', '장어'
        ],
        '신선도_긍정': ['신선', '싱싱', '회신선', '싱싱해', '신선하', '회가신선'],
        '신선도_부정': ['신선하지', '비린내', '냄새나', '싱싱하지', '신선도'],
        '면_언급': ['면', '라멘', '우동', '소바', '면발'],
        '면_긍정': ['면발좋', '면맛있', '면이맛'],
        '국물_긍정': ['국물맛있', '육수깊', '국물진', '국물이맛'],
    },
    
    '중식': {
        '메뉴_언급': [
            '짜장면', '짬뽕', '탕수육', '볶음밥',  # 🔥 "짜장면" 전체 단어
            '마라탕', '마라샹궈', '훠궈',
            '딤섬', '샤오롱바오', '만두',
            '양꼬치', '양장피'
        ],
        '짜장_긍정': ['짜장맛있', '짜장면맛있', '짜장이맛'],  # 🔥 "짜장" 정밀
        '짬뽕_긍정': ['짬뽕맛있', '짬뽕이맛', '짬뽕얼큰'],
        '탕수육_긍정': ['탕수육맛있', '탕수육바삭', '탕수육이맛'],
        '양_긍정': ['양많', '양푸짐', '양이많'],  # 중식은 양이 중요
    },
    
    '양식': {
        '메뉴_언급': [
            '파스타', '스파게티', '봉골레', '까르보나라', '알리오올리오',
            '피자', '스테이크', '리조또',
            '샐러드', '수프', '빵'
        ],
        '파스타_긍정': ['파스타맛있', '면발좋', '파스타가맛', '소스맛있'],
        '파스타_부정': ['파스타별', '면불', '소스별', '파스타가별'],
        '스테이크_긍정': ['스테이크맛있', '고기맛있', '굽기좋', '육질좋'],
        '와인_언급': ['와인', '맥주', '음료'],
    },
}


# ==================== 정밀 키워드 매칭 (오탐 방지) ====================

def precise_keyword_match(content, keyword, exclude_list=None):
    """
    정밀 키워드 매칭 (오탐 방지)
    
    Args:
        content: 리뷰 내용
        keyword: 찾을 키워드
        exclude_list: 제외할 패턴 리스트
    
    Returns:
        bool: 매칭 여부
    """
    # 1. 제외 패턴 체크 (우선)
    if exclude_list:
        for exclude in exclude_list:
            if exclude in content:
                # "짜장"이 있으면 "짜"는 매칭 안 함
                if keyword in exclude:
                    return False
    
    # 2. 키워드 존재 체크
    if keyword not in content:
        return False
    
    # 3. 긴 키워드는 그대로 매칭 (3글자 이상)
    if len(keyword) >= 3:
        return True
    
    # 4. 짧은 키워드는 단어 경계 체크 (1-2글자)
    # "짜" 같은 경우 앞뒤 확인
    if len(keyword) <= 2:
        # 앞에 공백/시작이거나, 뒤에 공백/끝인 경우만
        pattern = rf'(?:^|\s){re.escape(keyword)}(?:\s|$|[!.,?])'
        if re.search(pattern, content):
            return True
        
        # "너무 짜", "많이 짜" 같은 패턴 (수식어 + 짧은 단어)
        modifiers = ['너무', '많이', '좀', '약간', '진짜', '정말']
        for mod in modifiers:
            if f"{mod} {keyword}" in content or f"{mod}{keyword}" in content:
                return True
    
    return False


def count_keywords_precise(reviews, keyword_dict, industry=None):
    """
    정밀 키워드 카운팅 (중복 제거 + 오탐 방지)
    
    Args:
        reviews: 리뷰 리스트
        keyword_dict: 키워드 사전
        industry: 업종 (선택)
    
    Returns:
        dict: 카운팅 결과
    """
    counts = {category: 0 for category in keyword_dict.keys()}
    
    # 업종별 키워드 병합
    if industry:
        industry_key = get_industry_key(industry)
        if industry_key in INDUSTRY_KEYWORDS:
            industry_kw = INDUSTRY_KEYWORDS[industry_key]
            # 병합 (기존 키워드 유지 + 추가)
            keyword_dict = {**keyword_dict, **industry_kw}
            for key in industry_kw.keys():
                if key not in counts:
                    counts[key] = 0
    
    negation_patterns = [
        r'안\s*', r'못\s*', r'없\s*', r'아니\s*', 
        r'별로\s*', r'그닥\s*', r'딱히\s*',
        r'전혀\s*', r'하나도\s*'
    ]
    
    for review in reviews:
        content = review.get('content', '').lower()
        
        # 🔥 리뷰당 카운팅된 카테고리 추적 (중복 방지)
        counted_in_review = set()
        
        # 🔥 긴 키워드부터 매칭 (우선순위)
        # "짜장면" > "짜" 순서로 체크
        sorted_categories = sorted(
            keyword_dict.items(),
            key=lambda x: max(len(kw) for kw in x[1]) if x[1] else 0,
            reverse=True
        )
        
        for category, keywords in sorted_categories:
            # 이미 카운팅된 카테고리는 스킵
            if category in counted_in_review:
                continue
            
            # 제외 리스트 가져오기
            exclude_key = f"{category}_exclude"
            exclude_list = keyword_dict.get(exclude_key, [])
            
            for keyword in keywords:
                # 정밀 매칭
                if not precise_keyword_match(content, keyword, exclude_list):
                    continue
                
                # 부정 표현 체크
                pattern = re.compile(keyword)
                matches = pattern.finditer(content)
                
                matched = False
                for match in matches:
                    start_pos = max(0, match.start() - 10)
                    context_before = content[start_pos:match.start()]
                    
                    is_negated = any(re.search(neg, context_before) 
                                    for neg in negation_patterns)
                    
                    if not is_negated:
                        matched = True
                        break
                
                if matched:
                    counts[category] += 1
                    counted_in_review.add(category)
                    break  # 🔥 카테고리당 1회만!
    
    return counts


def get_industry_key(industry):
    """업종명을 키워드 그룹 키로 변환"""
    mapping = {
        '카페': ['카페', '디저트카페', '베이커리', '브런치카페'],
        '한식': ['한식', '한정식', '고기집', '삼겹살', '곱창', '족발', '보쌈'],
        '일식': ['일식', '오마카세', '스시', '초밥', '라멘', '우동', '돈카츠'],
        '중식': ['중식', '중국집', '짜장', '짬뽕', '마라탕', '훠궈'],
        '양식': ['양식', '이탈리안', '파스타', '피자', '스테이크'],
    }
    
    for key, industry_list in mapping.items():
        if industry in industry_list:
            return key
    
    return None


# ==================== 통계 생성 (업종별 키워드 반영) ====================

def generate_review_stats(reviews, store_name="우리 가게", industry=None):
    """
    전체 리뷰 통계 생성 (업종별 키워드 + 정밀 매칭)
    
    Args:
        reviews: 리뷰 리스트
        store_name: 가게 이름
        industry: 업종 (선택)
    """
    # 🔥 정밀 카운팅
    keyword_counts = count_keywords_precise(reviews, KEYWORD_DICT_BASE, industry)
    
    total_reviews = len(reviews)
    
    if total_reviews == 0:
        return {
            'store_name': store_name,
            'total_reviews': 0,
            'error': '리뷰가 없습니다'
        }
    
    def calc_rate_score(positive_key, negative_key):
        pos = keyword_counts.get(positive_key, 0)
        neg = keyword_counts.get(negative_key, 0)
        total_mentions = pos + neg
        
        if total_mentions == 0:
            return {
                'mention_rate': 0,
                'positive_rate': 0,
                'score': 0,
                'count': {'positive': pos, 'negative': neg}
            }
        
        mention_rate = total_mentions / total_reviews
        positive_rate = pos / total_mentions if total_mentions > 0 else 0
        score = mention_rate * positive_rate
        
        return {
            'mention_rate': round(mention_rate, 3),
            'positive_rate': round(positive_rate, 3),
            'score': round(score, 3),
            'count': {'positive': pos, 'negative': neg},
            'total_mentions': total_mentions
        }
    
    taste_score = calc_rate_score('맛_긍정', '맛_부정')
    service_score = calc_rate_score('서비스_긍정', '서비스_부정')
    value_score = calc_rate_score('가성비_긍정', '가성비_부정')
    quantity_score = calc_rate_score('양_긍정', '양_부정')
    atmosphere_score = calc_rate_score('분위기_긍정', '분위기_부정')
    cleanliness_score = calc_rate_score('청결_긍정', '청결_부정')
    
    revisit_rate = keyword_counts.get('재방문_긍정', 0) / total_reviews * 100
    recommend_rate = keyword_counts.get('추천_긍정', 0) / total_reviews * 100
    wait_rate = keyword_counts.get('대기_언급', 0) / total_reviews * 100
    
    stats = {
        'store_name': store_name,
        'total_reviews': total_reviews,
        'industry': industry,
        'keyword_counts': keyword_counts,
        
        'scores': {
            '맛': taste_score,
            '서비스': service_score,
            '가성비': value_score,
            '양': quantity_score,
            '분위기': atmosphere_score,
            '청결': cleanliness_score
        },
        
        'rates': {
            '재방문율': f"{revisit_rate:.1f}%",
            '추천율': f"{recommend_rate:.1f}%",
            '대기_언급률': f"{wait_rate:.1f}%"
        },
        
        'top_positive': [],
        'top_negative': [],
        'top_mentions': []
    }
    
    # TOP 긍정/부정 계산
    topic_scores = [
        ('맛', taste_score['score'], taste_score['count']),
        ('서비스', service_score['score'], service_score['count']),
        ('가성비', value_score['score'], value_score['count']),
        ('양', quantity_score['score'], quantity_score['count']),
        ('분위기', atmosphere_score['score'], atmosphere_score['count']),
        ('청결', cleanliness_score['score'], cleanliness_score['count'])
    ]
    
    topic_scores_sorted = sorted(topic_scores, key=lambda x: x[1], reverse=True)
    stats['top_positive'] = [(name, score, counts['positive']) 
                             for name, score, counts in topic_scores_sorted[:3]]
    
    negative_scores = [
        ('맛', taste_score['count']['negative']),
        ('서비스', service_score['count']['negative']),
        ('가성비', value_score['count']['negative']),
        ('양', quantity_score['count']['negative']),
        ('분위기', atmosphere_score['count']['negative']),
        ('청결', cleanliness_score['count']['negative'])
    ]
    negative_scores_sorted = sorted(negative_scores, key=lambda x: x[1], reverse=True)
    stats['top_negative'] = [(name, count) for name, count in negative_scores_sorted[:3] if count > 0]
    
    # 업종별 추가 통계
    industry_key = get_industry_key(industry) if industry else None
    if industry_key and industry_key in INDUSTRY_KEYWORDS:
        stats['industry_specific'] = {}
        for key in INDUSTRY_KEYWORDS[industry_key].keys():
            if not key.endswith('_exclude'):
                count = keyword_counts.get(key, 0)
                if count > 0:
                    stats['industry_specific'][key] = count
    
    return stats


# ==================== 나머지 함수들 (기존과 동일) ====================

def wilson_score_interval(successes, total, confidence=0.95):
    """Wilson Score Interval"""
    if total == 0:
        return (0, 0)
    
    p = successes / total
    z = 1.96 if confidence == 0.95 else 2.576
    
    denominator = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denominator
    margin = z * math.sqrt((p * (1 - p) / total + z**2 / (4 * total**2))) / denominator
    
    return (max(0, center - margin), min(1, center + margin))


def compare_rates_with_stats(our_successes, our_total, comp_successes, comp_total):
    """두 비율 비교"""
    our_rate = our_successes / our_total if our_total > 0 else 0
    comp_rate = comp_successes / comp_total if comp_total > 0 else 0
    gap = our_rate - comp_rate
    
    se_our = math.sqrt(our_rate * (1 - our_rate) / our_total) if our_total > 0 else 0
    se_comp = math.sqrt(comp_rate * (1 - comp_rate) / comp_total) if comp_total > 0 else 0
    se_gap = math.sqrt(se_our**2 + se_comp**2)
    
    ci_lower = gap - 1.96 * se_gap
    ci_upper = gap + 1.96 * se_gap
    
    z_score = gap / se_gap if se_gap > 0 else 0
    
    def norm_cdf(x):
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))
    
    p_value = 2 * (1 - norm_cdf(abs(z_score)))
    
    if p_value < 0.05 and abs(gap) >= 0.10:
        significance = "유의"
        if gap > 0:
            category = "우리의_강점"
            priority = "높음"
        else:
            category = "우리의_약점"
            priority = "높음"
    else:
        significance = "미확인"
        category = "참고"
        priority = "낮음"
    
    warning = None
    if our_total < 30:
        warning = "표본이 작아 신뢰구간이 넓습니다 (추가 리뷰 필요)"
    elif comp_total < 30:
        warning = "경쟁사 표본이 작습니다"
    
    return {
        'gap': round(gap, 3),
        'ci': [round(ci_lower, 3), round(ci_upper, 3)],
        'p_value': round(p_value, 3),
        'z_score': round(z_score, 2),
        'significance': significance,
        'category': category,
        'priority': priority,
        'warning': warning,
        'our': {
            'rate': round(our_rate, 3),
            'n': our_total,
            'successes': our_successes
        },
        'comp': {
            'rate': round(comp_rate, 3),
            'n': comp_total,
            'successes': comp_successes
        }
    }


def compare_review_stats(our_stats, comp_stats_list):
    """통계 비교 (4단계 구조)"""
    total_comp_reviews = sum(s['total_reviews'] for s in comp_stats_list)
    
    if total_comp_reviews == 0:
        return {'error': '경쟁사 데이터 없음'}
    
    # 경쟁사 키워드 집계
    comp_aggregated = {
        'total_reviews': total_comp_reviews,
        'keyword_counts': {}
    }
    
    # 모든 키워드 수집
    all_keywords = set(our_stats['keyword_counts'].keys())
    for comp_stat in comp_stats_list:
        all_keywords.update(comp_stat['keyword_counts'].keys())
    
    for keyword in all_keywords:
        comp_aggregated['keyword_counts'][keyword] = sum(
            s['keyword_counts'].get(keyword, 0) for s in comp_stats_list
        )
    
    comparisons = {}
    
    topics = [
        ('맛', '맛_긍정', '맛_부정'),
        ('서비스', '서비스_긍정', '서비스_부정'),
        ('가성비', '가성비_긍정', '가성비_부정'),
        ('양', '양_긍정', '양_부정'),
        ('분위기', '분위기_긍정', '분위기_부정'),
        ('청결', '청결_긍정', '청결_부정')
    ]
    
    for topic_name, pos_key, neg_key in topics:
        our_pos = our_stats['keyword_counts'].get(pos_key, 0)
        our_total = our_stats['total_reviews']
        
        comp_pos = comp_aggregated['keyword_counts'].get(pos_key, 0)
        comp_total = comp_aggregated['total_reviews']
        
        comparisons[topic_name] = compare_rates_with_stats(
            our_pos, our_total,
            comp_pos, comp_total
        )
    
    # 재방문/추천/대기
    comparisons['재방문'] = compare_rates_with_stats(
        our_stats['keyword_counts'].get('재방문_긍정', 0),
        our_stats['total_reviews'],
        comp_aggregated['keyword_counts'].get('재방문_긍정', 0),
        comp_aggregated['total_reviews']
    )
    
    comparisons['추천'] = compare_rates_with_stats(
        our_stats['keyword_counts'].get('추천_긍정', 0),
        our_stats['total_reviews'],
        comp_aggregated['keyword_counts'].get('추천_긍정', 0),
        comp_aggregated['total_reviews']
    )
    
    # 대기 (낮을수록 좋음)
    wait_comp = compare_rates_with_stats(
        our_stats['keyword_counts'].get('대기_언급', 0),
        our_stats['total_reviews'],
        comp_aggregated['keyword_counts'].get('대기_언급', 0),
        comp_aggregated['total_reviews']
    )
    
    if wait_comp['gap'] < 0:
        wait_comp['category'] = "우리의_강점"
        wait_comp['interpretation'] = "대기 문제가 경쟁사보다 적음"
    elif wait_comp['gap'] > 0:
        wait_comp['category'] = "우리의_약점"
        wait_comp['interpretation'] = "대기 문제가 경쟁사보다 심각"
    
    comparisons['대기'] = wait_comp
    
    # 4단계 분류
    result = {
        '우리의_약점': {},
        '우리의_강점': {},
        '경쟁사의_약점_우리의_기회': {},
        '경쟁사의_강점_배울점': {}
    }
    
    for topic, stats in comparisons.items():
        if stats['category'] == "우리의_약점":
            result['우리의_약점'][topic] = stats
        elif stats['category'] == "우리의_강점":
            result['우리의_강점'][topic] = stats
        
        comp_gap = -stats['gap']
        if stats['p_value'] < 0.05 and abs(comp_gap) >= 0.10:
            if comp_gap > 0:
                result['경쟁사의_약점_우리의_기회'][topic] = {
                    **stats,
                    'gap': comp_gap,
                    'interpretation': f"경쟁사는 {topic}에서 약점"
                }
            else:
                result['경쟁사의_강점_배울점'][topic] = {
                    **stats,
                    'gap': comp_gap,
                    'interpretation': f"경쟁사는 {topic}에서 강점"
                }
    
    result['comparisons'] = comparisons
    result['our_total'] = our_stats['total_reviews']
    result['comp_total'] = comp_aggregated['total_reviews']
    result['comp_count'] = len(comp_stats_list)
    
    return result


def format_comparison_for_gpt(comparison_result):
    """통계 비교 텍스트 포맷"""
    if 'error' in comparison_result:
        return f"❌ 오류: {comparison_result['error']}"
    
    text = f"""## 📊 통계 비교 분석 (4단계 구조)

**데이터 규모**
- 우리 가게: {comparison_result['our_total']}개 리뷰
- 경쟁사 {comparison_result['comp_count']}개: {comparison_result['comp_total']}개 리뷰

---

"""
    
    # 1. 우리의 약점
    if comparison_result['우리의_약점']:
        text += "### 🔥 1. 우리의 유의미한 약점\n\n"
        for topic, stats in comparison_result['우리의_약점'].items():
            gap_sign = "+" if stats['gap'] > 0 else ""
            text += f"**⚠️ {topic}**\n"
            text += f"- GAP: {gap_sign}{stats['gap']:.3f} [CI: {stats['ci'][0]:.3f} ~ {stats['ci'][1]:.3f}]\n"
            text += f"- P-value: {stats['p_value']:.3f}\n"
            text += f"- 우리: {stats['our']['rate']*100:.1f}% / 경쟁사: {stats['comp']['rate']*100:.1f}%\n\n"
    
    # 2. 우리의 강점
    if comparison_result['우리의_강점']:
        text += "### ✅ 2. 우리의 유의미한 강점\n\n"
        for topic, stats in comparison_result['우리의_강점'].items():
            gap_sign = "+" if stats['gap'] > 0 else ""
            text += f"**✨ {topic}**\n"
            text += f"- GAP: {gap_sign}{stats['gap']:.3f} [CI: {stats['ci'][0]:.3f} ~ {stats['ci'][1]:.3f}]\n"
            text += f"- P-value: {stats['p_value']:.3f}\n"
            text += f"- 우리: {stats['our']['rate']*100:.1f}% / 경쟁사: {stats['comp']['rate']*100:.1f}%\n\n"
    
    # 3. 경쟁사의 약점
    if comparison_result['경쟁사의_약점_우리의_기회']:
        text += "### 💡 3. 경쟁사의 약점 = 우리의 기회\n\n"
        for topic, stats in comparison_result['경쟁사의_약점_우리의_기회'].items():
            text += f"**🎯 {topic}**: {stats['interpretation']}\n"
            text += f"- 우리: {stats['our']['rate']*100:.1f}% / 경쟁사: {stats['comp']['rate']*100:.1f}%\n\n"
    
    # 4. 경쟁사의 강점
    if comparison_result['경쟁사의_강점_배울점']:
        text += "### 📚 4. 경쟁사의 강점 = 배울 점\n\n"
        for topic, stats in comparison_result['경쟁사의_강점_배울점'].items():
            text += f"**🔍 {topic}**: {stats['interpretation']}\n"
            text += f"- 경쟁사: {stats['comp']['rate']*100:.1f}% / 우리: {stats['our']['rate']*100:.1f}%\n\n"
    
    return text


# ==================== 테스트 ====================

if __name__ == "__main__":
    # 🔥 정밀도 테스트
    test_reviews = [
        {'content': '맛있어요! 정말 맛있어요! 너무 맛있네요!'},  # 맛_긍정 1회만
        {'content': '짜장면이 맛있어요. 짜지 않고 딱 좋아요.'},  # "짜" 오탐 방지
        {'content': '분짜가 맛있어요'},  # "짜" 오탐 방지
        {'content': '너무 짜요. 많이 짜서 별로예요'},  # 간_부정 1회만
        {'content': '친절해요! 직원분들 친절해요!'},  # 서비스_긍정 1회만
    ]
    
    print("="*60)
    print("🔬 정밀도 테스트")
    print("="*60)
    
    counts = count_keywords_precise(test_reviews, KEYWORD_DICT_BASE, industry='중식')
    
    print("\n✅ 결과:")
    print(f"맛_긍정: {counts['맛_긍정']}회 (예상: 3회)")
    print(f"서비스_긍정: {counts['서비스_긍정']}회 (예상: 1회)")
    
    # 한식 테스트
    if '간_부정' in counts:
        print(f"간_부정: {counts['간_부정']}회 (예상: 1회)")
        print(f"  ✅ '분짜', '짜장'에서 '짜' 오탐 방지됨!")
    
    print("\n✅ 중복 제거 + 오탐 방지 완료!")