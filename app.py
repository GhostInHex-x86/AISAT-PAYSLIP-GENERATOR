import os
import json
import uuid
import queue
import threading
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, Response, send_file, jsonify,
)

from config import Config
from utils.excel_parser import parse_excel
from utils.pdf_generator import generate_payslips_zip

app = Flask(__name__)
app.config.from_object(Config)

# ── In-memory job store ────────────────────────────────────────────────────
# job_id -> { queue, zip_path, done, error }
_jobs: dict = {}
_jobs_lock = threading.Lock()


# ── Auth helper ────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ── Routes ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if (username == app.config["ADMIN_USERNAME"] and
                password == app.config["ADMIN_PASSWORD"]):
            session["logged_in"] = True
            session["username"] = username
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/generate", methods=["POST"])
@login_required
def generate():
    if "excel_file" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400

    f = request.files["excel_file"]
    if not f.filename.lower().endswith((".xlsx", ".xls")):
        return jsonify({"error": "Please upload an Excel file (.xlsx / .xls)."}), 400

    job_id = str(uuid.uuid4())

    # Save uploaded file
    upload_dir = app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)
    upload_path = os.path.join(upload_dir, f"{job_id}.xlsx")
    f.save(upload_path)

    # Create output dir for this job
    output_dir = os.path.join(app.config["OUTPUT_FOLDER"], job_id)
    os.makedirs(output_dir, exist_ok=True)

    # Register job
    q = queue.Queue()
    with _jobs_lock:
        _jobs[job_id] = {"queue": q, "zip_path": None, "done": False, "error": None}

    # Launch background thread
    t = threading.Thread(
        target=_run_generation,
        args=(job_id, upload_path, output_dir),
        daemon=True,
    )
    t.start()

    return jsonify({"job_id": job_id})


def _run_generation(job_id: str, upload_path: str, output_dir: str):
    q = _jobs[job_id]["queue"]
    try:
        faculties, month, year = parse_excel(upload_path)
        zip_path = generate_payslips_zip(faculties, month, year, output_dir, q)
        with _jobs_lock:
            _jobs[job_id]["zip_path"] = zip_path
            _jobs[job_id]["done"] = True
    except Exception as exc:
        q.put({"progress": 100, "log": f"\u2717 Fatal error: {exc}", "done": True, "error": True})
        with _jobs_lock:
            _jobs[job_id]["error"] = str(exc)
            _jobs[job_id]["done"] = True
    finally:
        q.put(None)  # sentinel — signals SSE stream to close


@app.route("/progress/<job_id>")
@login_required
def progress(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        return "Job not found.", 404

    def event_stream():
        # If already done, replay a completion event immediately
        if job["done"] and job["zip_path"]:
            payload = json.dumps({
                "progress": 100,
                "log": "Job already complete — download ready.",
                "done": True,
                "zip_filename": os.path.basename(job["zip_path"]),
            })
            yield f"data: {payload}\n\n"
            return

        q = job["queue"]
        while True:
            try:
                event = q.get(timeout=55)
                if event is None:          # sentinel
                    break
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("done"):
                    break
            except queue.Empty:
                # Heartbeat to keep the connection alive through proxies
                yield "data: {\"keepalive\": true}\n\n"

    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.route("/download/<job_id>")
@login_required
def download(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)

    if not job:
        flash("Job not found.", "error")
        return redirect(url_for("dashboard"))

    zip_path = job.get("zip_path")
    if not zip_path or not os.path.exists(zip_path):
        flash("ZIP not ready yet — please wait.", "error")
        return redirect(url_for("dashboard"))

    return send_file(
        zip_path,
        as_attachment=True,
        download_name=os.path.basename(zip_path),
        mimetype="application/zip",
    )


# ── Entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, threaded=True, host="0.0.0.0", port=5000)