# -*- coding: utf-8 -*-
# hybrid_insight_engine.py - GPT 전처리 + Claude 인사이트 (시각화 중심)

import os
import json
import asyncio
from datetime import datetime
from openai import OpenAI
from anthropic import Anthropic

# API 클라이언트
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
anthropic_client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))


# ==================== STEP 1: GPT-4o 전처리 (10초) ====================

def preprocess_with_gpt(target_store, target_reviews, competitors, competitor_reviews, statistical_comparison):
    """GPT-4o: 빠른 정리 + 통계 검증"""
    
    print(f"\n{'='*60}")
    print(f"⚡ STEP 1: GPT-4o 전처리 (10초)")
    print(f"{'='*60}")
    
    # 샘플 리뷰 (부정 우선)
    def sort_by_rating(review):
        rating = review.get('rating', 5)
        return rating if rating > 0 else 5
    
    target_reviews_sorted = sorted(target_reviews, key=sort_by_rating)
    our_reviews_text = "\n".join([
        f"[리뷰#{i+1}] {r['content'][:200]}" 
        for i, r in enumerate(target_reviews_sorted[:50])
    ])
    
    prompt = f"""당신은 리뷰 분석 전문가입니다. 아래 리뷰를 분석하여 **장점과 단점만** 추출하세요.

## 리뷰 (50개)
{our_reviews_text}

## 요구사항

1. **장점 추출**: 긍정 언급된 항목과 개수
2. **단점 추출**: 부정 언급된 항목과 개수
3. 리뷰 번호 포함 필수

## JSON 출력 형식

{{
  "장점": [
    {{"aspect": "맛", "count": 18, "percentage": 28.0, "samples": ["[리뷰#1] 진짜 맛있어요"]}},
    {{"aspect": "분위기", "count": 14, "percentage": 22.0, "samples": ["[리뷰#3] 분위기 좋아요"]}}
  ],
  "단점": [
    {{"aspect": "온도", "count": 3, "percentage": 4.7, "samples": ["[리뷰#15] 커피가 미지근"]}},
    {{"aspect": "가격", "count": 2, "percentage": 3.1, "samples": ["[리뷰#20] 좀 비싸요"]}}
  ]
}}

**규칙**:
- 장점/단점 각각 상위 5개까지만
- 리뷰 번호 [리뷰#N] 필수
- 비율(percentage) 계산: (count / 전체 리뷰 수) * 100
"""
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "당신은 리뷰 분석 전문가입니다. JSON만 출력하세요."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=4000,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        print(f"   ✅ 전처리 완료")
        print(f"      장점: {len(result.get('장점', []))}개")
        print(f"      단점: {len(result.get('단점', []))}개")
        
        return result
        
    except Exception as e:
        print(f"   ❌ GPT 전처리 실패: {e}")
        return {"장점": [], "단점": []}


# ==================== STEP 2: Claude 인사이트 (40초) ====================

