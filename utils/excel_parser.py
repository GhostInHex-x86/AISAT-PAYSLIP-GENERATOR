import os
import re
import openpyxl
from dataclasses import dataclass
from typing import Optional


@dataclass
class Faculty:
    sl_no: int
    name: str
    emp_id: str
    email: str
    department: str
    designation: str
    total_days: int
    days_worked: int
    basic: float
    da: float
    hra: float
    agp: float
    interim_hike: float
    others_earning: float
    gross_salary: float
    prof_tax: float
    sal_adv: float
    other_deductions: float  # bus + canteen
    esi: float
    epf: float
    tds: float
    lop: float
    total_deduction: float
    net_salary: float


def _fv(v) -> float:
    """Safe float conversion; returns 0.0 for None/empty/invalid."""
    if v is None:
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _iv(v, default: int = 0) -> int:
    return int(_fv(v)) if v is not None else default


def _sv(v, default: str = "") -> str:
    if v is None:
        return default
    s = str(v).strip()
    return s if s not in ("None", "nan") else default


def parse_month_year(text: str):
    """Extract month name and 4-digit year from a header string."""
    MONTHS = [
        "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
        "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER",
    ]
    text_up = str(text).upper() if text else ""
    month = next((m.capitalize() for m in MONTHS if m in text_up), "Month")
    m = re.search(r"\b(20\d{2})\b", text_up)
    year = m.group(1) if m else "Year"
    return month, year


def _find_header_row(all_rows):
    """Return (index, headers_lower_list) for the data header row."""
    for i, row in enumerate(all_rows):
        vals = [str(v).strip().lower() if v else "" for v in row]
        # Must contain 'name' and at least one salary field
        if "name" in vals and any(k in vals for k in ("basic", "sl no", "employee id")):
            return i, vals
    return None, None


