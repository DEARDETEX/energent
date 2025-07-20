from fastapi import FastAPI, APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import asyncio
import json


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create uploads directory
UPLOADS_DIR = ROOT_DIR / "uploads"
PROCESSED_DIR = ROOT_DIR / "processed"
UPLOADS_DIR.mkdir(exist_ok=True)
PROCESSED_DIR.mkdir(exist_ok=True)

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class HologramProject(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    base_video_path: Optional[str] = None
    base_video_filename: Optional[str] = None
    base_video_size: Optional[int] = None
    hologram_media_path: Optional[str] = None
    hologram_media_filename: Optional[str] = None
    hologram_media_size: Optional[int] = None
    hologram_media_type: Optional[str] = None
    settings: dict = Field(default_factory=dict)
    status: str = "created"  # created, processing, completed, failed
    output_path: Optional[str] = None
    output_size: Optional[int] = None
    error_message: Optional[str] = None
    processing_progress: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class HologramSettings(BaseModel):
    hologram_size: float = 0.3  # 0.1 to 1.0
    hologram_position_x: float = 0.5  # 0.0 to 1.0
    hologram_position_y: float = 0.5  # 0.0 to 1.0
    glow_intensity: float = 0.7  # 0.0 to 1.0
    flicker_intensity: float = 0.3  # 0.0 to 1.0
    scanlines: bool = True
    blue_tint: bool = True
    rotation_angle: float = 0.0  # -45 to 45 degrees
    transparency: float = 0.7  # 0.0 to 1.0

class ProcessingStatus(BaseModel):
    project_id: str
    status: str
    progress: float = 0.0
    message: str = ""
    error_message: Optional[str] = None

class SystemStatus(BaseModel):
    message: str
    ffmpeg_available: bool
    ffmpeg_version: Optional[str] = None
    uploads_directory: str
    processed_directory: str
    total_projects: int = 0


# Video processing functions
def check_ffmpeg():
    """Check if FFmpeg is installed and get version info"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            # Extract version from output
            lines = result.stdout.split('\n')
            version_line = next((line for line in lines if line.startswith('ffmpeg version')), '')
            return True, version_line.split(' ')[2] if version_line else 'Unknown'
        return False, None
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        logger.error(f"FFmpeg check failed: {e}")
        return False, None

def get_video_info(video_path):
    """Get video information using FFprobe"""
    cmd = [
        'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams',
        str(video_path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return json.loads(result.stdout)
        logger.error(f"FFprobe failed: {result.stderr}")
        return None
    except Exception as e:
        logger.error(f"Error getting video info: {e}")
        return None

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    return f"{size_bytes:.1f} {size_names[i]}"

async def update_progress(project_id: str, progress: float, message: str):
    """Update processing progress"""
    await db.hologram_projects.update_one(
        {"id": project_id},
        {
            "$set": {
                "processing_progress": progress,
                "updated_at": datetime.utcnow()
            }
        }
    )
    logger.info(f"Project {project_id}: {progress:.1f}% - {message}")

async def process_hologram_video(project_id: str, base_video_path: str, hologram_media_path: str, settings: HologramSettings):
    """Process video with hologram effects using FFmpeg"""
    try:
        # Update project status
        await db.hologram_projects.update_one(
            {"id": project_id},
            {"$set": {"status": "processing", "processing_progress": 0.0, "updated_at": datetime.utcnow()}}
        )
        
        output_filename = f"hologram_{project_id}.mp4"
        output_path = PROCESSED_DIR / output_filename
        
        await update_progress(project_id, 10.0, "Analyzing input videos...")
        
        # Get video info
        base_video_info = get_video_info(base_video_path)
        if not base_video_info:
            raise Exception("Could not get base video information")
        
        # Find video stream
        video_stream = next((s for s in base_video_info['streams'] if s['codec_type'] == 'video'), None)
        if not video_stream:
            raise Exception("No video stream found in base video")
        
        base_width = int(video_stream['width'])
        base_height = int(video_stream['height'])
        
        await update_progress(project_id, 25.0, "Calculating hologram dimensions...")
        
        # Calculate hologram dimensions and position
        hologram_width = int(base_width * settings.hologram_size)
        hologram_height = int(base_height * settings.hologram_size)
        
        hologram_x = int((base_width - hologram_width) * settings.hologram_position_x)
        hologram_y = int((base_height - hologram_height) * settings.hologram_position_y)
        
        await update_progress(project_id, 40.0, "Building hologram effects pipeline...")
        
        # Create complex FFmpeg filter for hologram effect
        filter_complex = []
        
        # Scale and position hologram media
        filter_complex.append(f"[1:v]scale={hologram_width}:{hologram_height}[scaled]")
        
        # Add blue tint if enabled
        if settings.blue_tint:
            filter_complex.append("[scaled]colorbalance=rm=-0.3:gm=-0.2:bm=0.5[tinted]")
            last_filter = "tinted"
        else:
            last_filter = "scaled"
        
        # Add transparency
        filter_complex.append(f"[{last_filter}]format=rgba,colorchannelmixer=aa={settings.transparency}[transparent]")
        last_filter = "transparent"
        
        # Add glow effect
        if settings.glow_intensity > 0:
            glow_radius = max(2, int(settings.glow_intensity * 10))
            filter_complex.append(f"[{last_filter}]split[glow_input][main]")
            filter_complex.append(f"[glow_input]boxblur={glow_radius}:1[glow]")
            filter_complex.append(f"[glow][main]overlay[glowed]")
            last_filter = "glowed"
        
        # Add scanlines if enabled
        if settings.scanlines:
            scanline_height = max(2, hologram_height // 100)
            filter_complex.append(f"[{last_filter}]drawgrid=w=iw:h={scanline_height}:t=1:c=cyan@0.3[scanlined]")
            last_filter = "scanlined"
        
        # Add flicker effect using a simpler approach
        if settings.flicker_intensity > 0:
            # Use colorchannelmixer to create flicker effect
            alpha_value = 1.0 - (settings.flicker_intensity * 0.3)  # Reduce flicker intensity
            filter_complex.append(f"[{last_filter}]colorchannelmixer=aa={alpha_value}[flickered]")
            last_filter = "flickered"
        
        # Overlay on base video
        filter_complex.append(f"[0:v][{last_filter}]overlay={hologram_x}:{hologram_y}:enable='gte(t,0)'[output]")
        
        await update_progress(project_id, 60.0, "Starting video processing...")
        
        # Build FFmpeg command
        cmd = [
            'ffmpeg', '-y',
            '-i', str(base_video_path),
            '-i', str(hologram_media_path),
            '-filter_complex', ';'.join(filter_complex),
            '-map', '[output]',
            '-map', '0:a?',  # Copy audio if it exists
            '-c:a', 'copy',
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            str(output_path)
        ]
        
        logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
        
        await update_progress(project_id, 80.0, "Rendering hologram video...")
        
        # Run FFmpeg
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            logger.error(f"FFmpeg error: {stderr}")
            raise Exception(f"Video processing failed: {stderr}")
        
        await update_progress(project_id, 95.0, "Finalizing output...")
        
        # Get output file size
        output_size = output_path.stat().st_size if output_path.exists() else 0
        
        # Update project with success
        await db.hologram_projects.update_one(
            {"id": project_id},
            {
                "$set": {
                    "status": "completed",
                    "output_path": str(output_path),
                    "output_size": output_size,
                    "processing_progress": 100.0,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        logger.info(f"Successfully processed hologram video: {output_path} ({format_file_size(output_size)})")
        return str(output_path)
        
    except Exception as e:
        logger.error(f"Error processing hologram video: {e}")
        await db.hologram_projects.update_one(
            {"id": project_id},
            {
                "$set": {
                    "status": "failed",
                    "error_message": str(e),
                    "processing_progress": 0.0,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        raise


# API Routes
@api_router.get("/", response_model=SystemStatus)
async def get_system_status():
    """Get system status including FFmpeg availability"""
    ffmpeg_available, ffmpeg_version = check_ffmpeg()
    
    # Get total project count
    total_projects = await db.hologram_projects.count_documents({})
    
    return SystemStatus(
        message="Hologram Video Compositor API",
        ffmpeg_available=ffmpeg_available,
        ffmpeg_version=ffmpeg_version,
        uploads_directory=str(UPLOADS_DIR),
        processed_directory=str(PROCESSED_DIR),
        total_projects=total_projects
    )

@api_router.post("/projects", response_model=HologramProject)
async def create_project(name: str = Form(...)):
    """Create a new hologram project"""
    project = HologramProject(name=name)
    await db.hologram_projects.insert_one(project.dict())
    return project

@api_router.get("/projects", response_model=List[HologramProject])
async def get_projects():
    """Get all projects"""
    projects = await db.hologram_projects.find().sort("created_at", -1).to_list(100)
    return [HologramProject(**project) for project in projects]

@api_router.get("/projects/{project_id}", response_model=HologramProject)
async def get_project(project_id: str):
    """Get a specific project"""
    project = await db.hologram_projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return HologramProject(**project)

@api_router.post("/projects/{project_id}/upload-base-video")
async def upload_base_video(project_id: str, file: UploadFile = File(...)):
    """Upload base video for a project"""
    project = await db.hologram_projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith('video/'):
        raise HTTPException(status_code=400, detail="File must be a video")
    
    # Validate file size (max 100MB)
    if file.size and file.size > 100 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Video file too large (max 100MB)")
    
    # Save file
    file_extension = Path(file.filename).suffix
    filename = f"base_{project_id}{file_extension}"
    file_path = UPLOADS_DIR / filename
    
    # Write file in chunks
    with open(file_path, "wb") as buffer:
        while chunk := await file.read(8192):  # Read in 8KB chunks
            buffer.write(chunk)
    
    file_size = file_path.stat().st_size
    
    # Update project
    await db.hologram_projects.update_one(
        {"id": project_id},
        {
            "$set": {
                "base_video_path": str(file_path),
                "base_video_filename": file.filename,
                "base_video_size": file_size,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return {
        "message": "Base video uploaded successfully",
        "filename": file.filename,
        "size": format_file_size(file_size),
        "path": filename
    }

@api_router.post("/projects/{project_id}/upload-hologram-media")
async def upload_hologram_media(project_id: str, file: UploadFile = File(...)):
    """Upload hologram media (image or video) for a project"""
    project = await db.hologram_projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Validate file type
    if not file.content_type or not (file.content_type.startswith('video/') or file.content_type.startswith('image/')):
        raise HTTPException(status_code=400, detail="File must be a video or image")
    
    # Validate file size (max 50MB)
    if file.size and file.size > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Media file too large (max 50MB)")
    
    # Save file
    file_extension = Path(file.filename).suffix
    filename = f"hologram_{project_id}{file_extension}"
    file_path = UPLOADS_DIR / filename
    
    # Write file in chunks
    with open(file_path, "wb") as buffer:
        while chunk := await file.read(8192):  # Read in 8KB chunks
            buffer.write(chunk)
    
    file_size = file_path.stat().st_size
    
    # Update project
    await db.hologram_projects.update_one(
        {"id": project_id},
        {
            "$set": {
                "hologram_media_path": str(file_path),
                "hologram_media_filename": file.filename,
                "hologram_media_size": file_size,
                "hologram_media_type": file.content_type,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return {
        "message": "Hologram media uploaded successfully",
        "filename": file.filename,
        "size": format_file_size(file_size),
        "type": file.content_type,
        "path": filename
    }

@api_router.post("/projects/{project_id}/process")
async def process_project(
    background_tasks: BackgroundTasks,
    project_id: str,
    settings: HologramSettings = HologramSettings()
):
    """Process the hologram video with given settings"""
    project = await db.hologram_projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_obj = HologramProject(**project)
    
    if not project_obj.base_video_path or not project_obj.hologram_media_path:
        raise HTTPException(
            status_code=400,
            detail="Both base video and hologram media must be uploaded before processing"
        )
    
    if project_obj.status == "processing":
        raise HTTPException(status_code=400, detail="Project is already being processed")
    
    # Check FFmpeg availability
    ffmpeg_available, _ = check_ffmpeg()
    if not ffmpeg_available:
        raise HTTPException(status_code=503, detail="FFmpeg is not available. Cannot process video.")
    
    # Update project settings
    await db.hologram_projects.update_one(
        {"id": project_id},
        {"$set": {"settings": settings.dict(), "updated_at": datetime.utcnow()}}
    )
    
    # Start processing in background
    background_tasks.add_task(
        process_hologram_video,
        project_id,
        project_obj.base_video_path,
        project_obj.hologram_media_path,
        settings
    )
    
    return {
        "message": "Processing started",
        "project_id": project_id,
        "settings": settings.dict()
    }

@api_router.get("/projects/{project_id}/status", response_model=ProcessingStatus)
async def get_processing_status(project_id: str):
    """Get processing status for a project"""
    project = await db.hologram_projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_obj = HologramProject(**project)
    
    # Determine message based on status
    if project_obj.status == "created":
        message = "Project created, ready for processing"
    elif project_obj.status == "processing":
        message = f"Processing... {project_obj.processing_progress:.1f}% complete"
    elif project_obj.status == "completed":
        output_size = format_file_size(project_obj.output_size) if project_obj.output_size else "Unknown"
        message = f"Processing completed! Output file size: {output_size}"
    elif project_obj.status == "failed":
        message = f"Processing failed: {project_obj.error_message or 'Unknown error'}"
    else:
        message = f"Status: {project_obj.status}"
    
    return ProcessingStatus(
        project_id=project_id,
        status=project_obj.status,
        progress=project_obj.processing_progress,
        message=message,
        error_message=project_obj.error_message
    )

@api_router.get("/projects/{project_id}/download")
async def download_processed_video(project_id: str):
    """Download the processed hologram video"""
    project = await db.hologram_projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_obj = HologramProject(**project)
    
    if project_obj.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Video is not ready for download. Current status: {project_obj.status}"
        )
    
    if not project_obj.output_path:
        raise HTTPException(status_code=404, detail="Output file path not found")
    
    output_path = Path(project_obj.output_path)
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Processed video file not found on disk")
    
    return FileResponse(
        str(output_path),
        media_type='video/mp4',
        filename=f"hologram_{project_obj.name.replace(' ', '_')}_{project_id[:8]}.mp4",
        headers={
            "Content-Disposition": f"attachment; filename=hologram_{project_obj.name.replace(' ', '_')}_{project_id[:8]}.mp4"
        }
    )


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()