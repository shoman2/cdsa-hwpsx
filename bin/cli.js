#!/usr/bin/env node
/**
 * cdsa-hwpsx
 * 행정안전부 표준서식과 동일한 HWPX 문서를 생성하는 CLI.
 * 내부적으로 lib/generate_hwpx.py (python-hwpx + lxml)를 호출한다.
 *
 * 사용법:
 *   npx cdsa-hwpsx --demo                       데모 문서 즉시 생성
 *   npx cdsa-hwpsx --json ./doc.json            JSON 스펙으로 문서 생성
 *   npx cdsa-hwpsx --title "제목" --dept "부서" --author "담당자" --output out.hwpx
 */

const { spawnSync } = require("child_process");
const path = require("path");
const fs = require("fs");
const os = require("os");

const PY_SCRIPT = path.join(__dirname, "..", "lib", "generate_hwpx.py");

function findPython() {
  for (const cmd of ["python3", "python"]) {
    const check = spawnSync(cmd, ["--version"], { encoding: "utf-8" });
    if (!check.error) return cmd;
  }
  return null;
}

function checkDeps(pythonCmd) {
  const check = spawnSync(
    pythonCmd,
    ["-c", "import hwpx, lxml"],
    { encoding: "utf-8" }
  );
  return check.status === 0;
}

function printHelp() {
  console.log(`
cdsa-hwpsx — 행정안전부 표준서식 HWPX 생성기

옵션:
  --demo                  데모 문서를 즉시 생성 (보고서_데모.hwpx)
  --json <path>           문서 스펙 JSON 파일로 생성
  --title <text>          제목 (간단 모드)
  --dept <text>           작성 부서 (간단 모드)
  --author <text>         작성자 (간단 모드)
  --doctype <text>        문서 종류 (기본: 서면보고)
  --content <text>        본문 1줄 (간단 모드, ○ 불릿으로 삽입)
  --output <path>         출력 파일 경로 (기본: 보고서.hwpx)
  --help                  도움말

예시:
  npx cdsa-hwpsx --demo
  npx cdsa-hwpsx --title "AI 도입 계획 보고" --dept "AI정책과" --author "김태유 사무관" --content "AX 컨설팅 도입을 추진함." --output plan.hwpx
`);
}

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith("--")) {
      const key = a.slice(2);
      const next = argv[i + 1];
      if (next && !next.startsWith("--")) {
        args[key] = next;
        i++;
      } else {
        args[key] = true;
      }
    }
  }
  return args;
}

function main() {
  const argv = process.argv.slice(2);
  const args = parseArgs(argv);

  if (args.help || argv.length === 0) {
    printHelp();
    return;
  }

  const pythonCmd = findPython();
  if (!pythonCmd) {
    console.error(
      "❌ python3(또는 python)을 찾을 수 없습니다. Python 3.9 이상을 설치해 주세요."
    );
    process.exit(1);
  }

  if (!checkDeps(pythonCmd)) {
    console.log("⚙️  필요한 파이썬 패키지를 설치합니다 (python-hwpx, lxml)...");
    const install = spawnSync(
      pythonCmd,
      ["-m", "pip", "install", "python-hwpx", "lxml", "--break-system-packages", "-q"],
      { stdio: "inherit" }
    );
    if (install.status !== 0) {
      console.error(
        "❌ 자동 설치 실패. 수동으로 실행해 주세요: pip install python-hwpx lxml"
      );
      process.exit(1);
    }
  }

  let jsonPath;
  let tmpFile = null;

  if (args.demo) {
    // demo 모드: python 스크립트 자체 데모 실행
    const result = spawnSync(pythonCmd, [PY_SCRIPT], { stdio: "inherit" });
    process.exit(result.status || 0);
  } else if (args.json) {
    jsonPath = path.resolve(args.json);
    if (!fs.existsSync(jsonPath)) {
      console.error(`❌ JSON 파일을 찾을 수 없습니다: ${jsonPath}`);
      process.exit(1);
    }
  } else {
    // 간단 모드: 커맨드라인 인자로 최소 문서 스펙 조립
    const doc = {
      title: args.title || "보고서",
      doc_type: args.doctype || "서면보고",
      dept: args.dept || "",
      author: args.author || "",
      sections: args.content
        ? [
            {
              heading: "주요 내용",
              paragraphs: [args.content],
            },
          ]
        : [],
      output: args.output || "보고서.hwpx",
    };
    tmpFile = path.join(os.tmpdir(), `cdsa-hwpsx-${Date.now()}.json`);
    fs.writeFileSync(tmpFile, JSON.stringify(doc), "utf-8");
    jsonPath = tmpFile;
  }

  const result = spawnSync(pythonCmd, [PY_SCRIPT, "--json", jsonPath], {
    stdio: "inherit",
  });

  if (tmpFile) fs.unlinkSync(tmpFile);
  process.exit(result.status || 0);
}

main();