def parse_excel(filepath: str):
    """
    Parse either statements.xlsx or salary_filtered.xlsx.

    Returns:
        (list[Faculty], month_str, year_str)
    """
    wb = openpyxl.load_workbook(filepath, data_only=True)
    ws = wb.active
    all_rows = list(ws.iter_rows(values_only=True))

    if not all_rows:
        raise ValueError("The uploaded Excel file is empty.")

    # Month/year from row 2 (index 1)
    month_text = all_rows[1][0] if len(all_rows) > 1 else ""
    month, year = parse_month_year(month_text)

    header_idx, headers = _find_header_row(all_rows)
    if header_idx is None:
        raise ValueError(
            "Could not locate the header row in the uploaded file.")

    # Detect file format by presence of 'days worked' column
    has_days_worked = "days worked" in headers

    faculties = []

    if has_days_worked:
        # ── statements.xlsx layout (index-based for duplicate col names) ──
        # 0  Sl No
        # 1  Name
        # 2  Name (duplicate)
        # 3  EMPLOYEE ID
        # 4  EMAIL ID
        # 5  DEPARTMENT
        # 6  DESIGNATION
        # 7  Total working Days
        # 8  Days Worked
        # 9  Basic (original)
        # 10 DA
        # 11 HRA
        # 12 AGP
        # 13 Interim Hike
        # 14 Others
        # 15 Salary
        # 16 LOP Days
        # 17 LOP AMT (original)
        # 18 Basic (LOP-adjusted) ← use these for earnings display
        # 19 DA (LOP-adjusted)
        # 20 HRA (LOP-adjusted)
        # 21 AGP (LOP-adjusted)
        # 22 Interim Hike (LOP-adjusted)
        # 23 Others (LOP-adjusted)
        # 24 Gross Salary
        # 25 Prof. Tax
        # 26 Bus
        # 27 Adv
        # 28 Canteen
        # 29 ESI SALARY
        # 30 ESI Premium
        # 31 PF SALARY
        # 32 EPF
        # 33 TDS
        # 34 LOP AMT
        # 35 Hold
        # 36 Salary Paid
        # 37 Total Deduction
        # 38 Net Salary
        for row in all_rows[header_idx + 1:]:
            if not row or row[0] is None:
                continue
            sl = row[0]
            if not isinstance(sl, (int, float)):
                continue
            try:
                def R(i): return row[i] if len(row) > i else None  # noqa
                # Use LOP-adjusted earnings if present (col 18-23), else original (9-14)
                basic = _fv(R(18) if R(18) is not None else R(9))
                da = _fv(R(19) if R(19) is not None else R(10))
                hra = _fv(R(20) if R(20) is not None else R(11))
                agp = _fv(R(21) if R(21) is not None else R(12))
                interim = _fv(R(22) if R(22) is not None else R(13))
                others = _fv(R(23) if R(23) is not None else R(14))

                bus = _fv(R(26))
                canteen = _fv(R(28))

                emp_id_raw = R(3)
                if isinstance(emp_id_raw, float) and emp_id_raw.is_integer():
                    emp_id = str(int(emp_id_raw))
                else:
                    emp_id = _sv(emp_id_raw)

                faculties.append(Faculty(
                    sl_no=int(sl),
                    name=_sv(R(1), f"Employee_{int(sl)}"),
                    emp_id=emp_id,
                    email=_sv(R(4)),
                    department=_sv(R(5)),
                    designation=_sv(R(6)),
                    total_days=_iv(R(7), 30),
                    days_worked=_iv(R(8), 30),
                    basic=basic, da=da, hra=hra, agp=agp,
                    interim_hike=interim, others_earning=others,
                    gross_salary=_fv(R(24)),
                    prof_tax=_fv(R(25)),
                    sal_adv=_fv(R(27)),
                    other_deductions=bus + canteen,
                    esi=_fv(R(30)),
                    epf=_fv(R(32)),
                    tds=_fv(R(33)),
                    lop=_fv(R(34)),
                    total_deduction=_fv(R(37)),
                    net_salary=_fv(R(38)),
                ))
            except Exception:
                continue  # skip malformed rows silently

    else:
        # ── salary_filtered.xlsx layout ──
        # 0  Sl No | 1 Name | 2 Employee ID | 3 Email
        # 4 Basic | 5 DA | 6 HRA | 7 AGP | 8 Interim Hike | 9 Others
        # 10 Prof Tax | 11 Sal.Adv | 12 Other Deductions | 13 ESI
        # 14 EPF | 15 TDS | 16 LOP | 17 Gross Salary
        # 18 Total Deduction | 19 Net Salary
        for row in all_rows[header_idx + 1:]:
            if not row or row[0] is None:
                continue
            sl = row[0]
            if not isinstance(sl, (int, float)):
                continue
            try:
                def R(i): return row[i] if len(row) > i else None  # noqa

                emp_id_raw = R(2)
                if isinstance(emp_id_raw, float) and emp_id_raw.is_integer():
                    emp_id = str(int(emp_id_raw))
                else:
                    emp_id = _sv(emp_id_raw)

                faculties.append(Faculty(
                    sl_no=int(sl),
                    name=_sv(R(1), f"Employee_{int(sl)}"),
                    emp_id=emp_id,
                    email=_sv(R(3)),
                    department="", designation="",
                    total_days=30, days_worked="N/A",
                    basic=_fv(R(4)), da=_fv(R(5)),
                    hra=_fv(R(6)),  agp=_fv(R(7)),
                    interim_hike=_fv(R(8)), others_earning=_fv(R(9)),
                    gross_salary=_fv(R(17)),
                    prof_tax=_fv(R(10)),
                    sal_adv=_fv(R(11)),
                    other_deductions=_fv(R(12)),
                    esi=_fv(R(13)),
                    epf=_fv(R(14)),
                    tds=_fv(R(15)),
                    lop=_fv(R(16)),
                    total_deduction=_fv(R(18)),
                    net_salary=_fv(R(19)),
                ))
            except Exception:
                continue

    if not faculties:
        raise ValueError(
            "No faculty data rows found. Check that the file matches the expected format.")

    return faculties, month, year
