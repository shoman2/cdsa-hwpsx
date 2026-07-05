# cdsa-hwpsx

행정안전부 표준서식(hwpx)과 동일한 서식으로 공공행정문서를 자동 생성하는 npx CLI 도구입니다.
`npx cdsa-hwpsx` 한 줄로 별도 설치 없이 실행되며, 대제목(Ⅰ.)·중제목(□)·본문(○)·주석(※)·결론(⇒) 등
실제 공문서 서식 규칙과 3종 지정 폰트(HY헤드라인M / 휴먼명조 / 맑은 고딕)를 그대로 반영합니다.

## 배경

AX(AI Transformation) 강의와 컨설팅 현장에서는 교육 참가자나 실무 담당자가
"AI로 실제 행정/보고 문서를 표준 서식 그대로 만들 수 있는가"를 자주 묻습니다.
이 프로젝트는 그 답을 코드로 만든 예제이자, AI 에이전트 기반 업무자동화를 교육/컨설팅에서
실습형으로 보여주기 위한 도구입니다. 서식 생성 로직(Python, XML 레벨 패치)과 실행 인터페이스(Node CLI)를
분리해, "기존 로직을 감싸는 얇은 배포 레이어"로 npx 패키지를 만드는 과정 자체가 하나의 교육 사례입니다.

## 요구사항
- Node.js 16+
- Python 3.9+ (python-hwpx, lxml — 최초 실행 시 자동 설치 시도)

## 실행

```bash
npx cdsa-hwpsx --demo
```

### 모드 1 — 데모
```bash
npx cdsa-hwpsx --demo
```

### 모드 2 — JSON 스펙 (권장, 다단 섹션/표/주석/결론 전부 지원)
```bash
npx cdsa-hwpsx --json examples/sample-doc.json
```
JSON 스펙 필드는 `lib/generate_hwpx.py`의 `create_gov_hwpx(doc)` 입력 스펙과 동일합니다.

### 모드 3 — 간단 인자
```bash
npx cdsa-hwpsx \
  --title "AX 컨설팅 도입 계획 보고" \
  --dept "AI정책과" \
  --author "김태유 사무관" \
  --content "AX 컨설팅 및 업무자동화 도입을 추진함." \
  --output plan.hwpx
```

## 서식 규칙 (요약)
- 대제목: Ⅰ. → Ⅱ. ... / 중제목: □ / 본문: ○ / 하위: - / 주석: ※ / 결론: ⇒
- 폰트: HY헤드라인M(제목/중제목), 휴먼명조(본문), 맑은 고딕(표/주석)
- 셀 병합 금지, 표준 번호체계 준수

## 로컬 개발

```bash
git clone https://github.com/shoman2/cdsa-hwpsx.git
cd cdsa-hwpsx
node bin/cli.js --demo
```

## 배포 (npm publish)
```bash
npm login
npm publish --access public
```

## 만든 사람

**김태유**
AX(AI Transformation) 전문교수 · AI 박사 · 컨설턴트

기업/공공기관 대상 AX 교육과 AI PoC(Proof of Concept), 에이전트 기반 업무자동화 설계를
전문으로 하며, 1인 컨설팅 기업 Flowthat AI Consulting을 운영하고 있습니다.
삼성, 한화첨단소재, POSCO E&C, KPMG, NIA 등과의 교육·컨설팅 경험을 바탕으로,
"AI가 실제 업무 산출물을 만들어내는 실습형 도구"를 지속적으로 만들고 공유합니다.

- YouTube: 플로우댓(Flowthat) — AI 콘텐츠
- 컨설팅 문의: Flowthat AI Consulting

## License
MIT
