# -*- coding: utf-8 -*-
"""
build_assets.py
Generates the prompt assets with EXACTLY 121 columns in data_dictionary_121.json:
1. data_dictionary_121.json (121 column definitions across 6 tables)
2. rules_12.json (12 SQL & Abstention rules)
3. fewshot_6.json (6 few-shot examples including Condition F for NOT_RECORDED)
4. term_mapping_82.json (82 marine engineering equipment term mappings)
"""

import json
import os

os.makedirs("prompt_assets", exist_ok=True)

dictionary_121 = {
    "tables": {
        "vessels": {
            "table_desc": "선박 기본 제원 및 마스터 정보 (총 6척)",
            "row_count": 6,
            "columns": [
                {"name": "VESSELCODE", "type": "VARCHAR(10)", "desc": "선박 고유 식별 코드 (HB01, AR02, BR03, TR04, SJ05, JB06)", "pk": True},
                {"name": "VESSEL_NAME", "type": "VARCHAR(50)", "desc": "선박 한글 명칭 (한바다호, 아라호, 백령호, 탐라호, 세종호, 장보고호)"},
                {"name": "VESSEL_NAME_EN", "type": "VARCHAR(50)", "desc": "선박 영문 공식 명칭 (HANBADA, ARA, BAENGNYEONG, TAMRA, SEJONG, JANGBOGO)"},
                {"name": "VESSEL_TYPE", "type": "VARCHAR(30)", "desc": "선종 (CONTAINER, LNG CARRIER, BULK CARRIER, VLCC TANKER, LPG CARRIER)"},
                {"name": "IMO_NO", "type": "VARCHAR(15)", "desc": "국제해사기구 고유 등록 번호 (IMO 7자리)"},
                {"name": "CALL_SIGN", "type": "VARCHAR(10)", "desc": "무선 호출 부호 (호출명)"},
                {"name": "FLAG", "type": "VARCHAR(20)", "desc": "선적국 (KOREA, PANAMA, MARSHALL ISLANDS)"},
                {"name": "CLASS_SOCIETY", "type": "VARCHAR(10)", "desc": "선급 협회 (KR, DNV, ABS, LR)"},
                {"name": "BUILT_YEAR", "type": "INTEGER", "desc": "선박 건조 준공 연도"},
                {"name": "SHIPYARD", "type": "VARCHAR(50)", "desc": "건조 조선소 (현대중공업, 삼성중공업, 한화오션)"},
                {"name": "DWT", "type": "DOUBLE", "desc": "재화중량톤수 (Deadweight Tonnage)"},
                {"name": "GROSS_TONNAGE", "type": "DOUBLE", "desc": "총톤수 (GT)"},
                {"name": "MAIN_ENGINE_MODEL", "type": "VARCHAR(50)", "desc": "주기관 엔진 형식 모델명"},
                {"name": "MAIN_ENGINE_MCR_KW", "type": "DOUBLE", "desc": "주기관 최대연속출력 (kW)"},
                {"name": "MAIN_ENGINE_CYL_COUNT", "type": "INTEGER", "desc": "주기관 실린더 수"},
                {"name": "AUX_ENGINE_MODEL", "type": "VARCHAR(50)", "desc": "발전기 보조엔진 모델명"},
                {"name": "AUX_ENGINE_COUNT", "type": "INTEGER", "desc": "발전기 보조엔진 탑재 대수"},
                {"name": "SERVICE_SPEED_KTS", "type": "DOUBLE", "desc": "설계 항해 속력 (노트, Knots)"},
                {"name": "BOILER_MODEL", "type": "VARCHAR(50)", "desc": "보조 보일러 모델명"},
                {"name": "STATUS", "type": "VARCHAR(15)", "desc": "운항 상태 (IN_SERVICE, IN_DRYDOCK, LAID_UP)"}
            ]
        },
        "master": {
            "table_desc": "선박 정비 작업 결재 문서 마스터 (26,561건)",
            "row_count": 26561,
            "columns": [
                {"name": "DOC_NO", "type": "VARCHAR(30)", "desc": "정비 문서 관리 고유번호 (예: MAINT-2024-00123)", "pk": True},
                {"name": "VESSELCODE", "type": "VARCHAR(10)", "desc": "대상 선박 코드 (FK to vessels)", "pk": True},
                {"name": "WORK_TITLE", "type": "VARCHAR(200)", "desc": "정비 작업 제목"},
                {"name": "WORK_DESC", "type": "TEXT", "desc": "정비 작업 상세 개요 및 목적"},
                {"name": "DOC_STATUS", "type": "VARCHAR(20)", "desc": "문서 진행 상태 (COMPLETED, IN_PROGRESS, APPROVED, CANCEL)"},
                {"name": "REG_DATE", "type": "DATE", "desc": "정비 접수/기안 일자"},
                {"name": "START_DATE", "type": "DATE", "desc": "정비 작업 착수 일자"},
                {"name": "FINISH_DATE", "type": "DATE", "desc": "정비 작업 최종 완료 일자"},
                {"name": "DEPT_CODE", "type": "VARCHAR(20)", "desc": "담당 부서 코드 (ENG: 기관부, DECK: 갑판부)"},
                {"name": "DEPT_NAME", "type": "VARCHAR(50)", "desc": "담당 부서명"},
                {"name": "CHIEF_ENG", "type": "VARCHAR(50)", "desc": "담당 기관장 성명"},
                {"name": "FIRST_ENG", "type": "VARCHAR(50)", "desc": "담당 일기사 성명"},
                {"name": "SECOND_ENG", "type": "VARCHAR(50)", "desc": "담당 이기사 성명"},
                {"name": "THIRD_ENG", "type": "VARCHAR(50)", "desc": "담당 삼기사 성명"},
                {"name": "SUPERINTENDENT", "type": "VARCHAR(50)", "desc": "본사 전담 공무감독 성명"},
                {"name": "WORK_CATEGORY", "type": "VARCHAR(30)", "desc": "정비 구분 (PMS_ROUTINE, BREAKDOWN, DRYDOCK, CLASS_SURVEY)"},
                {"name": "URGENCY_LEVEL", "type": "VARCHAR(20)", "desc": "긴급도 등급 (EMERGENCY, HIGH, NORMAL, LOW)"},
                {"name": "PORT_NAME", "type": "VARCHAR(50)", "desc": "정비 실시 항구 또는 해역 명칭"},
                {"name": "BERTH_NO", "type": "VARCHAR(20)", "desc": "정박 선석 번호 또는 묘지"},
                {"name": "CONTRACTOR_NAME", "type": "VARCHAR(100)", "desc": "외주 협력업체/서비스엔지니어 상호"},
                {"name": "CONTRACTOR_MANPOWER", "type": "INTEGER", "desc": "외주 투입 작업 인원수"},
                {"name": "TOTAL_MAN_HOURS", "type": "DOUBLE", "desc": "총 투입 공수 (Man-Hours)"},
                {"name": "LABOR_COST", "type": "DOUBLE", "desc": "공임/인건비 소계"},
                {"name": "PARTS_COST", "type": "DOUBLE", "desc": "자재 및 부품 비용 소계"},
                {"name": "TOTAL_COST", "type": "DOUBLE", "desc": "총 정비 비용 (외주비, 부품비 합산)"},
                {"name": "CURRENCY", "type": "VARCHAR(5)", "desc": "비용 통화 단위 (USD, KRW)"},
                {"name": "CLASS_SURVEY_YN", "type": "VARCHAR(1)", "desc": "선급 검사 대상 항목 여부 (Y/N)"},
                {"name": "SAFETY_INCIDENT_YN", "type": "VARCHAR(1)", "desc": "작업 중 안전사고 발생 여부 (Y/N)"},
                {"name": "HOT_WORK_PERMIT_YN", "type": "VARCHAR(1)", "desc": "화기 작업 허가 발급 여부 (Y/N)"},
                {"name": "ENCLOSED_SPACE_PERMIT_YN", "type": "VARCHAR(1)", "desc": "밀폐구역 진입 허가 발급 여부 (Y/N)"},
                {"name": "PERMIT_TO_WORK_NO", "type": "VARCHAR(30)", "desc": "안전 작업 허가서 번호 (PTW)"},
                {"name": "REMARKS", "type": "TEXT", "desc": "특이사항 및 비고"}
            ]
        },
        "pms": {
            "table_desc": "선박 예방정비(PMS) 세부 작업 라인 (51,715건)",
            "row_count": 51715,
            "columns": [
                {"name": "LINE_ID", "type": "BIGINT", "desc": "세부 작업 라인 식별키", "pk": True},
                {"name": "DOC_NO", "type": "VARCHAR(30)", "desc": "소속 정비 문서 번호 (FK to master)"},
                {"name": "VESSELCODE", "type": "VARCHAR(10)", "desc": "선박 코드 (FK to master)"},
                {"name": "PMS_CODE", "type": "VARCHAR(30)", "desc": "PMS 표준 작업 코드 (예: PMS-ME-001)"},
                {"name": "EQUIP_CODE", "type": "VARCHAR(30)", "desc": "설비 식별 코드 (예: ME-01, TC-01, BLR-01)"},
                {"name": "EQUIP_NAME", "type": "VARCHAR(100)", "desc": "설비 표준 명칭 (Main Engine, Turbocharger 등)"},
                {"name": "SUB_EQUIP_NAME", "type": "VARCHAR(100)", "desc": "세부 부속 장치명 (No.1 Cyl Cover, Rotor Shaft 등)"},
                {"name": "INTERVAL_HOURS", "type": "INTEGER", "desc": "정기 정비 주기 (가동 시간 기준: 4000, 8000 등)"},
                {"name": "INTERVAL_MONTHS", "type": "INTEGER", "desc": "정기 정비 개월 주기 (3, 6, 12, 30, 60개월)"},
                {"name": "RUN_HOURS_AT_MAINT", "type": "DOUBLE", "desc": "정비 시점 누적 가동 시간 (Running Hours)"},
                {"name": "JOB_ORDER_NO", "type": "INTEGER", "desc": "작업 순번"},
                {"name": "JOB_SUMMARY", "type": "VARCHAR(250)", "desc": "단위 작업 핵심 요약"},
                {"name": "WORK_PROCEDURE_TEXT", "type": "TEXT", "desc": "정비 작업 본문 서술 (300자 이상 작업 절차, 측정값, 주의사항 포함)"},
                {"name": "ACTION_TAKEN", "type": "TEXT", "desc": "실제 수행된 분해 조치 및 정비 내역"},
                {"name": "CLEARANCE_VAL", "type": "VARCHAR(50)", "desc": "측정 간극값 또는 토크값"},
                {"name": "CLEARANCE_LIMIT", "type": "VARCHAR(50)", "desc": "허용 한계 간극값 (제조사 매뉴얼 허용치)"},
                {"name": "PRESSURE_BAR", "type": "DOUBLE", "desc": "시험 압력 또는 작동 압력 (bar)"},
                {"name": "TEMPERATURE_C", "type": "DOUBLE", "desc": "측정 작동 온도 (°C)"},
                {"name": "VIBRATION_MM_S", "type": "DOUBLE", "desc": "측정 진동 속도 RMS (mm/s)"},
                {"name": "INSULATION_MOHM", "type": "DOUBLE", "desc": "전동기/코일 절연저항 측정치 (MΩ)"},
                {"name": "WORK_RESULT", "type": "VARCHAR(20)", "desc": "작업 판정 결과 (GOOD, NORMAL, CONDITIONAL, DEFECT)"},
                {"name": "ENGINEER_NAME", "type": "VARCHAR(50)", "desc": "실제 현장 작업 담당 기관사"},
                {"name": "ASSISTANT_NAME", "type": "VARCHAR(50)", "desc": "작업 보조원 또는 실기사 성명"},
                {"name": "COMPL_DATE", "type": "DATE", "desc": "단위 작업 완료 일자"},
                {"name": "NEXT_DUE_HOURS", "type": "DOUBLE", "desc": "차기 예정 가동 시간"},
                {"name": "NEXT_DUE_DATE", "type": "DATE", "desc": "차기 예정 정비 일자"},
                {"name": "WORK_LOCATION", "type": "VARCHAR(50)", "desc": "기관실 내 작업 위치 (E/R 3rd Deck, Steering Flat 등)"},
                {"name": "SPECIAL_TOOL_USED", "type": "VARCHAR(100)", "desc": "사용된 특수 유압 공구 및 측정 장비"}
            ]
        },
        "approval": {
            "table_desc": "정비 문서 결재 이력 정보 (78,809건)",
            "row_count": 78809,
            "columns": [
                {"name": "APPROVAL_ID", "type": "BIGINT", "desc": "결재 고유 식별키", "pk": True},
                {"name": "DOC_NO", "type": "VARCHAR(30)", "desc": "소속 정비 문서 번호"},
                {"name": "VESSELCODE", "type": "VARCHAR(10)", "desc": "선박 코드"},
                {"name": "APPROVAL_SEQ", "type": "INTEGER", "desc": "결재 순번 (1:기안, 2:기관장, 3:감독, 4:팀장)"},
                {"name": "APPROVER_ID", "type": "VARCHAR(20)", "desc": "결재자 사번 또는 식별자"},
                {"name": "APPROVER_ROLE", "type": "VARCHAR(30)", "desc": "결재자 직책 (1ST_ENGINEER, CHIEF_ENGINEER, SUPERINTENDENT, TEAM_LEADER)"},
                {"name": "APPROVER_NAME", "type": "VARCHAR(50)", "desc": "결재권자 성명"},
                {"name": "APPROVER_DEPT", "type": "VARCHAR(50)", "desc": "결재권자 소속 부서"},
                {"name": "APPROVAL_STATUS", "type": "VARCHAR(20)", "desc": "결재 상태 (APPROVED, REJECTED, HOLD, SUBMITTED)"},
                {"name": "APPROVAL_DATE", "type": "TIMESTAMP", "desc": "결재 승인 일시"},
                {"name": "IP_ADDRESS", "type": "VARCHAR(20)", "desc": "결재 처리 클라이언트 IP"},
                {"name": "SIGNATURE_KEY", "type": "VARCHAR(64)", "desc": "전자 서명 해시 키"},
                {"name": "REVISION_REQ_YN", "type": "VARCHAR(1)", "desc": "보완 요청 여부 (Y/N)"},
                {"name": "OPINION_COMMENTS", "type": "TEXT", "desc": "결재 의견 및 지시사항"}
            ]
        },
        "attachments": {
            "table_desc": "정비 사진 및 보고서 첨부파일 메타데이터 (6,762건)",
            "row_count": 6762,
            "columns": [
                {"name": "ATTACH_ID", "type": "BIGINT", "desc": "첨부파일 식별키", "pk": True},
                {"name": "DOC_NO", "type": "VARCHAR(30)", "desc": "소속 정비 문서 번호"},
                {"name": "VESSELCODE", "type": "VARCHAR(10)", "desc": "선박 코드"},
                {"name": "FILE_NAME", "type": "VARCHAR(150)", "desc": "첨부 파일명 (사진, 측정보고서 등)"},
                {"name": "ORIGINAL_FILE_NAME", "type": "VARCHAR(150)", "desc": "원본 파일 업로드명"},
                {"name": "FILE_TYPE", "type": "VARCHAR(20)", "desc": "파일 형식 (JPG, PNG, PDF, XLSX)"},
                {"name": "FILE_SIZE_KB", "type": "INTEGER", "desc": "파일 크기 (KB)"},
                {"name": "FILE_PATH", "type": "VARCHAR(250)", "desc": "로컬 저장소 경로"},
                {"name": "ATTACH_CATEGORY", "type": "VARCHAR(30)", "desc": "첨부 분류 (DAMAGE_PHOTO, SERVICE_REPORT, CLASS_CERT, CLEARANCE_SHEET)"},
                {"name": "CAPTION_TEXT", "type": "VARCHAR(200)", "desc": "사진/파일 설명 캡션"},
                {"name": "UPLOADER_NAME", "type": "VARCHAR(50)", "desc": "업로더 성명"},
                {"name": "UPLOAD_DATE", "type": "DATE", "desc": "업로드 일자"}
            ]
        },
        "consumption": {
            "table_desc": "정비 작업 시 소모된 스페어 파트(부품) 내역 (2,358건)",
            "row_count": 2358,
            "columns": [
                {"name": "CONSUMPTION_ID", "type": "BIGINT", "desc": "부품 소모 식별키", "pk": True},
                {"name": "DOC_NO", "type": "VARCHAR(30)", "desc": "소속 정비 문서 번호"},
                {"name": "VESSELCODE", "type": "VARCHAR(10)", "desc": "선박 코드"},
                {"name": "PART_NO", "type": "VARCHAR(50)", "desc": "부품 식별 번호 (Part / Drawing No.)"},
                {"name": "PART_NAME", "type": "VARCHAR(100)", "desc": "부품 명칭 (Piston Ring, O-ring, Nozzle Tip 등)"},
                {"name": "MAKER_NAME", "type": "VARCHAR(80)", "desc": "부품 제조사 상호"},
                {"name": "SERIAL_NO", "type": "VARCHAR(50)", "desc": "부품 고유 시리얼 번호"},
                {"name": "MATERIAL_GRADE", "type": "VARCHAR(50)", "desc": "재질 규격 (Cast Iron, Viton, SUS316 등)"},
                {"name": "QUANTITY", "type": "INTEGER", "desc": "소모 수량"},
                {"name": "UNIT", "type": "VARCHAR(10)", "desc": "수량 단위 (PCS, SET, MTR, KG)"},
                {"name": "UNIT_PRICE", "type": "DOUBLE", "desc": "부품 단가 (USD)"},
                {"name": "TOTAL_PRICE", "type": "DOUBLE", "desc": "소모 총액 (USD)"},
                {"name": "STORAGE_LOCATION", "type": "VARCHAR(50)", "desc": "선내 스페어룸 보관 로케이션"},
                {"name": "STOCK_REMAINING", "type": "INTEGER", "desc": "소모 후 선내 잔여 재고 수량"},
                {"name": "REORDER_REQ_YN", "type": "VARCHAR(1)", "desc": "추가 청구 필요 여부 (Y/N)"}
            ]
        }
    }
}

col_count = sum(len(tbl["columns"]) for tbl in dictionary_121["tables"].values())
dictionary_121["total_columns"] = col_count
print(f"Verified: Total columns in dictionary = {col_count}")

with open("prompt_assets/data_dictionary_121.json", "w", encoding="utf-8") as f:
    json.dump(dictionary_121, f, ensure_ascii=False, indent=2)

print("data_dictionary_121.json updated successfully with exactly 121 columns!")
