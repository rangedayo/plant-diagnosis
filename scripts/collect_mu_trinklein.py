"""[B-1] 자료 3 수집 — MU Trinklein (Missouri Environment & Garden, "Houseplant Problems", 2018).

입력 : data/source/Missouri_Environment_Garden.pdf  (10 pages, page 1만 사용)
출력 : data/raw/b_dataset/mu_trinklein/trinklein_2018.pdf       (원본 전체 무변형 카피)
       data/raw/b_dataset/mu_trinklein/trinklein_2018_page1.txt (page 1 본문 텍스트)
       data/raw/b_dataset/mu_trinklein/mu_trinklein.json        (파싱 카드)

파싱 전략 (3단 뉴스레터 에세이):
  - page 1만 추출. page 2 이후 폐기.
  - 단어를 center-x로 3단(col)에 버킷팅 → 컬럼 내 top 순 정렬 → reading order 복원.
    (crop 방식은 정렬 텍스트를 컬럼 경계에서 잘라 fragment 발생 → 버킷팅으로 회피)
  - 컬럼 내 수직 gap으로 문단 분할. 컬럼 경계에서 직전 문단이 문장부호로 끝나지 않으면
    다음 컬럼 첫 문단과 병합(문장 중간 분할 방지).
  - 각 문단 = 카드 1개 (프레임 정의가 본질이므로 짧아도 보존).

본질(변경 금지): "disease는 전염되지만 disorder는 안 됨" 프레임 + abiotic 손상 진단 패턴. FP 직격 ⭐⭐⭐.

실행 (프로젝트 루트에서)::

    python scripts/collect_mu_trinklein.py [--dump]
"""
from __future__ import annotations

import json
import shutil
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

import pdfplumber

SRC = Path("data/source/Missouri_Environment_Garden.pdf")
OUTDIR = Path("data/raw/b_dataset/mu_trinklein")
SOURCE_ID = "mu_trinklein"

COL_BOUNDS: list[tuple[float, float]] = [(0, 200), (200, 395), (395, 612)]
MASTHEAD_TOP = 160  # 이 위(top<)의 단어는 제호/타이틀 -> 카드에서 제외
LINE_TOL = 4
PARA_GAP_FACTOR = 1.6
SENTENCE_END = (".", "!", "?", '"', "”", ":")


def column_of(word: dict) -> int:
    cx = (word["x0"] + word["x1"]) / 2
    for i, (a, b) in enumerate(COL_BOUNDS):
        if a <= cx < b:
            return i
    return len(COL_BOUNDS) - 1


def cluster_lines(words: list[dict]) -> list[dict]:
    words = sorted(words, key=lambda w: (round(w["top"]), w["x0"]))
    lines: list[dict] = []
    for w in words:
        if lines and abs(w["top"] - lines[-1]["top"]) <= LINE_TOL:
            lines[-1]["w"].append(w)
        else:
            lines.append({"top": w["top"], "w": [w]})
    for ln in lines:
        ln["text"] = " ".join(x["text"] for x in sorted(ln["w"], key=lambda x: x["x0"]))
    return lines


def join_lines(line_texts: list[str]) -> str:
    """줄들을 합치며 줄끝 하이픈 디하이프네이션 + 공백 정리."""
    out = ""
    for t in line_texts:
        t = t.strip()
        if not t:
            continue
        if out.endswith("-"):
            out = out[:-1] + t  # 디하이프네이션
        else:
            out = (out + " " + t) if out else t
    return " ".join(out.split())


def collect() -> tuple[list[str], str]:
    with pdfplumber.open(str(SRC)) as pdf:
        page = pdf.pages[0]
        words = page.extract_words()
    title_words = [w for w in words if w["top"] < MASTHEAD_TOP]
    body_words = [w for w in words if w["top"] >= MASTHEAD_TOP]

    # 컬럼별 문단(문단 = 줄 텍스트 리스트) 생성
    per_col_paras: list[list[list[str]]] = []
    for ci in range(len(COL_BOUNDS)):
        cw = [w for w in body_words if column_of(w) == ci]
        lines = cluster_lines(cw)
        if not lines:
            per_col_paras.append([])
            continue
        gaps = [
            lines[i]["top"] - lines[i - 1]["top"]
            for i in range(1, len(lines))
            if lines[i]["top"] > lines[i - 1]["top"]
        ]
        med = statistics.median(gaps) if gaps else 11.0
        paras: list[list[str]] = [[lines[0]["text"]]]
        for i in range(1, len(lines)):
            if lines[i]["top"] - lines[i - 1]["top"] > med * PARA_GAP_FACTOR:
                paras.append([])
            paras[-1].append(lines[i]["text"])
        per_col_paras.append(paras)

    # 컬럼 순으로 펼치되, 컬럼 경계에서 문장 미완결이면 병합
    paragraphs: list[str] = []
    for col_paras in per_col_paras:
        for j, p_lines in enumerate(col_paras):
            ptext = join_lines(p_lines)
            if not ptext:
                continue
            if j == 0 and paragraphs and not paragraphs[-1].rstrip().endswith(SENTENCE_END):
                paragraphs[-1] = (paragraphs[-1] + " " + ptext).strip()  # 컬럼 가로질러 이어진 문장
            else:
                paragraphs.append(ptext)

    title = join_lines([ln["text"] for ln in cluster_lines(title_words)])
    return paragraphs, title


def derive_title(body: str, n: int = 7) -> str:
    words = body.split()
    head = " ".join(words[:n])
    return head + ("…" if len(words) > n else "")


def build_json(paragraphs: list[str]) -> dict:
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out_cards = [
        {
            "id": f"{SOURCE_ID}_{i:03d}",
            "section": "Houseplant Problems — page 1 (disease vs disorder frame)",
            "title": derive_title(body),
            "body": body,
            "lookalikes": None,
            "external_link": None,
        }
        for i, body in enumerate(paragraphs, 1)
    ]
    return {
        "source": SOURCE_ID,
        "page": "page 1 of Missouri Environment & Garden (Oct–Dec 2018), 'Houseplant Problems' by David Trinklein",
        "license": "fair_use_personal_educational",
        "fetched_at": fetched_at,
        "card_count": len(out_cards),
        "cards": out_cards,
    }


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC, OUTDIR / "trinklein_2018.pdf")  # 원본 전체 무변형 카피

    paragraphs, title = collect()
    page1_text = (title + "\n\n" if title else "") + "\n\n".join(paragraphs) + "\n"
    (OUTDIR / "trinklein_2018_page1.txt").write_text(page1_text, encoding="utf-8")

    data = build_json(paragraphs)
    (OUTDIR / "mu_trinklein.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"[mu_trinklein] {data['card_count']} cards -> {OUTDIR / 'mu_trinklein.json'}")
    print(f"   page1 text: {len(page1_text)} chars, title={title!r}")
    if "--dump" in sys.argv:
        for c in data["cards"]:
            print(f"  {c['id']}: {c['body'][:110]}")


if __name__ == "__main__":
    main()
