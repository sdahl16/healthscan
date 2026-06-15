from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = ROOT / "cmsscan.pdf"
OUT_DIR = ROOT / "docs" / "source-images"


def main() -> None:
    reader = PdfReader(PDF_PATH)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    count = 0
    for page_index, page in enumerate(reader.pages, start=1):
        for image_index, image in enumerate(page.images, start=1):
            suffix = Path(image.name).suffix or ".bin"
            out_path = OUT_DIR / f"page-{page_index:02d}-image-{image_index:02d}{suffix}"
            out_path.write_bytes(image.data)
            count += 1
            print(out_path)

    print(f"images={count}")


if __name__ == "__main__":
    main()
