from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = ROOT / "cmsscan.pdf"
OUT_PATH = ROOT / "docs" / "source-text" / "cmsscan.txt"


def main() -> None:
    reader = PdfReader(PDF_PATH)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    chunks: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        chunks.append(f"\n\n--- Page {index} ---\n{text.strip()}\n")

    OUT_PATH.write_text("".join(chunks).strip() + "\n", encoding="utf-8")
    total_chars = sum(len(chunk) for chunk in chunks)
    print(f"pages={len(reader.pages)} chars={total_chars} output={OUT_PATH}")


if __name__ == "__main__":
    main()
