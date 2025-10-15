# -*- coding: utf-8 -*-
"""
업종 유사도 정확도 비교
- 하드코딩 방식 vs ML 방식 vs 하이브리드 방식
"""

import numpy as np
from typing import Dict, Tuple, List


# ==================== 1. 하드코딩 방식 (기존) ====================

HARDCODED_SIMILARITY = {
    # 동일 업종
    ('오마카세', '오마카세'): 1.00,
    ('카페', '카페'): 1.00,
    ('이자카야', '이자카야'): 1.00,
    
    # 높은 유사도 (같은 세부 카테고리)
    ('오마카세', '스시'): 0.85,
    ('스시', '회'): 0.75,
    ('카페', '디저트카페'): 0.85,
    ('디저트카페', '베이커리'): 0.85,
    ('이자카야', '야키토리'): 0.85,
    ('이자카야', '술집'): 0.75,
    ('아귀찜', '해물찜'): 0.85,
    ('갈비찜', '갈비'): 0.70,
    ('파스타', '이탈리안'): 0.85,
    
    # 중간 유사도 (같은 대분류)
    ('오마카세', '이자카야'): 0.60,
    ('라멘', '돈카츠'): 0.60,
    ('카페', '베이커리'): 0.75,
    ('파스타', '피자'): 0.75,
    ('마라탕', '딤섬'): 0.60,
    ('갈비찜', '찜닭'): 0.60,
    
    # 낮은 유사도 (다른 카테고리)
    ('카페', '한식'): 0.20,
    ('일식', '한식'): 0.40,
    ('카페', '이자카야'): 0.30,
    ('카페', '버거'): 0.40,
    ('오마카세', '마라탕'): 0.20,
}

def get_hardcoded_similarity(ind1: str, ind2: str) -> float:
    """하드코딩 방식"""
    if ind1 == ind2:
        return 1.00
    
    key = (ind1, ind2) if (ind1, ind2) in HARDCODED_SIMILARITY else (ind2, ind1)
    return HARDCODED_SIMILARITY.get(key, 0.0)


# ==================== 2. ML 방식 ====================

class MLSimilarityCalculator:
    """ML 기반 유사도 계산"""
    
    def __init__(self):
        self.model = None
        self.available = False
        
        try:
            from sentence_transformers import SentenceTransformer
            from sklearn.metrics.pairwise import cosine_similarity
            
            print("🤖 ML 모델 로딩 중...")
            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            self.cosine_similarity = cosine_similarity
            self.available = True
            print("✅ ML 모델 로드 완료!")
            
        except ImportError as e:
            print(f"⚠️ ML 라이브러리 없음: {e}")
            print("   설치: pip install sentence-transformers scikit-learn")
    
    def get_similarity(self, ind1: str, ind2: str) -> float:
        """ML 유사도 계산"""
        if not self.available:
            return 0.0
        
        if ind1 == ind2:
            return 1.00
        
        emb1 = self.model.encode([ind1])
        emb2 = self.model.encode([ind2])
        
        return float(self.cosine_similarity(emb1, emb2)[0][0])


# ==================== 3. 하이브리드 방식 (추천!) ====================

def get_hybrid_similarity(ind1: str, ind2: str, ml_calc: MLSimilarityCalculator) -> float:
    """하이브리드: 하드코딩 우선, 없으면 ML"""
    
    # 1. 하드코딩 확인
    hardcoded = get_hardcoded_similarity(ind1, ind2)
    if hardcoded > 0:
        return hardcoded
    
    # 2. ML로 계산
    if ml_calc.available:
        ml_score = ml_calc.get_similarity(ind1, ind2)
        
        # ML 점수는 보정 (0.5 이하는 신뢰도 낮음)
        if ml_score < 0.5:
            return ml_score * 0.5  # 더 보수적으로
        return ml_score
    
    # 3. 둘 다 없으면 0
    return 0.0


# ==================== 테스트 케이스 ====================

TEST_CASES = [
    # (업종1, 업종2, 기대값, 설명)
    # === 동일 업종 ===
    ('오마카세', '오마카세', 1.00, '동일 업종'),
    ('카페', '카페', 1.00, '동일 업종'),
    
    # === 높은 유사도 (0.7~0.9) ===
    ('오마카세', '스시', 0.85, '같은 일식 고급 스타일'),
    ('스시', '회', 0.75, '같은 생선 요리'),
    ('카페', '디저트카페', 0.85, '카페 세부 분류'),
    ('디저트카페', '베이커리', 0.85, '디저트 계열'),
    ('이자카야', '야키토리', 0.85, '이자카야 메뉴'),
    ('이자카야', '술집', 0.75, '주점 계열'),
    ('아귀찜', '해물찜', 0.85, '찜 요리 유사'),
    ('갈비찜', '갈비', 0.70, '조리법 차이'),
    ('파스타', '이탈리안', 0.85, '이탈리안 대표'),
    ('파스타', '피자', 0.75, '같은 이탈리안'),
    
    # === 중간 유사도 (0.4~0.7) ===
    ('오마카세', '이자카야', 0.60, '같은 일식이지만 스타일 다름'),
    ('라멘', '돈카츠', 0.60, '같은 일식 대중'),
    ('마라탕', '딤섬', 0.60, '같은 중식'),
    ('갈비찜', '찜닭', 0.60, '찜 요리 다른 재료'),
    ('카페', '베이커리', 0.75, '관련 있지만 다름'),
    ('카페', '버거', 0.40, '경계선'),
    
    # === 낮은 유사도 (0.0~0.4) ===
    ('카페', '한식', 0.20, '완전 다른 카테고리'),
    ('일식', '한식', 0.40, '다른 국가 음식'),
    ('카페', '이자카야', 0.30, '음식점 vs 술집'),
    ('오마카세', '마라탕', 0.20, '고급 vs 대중, 일식 vs 중식'),
    
    # === ML이 잘 잡을 것 ===
    ('브런치카페', '샌드위치', None, 'ML 테스트: 브런치 관련'),
    ('와인바', '칵테일바', None, 'ML 테스트: 술집 유사'),
    ('떡볶이', '순대', None, 'ML 테스트: 분식'),
    
    # === ML이 못 잡을 것 ===
    ('포장마차', '이자카야', None, 'ML 테스트: 한일 차이'),
    ('중화요리', '자장면', None, 'ML 테스트: 포함관계'),
]


