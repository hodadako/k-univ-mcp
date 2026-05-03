## Data Conventions

- 기본 export 경로는 `K_UNIV_MCP_OUTPUT_DIR`이며, 설정이 없으면 out을 사용한다.
- MCP를 통해 export를 실행하는 경우에도 출력물 기본 위치는 `out/`로 본다.
- 사용자가 자연어로 별도 경로를 지정하지 않았다면 MCP 경로에서도 `out/` 아래에 결과를 생성한다.
- export 명령은 기본적으로 csv, xlsx, json, jsonl을 생성한다.
- raw payload가 존재하면 raw/ 디렉터리를 함께 생성할 수 있다.

### 공통 원칙

- `src/k_univ_mcp/models.py`의 dataclass를 공통 계약으로 본다.
- 학교별 구현이 달라도 같은 의미의 데이터는 같은 필드에 넣는다.
- 확실하지 않은 정보는 억지로 공통 필드에 맞추지 말고 `raw`에 남긴다.
- 코드값과 표시명은 구분한다.
- 학교 원문 payload는 최대한 보존하고, 정규화 결과는 별도 필드에 담는다.
- 학교의 영어 이름은 약어를 쓰지 않는다.
  - `ssu` -> X `soongsil` -> O

### Campus

- `Campus.code`는 provider 내부에서 campus를 안정적으로 식별하는 값이다.
- `Campus.name`은 사용자에게 보여줄 대표 한글 이름이다.
- `Campus.english_name`은 학교 응답에 신뢰 가능한 영문 이름이 있을 때만 채운다.
- `Campus.raw`에는 campus를 구성한 원문 payload를 넣는다.
- 같은 학교에서 campus 구분이 사실상 하나뿐이어도, 이후 확장을 위해 code를 생략하지 않는다.

### University

- `University`는 campus 아래의 단과대/college 또는 그에 준하는 상위 학사 조직을 표현한다.
- `University.campus_code`는 반드시 상위 `Campus.code`와 연결되어야 한다.
- `University.code`는 해당 campus 범위 안에서 안정적인 식별자여야 한다.
- `University.name`은 사용자 노출 기준 대표 이름이다.
- 학교마다 "college", "division", "school" 같은 용어 차이가 있어도 공통 모델에서는 `University`에 매핑한다.
- `University.raw`에는 원문 조직 데이터 전체를 보존한다.

### Faculty

- `Faculty`는 강좌 조회의 실제 하위 조직 단위다.
- `Faculty.campus_code`와 `Faculty.university_code`는 반드시 상위 조직과 일관되어야 한다.
- `Faculty.code`는 course 조회 요청에 직접 사용하는 식별자를 우선한다.
- `Faculty.name`은 사용자에게 보여줄 대표 이름이다.
- 학교에 따라 학과, 전공, 프로그램, 학부전공처럼 표현이 달라도 공통 모델에서는 `Faculty`로 맞춘다.
- 단순 표시용 이름과 실제 조회용 코드가 다르면, 조회용 코드를 `code`에 넣고 다른 값은 `raw`에 남긴다.

### Course

- `Course`는 최종 export와 MCP 응답의 기준 모델이다.
- `provider`, `year`, `semester`, `campus_code`, `university_code`, `faculty_code`는 가능한 한 항상 채운다.
- `campus_name`, `university_name`, `faculty_name`은 각각 상위 조직의 사용자 노출 이름과 일치시킨다.
- `course_code`는 학교가 제공하는 공식 과목번호를 우선한다.
- `section`은 분반 값만 넣고, 과목번호와 합쳐진 문자열 전체를 중복 저장하지 않는다.
- `course_key`는 학교 내부 고유 키가 따로 있을 때만 사용한다.
- `title`은 대표 한글 과목명, `title_english`는 신뢰 가능한 영문명이 있을 때만 채운다.
- `lecture_time_raw`는 시간표 원문을 그대로 보존하는 필드다.
- `classroom`은 시간 정보와 분리 가능한 대표 강의실 문자열만 넣는다.
- `meeting_slots`는 구조화에 성공한 시간 정보만 담는다.
- `parse_warnings`는 부분 파싱, 애매한 패턴, 정보 손실 가능성을 기록한다.
- `raw`에는 해당 강좌 row 원문 전체를 최대한 보존한다.

### MeetingSlot

- `MeetingSlot`은 공통 시간표 구조화 결과의 최소 단위다.
- 현재 계약은 `day_code`, `day_name`, `period` 세 필드다.
- `day_name`은 사용자에게 보이는 요일 문자열이다.
- `day_code`는 parser 내부에서 일관되게 비교 가능한 값이어야 한다.
- provider마다 요일 표현이 달라도 최종 `day_code` 체계는 같은 provider 안에서 일관되어야 한다.
- `period`는 해당 학교가 실제로 사용하는 교시 또는 파서가 안정적으로 매핑한 순번만 넣는다.
- 원문이 시각 기반이라 교시 추정이 불확실하면 억지로 `MeetingSlot`을 만들지 않는다.
- 장소, 교수명, 온라인 여부 같은 정보는 `MeetingSlot`에 넣지 않는다.

### RawPayloadDump

- `RawPayloadDump`는 export 시 원문 응답을 파일로 보존하기 위한 모델이다.
- `provider`, `year`, `semester`, `campus_code`, `university_code`, `faculty_code`는 어떤 조회 범위의 raw인지 설명하는 메타데이터다.
- `payload`는 가공 전 학교 응답 row 목록을 넣는다.
- 정규화된 `Course.raw`와 `RawPayloadDump.payload`는 목적이 다르다.
- `Course.raw`는 개별 강좌 row 기준 원문 보존이다.
- `RawPayloadDump.payload`는 조회 단위 전체 응답 보존이다.

### raw 사용 규칙

- 공통 필드로 안전하게 올릴 수 있는 값만 정규화한다.
- 해석 기준이 아직 합의되지 않은 값은 삭제하지 말고 `raw`에 남긴다.
- 학교별 디버깅에 필요한 내부 키, 상태값, 추가 메타데이터는 `raw`에 보존한다.
- `raw`를 이유 없이 축소하거나 임의로 재구성하지 않는다.

### 학교별 구현 허용 범위

- 학교마다 응답 구조와 용어가 달라도 공통 모델의 의미는 바꾸지 않는다.
- 새 학교 구현 시 기존 학교의 필드 의미를 바꾸는 방식으로 맞추지 않는다.
- 특정 학교만 필요한 예외 필드는 공통 모델에 바로 추가하지 말고 먼저 `raw`로 보존한다.
- 공통 필드 추가가 필요하면 최소 두 곳 이상에서 반복되는지 확인한 뒤 문서와 모델을 함께 갱신한다.
