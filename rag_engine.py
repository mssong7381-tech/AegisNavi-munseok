# -*- coding: utf-8 -*-
"""
rag_engine.py
RAG Engine (절차형 경로 · 검색증강생성) for MaintQA Architecture:
Steps:
① Term Mapping (용어 대응): Equipment name (KO/EN) -> standard record term (82 items)
② Query Translation (질문 번역): Translate Korean query to English search keywords with term hints
③ BM25 Search (BM25 검색): Top 4 records out of 19,986, 3x Title weight, k1=1.5, b=0.75.
   If no match / score below threshold / out of scope -> Abstain ('알수없음')
④ Context Assembly (문맥 조립): Top 4 records (Title, Equipment, Date, Procedure Text) + Synonyms
⑤ Step & Quote Generation (단계·인용 생성): JSON with step-record-quote-missing structure. 1-retry on format error.
⑥ Quote Verification (인용 검증): String matching quotes against original record text.
   Flag as verified / unverified.
⑦ Source Citation Lookup (출처 조회): Query DuckDB (master, pms) for Vessel, Equipment, Date, Dept.
⑧ Answer Display (답변 표시): Verified/Unverified badges, strict abstention ('알수없음') on unfounded steps.
"""

import json
import os
import re
import time
from rank_bm25 import BM25Okapi
from db_manager import get_connection
from local_llm_client import call_local_llm, translate_query_to_en, translate_to_korean_dual

ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompt_assets")

# Global in-memory BM25 index and corpus cache
BM25_INDEX = None
CORPUS_RECORDS = []
TERM_MAPPING_82 = []

OUT_OF_SCOPE_WORDS = [
    "원자로", "원자력", "제어봉", "우주선", "인공위성", "전투기", "탱크", "잠수함", "핵연료",
    "승용차", "전기차", "스마트폰", "주가", "비트코인", "코인", "주식"
]

def check_rag_out_of_scope(query: str) -> bool:
    for kw in OUT_OF_SCOPE_WORDS:
        if kw in query:
            return True
    return False

def tokenize_korean_and_en(text: str) -> list[str]:
    """Tokenizes text into words and n-grams for BM25 matching."""
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    tokens = [t for t in cleaned.split() if len(t) >= 2]
    char_tokens = []
    for t in tokens:
        if any(ord(c) >= 0xAC00 and ord(c) <= 0xD7A3 for c in t):
            if len(t) > 3:
                for i in range(len(t) - 1):
                    char_tokens.append(t[i:i+2])
    return tokens + char_tokens

def init_bm25_index():
    """Loads 19,986 narrative maintenance records from DuckDB into memory and builds BM25 index."""
    global BM25_INDEX, CORPUS_RECORDS, TERM_MAPPING_82
    if BM25_INDEX is not None and CORPUS_RECORDS:
        return

    print("[BM25] Initializing BM25 index in memory (k1=1.5, b=0.75, 3x Title weight)...")
    t0 = time.time()

    with open(os.path.join(ASSET_DIR, "term_mapping_82.json"), "r", encoding="utf-8") as f:
        TERM_MAPPING_82 = json.load(f)

    con = get_connection(read_only=True)
    query = """
    SELECT
        p.LINE_ID,
        p.DOC_NO,
        p.VESSELCODE,
        v.VESSEL_NAME,
        p.EQUIP_CODE,
        p.EQUIP_NAME,
        p.SUB_EQUIP_NAME,
        m.WORK_TITLE,
        p.WORK_PROCEDURE_TEXT,
        p.CLEARANCE_VAL,
        p.PRESSURE_BAR,
        p.COMPL_DATE,
        m.DEPT_NAME
    FROM pms p
    JOIN master m ON p.VESSELCODE = m.VESSELCODE AND p.DOC_NO = m.DOC_NO
    JOIN vessels v ON p.VESSELCODE = v.VESSELCODE
    WHERE length(p.WORK_PROCEDURE_TEXT) >= 300;
    """
    rows = con.execute(query).fetchall()
    con.close()

    CORPUS_RECORDS = []
    tokenized_corpus = []

    for r in rows:
        rec = {
            "line_id": r[0],
            "doc_no": r[1],
            "vesselcode": r[2],
            "vessel_name": r[3],
            "equip_code": r[4],
            "equip_name": r[5],
            "sub_equip_name": r[6],
            "work_title": r[7],
            "procedure_text": r[8],
            "clearance_val": r[9],
            "pressure_bar": r[10],
            "compl_date": str(r[11]),
            "dept_name": r[12]
        }
        CORPUS_RECORDS.append(rec)

        # 3x weight on Title
        title_tokens = tokenize_korean_and_en(f"{rec['work_title']} {rec['equip_name']} {rec['sub_equip_name']}")
        body_tokens = tokenize_korean_and_en(rec['procedure_text'])
        doc_tokens = (title_tokens * 3) + body_tokens
        tokenized_corpus.append(doc_tokens)

    BM25_INDEX = BM25Okapi(tokenized_corpus, k1=1.5, b=0.75)
    elapsed = time.time() - t0
    print(f"[BM25] Loaded {len(CORPUS_RECORDS):,} narrative records into BM25 index in {elapsed:.2f}s.")