# ==================== 정확도 평가 ====================

def evaluate_accuracy():
    """정확도 비교 평가"""
    
    print("\n" + "="*80)
    print("📊 업종 유사도 정확도 비교")
    print("="*80)
    
    ml_calc = MLSimilarityCalculator()
    
    # 결과 저장
    results = []
    
    print(f"\n{'업종1':<15} {'업종2':<15} {'기대':<8} {'하드코딩':<10} {'ML':<10} {'하이브리드':<10} {'판정'}")
    print("-" * 90)
    
    for ind1, ind2, expected, desc in TEST_CASES:
        hardcoded = get_hardcoded_similarity(ind1, ind2)
        ml_score = ml_calc.get_similarity(ind1, ind2) if ml_calc.available else 0.0
        hybrid = get_hybrid_similarity(ind1, ind2, ml_calc)
        
        # 판정
        if expected is not None:
            # 오차 범위 ±0.15
            hard_ok = abs(hardcoded - expected) <= 0.15 if hardcoded > 0 else False
            ml_ok = abs(ml_score - expected) <= 0.15 if ml_score > 0 else False
            hybrid_ok = abs(hybrid - expected) <= 0.15 if hybrid > 0 else False
            
            verdict = ""
            if hard_ok and ml_ok:
                verdict = "✅ 둘 다 정확"
            elif hard_ok:
                verdict = "🔵 하드코딩 우세"
            elif ml_ok:
                verdict = "🟠 ML 우세"
            else:
                verdict = "❌ 둘 다 부정확"
            
            results.append({
                'hardcoded_correct': hard_ok,
                'ml_correct': ml_ok,
                'hybrid_correct': hybrid_ok
            })
        else:
            verdict = "🔍 ML 테스트"
        
        print(f"{ind1:<15} {ind2:<15} {expected if expected else 'N/A':<8} "
              f"{hardcoded:<10.2f} {ml_score:<10.2f} {hybrid:<10.2f} {verdict}")
    
    # 통계
    if results:
        print("\n" + "="*80)
        print("📈 정확도 통계")
        print("="*80)
        
        hard_acc = sum(r['hardcoded_correct'] for r in results) / len(results) * 100
        ml_acc = sum(r['ml_correct'] for r in results) / len(results) * 100 if ml_calc.available else 0
        hybrid_acc = sum(r['hybrid_correct'] for r in results) / len(results) * 100
        
        print(f"🔵 하드코딩:  {hard_acc:.1f}%")
        print(f"🟠 ML:        {ml_acc:.1f}%" if ml_calc.available else "🟠 ML:        N/A (라이브러리 없음)")
        print(f"🟣 하이브리드: {hybrid_acc:.1f}%")
        
        print("\n💡 결론:")
        if hybrid_acc >= hard_acc and hybrid_acc >= ml_acc:
            print("   → 하이브리드 방식이 가장 정확합니다!")
        elif hard_acc > ml_acc:
            print("   → 하드코딩이 더 정확하지만, 유지보수가 어렵습니다.")
        else:
            print("   → ML이 더 정확하지만, 도메인 특화 지식이 부족할 수 있습니다.")


# ==================== 실행 ====================

if __name__ == "__main__":
    evaluate_accuracy()
    
    print("\n" + "="*80)
    print("🎯 추천 전략")
    print("="*80)
    print("""
1. 🥇 하이브리드 (추천!)
   - 핵심 업종만 하드코딩 (50~100개)
   - 나머지는 ML로 자동 처리
   - 장점: 정확 + 유지보수 쉬움
   
2. 🥈 하드코딩 (현재 방식)
   - 장점: 매우 정확
   - 단점: 유지보수 지옥 (300줄+)
   - 새 업종 추가할 때마다 수동 업데이트
   
3. 🥉 ML만 (실험적)
   - 장점: 완전 자동
   - 단점: 도메인 특화 지식 부족
   - 예: "이자카야" vs "술집" 못 잡을 수도
    """)