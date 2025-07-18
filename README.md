# SQL 쿼리 생성/실행 LLM Agent

## 개요

이 프로젝트는 시스템 ERD 파일을 기반으로 사용자 질의에 대해 SQL 쿼리를 생성하고 실행하는 LLM Agent입니다. 3개의 서로 다른 전략을 가진 sub-agent가 협력하여 다양한 SQL 쿼리를 생성하며, Human-in-the-loop 방식으로 사용자의 피드백을 받아 최적의 쿼리를 실행합니다.

## 목적

- ERD 구조를 이해하고 사용자의 자연어 질의를 정확한 SQL 쿼리로 변환
- 다양한 전략을 통해 기본적인 쿼리부터 최적화된 쿼리까지 생성
- 사용자 피드백을 통한 쿼리 검증 및 개선
- 시스템 구조 개선 제안을 통한 장기적인 성능 향상 지원

## 기능

### 1. 다중 Sub-Agent 시스템
- **Query Agent 1**: 기본적인 SQL 쿼리 생성
- **Query Agent 2**: 최적화된 SQL 쿼리 생성
- **Query Agent 3**: 고급 쿼리 생성 및 ERD 구조 개선사항 제안

### 2. Human-in-the-loop 프로세스
- 쿼리 실행 전 사용자의 피드백 요청
- 여러 버전의 쿼리를 출처(sub-agent)와 함께 사용자에게 제시
- 사용자 선택에 따른 쿼리 실행 또는 수정

### 3. 사용자 피드백 처리
- **쿼리 실행**: 사용자가 선택한 버전의 쿼리를 실행하여 DB 결과 출력
- **쿼리 수정**: 사용자 피드백을 바탕으로 쿼리 수정 (특정 sub-agent 지정 가능)
- **실행 취소**: 초기 상태로 돌아가서 새로운 질의 대기

### 4. 쿼리 실행 안정성
- 구문 오류 발생 시 자동 쿼리 수정 및 재실행
- 최종 성공한 쿼리와 응답 출력

### 5. 시스템 개선 제안
- ERD 구조의 비합리적인 부분 식별
- 구조 변경을 통한 성능 향상 방안 제안
- 현재 쿼리 생성에는 영향을 미치지 않는 독립적인 제안

## 실행 방법

### 1. 프로젝트 설치
```bash
git clone <repository-url>
cd mvp
pip install -r requirements.txt
```

### 2. 환경 설정
```bash
# OpenAI API 키 설정 (필수)
export OPENAI_API_KEY="your_openai_api_key_here"

# MySQL 설정 (선택사항)
export MYSQL_HOSTNAME="localhost"
export MYSQL_PORT="3306"
export MYSQL_DATABASE="test"
export MYSQL_USERNAME="user"
export MYSQL_PASSWORD="1234"
```

### 3. Streamlit 웹 애플리케이션 실행
```bash
streamlit run src/streamlit_app.py
```

## 사용 예시

### Streamlit 웹 애플리케이션
1. 브라우저에서 `http://localhost:8501` 접속
2. 자연어 질문 입력: "활성 상태인 봇의 이름을 조회해주세요"
3. 생성된 3개의 SQL 쿼리 옵션 중 선택
4. 쿼리 실행 결과 확인
5. 필요시 추가 피드백으로 쿼리 수정

### 주요 기능
- **대화 히스토리**: 이전 질문과 답변 기록 유지
- **실시간 상호작용**: 쿼리 제안 및 피드백 처리
- **세션 관리**: 새 대화 시작 및 상태 초기화
- **오류 처리**: 자동 오류 감지 및 사용자 친화적 메시지

## 프로젝트 구조

```
mvp/
├── src/
│   ├── SQL_Query_Agent.py      # 메인 SQL 쿼리 에이전트
│   ├── streamlit_app.py        # Streamlit 웹 애플리케이션
│   ├── config.py               # 설정 관리 모듈
│   └── utils.py                # 유틸리티 함수 모음
├── resource/
│   ├── ERD.md.example          # ERD 스키마 예시 파일
│   └── prompt/                 # 프롬프트 템플릿 파일
│       ├── basic_sql_agent.template
│       ├── optimized_sql_agent.template
│       └── advanced_sql_agent.template
├── requirements.txt            # 의존성 패키지 목록
└── README.md                  # 이 파일
```

### 주요 컴포넌트

#### SQL_Query_Agent.py
- **SQLQueryAgent**: 메인 에이전트 클래스
- **DatabaseManager**: 데이터베이스 연결 및 쿼리 실행
- **LLMManager**: LLM 모델 관리
- **QueryChainManager**: 쿼리 생성 체인 관리
- **WorkflowManager**: 워크플로우 노드 관리

#### streamlit_app.py
- **StreamlitApp**: 메인 애플리케이션 클래스
- **SessionStateManager**: 세션 상태 관리
- **UIManager**: UI 컴포넌트 관리
- **WorkflowController**: 워크플로우 제어

#### config.py
- **ConfigManager**: 통합 설정 관리
- **DatabaseConfig**: 데이터베이스 설정
- **LLMConfig**: LLM 모델 설정
- **ProjectConfig**: 프로젝트 경로 설정

#### utils.py
- **ErrorHandler**: 오류 처리 및 분류
- **LoggerManager**: 로깅 관리
- **Validator**: 입력 검증
- **SafeExecutor**: 안전한 실행 및 재시도
- **PerformanceMonitor**: 성능 모니터링

## 개발 및 확장

### 새로운 에이전트 추가
1. `WorkflowManager`에 새로운 에이전트 메서드 추가
2. `QueryChainManager`에 새로운 체인 생성
3. 워크플로우 그래프에 새로운 노드 추가

### 데이터베이스 지원 확장
1. `DatabaseManager`에 새로운 DB 어댑터 추가
2. `config.py`에 새로운 DB 설정 클래스 추가
3. 해당 DB용 프롬프트 템플릿 생성

### UI/UX 개선
1. `UIManager`에 새로운 UI 컴포넌트 추가
2. `SessionStateManager`에 새로운 상태 추가
3. CSS 스타일링 및 JavaScript 기능 추가

## 문제 해결

### 일반적인 문제
1. **OpenAI API 키 오류**: 환경 변수 `OPENAI_API_KEY`가 올바르게 설정되었는지 확인
2. **ERD 파일 읽기 오류**: `resource/ERD.md` 파일이 존재하고 읽기 권한이 있는지 확인
3. **MySQL 연결 오류**: 데이터베이스 설정 및 연결 상태 확인
4. **의존성 오류**: `pip install -r requirements.txt`로 모든 패키지 설치
