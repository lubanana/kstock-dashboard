# 크론 작업 설정 가이드

## 권장 크론 작업 목록

### 1. DART 공시정보 일일 업데이트
```bash
# 매일 18:00 실행 (장 마감 후)
openclaw cron create --name dart-daily \
  --schedule "0 18 * * *" \
  --command "cd /root/.openclaw/workspace/strg && python3 fast_dart_update.py --days 3" \
  --sessionTarget isolated
```

### 2. 가격 데이터 일일 업데이트
```bash
# 매일 16:00 실행 (장 마감 직후)
openclaw cron create --name price-daily \
  --schedule "0 16 * * *" \
  --command "cd /root/.openclaw/workspace/strg && python3 unified_data_builder.py --mode daily --days 3" \
  --sessionTarget isolated
```

### 3. 누락 데이터 백필 (주간)
```bash
# 매주 일요일 02:00 실행
openclaw cron create --name backfill-weekly \
  --schedule "0 2 * * 0" \
  --command "cd /root/.openclaw/workspace/strg && python3 unified_data_builder.py --mode backfill --days 7" \
  --sessionTarget isolated
```

### 4. 데이터 품질 검증 (일간)
```bash
# 매일 19:00 실행
openclaw cron create --name data-verify \
  --schedule "0 19 * * *" \
  --command "cd /root/.openclaw/workspace/strg && python3 unified_data_builder.py --mode verify" \
  --sessionTarget isolated
```

## 현재 상태
- **등록된 크론**: 0개
- **수동 실행 필요**: DART 공시 업데이트 (04-02~04-09)

## 수동 실행 명령
```bash
# DART 공시 업데이트
cd /root/.openclaw/workspace/strg
python3 fast_dart_update.py --days 10

# 가격 데이터 업데이트
python3 unified_data_builder.py --mode daily

# 데이터 품질 검증
python3 unified_data_builder.py --mode verify
```
