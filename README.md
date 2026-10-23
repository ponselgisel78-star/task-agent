# Task Automation Agent

경량 ReAct (Reasoning + Acting) 아키텍처 기반의 자율 작업 자동화 및 질의응답 AI 에이전트입니다.

---

## 🌟 주요 특징

- **경량 Native ReAct Loop**: 무거운 블랙박스 프레임워크 없이 `Thought -> Action -> Observation` 순환 제어 구조를 투명하게 구현.
- **Pydantic v2 기반 스키마 검증**: 모든 도구 입력 파라미터의 타입 및 무결성 보장.
- **보안 가드레일 (Security Guardrails)**:
  - 시스템 파괴적 쉘 명령어(`rm -rf`, `format`, `Remove-Item.*Force`, `shutdown` 등) 사전 차단.
  - 작업 허용 루트 외부로의 Path Traversal(상위 경로 탈출) 차단.
  - AST 기반 안전한 수식 계산기(`CalculatorTool`) 제공.
- **이중 LLM 모드**:
  - `GeminiProvider`: Google Gemini 2.5 Flash 모델 연동.
  - `OfflineMockProvider`: API Key 없이도 즉시 테스트 가능한 오프라인 시뮬레이션 모드 지원.
- **Rich 터미널 UI**: 에이전트의 추론 및 도구 실행 과정을 시각적 패널로 제공.

---

## 📂 프로젝트 구조

```
task-agent/
├── task_agent/
│   ├── core/
│   │   ├── agent.py          # ReAct 루프 및 추론 컨트롤러
│   │   └── memory.py         # 윈도우 슬라이딩 기반 컨텍스트 메모리
│   ├── tools/
│   │   ├── base.py           # BaseTool 및 ToolRegistry
│   │   └── system.py         # Calculator, File, Command 도구
│   ├── security/
│   │   └── guardrails.py     # 파괴적 명령 및 경로 탈출 방지
│   └── llm/
│       └── provider.py       # Gemini 및 Offline Mock 제공자
├── tests/
│   ├── test_agent.py         # ReAct 루프 및 Mock LLM 검증
│   ├── test_guardrails.py    # 보안 정책 차단 검증
│   ├── test_memory.py        # 대화 히스토리 및 롤링 검증
│   └── test_tools.py         # 도구 스키마 및 실행 검증
├── cli.py                    # 인터랙티브 Rich CLI 인터페이스
├── requirements.txt          # 프로덕션 및 테스트 의존성
└── README.md
```

---

## 🚀 빠른 시작

### 1. 가상환경 활성화 및 패키지 설치
```bash
# 가상환경 활성화 (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# 의존성 설치
pip install -r requirements.txt
```

### 2. API Key 설정 (선택 사항)
Google Gemini API 키를 환경변수로 등록합니다 (미설정 시 자동으로 Offline Demo 모드로 실행됩니다):
```bash
$env:GEMINI_API_KEY="your-gemini-api-key"
```

### 3. CLI 실행
```bash
python cli.py
```

---

## 🧪 테스트 실행 (TDD 검증)

모든 단위 테스트를 실행합니다:
```bash
pytest tests/ -v
```

---

## 🔒 보안 정책

- 파일 읽기 및 쓰기 도구는 지정된 작업 루트(`allowed_root`)를 벗어날 수 없습니다.
- 허용되지 않은 쉘 명령어가 감지되면 `SecurityViolationError`를 발생시키며 즉시 실행이 거부됩니다.
