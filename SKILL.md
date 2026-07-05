---
name: cdsa-hwpsx
description: Generate Korean government-standard HWPX documents (행정안전부 표준서식) matching the official Ministry of the Interior and Safety format — title numbering (Ⅰ./□/○/-/※/⇒), three required fonts (HY헤드라인M, 휴먼명조, 맑은 고딕), navy section headers, and standard table styling. Use when the user needs a Korean 서면보고/기안/검토보고 document, or any .hwpx government report, generated programmatically instead of by hand in Hangul word processor.
---

# cdsa-hwpsx

행정안전부 'AI 친화 행정문서 작성 가이드라인' 기반 표준서식을 그대로 재현하는 HWPX 문서 생성기입니다.
설치 없이 `npx`로 실행됩니다.

## When to use

- 사용자가 한국 정부/공공기관 표준서식의 `.hwpx` 문서를 요청할 때
- 서면보고, 기안, 검토보고 등 공문서를 프로그래밍적으로 생성해야 할 때
- 대제목(Ⅰ.)·중제목(□)·본문(○)·하위(-)·주석(※)·결론(⇒) 체계를 따르는 문서가 필요할 때

## Requirements

- Node.js ≥ 16
- Python ≥ 3.9 (python-hwpx, lxml — 최초 실행 시 자동 설치 시도)

## Instructions

1. 문서 스펙을 JSON으로 구성한다 (아래 스키마 참고). 최소 `title`, `sections`가 있으면 된다.
2. 아래 명령으로 실행한다:
   ```bash
   npx cdsa-hwpsx --json <spec.json 경로>
   ```
   또는 간단한 1회성 문서는 인자만으로:
   ```bash
   npx cdsa-hwpsx --title "제목" --dept "부서" --author "작성자" --content "본문 문장." --output out.hwpx
   ```
3. 데모 문서로 빠르게 서식을 확인하려면:
   ```bash
   npx cdsa-hwpsx --demo
   ```
4. 결과물은 `output`에 지정한 경로(기본 `보고서.hwpx`)에 생성된다. 생성 후 사용자에게 파일 경로를 알려준다.

## JSON spec schema

```json
{
  "title": "문서 제목",
  "doc_type": "서면보고",
  "date": "2026. 7. 5.(일)",
  "dept": "담당부서",
  "author": "홍길동 사무관",
  "sections": [
    {
      "heading": "대제목 (Ⅰ.)",
      "subsections": [
        {
          "heading": "중제목 (□)",
          "paragraphs": ["본문 문장 (○ 불릿으로 출력)"],
          "notes": ["주석 (※)"],
          "conclusions": ["결론 (⇒)"],
          "table": { "rows": [["헤더1", "헤더2"], ["값1", "값2"]] }
        }
      ]
    }
  ],
  "output": "보고서.hwpx"
}
```

계층 규칙: 대제목(레벨1)에는 직접 본문을 넣지 않고 반드시 중제목(subsections)을 먼저 배치한다.
중제목(레벨2)에는 paragraphs(○) → subsections(레벨3, -) 순서로 배치한다.

## Format rules (요약)

| 요소 | 기호 | 폰트 | 크기 |
|---|:---:|---|:---:|
| 대제목 | Ⅰ. Ⅱ. … | 맑은 고딕 (Bold) | 15pt |
| 중제목 | □ | HY헤드라인M | 16pt |
| 본문 | ○ | 휴먼명조 | 15pt |
| 하위 | - | 휴먼명조 | 15pt |
| 주석 | ※ | 맑은 고딕 | 12pt |
| 결론 | ⇒ | 휴먼명조 | 15pt |

- 셀 병합 금지, 표준 번호체계 준수
- 줄간격: 본문 160%, 제목/메타 130%

## Files in this repo

- `bin/cli.js` — Node 실행 래퍼 (python 자동 설치 및 위임)
- `lib/generate_hwpx.py` — 실제 서식 생성 엔진 (python-hwpx + lxml XML 패치)
- `examples/sample-doc.json` — JSON 스펙 예시
