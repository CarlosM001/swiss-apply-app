from fastapi import FastAPI
from .routers import jobs, applications, letters, exports, job_tasks

app = FastAPI(title="KI Bewerbungsplattform API (v3)", version="0.3.0")

app.include_router(jobs.router, prefix="/v1/jobs", tags=["jobs"])
app.include_router(applications.router, prefix="/v1/applications", tags=["applications"])
app.include_router(letters.router, prefix="/v1/letters", tags=["letters"])
app.include_router(exports.router, prefix="/v1/exports", tags=["exports"])
app.include_router(job_tasks.router, prefix="/v1/job-tasks", tags=["job-tasks"])

@app.get("/health")
def health():
    return {"status": "ok"}