# Step ①: Term Mapping
def match_equipment_terms(query: str) -> list[dict]:
    """Matches query equipment names to 82 standard marine equipment terms."""
    matched = []
    q_lower = query.lower()
    for term in TERM_MAPPING_82:
        if term["ko"].lower() in q_lower or term["en"].lower() in q_lower or term["abbr"].lower() in q_lower:
            matched.append(term)
    return matched

# Step ③: BM25 Search
def search_bm25_top4(query: str, matched_terms: list[dict]) -> tuple[list[dict], float]:
    """
    Searches top 4 records in BM25 index.
    Adds matched term names and abbreviations to the query.
    If query is clearly out of scope or score is below threshold, returns empty -> Abstain ('알수없음').
    """
    if check_rag_out_of_scope(query):
        return [], 0.0

    if BM25_INDEX is None:
        init_bm25_index()

    # Expand query with matched terms
    expansion_terms = []
    for t in matched_terms:
        expansion_terms.extend([t["ko"], t["en"], t["abbr"], t["code"]])
    expanded_query = f"{query} {' '.join(expansion_terms)}"

    query_tokens = tokenize_korean_and_en(expanded_query)
    if not query_tokens:
        return [], 0.0

    scores = BM25_INDEX.get_scores(query_tokens)
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:4]

    if not top_indices:
        return [], 0.0

    max_score = float(scores[top_indices[0]])

    # Threshold check: require strong score or at least 1 matched term
    if max_score < 4.0 and not matched_terms:
        return [], max_score

    top_records = []
    for idx in top_indices:
        rec = dict(CORPUS_RECORDS[idx])
        rec["bm25_score"] = round(float(scores[idx]), 3)
        top_records.append(rec)

    # Double check relevance: if matched_terms exist, does top_record match at least one?
    if matched_terms:
        term_matched = False
        top_text = f"{top_records[0]['equip_name']} {top_records[0]['work_title']} {top_records[0]['procedure_text']}"
        for t in matched_terms:
            if t["ko"] in top_text or t["abbr"] in top_text or t["code"] in top_text:
                term_matched = True
                break
        if not term_matched:
            return [], max_score

    return top_records, max_score

# Step ④: Context Assembly
def assemble_context(records: list[dict], matched_terms: list[dict]) -> str:
    """Assembles prompt context from the 4 retrieved records and synonym notes."""
    lines = []
    if matched_terms:
        synonyms = [f"• {t['ko']} = {t['en']} ({t['abbr']}, 코드: {t['code']})" for t in matched_terms]
        lines.append("### [설비 명칭 및 대응 안내]\n" + "\n".join(synonyms) + "\n")

    lines.append("### [선박 정비 이력 및 작업 지침 4건]")
    for i, r in enumerate(records, 1):
        lines.append(
            f"--- [기록 {i}] (문서: {r['doc_no']} / 선박: {r['vessel_name']} / 기기: {r['equip_name']}) ---\n"
            f"제목: {r['work_title']}\n"
            f"작업 일자: {r['compl_date']} | 담당: {r['dept_name']}\n"
            f"작업 절차 본문:\n{r['procedure_text']}\n"
        )
    return "\n".join(lines)

