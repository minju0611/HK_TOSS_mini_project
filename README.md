✅ README.md (최종 정리본)
markdown
코드 복사
# 🔍 충정로역 맛집 추천 챗봇

서울 충정로역 주변 맛집 정보를 기반으로, 사용자의 질문에 적절한 가게 정보를 제공하는 챗봇입니다.  
LangChain의 Function Calling 기능과 RAG(Retrieval-Augmented Generation)를 결합하여,  
정확한 정보와 실제 사용자 리뷰에 기반한 추천을 제공합니다.

---

## 📁 프로젝트 구조

``` 
HK_TOSS_MINI_PROJECT/ ├── chatbot/ # 챗봇 응답 로직, Function Calling 정의 │ ├── app.py # Gradio UI 및 실행 진입점 │ ├── main_chain.py # 메모리 + RAG 결합 응답 처리 │ ├── tools.py # Function Calling 툴 함수 및 schema 정의 │ ├── crawler/
│ └── kakao_crawling.py # 카카오맵 기반 크롤링 코드 (선택 실행) │ ├── data/ # 크롤링 또는 전처리 후 저장된 파일 │ ├── stores.csv │ ├── menus.csv │ ├── reviews.csv │ ├── reviews_final.csv # 전처리된 리뷰 │ └── store_info.json # 가게 정보 + 메뉴 통합 JSON │ ├── preprocessing/
│ ├── reviews_to_clean.py # 리뷰 전처리 모듈 │ └── stores_menus_to_json.py # JSON 변환 모듈 │ ├── vectordb/ │ ├── embed_reviews.py # 리뷰 임베딩 및 Chroma DB 생성 │ ├── load_retriever.py # retriever 로딩 함수 │ └── chroma_reviews/ # ChromaDB 실제 저장 디렉토리 │ ├── config.py # 경로 설정 모듈 ├── run_pipeline.py # 전체 파이프라인 실행 스크립트 ├── requirements.txt # 의존성 명시 ├── .env # 환경변수 파일 (API 키 등) └── README.md
```

---

## ⚙️ 설치 및 실행 방법

### 1. `.env` 파일 생성
```bash
OPENAI_API_KEY=sk-xxxxxx...
2. 의존 패키지 설치
bash
코드 복사
conda activate hktoss
pip install -r requirements.txt
3. 전체 파이프라인 실행
bash
코드 복사
python run_pipeline.py
⚠️ run_pipeline.py는 다음을 자동 실행합니다:

리뷰 전처리

JSON 통합

리뷰 임베딩 및 벡터DB 저장

Gradio 챗봇 실행

4. 챗봇만 단독 실행
bash
코드 복사
python chatbot/app.py
🧠 기능 요약
Function Calling 기반 정적 정보 제공

주소, 전화번호, 메뉴, 영업시간, 음식 종류, 편의시설, 해시태그 등

RAG 기반 리뷰 추천

BGE 임베딩 모델로 벡터화 후 유사도 기반 검색

Gradio UI

사용자 친화적 챗봇 인터페이스 제공

대화 기억 기능

이전 질문/응답 히스토리를 기억하여 맥락 반영

🧩 사용 기술 스택
기술	설명
Python	메인 언어
LangChain	LLM 연결 및 툴/체인 구성
OpenAI GPT-4o	LLM 기반 응답 생성
HuggingFace	BAAI/bge-m3 임베딩 모델 사용
ChromaDB	벡터 검색용 DB
Gradio	프론트엔드 챗봇 UI
dotenv	환경변수 관리
pandas/numpy	데이터 처리

📝 참고
run_pipeline.py를 통해 파이프라인 자동 실행 가능

.env 파일은 반드시 루트에 위치해야 합니다

store_info.json, reviews_final.csv, chroma_reviews/는 파이프라인이 자동 생성합니다


