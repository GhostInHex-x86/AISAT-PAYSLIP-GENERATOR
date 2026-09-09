# AISAT Payslip Generator 📄

A modern, lightweight Flask web application designed for **Albertian Institute of Science and Technology (AISAT)** to automate faculty payslip generation. Upload an Excel spreadsheet of monthly salary statements, watch individual branded PDF payslips get generated in real time with live progress logs, and download all slips packaged in a single ZIP archive.

---

## Features

- **🔐 Admin Authentication**: Secure session-based login protected by environment variables (`.env`).
- **📊 Smart Excel Ingestion**:
  - Automatically parses `statements.xlsx` (including Department, Designation, Total Working Days, and Days Worked).
  - Backwards-compatible with `salary_filtered.xlsx`.
  - Automatically extracts salary month & year from the spreadsheet header.
- **⚡ Real-Time Progress Feedback**:
  - Live animated progress bar powered by **Server-Sent Events (SSE)** — zero WebSocket bloat.
  - Scrollable dark terminal log displaying real-time generation status for each faculty member.
- **🎨 Custom Branded Payslip PDFs**:
  - AISAT logo integration.
  - Formatted earnings & deductions table (Basic, DA, HRA, AGP, Interim Hike, PF, TDS, LOP, etc.).
  - Prominent Net Salary banner with Indian comma grouping (`₹` / `Rs.`).
  - Print-ready A4 single-page layout.
- **📦 Instant ZIP Packaging**: Compresses all generated faculty PDFs into `AISAT_Payslips_<Month>_<Year>.zip` ready for one-click download.

---

## 📋 Payslip Template Format

The generated PDF matches the official institutional slip format:

```text
┌────────────┬──────────────────────────┬─────────────┐
│            │                          │             │
│ AISAT LOGO │       SALARY SLIP        │ CONFIDENTIAL│
│            │       January 2022       │             │
├────────────┴──────────────┬───────────┴─────────────┤
│ Name: Dr.Jake Sully       │ Email: sully@aisat.ac.in│
│ Employee ID: 991          │ Days Worked: 31 / 31    │
│ Designation: PRINCIPAL    │ Department: OFFICE      │
├───────────────────────────┴─────────────────────────┤
│ Description          │ Earnings │ Deductions        │
├──────────────────────┼──────────┼───────────────────┤
│ Basic                │ 53,706   │                   │
│ DA                   │ 68,794   │                   │
│ HRA                  │ 1,500    │                   │
│ AGP                  │ 10,000   │                   │
│ Interim Hike         │ 0        │                   │
│ Others               │ 0        │                   │
│ Prof Tax             │          │ 0                 │
│ Sal. Adv             │          │ 0                 │
│ Other Deductions     │          │ 0                 │
│ ESI                  │          │ 0                 │
│ EPF                  │          │ 0                 │
│ TDS                  │          │ 30,000            │
│ LOP                  │          │ 0                 │
├──────────────────────┼──────────┼───────────────────┤
│ Gross Salary         │ 1,34,000 │                   │
│ Total Deduction      │          │ 30,000            │
├──────────────────────┴──────────┴───────────────────┤
│                     NET SALARY                      │
│                    Rs. 1,04,000                     │
└─────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

- **Backend**: Python 3.10+, [Flask](https://flask.palletsprojects.com/)
- **PDF Engine**: [xhtml2pdf](https://xhtml2pdf.readthedocs.io/) & [ReportLab](https://www.reportlab.com/) (Pure Python, no external GTK/wkhtmltopdf dependencies)
- **Excel Processing**: [openpyxl](https://openpyxl.readthedocs.io/)
- **Templating**: Jinja2
- **Real-Time Streaming**: Server-Sent Events (SSE) via native `EventSource` API
- **Frontend**: Vanilla JavaScript & CSS3 (Modern, responsive, drag-and-drop file upload)

---

## 📁 Project Structure

```text
PAYSLIP/
├── app.py                     # Flask application & SSE route handlers
├── config.py                  # Configuration loader
├── requirements.txt           # Python dependencies
├── .env                       # Admin credentials & secret key (gitignored)
├── logo.jpeg                  # AISAT official logo
├── utils/
│   ├── __init__.py
│   ├── excel_parser.py        # Robust parser for statements & filtered Excel
│   └── pdf_generator.py       # HTML-to-PDF rendering & ZIP compression
├── templates/
│   ├── base.html              # Base layout with navbar and footer
│   ├── login.html             # Admin login page
│   ├── dashboard.html         # Drag-and-drop upload & live progress UI
│   └── payslip_template.html  # Standalone print-ready PDF template
├── static/
│   ├── css/
│   │   └── styles.css         # UI styles and animations
│   ├── js/
│   │   └── dashboard.js       # SSE listener, drag-and-drop & progress logic
│   └── img/
│       └── logo.jpeg          # Web-served logo copy
├── uploads/                   # Temporary storage for uploaded spreadsheets
└── outputs/                   # Generated PDFs and downloadable ZIP archives
```

---

## 🚀 Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/aisat-payslip-generator.git
cd aisat-payslip-generator
```

### 2. Create and Activate Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create or edit the `.env` file in the root directory:
```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password
SECRET_KEY=generate_a_long_random_secret_string
```

### 5. Run the Application
```bash
python app.py
```
Open your browser and navigate to **`http://localhost:5000`**.

---

## 📖 Usage Guide

1. **Login**: Sign in with your admin credentials configured in `.env`.
2. **Upload**: Drag & drop your salary statement Excel file (`statements.xlsx` or `.xlsx`) onto the dashboard.
3. **Generate**: Click **⚡ Generate Payslips**.
4. **Monitor**: Watch the animated progress bar and live terminal logs as each faculty payslip is processed.
5. **Download**: Once processing hits 100%, click **⬇ Download ZIP** to retrieve the compressed archive containing all payslips.

---

## 🔒 Security Best Practices

- Always update `ADMIN_PASSWORD` and `SECRET_KEY` in `.env` before deploying to production.
- Do not commit your `.env`, `uploads/`, or `outputs/` folders to public repositories (included in `.gitignore`).

---

## 📄 License

This project was developed for internal institutional use at **Albertian Institute of Science and Technology (AISAT)**.
