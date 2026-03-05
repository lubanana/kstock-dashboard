# Telegram 연결 설정 가이드

## ✅ 설정 완료된 항목

### 1. Bot Token 설정
- Bot: @dddeokbot
- Token: `8714405922:AAEwXdtNQrIkPSrSDzqCDVOFynJXhl5wnJY`
- Status: ✅ 설정 완료

### 2. Gateway 설정
- Port: 18789
- Mode: local
- Status: ✅ 실행 중

## ⚠️ 주의사항

### DM(개인 메시지) 정상 작동
- 사용자가 먼저 봇에게 `/start`를 별내야 함
- 그 후 메시지 전송 가능

### 그룹 메시지 제한
- 현재 `groupPolicy: "allowlist"` 설정
- `groupAllowFrom`이 비어있어 모든 그룹 메시지 차단됨
- 그룹에서 사용하려면 설정 수정 필요

## 🔧 그룹 사용 설정 (선택사항)

`openclaw.json`에서 다음 수정:

```json
"telegram": {
  "enabled": true,
  "dmPolicy": "pairing",
  "botToken": "8714405922:AAEwXdtNQrIkPSrSDzqCDVOFynJXhl5wnJY",
  "groupPolicy": "open",
  "streaming": "partial"
}
```

또는 특정 그룹 ID 허용:

```json
"telegram": {
  "enabled": true,
  "dmPolicy": "pairing",
  "botToken": "8714405922:AAEwXdtNQrIkPSrSDzqCDVOFynJXhl5wnJY",
  "groupPolicy": "allowlist",
  "groupAllowFrom": ["-1001234567890"],
  "streaming": "partial"
}
```

## 📱 사용 방법

1. Telegram에서 @dddeokbot 검색
2. `/start` 버튼 클릭
3. 메시지 수신 가능

## 🧪 테스트 명령어

```bash
# 상태 확인
openclaw channels list

# 메시지 별내
openclaw message send --channel telegram --to <chat_id> "테스트 메시지"
```