def analyze_with_claude(preprocessed, target_store, competitors, competitor_reviews, statistical_comparison):
    """Claude: 사장님용 인사이트 생성"""
    
    print(f"\n{'='*60}")
    print(f"🧠 STEP 2: Claude 인사이트 (40초)")
    print(f"{'='*60}")
    
    # 경쟁사 샘플 리뷰
    comp_summary = []
    for comp in competitors[:3]:
        comp_revs = competitor_reviews.get(comp.place_id, [])[:3]
        if comp_revs:
            comp_summary.append(f"**{comp.name}**\n" + "\n".join([
                f"- {r['content'][:150]}" for r in comp_revs
            ]))
    
    comp_text = "\n\n".join(comp_summary)
    
    # 통계 요약
    stats_text = ""
    if statistical_comparison:
        stats_text = "## 📊 통계 비교\n\n"
        
        for section_name, label in [
            ('우리의_강점', '✅ 우리가 잘하는 것'),
            ('우리의_약점', '⚠️ 우리가 부족한 것')
        ]:
            if section_name in statistical_comparison:
                stats_text += f"### {label}\n\n"
                for topic, stat in list(statistical_comparison[section_name].items())[:3]:
                    gap_sign = "+" if stat['gap'] > 0 else ""
                    stats_text += f"- **{topic}**: 우리 {stat['our']['rate']*100:.1f}% vs 경쟁사 {stat['comp']['rate']*100:.1f}% (GAP {gap_sign}{stat['gap']*100:.1f}%p)\n"
                stats_text += "\n"
    
    prompt = f"""당신은 외식업 컨설턴트입니다. 아래 데이터를 바탕으로 **사장님용 리포트**를 작성하세요.

## 우리 가게 ({target_store['name']})

### 장점
{json.dumps(preprocessed.get('장점', []), ensure_ascii=False, indent=2)}

### 단점
{json.dumps(preprocessed.get('단점', []), ensure_ascii=False, indent=2)}

{stats_text}

## 경쟁사 샘플 리뷰
{comp_text}

---

## 작성 지침

### Part 1: 우리 가게 장점 (파이 차트용)
- 장점 항목별 비율 제공
- 예: {{"맛": 28, "분위기": 22, "서비스": 15}}

### Part 2: 우리 가게 단점
- 3개 이상: 파이 차트 데이터 제공
- 2개 이하: 리스트만

### Part 3: 경쟁사 비교
- 경쟁사 강점 (우리가 배울 것) 3개
- 경쟁사 약점 (우리가 강조할 것) 3개

### Part 4: 2주 체크리스트
- [ ] 항목 형식
- 측정 가능한 것만 (숫자/yes/no)

## JSON 출력 형식

{{
  "우리_장점_파이": {{
    "맛": 28,
    "분위기": 22,
    "서비스": 15,
    "청결": 8,
    "가성비": 5
  }},
  "우리_단점": {{
    "is_many": true,  // 3개 이상이면 true
    "pie_data": {{"온도": 4.7, "가격": 3.1, "대기": 1.5}},  // 3개 이상일 때만
    "list_data": ["온도 관리 미흡 (3건)", "가격 부담 (2건)"]  // 2개 이하일 때만
  }},
  "경쟁사_강점": [
    "메뉴 다양성 우수 (8.5% 언급 vs 우리 2.9%)",
    "재방문 유도 프로그램",
    "SNS 마케팅 활발"
  ],
  "경쟁사_약점": [
    "대기시간 길다 (1.6% 언급 vs 우리 0%)",
    "서비스 불친절 지적 많음",
    "가격 대비 양 불만"
  ],
  "체크리스트": [
    "커피 온도 10분 이내 서빙 (매일 체크)",
    "인스타 '자리 여유' 매일 3시 업로드",
    "메뉴판 시그니처 메뉴 상단 배치 (1주 내)",
    "리뷰 20개 이상 확보 (2주 목표)",
    "재방문 고객 수 카운트 (현재 __명)"
  ]
}}

**규칙**:
- 숫자는 정확히
- 체크리스트는 실행 가능한 것만
- 통계는 간단히 (%, 개수)
"""
    
    try:
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=8000,
            temperature=0.0,
            system="당신은 외식업 컨설턴트입니다. JSON만 출력하세요.",
            messages=[{"role": "user", "content": prompt}]
        )
        
        # JSON 추출 (```json ``` 제거)
        content = response.content[0].text
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        result = json.loads(content)
        print(f"   ✅ 인사이트 생성 완료")
        
        return result
        
    except Exception as e:
        print(f"   ❌ Claude 분석 실패: {e}")
        return None


# ==================== STEP 3: 시각화 리포트 생성 ====================

