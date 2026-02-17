# Agentic Search — Math-Aware Vectorless RAG

## What This Is

수학 수식이 포함된 PDF 문서(수능/시험 문제지)를 업로드하고 AI로 검색/질의할 수 있는 Vectorless RAG 시스템. 외부 오픈소스 프로젝트를 클론하여 교육/연구 목적으로 커스터마이징 중이며, 핵심 확장은 수학 수식의 LaTeX 파싱과 렌더링 지원.

## Core Value

수학 수식이 포함된 PDF 문서를 업로드하면 수식이 LaTeX 형식으로 정확하게 파싱되어, 검색 결과와 답변에서 수식이 올바르게 렌더링되어야 한다.

## Requirements

### Validated

<!-- 기존 코드베이스에서 이미 구현된 기능 -->

- ✓ PDF/Markdown/텍스트 문서 업로드 — existing
- ✓ 계층적 PageIndex 트리 생성 (ToC 감지 → 트리 빌딩) — existing
- ✓ 노드 요약, 키워드 추출, 콘텐츠 분류 — existing
- ✓ Atlas Search (BM25) + LLM 트리 내비게이션 이중 검색 — existing
- ✓ LLM 추론 루프 (최대 5회 반복, 충분성 평가) — existing
- ✓ SSE 스트리밍 응답 — existing
- ✓ 멀티턴 세션 관리 — existing
- ✓ 문서 목록/상세/삭제 관리 — existing
- ✓ React/Next.js 프론트엔드 (문서, 채팅, 세션 페이지) — existing
- ✓ Docker Compose 배포 (Atlas Search 프로필 포함) — existing

### Active

<!-- 현재 구현 목표 -->

- [ ] PDF에서 수학 수식을 LaTeX 형식($...$, $$...$$)으로 파싱
- [ ] PageIndex 트리 노드에 수식이 LaTeX로 보존
- [ ] 검색 결과/답변에서 수식이 LaTeX 형식으로 반환
- [ ] 프론트엔드에서 LaTeX 수식 렌더링 (KaTeX/MathJax)

### Out of Scope

- 벡터 임베딩 기반 검색 — 프로젝트 핵심이 Vectorless RAG
- 사용자 인증/권한 관리 — 연구용 단일 사용자 환경
- 모바일 앱 — 웹 인터페이스로 충분
- 수식 OCR (이미지 기반 수식 인식) — PDF 텍스트 레이어의 수식만 대상

## Context

- 외부 오픈소스 프로젝트(Agentic Search Vectorless)를 클론하여 커스터마이징
- 주 대상 문서: 수능 수학, 시험 문제지 등 수학 수식이 많은 교육 자료 PDF
- PDF 파싱에 PyPDF와 PyMuPDF를 사용 중이나, 수식 파싱 품질 확인 필요
- LLM이 트리 구조 생성과 검색 추론 모두에 사용되므로, 수식이 LLM에 전달될 때 LaTeX로 전달되어야 정확한 처리 가능
- 프론트엔드에서 수식 렌더링을 위한 라이브러리(KaTeX 등) 통합 필요

## Constraints

- **Tech stack**: 기존 스택(FastAPI + Next.js + MongoDB) 유지
- **PDF 파서**: PyPDF/PyMuPDF 기반, 필요시 추가 라이브러리 도입 가능
- **LLM 비용**: 수식 파싱에 LLM 호출이 추가되면 비용 증가 고려
- **수식 품질**: PDF 텍스트 레이어 품질에 따라 수식 추출 정확도가 달라짐

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 수식 렌더링 라이브러리 선택 (KaTeX vs MathJax) | KaTeX이 더 빠르고 가벼움, MathJax는 호환성 높음 | — Pending |
| 수식 파싱 방식 (PDF 파서 레벨 vs LLM 보정) | PDF 파서가 수식을 어떻게 추출하는지에 따라 후처리 전략 결정 | — Pending |
| 수식 감지 범위 (인라인만 vs 블록 수식 포함) | 수능 문제지에는 인라인/블록 수식 모두 존재 | — Pending |

---
*Last updated: 2026-02-17 after initialization*
