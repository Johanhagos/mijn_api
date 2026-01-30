from fpdf import FPDF
from pathlib import Path

MD = Path(__file__).parent.parent / "docs" / "UX_Flows.md"
OUT = Path(__file__).parent.parent / "docs" / "UX_Flows.pdf"


def render_md_to_pdf(md_path: Path, out_path: Path):
    text = md_path.read_text(encoding="utf-8")
    pdf = FPDF()
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)

    for line in text.splitlines():
        if line.strip().startswith("# "):
            pdf.set_font("Helvetica", size=16)
            pdf.cell(0, 10, line.strip("# "), ln=True)
            pdf.ln(2)
            pdf.set_font("Helvetica", size=12)
            continue
        if line.strip().startswith("## "):
            pdf.set_font("Helvetica", size=14)
            pdf.cell(0, 8, line.strip("# "), ln=True)
            pdf.ln(1)
            pdf.set_font("Helvetica", size=12)
            continue

        # regular paragraph
        pdf.multi_cell(0, 6, line)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_bytes = pdf.output(dest="S").encode("latin-1")
    out_path.write_bytes(pdf_bytes)


if __name__ == "__main__":
    render_md_to_pdf(MD, OUT)
    print("Generated", OUT)
