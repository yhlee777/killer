# -*- coding: utf-8 -*-
# all_in_one_html.py - 모든 분석을 HTML 하나로!

import os
import json
from datetime import datetime
from openai import OpenAI
from anthropic import Anthropic

openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
anthropic_client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))


def deep_analyze_reviews(target_reviews, target_store):
    """
    리뷰 심층 분석 (단점 절대 놓치지 않기!)
    """
    print(f"\n{'='*60}")
    print(f"🔍 심층 리뷰 분석 (단점 집중 탐지)")
    print(f"{'='*60}")
    
    # 별점별 분류
    by_rating = {1: [], 2: [], 3: [], 4: [], 5: []}
    for r in target_reviews:
        rating = int(r.get('rating', 5))
        if rating == 0:
            rating = 5
        by_rating[rating].append(r)
    
    print(f"   별점 분포:")
    for rating in [1, 2, 3, 4, 5]:
        count = len(by_rating[rating])
        print(f"      {'★' * rating}: {count}개")
    
    # 부정 리뷰 우선
    negative_reviews = by_rating[1] + by_rating[2] + by_rating[3][:10]
    positive_reviews = by_rating[5][:30] + by_rating[4][:20]
    
    review_text = "## 🚨 부정/중립 리뷰 (우선 분석)\n\n"
    for i, r in enumerate(negative_reviews[:30], 1):
        review_text += f"[리뷰#{i}] ★{int(r.get('rating', 0))} - {r['content'][:300]}\n\n"
    
    review_text += "\n## ✅ 긍정 리뷰\n\n"
    for i, r in enumerate(positive_reviews[:30], 31):
        review_text += f"[리뷰#{i}] ★{int(r.get('rating', 0))} - {r['content'][:200]}\n\n"
    
    prompt = f"""당신은 레스토랑 컨설턴트입니다. 아래 리뷰를 **철저히** 분석하세요.

{review_text}

## 🚨 중요: 단점을 절대 놓치지 마세요!

**단점 탐지 규칙**:
1. 별점 1-3점은 무조건 단점으로 간주
2. 부정 키워드: "별로", "실망", "아쉽", "비싸", "불친절", "느리", "짜", "싱겁", "미지근", "식", "늦", "더럽"
3. 작은 불만도 모두 기록
4. "그나마 괜찮", "그럭저럭" 같은 애매한 표현도 약점으로

## JSON 출력

{{
  "장점": [
    {{
      "aspect": "맛",
      "count": 18,
      "percentage": 28.0,
      "samples": ["[리뷰#31] 진짜 맛있어요"],
      "severity": "강점"  // "강점", "보통", "약함"
    }}
  ],
  "단점": [
    {{
      "aspect": "온도 관리",
      "count": 5,
      "percentage": 7.8,
      "samples": ["[리뷰#3] 커피가 미지근", "[리뷰#7] 파스타 식어서 나옴"],
      "severity": "심각"  // "심각", "보통", "경미"
    }},
    {{
      "aspect": "가격",
      "count": 3,
      "percentage": 4.7,
      "samples": ["[리뷰#5] 가격이 비싸요"],
      "severity": "보통"
    }}
  ],
  "잠재적_개선점": [
    "메뉴 다양성 부족 (경쟁사 대비)",
    "재방문 유도 프로그램 부재"
  ]
}}

**규칙**:
- 단점이 0개일 수 없음! 최소 3개 이상 찾기
- 리뷰 번호 [리뷰#N] 필수
- 비율 정확히 계산
"""
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "당신은 비판적 사고를 하는 컨설턴트입니다. 단점을 놓치지 마세요!"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=4000,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        print(f"   ✅ 분석 완료")
        print(f"      장점: {len(result.get('장점', []))}개")
        print(f"      단점: {len(result.get('단점', []))}개")
        
        return result
        
    except Exception as e:
        print(f"   ❌ 분석 실패: {e}")
        return {"장점": [], "단점": [], "잠재적_개선점": []}


