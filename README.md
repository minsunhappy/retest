# 설문조사 웹페이지 배포 가이드

## 파일 구조
```
retest/
├── index.html              # 첫 번째 페이지 (인터페이스 설명 + 참가자 정보 입력)
├── test.html               # 테스트 페이지 (인터페이스 경험 + 질문)
├── final.html              # 완료 페이지
├── config.js               # 인터페이스-데이터 매핑 설정
├── questions.md            # 질문 및 선지 (수정 가능)
├── preview/                # 인터페이스 미리보기 비디오
│   ├── C.MP4              # 인터페이스 A (ComVi)
│   ├── Y.MP4              # 인터페이스 B (YouTube)
│   ├── D.MP4              # 인터페이스 C (Danmaku)
│   ├── D1.MP4             # 인터페이스 D (Danmaku One)
│   └── Y1.MP4             # 인터페이스 E (YouTube One)
└── data_folders.json       # 데이터 폴더 목록 (자동 생성)
```

**데이터 폴더 구조** (config.js의 dataBasePath에 지정된 경로):
```
[dataBasePath]/
├── [폴더1]/
│   ├── comvi_ui_default.html
│   ├── youtube_ui.html
│   ├── youtube_ui_one.html
│   ├── danmaku_ui_default.html
│   └── danmaku_ui_one_default.html
├── [폴더2]/ (동일한 구조)
├── [폴더3]/ (동일한 구조)
├── [폴더4]/ (동일한 구조)
└── [폴더5]/ (동일한 구조)
└── README.md
```

## 설정 방법

### 1. 데이터 폴더 복사 (권장)
먼저 `setup_data.py` 스크립트를 실행하여 필요한 데이터를 retest 폴더로 복사하세요:
```bash
cd /source/minsunkim/comment/usertest/retest
python3 setup_data.py
```
이 스크립트는:
- config.js의 dataBasePath에 지정된 경로의 폴더들을 읽어옵니다
- retest/data/ 아래로 복사합니다
- 폴더 이름을 A, B, C, D, E로 변경합니다

### 2. 데이터 폴더 목록 생성
`get_data_folders.py` 스크립트를 실행하여 data 폴더 내의 하위 폴더 목록을 생성하세요:
```bash
cd /source/minsunkim/comment/usertest/retest
python3 get_data_folders.py
```
이 스크립트는 `data_folders.json` 파일을 생성합니다.

### 2. 데이터 폴더 경로 설정
`config.js` 파일에서 `dataBasePath`를 실제 데이터 폴더 위치로 수정하세요:
```javascript
dataBasePath: 'data',  // 예: '../data' 또는 절대 경로
```

### 3. 질문 수정
`questions.md` 파일을 열어 질문 텍스트와 척도 라벨을 수정할 수 있습니다.

## 배포 방법

### 방법 1: Python HTTP 서버 (로컬 테스트용)
```bash
cd /source/minsunkim/comment/usertest/retest
python3 -m http.server 8000
```
브라우저에서 `http://localhost:8000` 접속

### 방법 2: Node.js HTTP 서버
```bash
cd /source/minsunkim/comment/usertest/retest
npx http-server -p 8000
```

### 방법 3: 실제 웹 서버 배포
- Apache, Nginx 등의 웹 서버에 파일 업로드
- 또는 GitHub Pages, Netlify, Vercel 등 정적 호스팅 서비스 사용

## 동작 방식

1. **첫 번째 페이지 (index.html)**
   - 인터페이스 설명 및 참가자 정보 입력
   - 모든 필수 항목 입력 후 다음 페이지로 이동

2. **테스트 페이지 (test.html)**
   - 인터페이스-데이터 쌍을 랜덤하게 생성 (모든 인터페이스 경험, 데이터 중복 없음)
   - 각 인터페이스를 iframe으로 로드
   - 인터페이스 아래에 4가지 질문 표시 (1-7 척도)
   - 모든 질문에 답해야 다음으로 진행 가능
   - 총 5개의 인터페이스 테스트 진행

3. **완료 페이지 (final.html)**
   - 테스트 완료 메시지
   - 결과는 localStorage에 저장됨

## 데이터 수집

모든 결과는 브라우저의 localStorage에 저장됩니다:
- `participantData`: 참가자 정보
- `interfaceDataPairs`: 인터페이스-데이터 매핑
- `testResults`: 각 테스트 단계의 답변
- `finalResults`: 최종 결과 (모든 데이터 포함)

서버로 전송하려면 `final.html`의 JavaScript에 API 호출 코드를 추가하세요.

## 참고사항
- 모든 비디오 파일은 `preview/` 폴더에 있어야 합니다
- 모든 인터페이스 HTML 파일은 `config.js`에서 지정한 `dataBasePath` 바로 아래의 폴더들 안에 있어야 합니다
  - 예: `dataBasePath`가 `/path/to/data`라면, `/path/to/data/[폴더명]/` 아래에 HTML 파일들이 있어야 합니다
- 참가자 정보는 localStorage에 저장됩니다
- 모든 필수 항목을 입력해야만 다음 페이지로 진행 가능합니다
