
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from docx import Document

def export_to_pdf(text: str, out_path: str):
    c = canvas.Canvas(out_path, pagesize=letter)
    width, height = letter
    x, y = inch, height - inch
    for line in text.splitlines():
        for wrapped in _wrap_line(line, 90):
            if y < inch:
                c.showPage()
                y = height - inch
            c.drawString(x, y, wrapped)
            y -= 14
    c.save()

def _wrap_line(text, width=90):
    words = text.split(" ")
    cur = ""
    for w in words:
        if len(cur) + 1 + len(w) > width:
            if cur:
                yield cur
            cur = w
        else:
            cur = w if not cur else cur + " " + w
    if cur:
        yield cur

def export_to_docx(text: str, out_path: str):
    doc = Document()
    for para in text.split("\n\n"):
        doc.add_paragraph(para)
    doc.save(out_path)

def export_to_json(mapping: dict, note_text: str, out_path: str):
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"note": note_text, "mapping": mapping}, f, indent=2)