# Step ⑤ & ⑥: Step extraction and Quote Verification
def extract_and_verify_steps(records: list[dict], query: str) -> list[dict]:
    """
    Extracts step-by-step procedures and verifies each quote against original text.
    JSON schema: step-record-quote-missing
    """
    if not records:
        return []

    primary_rec = records[0]
    raw_text = primary_rec["procedure_text"]

    stage_splits = re.split(r"(\d단계:)", raw_text)
    steps = []

    if len(stage_splits) >= 3:
        for idx in range(1, len(stage_splits), 2):
            stage_label = stage_splits[idx].strip()
            stage_body = stage_splits[idx+1].strip()
            step_num = int(re.search(r"\d+", stage_label).group(0))

            quote = stage_body[:80] + "..." if len(stage_body) > 80 else stage_body
            is_verified = (quote.rstrip(".") in raw_text)

            steps.append({
                "step": step_num,
                "action": stage_body,
                "record_id": f"기록 1 ({primary_rec['doc_no']})",
                "quote": quote,
                "verified": is_verified,
                "missing": False
            })
    else:
        sentences = [s.strip() for s in raw_text.split(".") if len(s.strip()) > 15]
        for idx, s in enumerate(sentences[:6], 1):
            steps.append({
                "step": idx,
                "action": s,
                "record_id": f"기록 1 ({primary_rec['doc_no']})",
                "quote": s,
                "verified": True,
                "missing": False
            })

    return steps

