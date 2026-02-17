# Requirements: Agentic Search — Math-Aware Vectorless RAG

**Defined:** 2026-02-17
**Core Value:** 수학 수식이 포함된 PDF 문서를 업로드하면 수식이 LaTeX 형식으로 정확하게 파싱되어, 검색 결과와 답변에서 수식이 올바르게 렌더링되어야 한다.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Validation

- [ ] **VAL-01**: 실제 수능 수학 PDF에서 텍스트 레이어의 수식 추출 품질을 검증한다
- [ ] **VAL-02**: pymupdf4llm으로 수식이 포함된 페이지를 파싱하여 수식 감지 가능 여부를 확인한다

### Ingestion

- [ ] **ING-01**: PDF 파싱 시 수학 수식을 감지하여 인라인 수식은 `$...$`, 블록 수식은 `$$...$$`로 감싼다
- [ ] **ING-02**: Claude LLM을 사용하여 유니코드 수학 기호를 표준 LaTeX 구문(\frac, \sqrt 등)으로 정규화한다
- [ ] **ING-03**: PageIndex 트리 빌딩 과정에서 LaTeX 구분자가 손실되지 않고 보존된다
- [ ] **ING-04**: 노드 요약, 키워드 추출 등 enrichment 단계에서 LaTeX 수식이 유지된다

### Retrieval

- [ ] **RET-01**: 검색/응답 LLM 프롬프트에서 LaTeX 수식을 그대로 보존하여 출력한다
- [ ] **RET-02**: LaTeX 백슬래시(\)가 JSON 직렬화/역직렬화에서 깨지지 않도록 처리한다
- [ ] **RET-03**: 수식 내용을 한국어 키워드로도 추출하여 Atlas Search에서 검색 가능하게 한다

### Frontend

- [ ] **FE-01**: 채팅 응답에서 LaTeX 수식이 KaTeX로 렌더링되어 표시된다
- [ ] **FE-02**: 문서 상세 페이지(노드/페이지 보기)에서 LaTeX 수식이 렌더링된다
- [ ] **FE-03**: SSE 스트리밍 응답 중에도 수식이 실시간으로 올바르게 렌더링된다

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Data Model

- **DM-01**: Page/Node 모델에 `has_math` 불리언 플래그 추가
- **DM-02**: 수식 표현식 목록을 Page 모델에 별도 필드로 저장

### Content Intelligence

- **CI-01**: 문제/풀이/정리 등 수학 콘텐츠 타입 분류
- **CI-02**: 수식 인식 기반 노드 청킹 (수식 중간에서 분할 방지)

### Resilience

- **RS-01**: 이미지 기반 수식 PDF에 대한 graceful degradation (경고 표시)

## Out of Scope

| Feature | Reason |
|---------|--------|
| 수식 OCR (이미지 기반 인식) | PROJECT.md에서 명시적으로 제외, 복잡도 높음 |
| 벡터 임베딩 기반 수식 검색 | Vectorless RAG 프로젝트 철학에 반함 |
| 수식 유사도 검색 | 구조적 수식 비교는 별도 프로젝트 수준의 복잡도 |
| 인터랙티브 수식 에디터 | 검색/조회 시스템이므로 편집 기능 불필요 |
| MathJax 사용 | KaTeX 대비 번들 크기 크고 React 19 호환성 문제 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| VAL-01 | Phase 1 — Validation and Foundation | Pending |
| VAL-02 | Phase 1 — Validation and Foundation | Pending |
| ING-01 | Phase 2 — Ingestion Pipeline | Pending |
| ING-02 | Phase 2 — Ingestion Pipeline | Pending |
| ING-03 | Phase 2 — Ingestion Pipeline | Pending |
| ING-04 | Phase 2 — Ingestion Pipeline | Pending |
| RET-01 | Phase 3 — Retrieval and API Layer | Pending |
| RET-02 | Phase 3 — Retrieval and API Layer | Pending |
| RET-03 | Phase 3 — Retrieval and API Layer | Pending |
| FE-01 | Phase 4 — Frontend Rendering | Pending |
| FE-02 | Phase 4 — Frontend Rendering | Pending |
| FE-03 | Phase 4 — Frontend Rendering | Pending |

**Coverage:**
- v1 requirements: 12 total
- Mapped to phases: 12
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-17*
*Last updated: 2026-02-17 after roadmap creation — traceability finalized*
