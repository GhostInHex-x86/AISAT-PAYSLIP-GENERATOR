import os
import re
import base64
import zipfile

from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa
from io import BytesIO
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO_PATH = os.path.join(BASE_DIR, "logo.jpeg")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Register system TrueType fonts if available
_font_regular = r"C:\Windows\Fonts\arial.ttf"
_font_bold = r"C:\Windows\Fonts\arialbd.ttf"
if os.path.exists(_font_regular):
    try:
        pdfmetrics.registerFont(TTFont("Arial", _font_regular))
    except Exception:
        pass
if os.path.exists(_font_bold):
    try:
        pdfmetrics.registerFont(TTFont("Arial-Bold", _font_bold))
    except Exception:
        pass


# ── Currency formatter (Indian number system) ──────────────────────────────

def fmt_currency(val) -> str:
    """Format a number using Indian comma grouping. Returns '0' for zero."""
    try:
        val = round(float(val), 2)
    except (TypeError, ValueError):
        return "0"

    if val == 0:
        return "0"

    negative = val < 0
    val = abs(val)
    int_part = int(val)
    dec_part = round(val - int_part, 2)

    s = str(int_part)
    if len(s) > 3:
        last3 = s[-3:]
        rest = s[:-3]
        parts = []
        while len(rest) > 2:
            parts.append(rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.append(rest)
        parts.reverse()
        formatted = ",".join(parts) + "," + last3
    else:
        formatted = s

    if dec_part >= 0.005:
        formatted += f".{int(round(dec_part * 100)):02d}"

    return ("-" if negative else "") + formatted


# ── Logo helper ────────────────────────────────────────────────────────────

def get_logo_b64() -> str:
    """Return AISAT logo as a base64 data URI, or empty string if not found."""
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        return f"data:image/jpeg;base64,{data}"
    return ""


# ── Safe filename ──────────────────────────────────────────────────────────

def safe_filename(name: str) -> str:
    """Strip unsafe characters from a name for use in filenames."""
    name = re.sub(r"[^\w\s\-.]", "", name)
    return name.strip().replace(" ", "_")


# ── PDF generation ─────────────────────────────────────────────────────────

def _render_html(template, faculty, month: str, year: str, logo_b64: str) -> str:
    return template.render(
        faculty=faculty,
        month=month,
        year=year,
        logo_b64=logo_b64,
    )


def _html_to_pdf(html: str, dest_path: str) -> bool:
    """Render HTML to PDF using xhtml2pdf. Returns True on success."""
    with open(dest_path, "wb") as pdf_file:
        result = pisa.CreatePDF(
            BytesIO(html.encode("utf-8")),
            dest=pdf_file,
            encoding="utf-8",
        )
    return not result.err


# ── Main entry point ───────────────────────────────────────────────────────

def generate_payslips_zip(faculties, month: str, year: str,
                          output_dir: str, progress_queue) -> str:
    """
    Generate one PDF per faculty and zip them all up.

    Puts progress dicts into `progress_queue` as each PDF is created.
    Returns the absolute path to the generated ZIP file.
    """
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    env.filters["currency"] = fmt_currency
    template = env.get_template("payslip_template.html")

    logo_b64 = get_logo_b64()
    total = len(faculties)
    pdf_paths = []

    for i, faculty in enumerate(faculties):
        progress_pct = round((i + 1) / total * 100)
        try:
            html = _render_html(template, faculty, month, year, logo_b64)

            emp_id = faculty.emp_id or f"EMP{i + 1}"
            fname = f"{emp_id}_{safe_filename(faculty.name)}_payslip.pdf"
            pdf_path = os.path.join(output_dir, fname)

            ok = _html_to_pdf(html, pdf_path)

            if ok:
                pdf_paths.append(pdf_path)
                progress_queue.put({
                    "progress": progress_pct,
                    "log": f"\u2713 [{i + 1}/{total}] {faculty.name} (ID: {emp_id})",
                })
            else:
                progress_queue.put({
                    "progress": progress_pct,
                    "log": f"\u26a0 [{i + 1}/{total}] PDF issues for {faculty.name} — included anyway",
                })
                if os.path.exists(pdf_path):
                    pdf_paths.append(pdf_path)

        except Exception as exc:
            progress_queue.put({
                "progress": progress_pct,
                "log": f"\u2717 [{i + 1}/{total}] Error for {faculty.name}: {exc}",
            })

    # Build ZIP
    zip_name = f"AISAT_Payslips_{month}_{year}.zip"
    zip_path = os.path.join(output_dir, zip_name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in pdf_paths:
            zf.write(p, os.path.basename(p))

    progress_queue.put({
        "progress": 100,
        "log": f"\u2705 Done! {len(pdf_paths)}/{total} payslips packaged into {zip_name}",
        "done": True,
        "zip_filename": zip_name,
    })

    return zip_path