def generate_visual_report(preprocessed, claude_result, target_store, competitors):
    """HTML 리포트 생성 (차트 포함)"""
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    # 장점 파이 차트 데이터
    strengths_pie = claude_result.get('우리_장점_파이', {})
    strengths_data = [{"name": k, "value": v} for k, v in strengths_pie.items()]
    
    # 단점 처리
    weaknesses = claude_result.get('우리_단점', {})
    is_many = weaknesses.get('is_many', False)
    
    weaknesses_html = ""
    if is_many:
        # 파이 차트
        pie_data = weaknesses.get('pie_data', {})
        weaknesses_data = [{"name": k, "value": v} for k, v in pie_data.items()]
        weaknesses_html = f"""
        <div class="chart-container">
            <h3>📉 단점 분포</h3>
            <div id="weaknesses-chart"></div>
        </div>
        """
    else:
        # 리스트
        list_data = weaknesses.get('list_data', [])
        weaknesses_html = """
        <div class="weakness-list">
            <h3>📉 단점</h3>
            <ul>
        """ + "\n".join([f"<li>{item}</li>" for item in list_data]) + """
            </ul>
        </div>
        """
    
    # 경쟁사
    comp_strengths = claude_result.get('경쟁사_강점', [])
    comp_weaknesses = claude_result.get('경쟁사_약점', [])
    
    # 체크리스트
    checklist = claude_result.get('체크리스트', [])
    
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{target_store['name']} 리뷰 분석</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: 'Noto Sans KR', sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        h1 {{ margin: 0; }}
        .meta {{ opacity: 0.9; margin-top: 10px; }}
        .section {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .chart-container {{
            max-width: 500px;
            margin: 20px auto;
        }}
        .grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        ul {{
            list-style: none;
            padding: 0;
        }}
        li {{
            padding: 10px;
            margin: 8px 0;
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            border-radius: 4px;
        }}
        .checklist li {{
            border-left-color: #28a745;
        }}
        .checklist input {{
            margin-right: 10px;
            transform: scale(1.2);
        }}
        h2 {{
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        h3 {{
            color: #555;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🏪 {target_store['name']} 리뷰 분석</h1>
        <div class="meta">
            📅 {timestamp} | 📍 {target_store['district']} | 🍽️ {target_store['industry']}
        </div>
    </div>

    <div class="section">
        <h2>✅ 우리 가게 장점</h2>
        <div class="chart-container">
            <canvas id="strengths-chart"></canvas>
        </div>
    </div>

    <div class="section">
        <h2>⚠️ 우리 가게 단점</h2>
        {weaknesses_html}
    </div>

    <div class="section">
        <h2>🏆 경쟁사 비교</h2>
        <div class="grid">
            <div>
                <h3>📚 경쟁사 강점 (배울 점)</h3>
                <ul>
                    {''.join([f'<li>{item}</li>' for item in comp_strengths])}
                </ul>
            </div>
            <div>
                <h3>💡 경쟁사 약점 (우리 강조)</h3>
                <ul>
                    {''.join([f'<li>{item}</li>' for item in comp_weaknesses])}
                </ul>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>✅ 2주 체크리스트</h2>
        <ul class="checklist">
            {''.join([f'<li><input type="checkbox"> {item}</li>' for item in checklist])}
        </ul>
    </div>

    <script>
        // 장점 파이 차트
        const strengthsCtx = document.getElementById('strengths-chart').getContext('2d');
        new Chart(strengthsCtx, {{
            type: 'pie',
            data: {{
                labels: {json.dumps(list(strengths_pie.keys()))},
                datasets: [{{
                    data: {json.dumps(list(strengths_pie.values()))},
                    backgroundColor: [
                        '#667eea', '#764ba2', '#f093fb', '#4facfe',
                        '#43e97b', '#fa709a', '#fee140', '#30cfd0'
                    ]
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ position: 'bottom' }},
                    title: {{
                        display: true,
                        text: '장점 분포 (%)',
                        font: {{ size: 16 }}
                    }}
                }}
            }}
        }});

        {'// 단점 파이 차트' if is_many else ''}
        {f'''
        const weaknessesCtx = document.getElementById('weaknesses-chart').getContext('2d');
        new Chart(weaknessesCtx, {{
            type: 'pie',
            data: {{
                labels: {json.dumps(list(weaknesses.get('pie_data', {}).keys()))},
                datasets: [{{
                    data: {json.dumps(list(weaknesses.get('pie_data', {}).values()))},
                    backgroundColor: ['#ff6b6b', '#feca57', '#48dbfb']
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ position: 'bottom' }},
                    title: {{
                        display: true,
                        text: '단점 언급률 (%)',
                        font: {{ size: 16 }}
                    }}
                }}
            }}
        }});
        ''' if is_many else ''}
    </script>
</body>
</html>
"""
    
    return html


# ==================== 메인 실행 함수 (async) ====================

async def generate_hybrid_report(target_store, target_reviews, competitors, 
                                 competitor_reviews, statistical_comparison=None):
    """하이브리드 리포트 생성 (GPT + Claude + 시각화)"""
    
    print(f"\n{'='*60}")
    print(f"🚀 하이브리드 인사이트 시스템")
    print(f"{'='*60}")
    print(f"   전략: GPT 전처리 → Claude 인사이트")
    print(f"   출력: HTML 리포트 (차트 포함)")
    
    # STEP 1: GPT 전처리
    preprocessed = preprocess_with_gpt(
        target_store, target_reviews, competitors, 
        competitor_reviews, statistical_comparison
    )
    
    # STEP 2: Claude 인사이트
    claude_result = analyze_with_claude(
        preprocessed, target_store, competitors, 
        competitor_reviews, statistical_comparison
    )
    
    if not claude_result:
        return None
    
    # STEP 3: 시각화 리포트
    print(f"\n{'='*60}")
    print(f"📊 STEP 3: 시각화 리포트 생성")
    print(f"{'='*60}")
    
    html_report = generate_visual_report(
        preprocessed, claude_result, target_store, competitors
    )
    
    # 파일 저장
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"report_{target_store['name'].replace(' ', '_')}_{timestamp}.html"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_report)
        print(f"   ✅ 리포트 저장: {filename}")
        print(f"   💡 브라우저로 열어보세요!")
        
        return html_report  # HTML 문자열 반환
        
    except Exception as e:
        print(f"   ❌ 파일 저장 실패: {e}")
        return None