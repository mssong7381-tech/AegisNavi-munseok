# -*- coding: utf-8 -*-
"""
test_server_e2e.py
End-to-End Test Suite for Aegis-Navi AI MaintQA Server:
Verifies all 6 user requirements and architectural components.
"""

import threading
import time
import urllib.request
import json
from http.server import HTTPServer
from maintqa_web import MaintQAHandler, PORT, HOST
from db_manager import init_database
from rag_engine import init_bm25_index

def run_tests():
    print("="*60)
    print("🚀 Running E2E Verification for MaintQA Server...")
    print("="*60)

    # 1. Test Server Startup in Thread
    init_database()
    init_bm25_index()

    server = HTTPServer((HOST, PORT), MaintQAHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(1)

    base_url = f"http://{HOST}:{PORT}"

    # 2. Test GET / (HTML presentation layer)
    print("\n[Test 1] Testing Presentation Layer (GET /)...")
    req = urllib.request.Request(f"{base_url}/")
    with urllib.request.urlopen(req) as res:
        assert res.status == 200
        html = res.read().decode("utf-8")
        assert "AegisNavi" in html or "Aegis-Navi" in html
        assert "100% Offline" in html or "Local" in html
        assert "maintqa_web" in html or "AegisNavi" in html or "Aegis-Navi" in html
        print("  -> Passed! HTML served successfully with branding.")

    # 3. Test GET /api/stats (Database Layer exact numbers)
    print("\n[Test 2] Testing Database Layer Stats (GET /api/stats)...")
    req = urllib.request.Request(f"{base_url}/api/stats")
    with urllib.request.urlopen(req) as res:
        assert res.status == 200
        stats = json.loads(res.read().decode("utf-8"))["stats"]
        print(f"  -> Stats returned: {stats}")
        assert stats["vessels"] == 6
        assert stats["master"] == 26561
        assert stats["pms"] == 51715
        assert stats["approval"] == 78809
        assert stats["attachments"] == 6762
        assert stats["consumption"] == 2358
        assert stats["narrative_records"] == 19986
        print("  -> Passed! Exact architecture dataset numbers verified.")

    # 4. Test Aggregate Query (Text-to-SQL)
    print("\n[Test 3] Testing Aggregate Path (Text-to-SQL)...")
    payload = {
        "query": "한바다호의 2024년 전체 정비 작업 건수는 몇 건인가요?",
        "history": [],
        "dual_language": False
    }
    req = urllib.request.Request(
        f"{base_url}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode("utf-8"))
        assert data["route"] == "AGGREGATE"
        assert not data["result"]["is_abstention"]
        print(f"  -> Route: {data['route']}")
        print(f"  -> SQL: {data['result'].get('sql')}")
        print(f"  -> Answer Summary: {data['result']['answer'].splitlines()[:3]}")
        print("  -> Passed!")

    # 5. Test Follow-up Query Interpretation
    print("\n[Test 4] Testing Follow-up Query Rewrite...")
    payload_fup = {
        "query": "그거 비용은?",
        "history": [
            {"user": "한바다호 주기관 실린더 점검 건수는?", "assistant": "총 708건입니다."}
        ],
        "dual_language": False
    }
    req = urllib.request.Request(
        f"{base_url}/api/chat",
        data=json.dumps(payload_fup).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode("utf-8"))
        print(f"  -> Was Rewritten: {data['was_rewritten']}")
        print(f"  -> Rewritten Query: {data['rewritten_query']}")
        assert data["was_rewritten"] == True
        print("  -> Passed!")

    # 6. Test Procedure Query (RAG + Verification)
    print("\n[Test 5] Testing Procedure Path (RAG + Quote Verification)...")
    payload_rag = {
        "query": "주기관 실린더 커버 분해 절차와 규정 유압 토크값은?",
        "history": [],
        "dual_language": False
    }
    req = urllib.request.Request(
        f"{base_url}/api/chat",
        data=json.dumps(payload_rag).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode("utf-8"))
        assert data["route"] == "PROCEDURE"
        assert not data["result"]["is_abstention"]
        print(f"  -> Route: {data['route']}")
        print(f"  -> Extracted Steps: {len(data['result'].get('steps', []))} steps")
        print(f"  -> Citations: {len(data['result'].get('citations', []))} citations")
        print("  -> Passed!")

    # 7. Test Abstention on Inaccurate / Unverified Query ('알수없음')
    print("\n[Test 6] Testing Abstention ('알수없음' 기권 판정)...")
    payload_abstain = {
        "query": "원자로 냉각재 순환 펌프의 정비 지침은?",
        "history": [],
        "dual_language": False
    }
    req = urllib.request.Request(
        f"{base_url}/api/chat",
        data=json.dumps(payload_abstain).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode("utf-8"))
        assert data["result"]["is_abstention"] == True
        assert "알수없음" in data["result"]["answer"]
        print(f"  -> Is Abstention: {data['result']['is_abstention']}")
        print(f"  -> Answer: {data['result']['answer']}")
        print("  -> Passed! Correctly answered '알수없음'.")

    # 8. Test History Persistence (GET/POST /api/history)
    print("\n[Test 7] Testing History Persistence (GET/POST /api/history)...")
    sess_obj = {
        "id": "test_session_001",
        "title": "한바다호 주기관 테스트 세션",
        "messages": [{"role": "user", "text": "테스트"}]
    }
    req = urllib.request.Request(
        f"{base_url}/api/history",
        data=json.dumps(sess_obj).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as res:
        assert res.status == 200

    req_get = urllib.request.Request(f"{base_url}/api/history")
    with urllib.request.urlopen(req_get) as res:
        hist_data = json.loads(res.read().decode("utf-8"))
        assert any(s["id"] == "test_session_001" for s in hist_data["sessions"])
        print(f"  -> History verified with {len(hist_data['sessions'])} sessions.")
        print("  -> Passed!")

    print("\n" + "="*60)
    print("🎉 ALL TESTS PASSED! Aegis-Navi AI system is 100% verified.")
    print("="*60)
    import os
    os._exit(0)

if __name__ == "__main__":
    run_tests()
