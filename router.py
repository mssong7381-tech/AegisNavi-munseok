# -*- coding: utf-8 -*-
"""
router.py
Rule-based Router for MaintQA Architecture:
Determines whether a query follows:
1. 'AGGREGATE' (Text-to-SQL): queries asking for counts, averages, lists, costs, rankings.
2. 'PROCEDURE' (RAG): queries asking for how-to, procedures, technical specs, warnings/cautions.
3. 'FOLLOW_UP': queries with demonstratives or <= 8 characters that require rewrites from the previous 3 turns.

Runs via deterministic regular expressions without calling LLM (0.1ms latency).
"""

import re

# Regex patterns for Text-to-SQL (집계형 경로)
SQL_PATTERNS = [
    r"몇\s*건",
    r"건수",
    r"개수",
    r"총\s*건",
    r"수량",
    r"몇\s*개",
    r"평균",
    r"합계",
    r"총합",
    r"누적",
    r"통계",
    r"비율",
    r"비용",
    r"금액",
    r"단가",
    r"지출",
    r"얼마(?:인가|였|인가요)",
    r"순위",
    r"랭킹",
    r"상위\s*\d*",
    r"하위\s*\d*",
    r"가장\s*많은",
    r"최다",
    r"가장\s*적은",
    r"최소",
    r"선박별",
    r"기기별",
    r"월별",
    r"연도별",
    r"부품\s*소모",
    r"목록(?:을|만)?\s*(?:보여줘|출력|조회|알려줘)?",
    r"리스트",
    r"현황(?:은|을)?",
    r"top\s*\d+",
    # English SQL patterns
    r"\bcount\b",
    r"\bhow many\b",
    r"\bdocument count\b",
    r"\bpercentage\b",
    r"\btotal\b",
    r"\bsum\b",
    r"\baverage\b",
    r"\brank\b",
    r"\branking\b",
    r"\bshow (?:the )?(?:document|maintenance|records|count)\b",
    r"\bcount the\b"
]

# Regex patterns for RAG (절차형 경로)
RAG_PATTERNS = [
    r"어떻게",
    r"방법",
    r"절차",
    r"순서",
    r"과정",
    r"단계",
    r"요령",
    r"수칙",
    r"매뉴얼",
    r"지침",
    r"가이드",
    r"기술값",
    r"스펙",
    r"규격",
    r"토크(?:값)?",
    r"압력(?:값)?",
    r"간극",
    r"클리어런스",
    r"온도",
    r"허용치",
    r"기준값",
    r"허용한도",
    r"위험",
    r"조심",
    r"주의(?:사항)?",
    r"안전",
    r"사고\s*예방",
    r"고장\s*(?:원인|진단|현상)",
    r"원인",
    r"대처",
    r"조치\s*(?:방법|내역)",
    r"분해",
    r"조립",
    r"오버홀",
    r"인발",
    r"발출",
    r"세정",
    r"소탕",
    r"교체\s*(?:방법|절차)",
    r"래핑",
    r"디스케일링",
    r"점검\s*(?:방법|절차)",
    # English RAG patterns
    r"\bhow to\b",
    r"\bprocedure\b",
    r"\btorque\b",
    r"\bpressure\b",
    r"\bclearance\b",
    r"\bwater washing\b",
    r"\bwhat was found\b",
    r"\bwhat causes\b",
    r"\brenewal criterion\b",
    r"\bset pressure\b",
    r"\bhow should\b",
    r"\bwhat engine load\b"
]

# Regex patterns for Follow-up / Demonstratives (후속 질문 판정)
FOLLOW_UP_PATTERNS = [
    r"그거",
    r"그\s*작업",
    r"이전\s*(?:건|작업|질문)",
    r"그\s*배",
    r"해당\s*선박",
    r"이\s*기기",
    r"그\s*장비",
    r"그때",
    r"방금",
    r"앞서",
    r"거기서",
    r"비용은\??",
    r"절차는\??",
    r"원인은\??"
]

SQL_REGEX = re.compile("|".join(SQL_PATTERNS), re.IGNORECASE)
RAG_REGEX = re.compile("|".join(RAG_PATTERNS), re.IGNORECASE)
FOLLOW_UP_REGEX = re.compile("|".join(FOLLOW_UP_PATTERNS), re.IGNORECASE)

def needs_followup_rewrite(query: str) -> bool:
    """
    Returns True if query has demonstratives or is <= 8 characters.
    According to diagram: '지시어가 있거나 8자 이하인 질문만 직전 3턴으로 재작성'
    """
    cleaned = query.strip()
    if len(cleaned) <= 8:
        return True
    if FOLLOW_UP_REGEX.search(cleaned):
        return True
    return False

def route_query(query: str) -> str:
    """
    Routes the query into 'AGGREGATE' (Text-to-SQL) or 'PROCEDURE' (RAG).
    Returns: 'AGGREGATE' or 'PROCEDURE'
    """
    cleaned = query.strip()

    sql_match = SQL_REGEX.search(cleaned)
    rag_match = RAG_REGEX.search(cleaned)

    # If SQL patterns match strongly
    if sql_match and not rag_match:
        return "AGGREGATE"
    elif rag_match and not sql_match:
        return "PROCEDURE"
    elif sql_match and rag_match:
        # Conflict resolution: if asking for count/cost/list of procedures vs procedure itself
        if any(kw in cleaned for kw in ["건수", "몇 건", "순위", "합계", "비용", "평균", "목록"]):
            return "AGGREGATE"
        else:
            return "PROCEDURE"
    else:
        # Default fallback: if asks for information about a component/maintenance, treat as PROCEDURE (RAG)
        return "PROCEDURE"

if __name__ == "__main__":
    # Test cases
    test_queries = [
        "한바다호의 2024년 전체 정비 작업 건수는 몇 건인가요?",
        "2024년 선박별 누적 정비 비용 순위를 보여줘",
        "주기관 실린더 커버 분해 절차와 규정 유압 토크값은?",
        "연료유 청정기 볼 분해 소탕 방법 및 주의사항 알려줘",
        "그거 비용은?",
        "절차는?",
        "원자로 냉각 펌프 정비 비용은?"
    ]
    for q in test_queries:
        f_up = needs_followup_rewrite(q)
        route = route_query(q)
        print(f"Query: '{q}' -> FollowUpRewrite: {f_up}, Route: {route}")

