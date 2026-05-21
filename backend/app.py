import os
import json
import uuid
import shutil
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from meridian_runner import run_meridian_analysis
from report_generator import generate_full_report

app = FastAPI(title="Meridian MMM Tool")

# Allow the frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store job status in memory
jobs = {}


@app.get("/health")
def health():
    return {"status": "ok", "message": "Meridian MMM Tool is running"}


@app.post("/analyze")
async def analyze(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    config: str = Form(...),
    date_start: str = Form(...),
    date_end: str = Form(...),
):
    # Create unique job ID
    job_id = str(uuid.uuid4())
    csv_path = f"/tmp/{job_id}.csv"

    # Save uploaded CSV file
    with open(csv_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Mark job as pending
    jobs[job_id] = {
        "status": "pending",
        "report": None,
        "error": None
    }

    # Run analysis in background
    background_tasks.add_task(
        run_analysis_job,
        job_id=job_id,
        csv_path=csv_path,
        config=json.loads(config),
        date_start=date_start,
        date_end=date_end,
    )

    return JSONResponse({
        "job_id": job_id,
        "status": "pending",
        "message": "Analysis started. Poll /status/{job_id} for updates."
    })


def run_analysis_job(job_id, csv_path, config, date_start, date_end):
    """Background task that runs Meridian and stores the HTML report."""
    try:
        # Update status to running
        jobs[job_id]["status"] = "running"
        print(f"Job {job_id} started")

        # Run full Meridian pipeline
        results = run_meridian_analysis(csv_path, config, date_start, date_end)

        # Generate HTML report
        report_html = generate_full_report(results, job_id)

        # Store completed report
        jobs[job_id]["status"] = "complete"
        jobs[job_id]["report"] = report_html
        print(f"Job {job_id} complete")

    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)
        print(f"Job {job_id} failed: {e}")


@app.get("/status/{job_id}")
def get_status(job_id: str):
    """Check the status of an analysis job."""
    if job_id not in jobs:
        return JSONResponse(
            {"error": "Job not found"},
            status_code=404
        )
    return JSONResponse({
        "job_id": job_id,
        "status": jobs[job_id]["status"],
        "error": jobs[job_id].get("error")
    })


@app.get("/report/{job_id}", response_class=HTMLResponse)
def get_report(job_id: str):
    """Get the completed HTML report for a job."""
    if job_id not in jobs:
        return HTMLResponse("<h2>Job not found</h2>", status_code=404)
    if jobs[job_id]["status"] != "complete":
        return HTMLResponse(
            f"<h2>Report not ready. Status: {jobs[job_id]['status']}</h2>",
            status_code=202
        )
    return HTMLResponse(content=jobs[job_id]["report"])


@app.get("/jobs")
def list_jobs():
    """List all jobs and their statuses."""
    return JSONResponse({
        job_id: {"status": info["status"], "error": info.get("error")}
        for job_id, info in jobs.items()
    })