def generate_all_in_one_html(
    target_store,
    target_reviews,
    blog_profile,
    analysis_result,
    competitors,
    statistical_comparison
):
    """
    모든 분석을 HTML 하나로 통합
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 데이터 준비
    strengths = analysis_result.get('장점', [])
    weaknesses = analysis_result.get('단점', [])
    improvements = analysis_result.get('잠재적_개선점', [])
    
    # 장점 차트 데이터
    strengths_labels = [s['aspect'] for s in strengths[:6]]
    strengths_values = [s['percentage'] for s in strengths[:6]]
    
    # 단점 차트 데이터
    weaknesses_labels = [w['aspect'] for w in weaknesses[:6]]
    weaknesses_values = [w['percentage'] for w in weaknesses[:6]]
    
    # 별점 분포
    rating_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in target_reviews:
        rating = int(r.get('rating', 5))
        if rating == 0:
            rating = 5
        rating_dist[rating] += 1
    
    # 블로그 데이터
    blog_html = ""
    if blog_profile:
        blog_html = f"""
        <div class="section">
            <h2>📱 블로그 평판 분석</h2>
            <div class="grid-3">
                <div class="stat-card">
                    <div class="stat-value">{blog_profile.total_blog_posts}</div>
                    <div class="stat-label">분석 블로그</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{blog_profile.positive_ratio:.1%}</div>
                    <div class="stat-label">긍정 비율</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{blog_profile.concept}</div>
                    <div class="stat-label">인식 컨셉</div>
                </div>
            </div>
            <div class="blog-insights">
                <h3>주요 방문 목적</h3>
                <ul>
                    {' '.join([f"<li>{purpose}: {count}회</li>" for purpose, count in list(blog_profile.visit_purposes.items())[:3]])}
                </ul>
                <h3>분위기</h3>
                <p>{', '.join(blog_profile.atmosphere_keywords[:5])}</p>
            </div>
        </div>
        """
    
    # 경쟁사 비교
    comp_html = ""
    if statistical_comparison:
        comp_strengths = statistical_comparison.get('우리의_강점', {})
        comp_weaknesses = statistical_comparison.get('우리의_약점', {})
        
        comp_html = f"""
        <div class="section">
            <h2>🏆 경쟁사 비교 ({len(competitors)}개)</h2>
            <div class="grid-2">
                <div>
                    <h3>✅ 우리가 강한 부분</h3>
                    <ul class="comparison-list">
                        {' '.join([f"<li class='positive'><strong>{topic}</strong>: 우리 {stat['our']['rate']*100:.1f}% vs 경쟁사 {stat['comp']['rate']*100:.1f}%</li>" for topic, stat in list(comp_strengths.items())[:5]])}
                    </ul>
                </div>
                <div>
                    <h3>⚠️ 우리가 약한 부분</h3>
                    <ul class="comparison-list">
                        {' '.join([f"<li class='negative'><strong>{topic}</strong>: 우리 {stat['our']['rate']*100:.1f}% vs 경쟁사 {stat['comp']['rate']*100:.1f}%</li>" for topic, stat in list(comp_weaknesses.items())[:5]])}
                    </ul>
                </div>
            </div>
        </div>
        """
    
    # HTML 생성
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{target_store['name']} - 올인원 분석 리포트</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Segoe UI', 'Noto Sans KR', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        .meta {{
            opacity: 0.9;
            font-size: 1.1em;
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .section {{
            background: #f8f9fa;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        }}
        
        h2 {{
            color: #333;
            font-size: 1.8em;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}
        
        h3 {{
            color: #555;
            font-size: 1.3em;
            margin: 20px 0 15px 0;
        }}
        
        .grid-2 {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }}
        
        .grid-3 {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
        }}
        
        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 10px;
        }}
        
        .stat-label {{
            color: #666;
            font-size: 1.1em;
        }}
        
        .chart-container {{
            background: white;
            padding: 25px;
            border-radius: 12px;
            margin: 20px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .chart-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }}
        
        .weakness-item {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin: 15px 0;
            border-left: 4px solid #ff6b6b;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .weakness-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        
        .weakness-title {{
            font-size: 1.2em;
            font-weight: bold;
            color: #333;
        }}
        
        .weakness-severity {{
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
        }}
        
        .severity-심각 {{ background: #ff6b6b; color: white; }}
        .severity-보통 {{ background: #feca57; color: #333; }}
        .severity-경미 {{ background: #48dbfb; color: white; }}
        
        .weakness-stats {{
            color: #666;
            margin: 10px 0;
        }}
        
        .weakness-samples {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
        }}
        
        .review-sample {{
            padding: 8px 0;
            color: #555;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        .review-sample:last-child {{
            border-bottom: none;
        }}
        
        .strength-item {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin: 15px 0;
            border-left: 4px solid #51cf66;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .comparison-list {{
            list-style: none;
            padding: 0;
        }}
        
        .comparison-list li {{
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
            background: white;
        }}
        
        .comparison-list li.positive {{
            border-left: 4px solid #51cf66;
        }}
        
        .comparison-list li.negative {{
            border-left: 4px solid #ff6b6b;
        }}
        
        .checklist {{
            background: white;
            padding: 20px;
            border-radius: 10px;
        }}
        
        .checklist-item {{
            padding: 15px;
            margin: 10px 0;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #667eea;
            cursor: pointer;
            transition: all 0.3s;
        }}
        
        .checklist-item:hover {{
            background: #e9ecef;
            transform: translateX(5px);
        }}
        
        .checklist-item input {{
            margin-right: 15px;
            transform: scale(1.5);
            cursor: pointer;
        }}
        
        .alert {{
            background: #fff3cd;
            border: 2px solid #ffc107;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
        }}
        
        .alert-title {{
            font-weight: bold;
            color: #856404;
            margin-bottom: 10px;
            font-size: 1.2em;
        }}
        
        .improvement-list {{
            list-style: none;
            padding: 0;
        }}
        
        .improvement-list li {{
            padding: 12px;
            margin: 8px 0;
            background: white;
            border-radius: 6px;
            border-left: 3px solid #667eea;
        }}
        
        @media (max-width: 768px) {{
            .grid-2, .grid-3, .chart-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        
        @media print {{
            body {{
                background: white;
            }}
            .container {{
                box-shadow: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏪 {target_store['name']}</h1>
            <div class="meta">
                📅 {timestamp} | 📍 {target_store['district']} | 🍽️ {target_store['industry']}
            </div>
            <div class="meta" style="margin-top: 15px; font-size: 1em;">
                분석 리뷰: {len(target_reviews)}개 | 경쟁사: {len(competitors)}개
            </div>
        </div>
        
        <div class="content">
            <!-- 종합 통계 -->
            <div class="section">
                <h2>📊 종합 통계</h2>
                <div class="grid-3">
                    <div class="stat-card">
                        <div class="stat-value">{len(strengths)}</div>
                        <div class="stat-label">발견된 장점</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" style="color: #ff6b6b;">{len(weaknesses)}</div>
                        <div class="stat-label">발견된 단점</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{rating_dist[5] / len(target_reviews) * 100:.1f}%</div>
                        <div class="stat-label">5점 비율</div>
                    </div>
                </div>
                
                <div class="chart-container">
                    <canvas id="rating-chart" style="max-height: 300px;"></canvas>
                </div>
            </div>
            
            <!-- 블로그 분석 -->
            {blog_html}
            
            <!-- 장점 분석 -->
            <div class="section">
                <h2>✅ 우리 가게 장점</h2>
                <div class="chart-grid">
                    <div class="chart-container">
                        <canvas id="strengths-pie"></canvas>
                    </div>
                    <div>
                        {''.join([f'''
                        <div class="strength-item">
                            <div class="weakness-header">
                                <div class="weakness-title">{s['aspect']}</div>
                                <div class="weakness-stats">{s['count']}회 ({s['percentage']:.1f}%)</div>
                            </div>
                            <div class="weakness-samples">
                                {''.join([f'<div class="review-sample">💬 {sample}</div>' for sample in s['samples'][:2]])}
                            </div>
                        </div>
                        ''' for s in strengths[:5]])}
                    </div>
                </div>
            </div>
            
            <!-- 단점 분석 -->
            <div class="section">
                <h2>⚠️ 개선이 필요한 부분</h2>
                
                {'<div class="alert"><div class="alert-title">⚠️ 분석 결과</div><p>150개 리뷰를 분석한 결과, 다음과 같은 개선점이 발견되었습니다.</p></div>' if weaknesses else '<div class="alert" style="background: #d4edda; border-color: #28a745;"><div class="alert-title" style="color: #155724;">✅ 우수한 상태</div><p>고객 만족도가 매우 높습니다!</p></div>'}
                
                <div class="chart-grid">
                    <div class="chart-container">
                        <canvas id="weaknesses-pie"></canvas>
                    </div>
                    <div>
                        {''.join([f'''
                        <div class="weakness-item">
                            <div class="weakness-header">
                                <div class="weakness-title">🚨 {w['aspect']}</div>
                                <div class="weakness-severity severity-{w['severity']}">{w['severity']}</div>
                            </div>
                            <div class="weakness-stats">
                                📊 {w['count']}회 언급 ({w['percentage']:.1f}%)
                            </div>
                            <div class="weakness-samples">
                                <strong>실제 리뷰:</strong>
                                {''.join([f'<div class="review-sample">💬 {sample}</div>' for sample in w['samples'][:3]])}
                            </div>
                        </div>
                        ''' for w in weaknesses])}
                    </div>
                </div>
                
                {'<h3>💡 잠재적 개선 기회</h3><ul class="improvement-list">' + ''.join([f'<li>{imp}</li>' for imp in improvements]) + '</ul>' if improvements else ''}
            </div>
            
            <!-- 경쟁사 비교 -->
            {comp_html}
            
            <!-- 2주 체크리스트 -->
            <div class="section">
                <h2>✅ 2주 실행 체크리스트</h2>
                <div class="checklist">
                    {''.join([f'''
                    <div class="checklist-item" onclick="this.querySelector('input').checked = !this.querySelector('input').checked">
                        <input type="checkbox">
                        <strong>{w['aspect']}</strong> 개선: {w['samples'][0].split(']')[1] if ']' in w['samples'][0] else w['samples'][0][:50]}에 대한 대응
                    </div>
                    ''' for w in weaknesses[:5]])}
                    
                    <div class="checklist-item" onclick="this.querySelector('input').checked = !this.querySelector('input').checked">
                        <input type="checkbox">
                        <strong>리뷰 관리</strong>: 네이버 플레이스 리뷰 주 5개 이상 확보
                    </div>
                    
                    <div class="checklist-item" onclick="this.querySelector('input').checked = !this.querySelector('input').checked">
                        <input type="checkbox">
                        <strong>SNS 업데이트</strong>: 인스타그램 주 3회 이상 포스팅
                    </div>
                    
                    <div class="checklist-item" onclick="this.querySelector('input').checked = !this.querySelector('input').checked">
                        <input type="checkbox">
                        <strong>고객 피드백</strong>: 테이블 QR 설문 20건 이상 수집
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // 별점 분포 차트
        new Chart(document.getElementById('rating-chart'), {{
            type: 'bar',
            data: {{
                labels: ['★', '★★', '★★★', '★★★★', '★★★★★'],
                datasets: [{{
                    label: '리뷰 수',
                    data: [{rating_dist[1]}, {rating_dist[2]}, {rating_dist[3]}, {rating_dist[4]}, {rating_dist[5]}],
                    backgroundColor: ['#ff6b6b', '#feca57', '#ffeaa7', '#55efc4', '#00b894']
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{ display: true, text: '별점 분포', font: {{ size: 18 }} }},
                    legend: {{ display: false }}
                }},
                scales: {{
                    y: {{ beginAtZero: true }}
                }}
            }}
        }});
        
        // 장점 파이 차트
        new Chart(document.getElementById('strengths-pie'), {{
            type: 'pie',
            data: {{
                labels: {json.dumps(strengths_labels, ensure_ascii=False)},
                datasets: [{{
                    data: {json.dumps(strengths_values)},
                    backgroundColor: [
                        '#667eea', '#764ba2', '#f093fb', '#4facfe',
                        '#43e97b', '#fa709a', '#fee140', '#30cfd0'
                    ]
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{ display: true, text: '장점 분포 (%)', font: {{ size: 16 }} }},
                    legend: {{ position: 'bottom' }}
                }}
            }}
        }});
        
        // 단점 파이 차트
        new Chart(document.getElementById('weaknesses-pie'), {{
            type: 'pie',
            data: {{
                labels: {json.dumps(weaknesses_labels, ensure_ascii=False)},
                datasets: [{{
                    data: {json.dumps(weaknesses_values)},
                    backgroundColor: [
                        '#ff6b6b', '#feca57', '#48dbfb',
                        '#ff8787', '#ffd93d', '#6bcf7f'
                    ]
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{ display: true, text: '단점 언급률 (%)', font: {{ size: 16 }} }},
                    legend: {{ position: 'bottom' }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
    
    return html


async def generate_all_in_one_report(
    target_store, target_reviews, blog_profile,
    competitors, competitor_reviews, statistical_comparison
):
    """
    메인 실행 함수 (mvp_analyzer.py에서 호출)
    """
    # STEP 1: 심층 분석
    analysis = deep_analyze_reviews(target_reviews, target_store)
    
    # STEP 2: HTML 생성
    html = generate_all_in_one_html(
        target_store, target_reviews, blog_profile,
        analysis, competitors, statistical_comparison
    )
    
    # STEP 3: 파일 저장
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"report_{target_store['name'].replace(' ', '_')}_{timestamp}.html"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"\n✅ 올인원 HTML 리포트 생성 완료!")
        print(f"📂 파일: {filename}")
        print(f"💡 브라우저로 열어보세요!")
        
        return html
        
    except Exception as e:
        print(f"❌ 파일 저장 실패: {e}")
        return None