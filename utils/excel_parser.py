import re
import logging
import openpyxl
from dataclasses import dataclass
from typing import Union

log = logging.getLogger(__name__)


@dataclass
class Faculty:
    sl_no: int
    name: str
    emp_id: str
    email: str
    department: str
    designation: str
    total_days: int
    days_worked: Union[int, str]
    basic: float
    da: float
    hra: float
    agp: float
    interim_hike: float
    others_earning: float
    gross_salary: float
    prof_tax: float
    sal_adv: float
    other_deductions: float  # bus + canteen, or "Other Deductions"
    esi: float
    epf: float
    tds: float
    lop: float
    total_deduction: float
    net_salary: float


# ───────────────────────── value helpers ─────────────────────────

def _fv(v) -> float:
    if v is None:
        return 0.0
    try:
        return float(str(v).replace(",", "").strip() or 0)
    except (TypeError, ValueError):
        return 0.0


def _sv(v, default: str = "") -> str:
    if v is None:
        return default
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    s = str(v).strip()
    return s if s and s.lower() not in ("none", "nan") else default


def _is_number(v) -> bool:
    if isinstance(v, (int, float)):
        return True
    try:
        float(str(v).strip())
        return True
    except (TypeError, ValueError):
        return False


def _norm(h) -> str:
    """'Prof. Tax ' -> 'proftax', 'EMAIL ID' -> 'emailid'"""
    return re.sub(r"[^a-z0-9]", "", str(h).lower()) if h is not None else ""


def parse_month_year(text: str):
    MONTHS = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY",
              "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"]
    text_up = str(text).upper() if text else ""
    month = next((m.capitalize() for m in MONTHS if m in text_up), "Month")
    m = re.search(r"\b(20\d{2})\b", text_up)
    return month, (m.group(1) if m else "Year")


# ───────────────────────── header mapping ─────────────────────────

class ColumnMap:
    """Maps normalized header names -> list of column indexes (handles duplicates)."""

    def __init__(self, header_row):
        self.cols = {}
        for i, h in enumerate(header_row):
            key = _norm(h)
            if key:
                self.cols.setdefault(key, []).append(i)

    def has(self, *aliases) -> bool:
        return any(a in self.cols for a in aliases)

    def indexes(self, *aliases):
        for a in aliases:
            if a in self.cols:
                return self.cols[a]
        return []

    def get(self, row, *aliases, occurrence: int = 0, fallback_first: bool = True):
        """
        occurrence=0 -> first column with that header
        occurrence=1 -> second column (e.g. LOP-adjusted Basic)
        occurrence=-1 -> last column
        """
        idxs = self.indexes(*aliases)
        if not idxs:
            return None
        if occurrence == -1:
            i = idxs[-1]
        elif occurrence < len(idxs):
            i = idxs[occurrence]
        elif fallback_first:
            i = idxs[0]
        else:
            return None
        return row[i] if i < len(row) else None


def _find_header_row(all_rows):
    for i, row in enumerate(all_rows[:20]):  # header is near the top
        norms = {_norm(v) for v in row}
        if "name" in norms and norms & {"basic", "grosssalary", "netsalary"}:
            return i
    return None


# ───────────────────────── main parser ─────────────────────────

def parse_excel(filepath: str):
    """
    Parse either salary format by header names.
    Returns: (list[Faculty], month_str, year_str)
    """
    wb = openpyxl.load_workbook(filepath, data_only=True)
    ws = wb.active
    all_rows = list(ws.iter_rows(values_only=True))
    if not all_rows:
        raise ValueError("The uploaded Excel file is empty.")

    month_text = all_rows[1][0] if len(all_rows) > 1 and all_rows[1] else ""
    month, year = parse_month_year(month_text)

    header_idx = _find_header_row(all_rows)
    if header_idx is None:
        raise ValueError("Could not locate the header row in the uploaded file.")

    cm = ColumnMap(all_rows[header_idx])

    # statements format has LOP-adjusted earnings as a 2nd set of columns
    has_adjusted = len(cm.indexes("basic")) > 1
    earn_occ = 1 if has_adjusted else 0

    faculties = []
    counter = 0

    for row in all_rows[header_idx + 1:]:
        if not row or all(v is None for v in row):
            continue

        # Name: first "Name" column that holds real text (skips a numeric serial column)
        name = ""
        for i in cm.indexes("name", "employeename"):
            v = row[i] if i < len(row) else None
            if v is not None and not _is_number(v) and _sv(v):
                name = _sv(v)
                break
        if not name or "total" in name.lower():
            continue  # blank row or a totals row

        gross = _fv(cm.get(row, "grosssalary"))
        net = _fv(cm.get(row, "netsalary"))
        if gross == 0 and net == 0 and _fv(cm.get(row, "basic")) == 0:
            continue  # not a data row

        counter += 1
        sl_raw = cm.get(row, "slno", "sno", "sl", "serialno")
        sl_no = int(_fv(sl_raw)) if _is_number(sl_raw) else counter

        total_days = int(_fv(cm.get(row, "totalworkingdays", "totaldaysworked", "totaldays"))) or 30

        if cm.has("daysworked"):
            days_worked = int(_fv(cm.get(row, "daysworked")))
            if days_worked > 31:
                log.warning("Row %s (%s): days worked = %s looks wrong", sl_no, name, days_worked)
        else:
            days_worked = "N/A"

        if cm.has("otherdeductions"):
            other_ded = _fv(cm.get(row, "otherdeductions"))
        else:
            other_ded = _fv(cm.get(row, "bus")) + _fv(cm.get(row, "canteen"))

        faculties.append(Faculty(
            sl_no=sl_no,
            name=name,
            emp_id=_sv(cm.get(row, "employeeid", "empid", "employeecode")),
            email=_sv(cm.get(row, "emailid", "email")),
            department=_sv(cm.get(row, "department", "dept")),
            designation=_sv(cm.get(row, "designation")),
            total_days=total_days,
            days_worked=days_worked,
            basic=_fv(cm.get(row, "basic", occurrence=earn_occ)),
            da=_fv(cm.get(row, "da", occurrence=earn_occ)),
            hra=_fv(cm.get(row, "hra", occurrence=earn_occ)),
            agp=_fv(cm.get(row, "agp", occurrence=earn_occ)),
            interim_hike=_fv(cm.get(row, "interimhike", occurrence=earn_occ)),
            others_earning=_fv(cm.get(row, "others", occurrence=earn_occ)),
            gross_salary=gross,
            prof_tax=_fv(cm.get(row, "proftax", "professionaltax")),
            sal_adv=_fv(cm.get(row, "saladv", "adv", "advance", "salaryadvance")),
            other_deductions=other_ded,
            esi=_fv(cm.get(row, "esipremium", "esi")),
            epf=_fv(cm.get(row, "epf")),
            tds=_fv(cm.get(row, "tds")),
            lop=_fv(cm.get(row, "lopamt", "lop", occurrence=-1)),
            total_deduction=_fv(cm.get(row, "totaldeduction", "totaldeductions")),
            net_salary=net,
        ))

    if not faculties:
        raise ValueError("No faculty data rows found. Check that the file matches the expected format.")

    return faculties, month, year