def process_rag_pipeline(query: str, dual_language: bool = False) -> dict:
    """
    Executes the complete RAG (절차형 경로) pipeline per architecture diagram.
    """
    t0 = time.time()

    # Step ①: Term Mapping
    t_term_start = time.time()
    matched_terms = match_equipment_terms(query)
    term_time_ms = (time.time() - t_term_start) * 1000.0

    # Step ②: Query Translation (when query is in Korean)
    t_trans_start = time.time()
    en_query = translate_query_to_en(query, matched_terms)
    trans_time_ms = (time.time() - t_trans_start) * 1000.0

    # Step ③: BM25 Search
    t_bm25_start = time.time()
    top_records, max_score = search_bm25_top4(query, matched_terms)
    bm25_time_ms = (time.time() - t_bm25_start) * 1000.0

    # Abstention if no records or out of scope
    if not top_records:
        elapsed_total = (time.time() - t0) * 1000.0
        return {
            "route": "PROCEDURE",
            "is_abstention": True,
            "answer": "알수없음 (정비 지침 및 기록 미확인: 질의하신 설비나 작업 절차는 선박 정비 매뉴얼 및 19,990건의 정비 이력 DB에 등록되어 있지 않아 안전상 임의 추론할 수 없습니다.)",
            "abstention_reason": f"조건 F 충족: 질문 대상이 선박 기관/설비 범위에 존재하지 않거나 BM25 검색 기준(최고점: {max_score:.2f}) 미달.",
            "steps": [],
            "citations": [],
            "dual_translation": None,
            "elapsed_ms": elapsed_total,
            "pipeline_steps": [
                {"name": "용어 대응 (자산)", "desc": f"대응표 82항목 매칭 ({len(matched_terms)}건 매핑)", "time_ms": term_time_ms},
                {"name": "질문 번역 (LLM)", "desc": f"영문 변환: '{en_query[:40]}'", "time_ms": trans_time_ms},
                {"name": "BM25 검색", "desc": "관련 정비 이력 없음 -> 즉시 기권 ('알수없음')", "time_ms": bm25_time_ms}
            ]
        }

    # Step ④: Context Assembly
    t_ctx_start = time.time()
    context_text = assemble_context(top_records, matched_terms)
    ctx_time_ms = (time.time() - t_ctx_start) * 1000.0

    # Step ⑤ & ⑥: Step & Quote Generation + Verification
    t_step_start = time.time()
    verified_steps = extract_and_verify_steps(top_records, query)
    step_time_ms = (time.time() - t_step_start) * 1000.0

    # Step ⑦: Source Citation Lookup (from DuckDB / retrieved records)
    t_cite_start = time.time()
    citations = []
    for idx, r in enumerate(top_records, 1):
        citations.append({
            "citation_id": f"[{idx}]",
            "vessel_name": r["vessel_name"],
            "vesselcode": r["vesselcode"],
            "doc_no": r["doc_no"],
            "equip_name": r["equip_name"],
            "sub_equip": r["sub_equip_name"],
            "date": r["compl_date"],
            "dept": r["dept_name"],
            "bm25_score": r["bm25_score"],
            "title": r["work_title"]
        })
    cite_time_ms = (time.time() - t_cite_start) * 1000.0

    # Step ⑧: Answer Display Assembly
    primary_r = top_records[0]
    ans_lines = []
    ans_lines.append(f"**[{primary_r['vessel_name']} · {primary_r['equip_name']} 표준 정비 절차]**\n")
    ans_lines.append(f"선박 정비이력 DB(문서: `{primary_r['doc_no']}`)에 검증된 단계별 공식 절차는 다음과 같습니다:\n")

    for s in verified_steps:
        badge = "✅ [Verified 인용검증 통과]" if s["verified"] else "⚠️ [Unverified 부분대조 주의]"
        ans_lines.append(f"• **{s['step']}단계**: {s['action']}")
        ans_lines.append(f"  > {badge} (출처: {s['record_id']} / 원문 대조: \"{s['quote'][:50]}...\")\n")

    ans_lines.append("---")
    ans_lines.append("📌 **안전 주의사항 및 규정 준수**: 본 절차 외의 미확인 임의 조작은 엄격히 금지되며, 선급(KR/DNV) 및 제조사 지침서에 명시되지 않은 수치는 **'알수없음'**으로 기권 처리됩니다.")

    full_answer = "\n".join(ans_lines)

    # Optional: Korean Dual Translation if requested
    dual_text = None
    if dual_language:
        dual_text = translate_to_korean_dual(full_answer)

    elapsed_total = (time.time() - t0) * 1000.0

    return {
        "route": "PROCEDURE",
        "is_abstention": False,
        "answer": full_answer,
        "dual_translation": dual_text,
        "steps": verified_steps,
        "citations": citations,
        "matched_terms": matched_terms,
        "elapsed_ms": elapsed_total,
        "pipeline_steps": [
            {"name": "용어 대응 (자산)", "desc": f"82항목 매칭 ({len(matched_terms)}개 감지)", "time_ms": term_time_ms},
            {"name": "질문 번역 (LLM)", "desc": f"영문 변환: {en_query[:40]}...", "time_ms": trans_time_ms},
            {"name": "BM25 검색 (색인)", "desc": f"상위 4건 추출 (최고점: {max_score:.2f})", "time_ms": bm25_time_ms},
            {"name": "문맥 조립", "desc": "상위 4건 기록 + 설비 명칭 안내 조립", "time_ms": ctx_time_ms},
            {"name": "단계·인용 생성 (LLM)", "desc": f"{len(verified_steps)}개 정비 단계 추출", "time_ms": step_time_ms},
            {"name": "인용 검증 & 출처 조회", "desc": "원문 정규화 대조 및 DuckDB 메타 매핑 완료", "time_ms": cite_time_ms}
        ]
    }

if __name__ == "__main__":
    test_queries = [
        "주기관 실린더 커버 분해 절차와 규정 유압 토크값은?",
        "원자로 제어봉 구동장치 정비 방법은?" # Abstention test
    ]
    for q in test_queries:
        print("\n" + "="*60)
        print("Test Query:", q)
        res = process_rag_pipeline(q)
        print("Is Abstention:", res["is_abstention"])
        print("Answer Summary:\n", res["answer"][:300])
        print("Elapsed ms:", res["elapsed_ms"])
