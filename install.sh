#!/bin/bash
# KStock Analyzer 설치 스크립트

echo "🚀 KStock Analyzer 설치 중..."

cd /home/programs/kstock_analyzer

# 가상환경 생성
echo "📦 가상환경 생성..."
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# 의존성 설치
echo "📦 의존성 설치..."
pip install --upgrade pip
pip install -r requirements.txt

# 실행 권한 설정
chmod +x kstock.sh
chmod +x kstock.py

# 심볼릭 링크 생성 (선택)
if [ -d "$HOME/.local/bin" ]; then
    ln -sf /home/programs/kstock_analyzer/kstock.sh "$HOME/.local/bin/kstock"
    echo "✅ kstock 명령어 등록 완료 (재로그인 필요)"
fi

echo "✅ 설치 완료!"
echo ""
echo "사용법:"
echo "  ./kstock.sh          # 대화형 모드"
echo "  ./kstock.sh 005930   # 삼성전자 분석"
echo ""
echo "또는:"
echo "  python3 kstock.py"
