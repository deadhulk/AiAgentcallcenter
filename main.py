from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse, PlainTextResponse
from src.ops import monitoring
from src.api.routes import router as api_router
from src.api.orchestration import router as orchestration_router
from src.database.models import init_db
import uvicorn
from dotenv import load_dotenv
import logging
import time

# orchestration & monitoring hooks
from src.ops.orchestration import init_orchestration, shutdown_orchestration
from src.ops.monitoring import init_monitoring, metrics_handler

# Load environment variables
load_dotenv()

# Custom middleware for file size limit
async def file_size_limit_middleware(request, call_next):
    if request.method == "POST" and "multipart/form-data" in request.headers.get("content-type", ""):
        content_length = int(request.headers.get("content-length", 0))
        if content_length > 1024 * 1024:  # 1MB limit
            return JSONResponse(
                status_code=413,
                content={"detail": "File too large. Maximum size is 1MB"}
            )
    return await call_next(request)

# Initialize FastAPI app
app = FastAPI(
    title="AI Call Center Agent",
    description="An intelligent call center agent for handling customer service calls",
    version="1.0.0"
)

# Add middlewares
app.middleware("http")(file_size_limit_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add root route that redirects to docs
@app.get("/")
async def root():
    return RedirectResponse(url="/docs")

# Include API routes
app.include_router(api_router, prefix="/api")
app.include_router(orchestration_router, prefix="/api/orchestration")

# health & monitoring
@app.get("/health")
async def health():
    monitoring.track_request("/health", "GET", 200)
    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - app.state.start_time)
    }

@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    # Get Prometheus formatted metrics
    return monitoring.get_metrics()

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()
    # record start time for simple uptime metric
    app.state.start_time = time.time()
    # initialize monitoring and orchestration components
    init_monitoring(app)
    init_orchestration(app)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)