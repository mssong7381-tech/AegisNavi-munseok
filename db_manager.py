# -*- coding: utf-8 -*-
"""
db_manager.py
Manages DuckDB database initialization, schema creation, high-speed data population,
and read-only query execution.

Target counts matching the architecture specification:
- vessels: 6 rows
- master: 26,561 rows
- pms: 51,715 rows
- approval: 78,809 rows
- attachments: 6,762 rows
- consumption: 2,358 rows
- BM25 narrative records: 19,986 rows (stored in pms WORK_PROCEDURE_TEXT with length >= 300 chars)
"""

import os
import time
import random
import duckdb

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ship_maint.duckdb")

def get_connection(read_only=True):
    """Returns a DuckDB connection."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return duckdb.connect(DB_PATH, read_only=read_only)

def init_database(force_recreate=False):
    """Initializes the database schema and populates exact target rows."""
    if os.path.exists(DB_PATH) and not force_recreate:
        try:
            con = get_connection(read_only=True)
            cnt = con.execute("SELECT COUNT(*) FROM master").fetchone()[0]
            con.close()
            if cnt == 26561:
                print(f"[DB] Database already initialized with {cnt} master rows.")
                return
        except Exception as e:
            print(f"[DB] Need recreation due to: {e}")

    print("[DB] Initializing DuckDB database with architecture specifications...")
    t0 = time.time()
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except Exception:
            pass

    con = get_connection(read_only=False)

    # 1. Vessels Table (6 vessels)
    con.execute("""
    CREATE TABLE vessels (
        VESSELCODE VARCHAR(10) PRIMARY KEY,
        VESSEL_NAME VARCHAR(50) NOT NULL,
        VESSEL_NAME_EN VARCHAR(50) NOT NULL,
        VESSEL_TYPE VARCHAR(30) NOT NULL,
        IMO_NO VARCHAR(15),
        CALL_SIGN VARCHAR(10),
        FLAG VARCHAR(20),
        CLASS_SOCIETY VARCHAR(10),
        BUILT_YEAR INTEGER,
        SHIPYARD VARCHAR(50),
        DWT DOUBLE,
        GROSS_TONNAGE DOUBLE,
        MAIN_ENGINE_MODEL VARCHAR(50),
        MAIN_ENGINE_MCR_KW DOUBLE,
        MAIN_ENGINE_CYL_COUNT INTEGER,
        AUX_ENGINE_MODEL VARCHAR(50),
        AUX_ENGINE_COUNT INTEGER,
        SERVICE_SPEED_KTS DOUBLE,
        BOILER_MODEL VARCHAR(50),
        STATUS VARCHAR(15)
    );
    """)

    con.execute("""
    INSERT INTO vessels VALUES
    ('HB01', '한바다호', 'HANBADA', 'CONTAINER', '9812345', 'D7AB', 'KOREA', 'KR', 2021, '현대중공업', 152000.0, 140000.0, 'MAN B&W 11G95ME-C9.5', 68530.0, 11, 'HiMSEN 9H32/40', 4, 22.5, 'MIURA VWH-2500', 'IN_SERVICE'),
    ('AR02', '아라호', 'ARA', 'LNG CARRIER', '9823456', 'D7CD', 'KOREA', 'KR', 2022, '삼성중공업', 96000.0, 118000.0, 'WinGD X72DF', 34200.0, 6, 'MAN 8L51/60DF', 4, 19.5, 'KANGNAM MC-1500', 'IN_SERVICE'),
    ('BR03', '백령호', 'BAENGNYEONG', 'BULK CARRIER', '9798765', 'D7EF', 'PANAMA', 'KR', 2019, '한화오션', 181000.0, 95000.0, 'MAN B&W 6S70ME-C8.2', 19620.0, 6, 'Yanmar 6EY18AL', 3, 14.5, 'AALBORG MISSION OS', 'IN_SERVICE'),
    ('TR04', '탐라호', 'TAMRA', 'VLCC TANKER', '9845678', 'D7GH', 'MARSHALL ISLANDS', 'DNV', 2023, '현대삼호중공업', 319000.0, 162000.0, 'Hyundai-MAN 7G80ME-C9.2', 273000.0, 7, 'HiMSEN 6H21/32', 3, 15.0, 'ALFA LAVAL OLV', 'IN_SERVICE'),
    ('SJ05', '세종호', 'SEJONG', 'CONTAINER', '9867890', 'D7IJ', 'KOREA', 'KR', 2023, '삼성중공업', 235000.0, 228000.0, 'MAN B&W 12G95ME-C10.5', 75570.0, 12, 'HiMSEN 9H32/40', 5, 23.0, 'MIURA VWH-3000', 'IN_SERVICE'),
    ('JB06', '장보고호', 'JANGBOGO', 'LPG CARRIER', '9801122', 'D7KL', 'PANAMA', 'ABS', 2020, '현대미포조선', 54000.0, 48000.0, 'MAN B&W 6G60ME-C9.5', 16080.0, 6, 'Daihatsu 6DE-18', 3, 16.5, 'KANGNAM MC-1200', 'IN_SERVICE');
    """)

    # 2. Master Table (26,561 rows)
    con.execute("""
    CREATE TABLE master (
        DOC_NO VARCHAR(30),
        VESSELCODE VARCHAR(10),
        WORK_TITLE VARCHAR(200),
        WORK_DESC TEXT,
        DOC_STATUS VARCHAR(20),
        REG_DATE DATE,
        START_DATE DATE,
        FINISH_DATE DATE,
        DEPT_CODE VARCHAR(20),
        DEPT_NAME VARCHAR(50),
        CHIEF_ENG VARCHAR(50),
        FIRST_ENG VARCHAR(50),
        SECOND_ENG VARCHAR(50),
        THIRD_ENG VARCHAR(50),
        SUPERINTENDENT VARCHAR(50),
        WORK_CATEGORY VARCHAR(30),
        URGENCY_LEVEL VARCHAR(20),
        PORT_NAME VARCHAR(50),
        BERTH_NO VARCHAR(20),
        CONTRACTOR_NAME VARCHAR(100),
        CONTRACTOR_MANPOWER INTEGER,
        TOTAL_MAN_HOURS DOUBLE,
        LABOR_COST DOUBLE,
        PARTS_COST DOUBLE,
        TOTAL_COST DOUBLE,
        CURRENCY VARCHAR(5),
        CLASS_SURVEY_YN VARCHAR(1),
        SAFETY_INCIDENT_YN VARCHAR(1),
        HOT_WORK_PERMIT_YN VARCHAR(1),
        ENCLOSED_SPACE_PERMIT_YN VARCHAR(1),
        PERMIT_TO_WORK_NO VARCHAR(30),
        REMARKS TEXT,
        PRIMARY KEY (VESSELCODE, DOC_NO)
    );
    """)

    # Generate 26,561 master records using set-based SQL generation
    print("[DB] Generating master table (26,561 rows)...")
    con.execute("""
    INSERT INTO master
    WITH seq AS (SELECT range AS i FROM range(26561))
    SELECT
        concat('DOC-MAINT-', strftime(DATE '2020-01-01' + INTERVAL (i % 2100) DAY, '%Y%m%d'), '-', lpad(CAST(i AS VARCHAR), 6, '0')) AS DOC_NO,
        CASE (i % 6)
            WHEN 0 THEN 'HB01'
            WHEN 1 THEN 'AR02'
            WHEN 2 THEN 'BR03'
            WHEN 3 THEN 'TR04'
            WHEN 4 THEN 'SJ05'
            ELSE 'JB06'
        END AS VESSELCODE,
        CASE (i % 12)
            WHEN 0 THEN '주기관 No.' || ((i % 11) + 1) || ' 실린더 커버 및 배기밸브 정기 분해 정비'
            WHEN 1 THEN '과급기(T/C) 로터 샤프트 세정 및 베어링 간극 점검'
            WHEN 2 THEN '발전기 엔진 No.' || ((i % 3) + 1) || ' 4,000시간 주기 흡배기 밸브 개방 검사'
            WHEN 3 THEN '연료유 청정기(F.O. Purifier) 볼(Bowl) 분해 및 디스크 스택 화학 세정'
            WHEN 4 THEN '보조 보일러 버너 점화 노즐 교체 및 스팀 안전밸브 작동 시험'
            WHEN 5 THEN '조타기(Steering Gear) 유압 램 및 밸브 블록 누설 정밀 점검'
            WHEN 6 THEN '조수기(Fresh Water Generator) 플레이트 증발기 디스케일링 및 가스켓 교환'
            WHEN 7 THEN '15ppm 빌지 유수분리기(OWS) OCM 센서 교정 및 3방향 밸브 작동 시험'
            WHEN 8 THEN '주 공기압축기 No.' || ((i % 2) + 1) || ' 고압 밸브 소탕 및 오일 스트레이너 세정'
            WHEN 9 THEN '평형수 처리장치(BWTS) 필터 백 역세척 및 UV 램프 모듈 점검'
            WHEN 10 THEN '선용 냉동기 컴프레서 샤프트 실 교체 및 R404A 냉매 보충'
            ELSE '기관실 해수 냉각 펌프 임펠러 마모 점검 및 메카니컬 실 신품 교환'
        END AS WORK_TITLE,
        '선박 정기 예방정비 지침 및 제조사 매뉴얼에 따른 계획 정비 및 성능 복구 조치 건' AS WORK_DESC,
        CASE
            WHEN (i % 35 = 0) THEN 'CANCEL'
            WHEN (i % 15 = 0) THEN 'IN_PROGRESS'
            WHEN (i % 10 = 0) THEN 'APPROVED'
            ELSE 'COMPLETED'
        END AS DOC_STATUS,
        DATE '2020-01-01' + INTERVAL (i % 2100) DAY AS REG_DATE,
        DATE '2020-01-01' + INTERVAL (i % 2100) DAY AS START_DATE,
        DATE '2020-01-01' + INTERVAL ((i % 2100) + (i % 4) + 1) DAY AS FINISH_DATE,
        CASE WHEN (i % 8 = 0) THEN 'DECK' ELSE 'ENG' END AS DEPT_CODE,
        CASE WHEN (i % 8 = 0) THEN '갑판부' ELSE '기관부' END AS DEPT_NAME,
        CASE (i % 5)
            WHEN 0 THEN '김철수 기관장'
            WHEN 1 THEN '이영호 기관장'
            WHEN 2 THEN '박민준 기관장'
            WHEN 3 THEN '정승원 기관장'
            ELSE '최현우 기관장'
        END AS CHIEF_ENG,
        '오동훈 1기사' AS FIRST_ENG,
        '강지원 2기사' AS SECOND_ENG,
        '윤서준 3기사' AS THIRD_ENG,
        CASE (i % 4)
            WHEN 0 THEN '황보건 감독'
            WHEN 1 THEN '송재혁 감독'
            WHEN 2 THEN '임동규 감독'
            ELSE '문선우 감독'
        END AS SUPERINTENDENT,
        CASE (i % 7)
            WHEN 0 THEN 'BREAKDOWN'
            WHEN 1 THEN 'CLASS_SURVEY'
            WHEN 2 THEN 'DRYDOCK'
            ELSE 'PMS_ROUTINE'
        END AS WORK_CATEGORY,
        CASE
            WHEN (i % 40 = 0) THEN 'EMERGENCY'
            WHEN (i % 10 = 0) THEN 'HIGH'
            WHEN (i % 4 = 0) THEN 'LOW'
            ELSE 'NORMAL'
        END AS URGENCY_LEVEL,
        CASE (i % 6)
            WHEN 0 THEN '부산항 신항'
            WHEN 1 THEN '싱가포르항'
            WHEN 2 THEN '로테르담항'
            WHEN 3 THEN '상하이 양산항'
            WHEN 4 THEN '울산 온산항'
            ELSE '태평양 외해'
        END AS PORT_NAME,
        'Berth #' || ((i % 12) + 1) AS BERTH_NO,
        CASE WHEN (i % 3 = 0) THEN '현대글로벌서비스' WHEN (i % 3 = 1) THEN '만엔진서비스' ELSE '선내 자체 정비' END AS CONTRACTOR_NAME,
        (i % 5) + 2 AS CONTRACTOR_MANPOWER,
        ROUND((i % 50) * 1.5 + 8.0, 1) AS TOTAL_MAN_HOURS,
        ROUND(((i % 150) * 80.0 + 350.0), 2) AS LABOR_COST,
        ROUND(((i % 300) * 120.0 + 600.0), 2) AS PARTS_COST,
        ROUND(((i % 150) * 80.0 + 350.0) + ((i % 300) * 120.0 + 600.0), 2) AS TOTAL_COST,
        'USD' AS CURRENCY,
        CASE WHEN (i % 10 = 0) THEN 'Y' ELSE 'N' END AS CLASS_SURVEY_YN,
        'N' AS SAFETY_INCIDENT_YN,
        CASE WHEN (i % 12 = 0) THEN 'Y' ELSE 'N' END AS HOT_WORK_PERMIT_YN,
        CASE WHEN (i % 8 = 0) THEN 'Y' ELSE 'N' END AS ENCLOSED_SPACE_PERMIT_YN,
        'PTW-2024-' || lpad(CAST(i AS VARCHAR), 5, '0') AS PERMIT_TO_WORK_NO,
        '작업 완료 후 정상 기밀 시험 및 시운전 완료 상태 양호' AS REMARKS
    FROM seq;
    """)

    # 3. PMS Table (51,715 rows, including 19,986 narrative records >= 300 chars)
    con.execute("""
    CREATE TABLE pms (
        LINE_ID BIGINT PRIMARY KEY,
        DOC_NO VARCHAR(30),
        VESSELCODE VARCHAR(10),
        PMS_CODE VARCHAR(30),
        EQUIP_CODE VARCHAR(30),
        EQUIP_NAME VARCHAR(100),
        SUB_EQUIP_NAME VARCHAR(100),
        INTERVAL_HOURS INTEGER,
        INTERVAL_MONTHS INTEGER,
        RUN_HOURS_AT_MAINT DOUBLE,
        JOB_ORDER_NO INTEGER,
        JOB_SUMMARY VARCHAR(250),
        WORK_PROCEDURE_TEXT TEXT,
        ACTION_TAKEN TEXT,
        CLEARANCE_VAL VARCHAR(50),
        CLEARANCE_LIMIT VARCHAR(50),
        PRESSURE_BAR DOUBLE,
        TEMPERATURE_C DOUBLE,
        VIBRATION_MM_S DOUBLE,
        INSULATION_MOHM DOUBLE,
        WORK_RESULT VARCHAR(20),
        ENGINEER_NAME VARCHAR(50),
        ASSISTANT_NAME VARCHAR(50),
        COMPL_DATE DATE,
        NEXT_DUE_HOURS DOUBLE,
        NEXT_DUE_DATE DATE,
        WORK_LOCATION VARCHAR(50),
        SPECIAL_TOOL_USED VARCHAR(100)
    );
    """)

    print("[DB] Generating pms table (51,715 rows, 19,986 narrative records >= 300 chars)...")
    # We will build pms rows using SQL and embed rich maritime technical procedures for 19,986 records
    con.execute("""
    INSERT INTO pms
    WITH seq AS (SELECT range AS i FROM range(51715)),
    base_master AS (
        SELECT DOC_NO, VESSELCODE, REG_DATE, i AS master_idx
        FROM master, (SELECT 0 AS dummy)
        WHERE (i % 26561) = (SELECT (seq.i % 26561) FROM seq WHERE seq.i = seq.i LIMIT 1)
    )
    SELECT
        seq.i AS LINE_ID,
        m.DOC_NO,
        m.VESSELCODE,
        'PMS-ME-' || lpad(CAST((seq.i % 850) AS VARCHAR), 4, '0') AS PMS_CODE,
        CASE (seq.i % 12)
            WHEN 0 THEN 'ME-01'
            WHEN 1 THEN 'TC-01'
            WHEN 2 THEN 'GE-01'
            WHEN 3 THEN 'FO-PUR-01'
            WHEN 4 THEN 'BLR-01'
            WHEN 5 THEN 'STG-01'
            WHEN 6 THEN 'FWG-01'
            WHEN 7 THEN 'OWS-01'
            WHEN 8 THEN 'AC-01'
            WHEN 9 THEN 'BWTS-01'
            WHEN 10 THEN 'REF-01'
            ELSE 'PMP-SW'
        END AS EQUIP_CODE,
        CASE (seq.i % 12)
            WHEN 0 THEN 'Main Engine (주기관)'
            WHEN 1 THEN 'Turbocharger (과급기)'
            WHEN 2 THEN 'Generator Engine (발전기)'
            WHEN 3 THEN 'Fuel Oil Purifier (연료유 청정기)'
            WHEN 4 THEN 'Auxiliary Boiler (보조 보일러)'
            WHEN 5 THEN 'Steering Gear (조타기)'
            WHEN 6 THEN 'Fresh Water Generator (조수기)'
            WHEN 7 THEN 'Oily Water Separator (유수분리기)'
            WHEN 8 THEN 'Main Air Compressor (주 공기압축기)'
            WHEN 9 THEN 'Ballast Water Treatment (평형수 처리장치)'
            WHEN 10 THEN 'Provision Refrigerator (선용 냉동기)'
            ELSE 'Sea Water Cooling Pump (해수 냉각 펌프)'
        END AS EQUIP_NAME,
        CASE (seq.i % 12)
            WHEN 0 THEN 'No.' || ((seq.i % 11) + 1) || ' Cylinder Cover & Exhaust Valve'
            WHEN 1 THEN 'Rotor Shaft & Turbine Blading'
            WHEN 2 THEN 'No.' || ((seq.i % 3) + 1) || ' D/G Inlet/Exhaust Valve & Injector'
            WHEN 3 THEN 'Centrifugal Bowl & Disc Stack'
            WHEN 4 THEN 'Burner Assembly & Safety Relief Valve'
            WHEN 5 THEN 'Hydraulic Ram & Solenoid Control Block'
            WHEN 6 THEN 'Titanium Plate Evaporator & Ejector'
            WHEN 7 THEN 'Coalescer Stage & 15ppm Bilge Alarm OCM'
            WHEN 8 THEN 'High/Low Pressure Valve & Oil Strainer'
            WHEN 9 THEN 'Electrolysis Cell & Neutralization Pump'
            WHEN 10 THEN 'Compressor Head & Shaft Mechanical Seal'
            ELSE 'Bronze Impeller & Mechanical Seal Ring'
        END AS SUB_EQUIP_NAME,
        CASE (seq.i % 5) WHEN 0 THEN 2000 WHEN 1 THEN 4000 WHEN 2 THEN 8000 WHEN 3 THEN 12000 ELSE 16000 END AS INTERVAL_HOURS,
        CASE (seq.i % 4) WHEN 0 THEN 6 WHEN 1 THEN 12 WHEN 2 THEN 30 ELSE 60 END AS INTERVAL_MONTHS,
        ROUND((seq.i * 1.7) % 45000 + 1200.0, 1) AS RUN_HOURS_AT_MAINT,
        (seq.i % 4) + 1 AS JOB_ORDER_NO,
        '정밀 점검 분해 정비 및 기준 간극 측정 조치' AS JOB_SUMMARY,
        CASE
            -- First 19,986 records get rich, detailed procedure texts (> 300 Korean characters)
            WHEN seq.i < 19986 THEN
                CASE (seq.i % 8)
                    WHEN 0 THEN
                        '[작업 절차 및 조치 내역] 1단계: 주기관 정지 후 시동공기 밸브를 차단하고 인디케이터 밸브를 개방하여 잔류 압력을 완전히 벤트하였다. 터닝 기어를 체결하고 크랭크케이스 통풍을 30분간 실시함. 2단계: 유압 잭(Hydraulic Jack)을 사용하여 실린더 커버 스터드 볼트를 1,450 bar 규정 압력으로 신장시킨 후 너트를 이완하고 호이스트 크레인으로 커버를 안전하게 인발하였다. 3단계: 배기밸브 하우징을 분해하여 밸브 스핀들 시트면의 블로바이(Blow-by) 및 카본 퇴적을 점검함. 4단계: 밸브 시트면 연마(Lapping) 작업을 실시하고 밸브 가이드 간극을 필러 게이지로 측정한 결과 0.38mm(허용치 0.45mm 이내)로 양호함. 5단계: 신품 O-Ring 및 가스켓 세트를 도유하여 장착하고 규정 유압 토크로 대각선 균등 체결 완료함. 6단계: 냉각수 통수 후 수압 7 bar에서 누설 없음을 확인하고 인디케이터 콕 블로업 후 정상 시운전 완료.'
                    WHEN 1 THEN
                        '[작업 절차 및 조치 내역] 1단계: Keep engine load between 50% and 85% for compressor side cleaning. 압축기 측 세척 시 엔진 부하를 50%에서 85% 사이로 유지하십시오. Engine load was kept between 50% and 85% for compressor side cleaning. 2단계: Reduce engine load below 40% before turbine side cleaning. 터빈 측 세척 전 엔진 부하를 40% 미만으로 낮추십시오. Engine load was reduced below 40% before injection for turbine side cleaning. 3단계: Monitor turbine inlet temperature and keep it under 430 degC. 터빈 입구 온도를 모니터링하고 430 degC 미만으로 유지하십시오. Turbine inlet temperature was monitored throughout and kept under 430 degC.'
                    WHEN 2 THEN
                        '[작업 절차 및 조치 내역] 1단계: 발전기 No.' || ((seq.i % 3) + 1) || ' D/G를 정지하고 주배전반(MSBD) 발전기 ACB 차단기를 인출(Draw-out) 후 오작동 방지 안전 태그(Lock-out/Tag-out)를 부착함. 2단계: 실린더 헤드 록커암 어셈블리를 탈거하고 흡/배기 밸브 브릿지 및 푸시로드를 점검함. 3단계: 흡기 및 배기 밸브 간극(Tappet Clearance)을 냉간 상태에서 마이크로미터로 계측하여 흡기 0.40mm, 배기 0.60mm 표준치로 재조정함. 4단계: 연료 분사 밸브(Injector)를 발출하여 분사시험기에서 분사 개시 압력 320 bar 도달 및 분무 상태(Spray Pattern)의 양호함을 확인함. 5단계: 거버너 링크 장치에 그리스를 주입하고 유압 오일을 신품으로 교체함. 6단계: 엔진 시동 후 무부하 60Hz 450V 확인 및 50%, 80% 부하 투입 시험에서 헌팅 없이 주파수 변동 0.5Hz 이내로 완벽히 정비됨.'
                    WHEN 3 THEN
                        '[작업 절차 및 조치 내역] 1단계: 연료유 청정기(F.O. Purifier) 전원을 차단하고 관성 회전이 완전히 정지(약 15분 소요)될 때까지 대기 후 브레이크를 체결함. 2단계: 볼 후드를 개방하고 특수 인발 지그를 장착하여 볼 본체와 120장의 스테인리스 디스크 스택을 분리함. 3단계: 디스크 표면에 부착된 아스팔텐 및 슬러지를 고온 세정조(Chemical Cleaning Tank)에서 초음파 세척함. 4단계: 작동수(Operating Water) 공급 밸브 및 드레인 노즐의 이물질을 소탕하고 디스트리뷰터 챔버를 청소함. 5단계: 나이론제 주 실링 링(Main Sealing Ring) 및 페어링 챔버 O-Ring 전량을 신품 키트로 교환함. 6단계: 역순 조립 후 규정 토크 체결을 확인하고 물 시운전(Water Trial) 실시. 자동 슬러지 배출(Sludge Discharge) 작동 시 압력 드롭 및 복귀가 지극히 정상임을 확인 완료.'
                    WHEN 4 THEN
                        '[작업 절차 및 조치 내역] 1단계: 보조 보일러 화염을 소화하고 스팀 밸브를 차단하여 드럼 압력을 0 bar까지 감압 냉각함. 2단계: 버너 힌지 도어를 개방하여 화염 감지기(Flame Eye) 광전관과 점화 플러그의 카본을 제거하고 점극 간극을 3.0mm로 보정함. 3단계: 연료 분사 분무 노즐 팁(Atomizer Tip)을 신품으로 교체하고 오리피스 오염을 현미경 점검함. 4단계: 보일러 수면계(Gauge Glass) 상하 밸브를 블로우다운(Blow-down) 세정하여 수위 지침의 정상 반응을 확인. 5단계: 보일러 안전밸브(Safety Valve)를 수동 테스터로 들어올려 18.5 bar에서 정상 작동함을 실측 검증함. 6단계: 점화 테스트를 수행하여 무연소 경보(Flame Failure) 인터록 정상 작동 및 자동 착화 완료 후 연소가스 분석기 O2 농도 3.2%의 우수한 연소 상태를 기록함.'
                    WHEN 5 THEN
                        '[작업 절차 및 조치 내역] 1단계: 조타기(Steering Gear) 파워 유닛 1호기를 기동하여 타각을 좌현 35도에서 우현 35도까지 전타(Hard Over)하면서 램(Ram) 표면의 흠집 및 패킹 누유를 확인. 2단계: 오토파일럿 및 휠 조타 신호 수신 상태를 점검하고 유압 솔레노이드 비례제어 밸브의 응답성을 오실로스코프로 실측함. 3단계: 유압 작동유 리턴 필터 엘리먼트를 분해하여 금속 마모 입자 유무를 자석으로 확인(특이사항 없음). 4단계: 틸러 핀 및 베어링 마모 틈새를 피러 게이지로 측정한 결과 0.15mm(규정 한도 0.35mm)로 양호함. 5단계: 비상 조타실에서 비상 수동 전환 밸브를 조작하여 28초 이내 타각 복귀 규정(SOLAS 기준 28초 이내)을 충족(21.4초 기록)함을 선급 입회 하에 검증 완료함. 6단계: 유압 보충 탱크 오일 레벨 정상 확인 및 시스템 정상 복귀.'
                    WHEN 6 THEN
                        '[작업 절차 및 조치 내역] 1단계: 조수기(FWG) 재킷 냉각수 밸브 및 진공 파괴 밸브를 조작하여 대기압으로 복귀 후 해수 공급 펌프를 정지함. 2단계: 전면 티타늄 플레이트(Titanium Plate) 커버를 개방하고 총 48매의 전열판을 일련번호 순으로 안전하게 인출함. 3단계: 증발판 표면의 탄산칼슘(CaCO3) 및 염분 스케일을 구연산(Sulfamic Acid) 5% 희석액에 4시간 침적 세정함. 4단계: 노화된 EPDM 가스켓을 전량 탈거하고 접착면을 알코올로 소탕 후 신품 가스켓을 정밀 부착함. 5단계: 플레이트 팩을 가이드 바에 장착하고 타이드 로드(Tie-rod)를 규정 두께 A치수 342mm까지 대칭 균등 조임 완료. 6단계: 진공 펌프를 기동하여 -0.92 bar 고진공 형성을 확인하고 청수 생산량 일일 25톤, 염분 농도 3.2 ppm(경보 10 ppm 이하)의 고순도 청수 생산을 확인함.'
                    ELSE
                        '[작업 절차 및 조치 내역] 1단계: 15ppm 빌지 유수분리기(OWS) 흡입 밸브 및 배출 배관 차단 밸브를 잠그고 전원 차단기 스위치를 OFF함. 2단계: 1차 챔버의 오일 트랩 격벽 슬러지를 드레인 밸브로 배출하고 온수로 내부를 세척함. 3단계: 2차 챔버 내부의 코어레서(Coalescer) 필터 엘리먼트 4개를 발출하여 오일 오염도를 점검하고 신품 카트리지로 전량 교체 장착함. 4단계: 15ppm 오일 경보계(OCM) 센서 셀을 면봉과 세정액으로 투명하게 닦아내고 청수 제로 캘리브레이션(Zero Calibration)을 수행함. 5단계: 테스트 스위치를 작동시켜 15ppm 초과 시 배출 솔레노이드 밸브가 차단되고 빌지 홀딩 탱크로 회수되는 3방향 전환 밸브의 기계적 작동을 확인함. 6단계: 해양오염방지설비(MARPOL Annex I) 정기 검사 요건에 부합함을 기록부에 등재하고 정비 완료함.'
                END
            ELSE
                '[정기 점검 기록] 장비의 외관 상태 및 기밀성을 육안 검사하고 체결 볼트 토크 및 윤활 상태를 점검함. 이상 징후 없으며 규정 주기 PMS 점검표에 의거 정상 조치 완료.'
        END AS WORK_PROCEDURE_TEXT,
        '부품 분해 소탕, 간극 계측, 노후 소모품 교체 및 규정 압력 기밀 시험 실시' AS ACTION_TAKEN,
        '0.35 mm' AS CLEARANCE_VAL,
        '0.50 mm' AS CLEARANCE_LIMIT,
        ROUND((seq.i % 30) * 1.2 + 2.5, 1) AS PRESSURE_BAR,
        ROUND((seq.i % 45) * 1.5 + 45.0, 1) AS TEMPERATURE_C,
        ROUND((seq.i % 25) * 0.15 + 0.8, 2) AS VIBRATION_MM_S,
        ROUND((seq.i % 50) * 2.0 + 10.0, 1) AS INSULATION_MOHM,
        CASE WHEN (seq.i % 25 = 0) THEN 'CONDITIONAL' WHEN (seq.i % 50 = 0) THEN 'DEFECT' ELSE 'GOOD' END AS WORK_RESULT,
        '김영수 2기사' AS ENGINEER_NAME,
        '이진혁 3기사' AS ASSISTANT_NAME,
        (SELECT REG_DATE FROM master WHERE master.DOC_NO = ('DOC-MAINT-' || strftime(DATE '2020-01-01' + INTERVAL (seq.i % 2100) DAY, '%Y%m%d') || '-' || lpad(CAST(seq.i % 26561 AS VARCHAR), 6, '0')) LIMIT 1) AS COMPL_DATE,
        ROUND(((seq.i * 1.7) % 45000 + 1200.0) + 4000.0, 1) AS NEXT_DUE_HOURS,
        DATE '2025-06-30' AS NEXT_DUE_DATE,
        '기관실 3rd Deck' AS WORK_LOCATION,
        '유압 스터드 텐셔너(Hydraulic Tensioner), 토크 렌치' AS SPECIAL_TOOL_USED
    FROM seq
    JOIN (
        SELECT DOC_NO, VESSELCODE, REG_DATE, row_number() OVER () - 1 AS m_idx
        FROM master
    ) m ON (seq.i % 26561) = m.m_idx;
    """)

    # 4. Approval Table (78,809 rows)
    con.execute("""
    CREATE TABLE approval (
        APPROVAL_ID BIGINT PRIMARY KEY,
        DOC_NO VARCHAR(30),
        VESSELCODE VARCHAR(10),
        APPROVAL_SEQ INTEGER,
        APPROVER_ID VARCHAR(20),
        APPROVER_ROLE VARCHAR(30),
        APPROVER_NAME VARCHAR(50),
        APPROVER_DEPT VARCHAR(50),
        APPROVAL_STATUS VARCHAR(20),
        APPROVAL_DATE TIMESTAMP,
        IP_ADDRESS VARCHAR(20),
        SIGNATURE_KEY VARCHAR(64),
        REVISION_REQ_YN VARCHAR(1),
        OPINION_COMMENTS TEXT
    );
    """)

    print("[DB] Generating approval table (78,809 rows)...")
    con.execute("""
    INSERT INTO approval
    WITH seq AS (SELECT range AS i FROM range(78809)),
    m AS (
        SELECT DOC_NO, VESSELCODE, row_number() OVER () - 1 AS m_idx
        FROM master
    )
    SELECT
        seq.i AS APPROVAL_ID,
        m.DOC_NO,
        m.VESSELCODE,
        (seq.i % 3) + 1 AS APPROVAL_SEQ,
        'EMP-' || lpad(CAST((seq.i % 500) AS VARCHAR), 5, '0') AS APPROVER_ID,
        CASE (seq.i % 3)
            WHEN 0 THEN '1ST_ENGINEER'
            WHEN 1 THEN 'CHIEF_ENGINEER'
            ELSE 'SUPERINTENDENT'
        END AS APPROVER_ROLE,
        CASE (seq.i % 3)
            WHEN 0 THEN '오동훈 1기사'
            WHEN 1 THEN '김철수 기관장'
            ELSE '황보건 감독'
        END AS APPROVER_NAME,
        CASE (seq.i % 3)
            WHEN 2 THEN '본사 해사공무팀'
            ELSE '선박 기관부'
        END AS APPROVER_DEPT,
        CASE WHEN (seq.i % 45 = 0) THEN 'HOLD' WHEN (seq.i % 60 = 0) THEN 'REJECTED' ELSE 'APPROVED' END AS APPROVAL_STATUS,
        TIMESTAMP '2020-01-01 09:00:00' + INTERVAL (seq.i % 2100) DAY + INTERVAL ((seq.i % 10) * 2) HOUR AS APPROVAL_DATE,
        '192.168.1.' || ((seq.i % 200) + 10) AS IP_ADDRESS,
        md5(CAST(seq.i AS VARCHAR)) AS SIGNATURE_KEY,
        CASE WHEN (seq.i % 45 = 0) THEN 'Y' ELSE 'N' END AS REVISION_REQ_YN,
        '정비 작업 지침 및 선급 안전 기준에 적합하게 작업 완료됨을 확인하고 결재 승인함.' AS OPINION_COMMENTS
    FROM seq
    JOIN m ON (seq.i % 26561) = m.m_idx;
    """)

    # 5. Attachments Table (6,762 rows)
    con.execute("""
    CREATE TABLE attachments (
        ATTACH_ID BIGINT PRIMARY KEY,
        DOC_NO VARCHAR(30),
        VESSELCODE VARCHAR(10),
        FILE_NAME VARCHAR(150),
        ORIGINAL_FILE_NAME VARCHAR(150),
        FILE_TYPE VARCHAR(20),
        FILE_SIZE_KB INTEGER,
        FILE_PATH VARCHAR(250),
        ATTACH_CATEGORY VARCHAR(30),
        CAPTION_TEXT VARCHAR(200),
        UPLOADER_NAME VARCHAR(50),
        UPLOAD_DATE DATE
    );
    """)

    print("[DB] Generating attachments table (6,762 rows)...")
    con.execute("""
    INSERT INTO attachments
    WITH seq AS (SELECT range AS i FROM range(6762)),
    m AS (
        SELECT DOC_NO, VESSELCODE, REG_DATE, row_number() OVER () - 1 AS m_idx
        FROM master
    )
    SELECT
        seq.i AS ATTACH_ID,
        m.DOC_NO,
        m.VESSELCODE,
        'ATTACH_' || strftime(m.REG_DATE, '%Y%m%d') || '_' || lpad(CAST(seq.i AS VARCHAR), 5, '0') || '.JPG' AS FILE_NAME,
        'maint_report_photo_' || seq.i || '.jpg' AS ORIGINAL_FILE_NAME,
        'JPG' AS FILE_TYPE,
        (seq.i % 4500) + 450 AS FILE_SIZE_KB,
        '/data/maint_photos/' || m.VESSELCODE || '/' || strftime(m.REG_DATE, '%Y%m') || '/photo_' || seq.i || '.jpg' AS FILE_PATH,
        CASE (seq.i % 4)
            WHEN 0 THEN 'DAMAGE_PHOTO'
            WHEN 1 THEN 'SERVICE_REPORT'
            WHEN 2 THEN 'CLEARANCE_SHEET'
            ELSE 'CLASS_CERT'
        END AS ATTACH_CATEGORY,
        '정비 분해 전후 설비 부품 마모도 및 조립 상태 증빙 사진' AS CAPTION_TEXT,
        '오동훈 1기사' AS UPLOADER_NAME,
        m.REG_DATE AS UPLOAD_DATE
    FROM seq
    JOIN m ON (seq.i % 26561) = m.m_idx;
    """)

    # 6. Consumption Table (2,358 rows)
    con.execute("""
    CREATE TABLE consumption (
        CONSUMPTION_ID BIGINT PRIMARY KEY,
        DOC_NO VARCHAR(30),
        VESSELCODE VARCHAR(10),
        PART_NO VARCHAR(50),
        PART_NAME VARCHAR(100),
        MAKER_NAME VARCHAR(80),
        SERIAL_NO VARCHAR(50),
        MATERIAL_GRADE VARCHAR(50),
        QUANTITY INTEGER,
        UNIT VARCHAR(10),
        UNIT_PRICE DOUBLE,
        TOTAL_PRICE DOUBLE,
        STORAGE_LOCATION VARCHAR(50),
        STOCK_REMAINING INTEGER,
        REORDER_REQ_YN VARCHAR(1)
    );
    """)

    print("[DB] Generating consumption table (2,358 rows)...")
    con.execute("""
    INSERT INTO consumption
    WITH seq AS (SELECT range AS i FROM range(2358)),
    m AS (
        SELECT DOC_NO, VESSELCODE, row_number() OVER () - 1 AS m_idx
        FROM master
    )
    SELECT
        seq.i AS CONSUMPTION_ID,
        m.DOC_NO,
        m.VESSELCODE,
        CASE (seq.i % 10)
            WHEN 0 THEN 'PSTN-RNG-95'
            WHEN 1 THEN 'EXH-SPNDL-01'
            WHEN 2 THEN 'FIV-NOZZLE-04'
            WHEN 3 THEN 'PUR-BOWL-ORING-SET'
            WHEN 4 THEN 'TC-JOURNAL-BEARING'
            WHEN 5 THEN 'STG-RAM-PACKING'
            WHEN 6 THEN 'BLR-BURNER-TIP'
            WHEN 7 THEN 'FWG-TITAN-GASKET'
            WHEN 8 THEN 'AC-DISC-VALVE'
            ELSE 'OWS-COALESCER-CART'
        END AS PART_NO,
        CASE (seq.i % 10)
            WHEN 0 THEN 'Piston Ring Set (Top & Comp)'
            WHEN 1 THEN 'Exhaust Valve Spindle'
            WHEN 2 THEN 'Fuel Injection Nozzle Tip'
            WHEN 3 THEN 'Bowl O-Ring Service Kit'
            WHEN 4 THEN 'Turbocharger Journal Bushing'
            WHEN 5 THEN 'Steering Hydraulic Ram Seal Set'
            WHEN 6 THEN 'Boiler Burner Atomizer Nozzle'
            WHEN 7 THEN 'Titanium Plate EPDM Gasket'
            WHEN 8 THEN 'Compressor Suction/Discharge Valve'
            ELSE 'OWS Coalescer Filter Cartridge'
        END AS PART_NAME,
        CASE (seq.i % 4)
            WHEN 0 THEN 'MAN Energy Solutions'
            WHEN 1 THEN 'Alfa Laval'
            WHEN 2 THEN 'WinGD OEM Parts'
            ELSE 'Hyundai Heavy Industries'
        END AS MAKER_NAME,
        'SN-PART-' || lpad(CAST((seq.i * 7 + 101) AS VARCHAR), 7, '0') AS SERIAL_NO,
        CASE (seq.i % 4) WHEN 0 THEN 'Special Cast Iron' WHEN 1 THEN 'Nimonic 80A' WHEN 2 THEN 'EPDM/Viton' ELSE 'Bronze alloy' END AS MATERIAL_GRADE,
        (seq.i % 6) + 1 AS QUANTITY,
        CASE (seq.i % 3) WHEN 0 THEN 'SET' WHEN 1 THEN 'PCS' ELSE 'KIT' END AS UNIT,
        ROUND((seq.i % 50) * 35.0 + 120.0, 2) AS UNIT_PRICE,
        ROUND(((seq.i % 6) + 1) * ((seq.i % 50) * 35.0 + 120.0), 2) AS TOTAL_PRICE,
        'Spare Room Shelf #' || ((seq.i % 15) + 1) AS STORAGE_LOCATION,
        (seq.i % 8) + 2 AS STOCK_REMAINING,
        CASE WHEN (seq.i % 5 = 0) THEN 'Y' ELSE 'N' END AS REORDER_REQ_YN
    FROM seq
    JOIN m ON (seq.i % 26561) = m.m_idx;
    """)

    # Verify counts
    counts = {}
    for tbl in ["vessels", "master", "pms", "approval", "attachments", "consumption"]:
        c = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        counts[tbl] = c
    
    narrative_cnt = con.execute("SELECT COUNT(*) FROM pms WHERE length(WORK_PROCEDURE_TEXT) >= 300").fetchone()[0]
    counts["narrative_records_ge_300"] = narrative_cnt

    con.close()
    elapsed = time.time() - t0
    print(f"[DB] Initialized DuckDB database in {elapsed:.2f}s:")
    for tbl, cnt in counts.items():
        print(f"  - {tbl}: {cnt:,}")

def execute_readonly_sql(sql_query, max_rows=50):
    """
    Executes a read-only SQL query on the DuckDB database.
    Enforces read-only safety, limits row return, and returns columns & rows.
    """
    cleaned_sql = sql_query.strip().rstrip(";")
    upper_sql = cleaned_sql.upper()

    # Safety checks
    forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "PRAGMA", "ATTACH", "DETACH", "COPY"]
    for kw in forbidden:
        # Check as whole word
        tokens = upper_sql.split()
        if kw in tokens:
            raise PermissionError(f"안전 규칙 위반: '{kw}' 구문은 읽기 전용 환경에서 허용되지 않습니다.")

    # Limit to max_rows if not specified
    if "LIMIT" not in upper_sql:
        cleaned_sql += f" LIMIT {max_rows}"

    con = get_connection(read_only=True)
    try:
        t0 = time.time()
        cursor = con.execute(cleaned_sql)
        cols = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        elapsed_ms = (time.time() - t0) * 1000.0
        return {
            "success": True,
            "columns": cols,
            "rows": rows,
            "row_count": len(rows),
            "elapsed_ms": elapsed_ms,
            "sql": cleaned_sql
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "sql": cleaned_sql
        }
    finally:
        con.close()

if __name__ == "__main__":
    init_database(force_recreate=True)
