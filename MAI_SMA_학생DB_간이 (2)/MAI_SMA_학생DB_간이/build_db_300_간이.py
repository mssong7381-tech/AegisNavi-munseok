# -*- coding: utf-8 -*-
"""학생용 간이 DB — 비식별 전체 DB 에서 정비 문서 약 300건을 뽑는다.

  python build_db_300_간이.py [원본 duckdb 경로]

단위는 문서((VESSELCODE, DOC_NO)). 고른 문서에 딸린 pms·approval·attachments·
consumption 행을 함께 가져오므로 테이블 사이 연결이 끊기지 않는다. 어느 테이블도
1,000행을 넘지 않게 한다. 값은 원본(가명처리된 값)을 그대로 쓴다.

교육용 '함정'이 남도록 아래 문서를 먼저 넣고 나머지는 선박별로 고르게 무작위로 채운다.
  ① 같은 DOC_NO 가 두 척 이상에 있는 문서(조인 키는 선박+문서번호)
  ② 시스템 도입 때 일괄 입력된 인공 기준일 행이 든 문서(선박별 날짜 짝)
  ③ 부품 소모 기록이 있는 문서   ④ 발전기 정비와 '…GENERATOR' 가 붙은 다른 기기
  ⑤ 주기관 정비   ⑥ 중요 정비(CRITICAL_YN='Y')   ⑦ 첨부가 있는 문서
  ⑧ 시연용 서술(번호 붙은 절차문)이 든 문서
"""
import os
import random
import sys

import duckdb

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(HERE), 'kmou_maintenance_data', 'deid_kit', 'db', 'deid_maint.duckdb')
N_DOCS, MAX_ROWS, SEED = 300, 1000, 20261110
DST = os.path.join(HERE, 'deid_maint_300.duckdb')
TABLES = ['master', 'pms', 'approval', 'attachments', 'consumption']
# 규칙 3 의 인공 기준일(선박, 날짜) — 키트 프롬프트의 규칙문과 같은 값
ART = [('V05', '2024-02-01'), ('V04', '2024-06-03'), ('V06', '2024-07-01'),
       ('V01', '2024-04-30'), ('V02', '2024-10-04'), ('V03', '2025-01-10')]

rnd = random.Random(SEED)
src = duckdb.connect(SRC, read_only=True)
q = lambda s: src.sql(s).fetchall()

docs = q('SELECT VESSELCODE, DOC_NO FROM master')
vessels = sorted({v for v, _ in docs})
by_v = {v: sorted(d for vv, d in docs if vv == v) for v in vessels}


def pick(rows, n):
    rows = sorted(set(rows))
    rnd.shuffle(rows)
    return rows[:n]


pri = []
# ① 같은 DOC_NO 가 여러 척에 있는 경우 — 5개 번호의 문서 전부
shared = [d for (d,) in q('SELECT DOC_NO FROM master GROUP BY DOC_NO '
                          'HAVING count(DISTINCT VESSELCODE) >= 2 ORDER BY DOC_NO')]
for d in pick(shared, 5):
    pri += [(v, d) for v, dd in docs if dd == d]
# ② 인공 기준일 — 선박마다 2건
for v, day in ART:
    pri += pick(q(f"SELECT DISTINCT VESSELCODE, DOC_NO FROM pms WHERE VESSELCODE='{v}' "
                  f"AND CAST(LAST_WORK_DATE AS DATE)=DATE '{day}'"), 2)
# ③ 부품 소모 기록
pri += pick(q('SELECT DISTINCT VESSELCODE, DOC_NO FROM consumption'), 15)
# ④ 발전기와 이름에 GENERATOR 가 붙은 다른 기기
pri += pick(q("SELECT DISTINCT VESSELCODE, DOC_NO FROM pms "
              "WHERE MACH_DESC='GENERATOR ENGINE(DIESEL)'"), 15)
pri += pick(q("SELECT DISTINCT VESSELCODE, DOC_NO FROM pms WHERE MACH_DESC LIKE '%GENERATOR%' "
              "AND MACH_DESC<>'GENERATOR ENGINE(DIESEL)'"), 8)
# ⑤ 주기관  ⑥ 중요 정비  ⑦ 첨부
pri += pick(q("SELECT DISTINCT VESSELCODE, DOC_NO FROM pms WHERE MACH_DESC='MAIN ENGINE(DIESEL)'"), 15)
pri += pick(q("SELECT DISTINCT VESSELCODE, DOC_NO FROM pms WHERE CRITICAL_YN='Y'"), 15)
pri += pick(q('SELECT DISTINCT VESSELCODE, DOC_NO FROM attachments'), 10)
# ⑧ 시연용 서술 — 번호 붙은 절차문
pri += [tuple(r) for r in q("SELECT VESSELCODE, DOC_NO FROM master "
                            "WHERE WORK_REMARK LIKE '%1)%' AND WORK_REMARK LIKE '%2)%' "
                            "ORDER BY length(WORK_REMARK) DESC LIMIT 10")]

chosen = []
for x in pri:
    if x not in chosen:
        chosen.append(x)

# 행 수 상한을 지키며 채운다
cnt = {t: {} for t in TABLES}
for t in TABLES:
    for v, d, n in q(f'SELECT VESSELCODE, DOC_NO, count(*) FROM {t} GROUP BY 1, 2'):
        cnt[t][(v, d)] = n


def fits(sel):
    return all(sum(cnt[t].get(x, 0) for x in sel) <= MAX_ROWS for t in TABLES)


final = []
for x in chosen:
    if len(final) < N_DOCS and fits(final + [x]):
        final.append(x)
pools = {v: [x for x in pick([(v, d) for d in by_v[v]], len(by_v[v])) if x not in final]
         for v in vessels}
i = 0
while len(final) < N_DOCS and any(pools.values()):
    v = vessels[i % len(vessels)]
    i += 1
    if pools[v]:
        x = pools[v].pop()
        if fits(final + [x]):
            final.append(x)

# 새 DB
if os.path.exists(DST):
    os.remove(DST)
dst = duckdb.connect(DST)
dst.execute(f"ATTACH '{SRC}' AS s (READ_ONLY)")
dst.execute('CREATE TABLE _keep (VESSELCODE VARCHAR, DOC_NO VARCHAR)')
dst.executemany('INSERT INTO _keep VALUES (?, ?)', final)
for t in TABLES:
    dst.execute(f'CREATE TABLE {t} AS SELECT x.* FROM s.{t} x '
                f'JOIN _keep k ON x.VESSELCODE=k.VESSELCODE AND x.DOC_NO=k.DOC_NO')
dst.execute('CREATE TABLE vessels AS SELECT * FROM s.vessels')
# vessels 의 집계 열은 이 DB 기준으로 다시 센다
dst.execute("""
UPDATE vessels SET
  RECORDS = (SELECT count(*) FROM master m WHERE m.VESSELCODE=vessels.VESSELCODE),
  PMS_LINES = (SELECT count(*) FROM pms p WHERE p.VESSELCODE=vessels.VESSELCODE),
  CONS_LINES = (SELECT count(*) FROM consumption c WHERE c.VESSELCODE=vessels.VESSELCODE),
  ATTACHMENTS = (SELECT count(*) FROM attachments a WHERE a.VESSELCODE=vessels.VESSELCODE),
  WORK_DATE_FROM = (SELECT min(WORK_DATE) FROM master m WHERE m.VESSELCODE=vessels.VESSELCODE),
  WORK_DATE_TO = (SELECT max(WORK_DATE) FROM master m WHERE m.VESSELCODE=vessels.VESSELCODE)
""")
dst.execute('DROP TABLE _keep')
dst.execute('DETACH s')

# 엑셀·CSV
import pandas as pd
from openpyxl.utils import get_column_letter
xlsx = os.path.join(HERE, 'deid_maint_300.xlsx')
os.makedirs(os.path.join(HERE, 'csv'), exist_ok=True)
summary = []
with pd.ExcelWriter(xlsx, engine='openpyxl') as w:
    for t in TABLES + ['vessels']:
        df = dst.sql(f'SELECT * FROM {t}').df()
        df.to_csv(os.path.join(HERE, 'csv', f'{t}.csv'), index=False, encoding='utf-8-sig')
        df.to_excel(w, sheet_name=t, index=False)
        ws = w.sheets[t]
        ws.freeze_panes = 'A2'
        ws.auto_filter.ref = ws.dimensions
        for j, c in enumerate(df.columns, 1):
            ws.column_dimensions[get_column_letter(j)].width = min(45, max(10, len(str(c)) + 2))
        summary.append((t, len(df), len(df.columns)))
dst.close()

by_vessel = {}
for v, _ in final:
    by_vessel[v] = by_vessel.get(v, 0) + 1
print('문서', len(final), '건 · 선박별', dict(sorted(by_vessel.items())))
for t, n, c in summary:
    print(f'  {t:12s} {n:5d}행 {c:3d}열')
