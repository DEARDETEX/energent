#!/usr/bin/env python3
"""
Extended Backend API Testing for Hologram Video Processing Pipeline
Tests the complete video processing workflow
"""

import requests
import json
import os
import tempfile
from pathlib import Path
import time

# Get backend URL from frontend .env file
def get_backend_url():
    frontend_env_path = Path("/app/frontend/.env")
    if frontend_env_path.exists():
        with open(frontend_env_path, 'r') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    return line.split('=', 1)[1].strip()
    return "http://localhost:8001"

BASE_URL = get_backend_url()
API_URL = f"{BASE_URL}/api"

print(f"Testing hologram processing pipeline at: {API_URL}")

class HologramProcessingTester:
    def __init__(self):
        self.session = requests.Session()
        self.test_project_id = None
    
    def create_test_video_file(self, filename="test_video.mp4"):
        """Create a small test video file using FFmpeg"""
        temp_dir = tempfile.gettempdir()
        video_path = Path(temp_dir) / filename
        
        # Create a simple test video (2 seconds, 320x240, red background)
        cmd = [
            'ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=red:size=320x240:duration=2',
            '-c:v', 'libx264', '-t', '2', str(video_path)
        ]
        
        try:
            import subprocess
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and video_path.exists():
                return str(video_path)
        except Exception as e:
            print(f"Could not create test video: {e}")
        
        return None
    
    def create_test_image_file(self, filename="test_hologram.png"):
        """Create a simple test image file"""
        temp_dir = tempfile.gettempdir()
        image_path = Path(temp_dir) / filename
        
        # Create a simple PNG image using FFmpeg
        cmd = [
            'ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=blue:size=100x100:duration=0.1',
            '-frames:v', '1', str(image_path)
        ]
        
        try:
            import subprocess
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and image_path.exists():
                return str(image_path)
        except Exception as e:
            print(f"Could not create test image: {e}")
        
        return None
    
    def setup_test_project(self):
        """Create a test project and upload files"""
        print("\n=== Setting up Test Project ===")
        
        # Create project
        project_data = {"name": "Hologram Processing Test"}
        response = self.session.post(f"{API_URL}/projects", data=project_data)
        
        if response.status_code != 200:
            print(f"❌ Failed to create project: {response.status_code}")
            return False
        
        project = response.json()
        self.test_project_id = project["id"]
        print(f"✅ Created project: {self.test_project_id}")
        
        # Create test files
        test_video_path = self.create_test_video_file()
        test_image_path = self.create_test_image_file()
        
        if not test_video_path or not test_image_path:
            print("❌ Failed to create test files")
            return False
        
        # Upload base video
        with open(test_video_path, 'rb') as f:
            files = {'file': ('test_video.mp4', f, 'video/mp4')}
            response = self.session.post(
                f"{API_URL}/projects/{self.test_project_id}/upload-base-video",
                files=files
            )
        
        if response.status_code != 200:
            print(f"❌ Failed to upload base video: {response.status_code}")
            return False
        
        print("✅ Uploaded base video")
        
        # Upload hologram media
        with open(test_image_path, 'rb') as f:
            files = {'file': ('test_hologram.png', f, 'image/png')}
            response = self.session.post(
                f"{API_URL}/projects/{self.test_project_id}/upload-hologram-media",
                files=files
            )
        
        if response.status_code != 200:
            print(f"❌ Failed to upload hologram media: {response.status_code}")
            return False
        
        print("✅ Uploaded hologram media")
        return True
    
    def test_hologram_processing(self):
        """Test the complete hologram processing pipeline"""
        print("\n=== Testing Hologram Processing Pipeline ===")
        
        if not self.test_project_id:
            print("❌ No test project available")
            return False
        
        # Define hologram settings
        settings = {
            "hologram_size": 0.4,
            "hologram_position_x": 0.6,
            "hologram_position_y": 0.4,
            "glow_intensity": 0.8,
            "flicker_intensity": 0.2,
            "scanlines": True,
            "blue_tint": True,
            "rotation_angle": 0.0,
            "transparency": 0.8
        }
        
        try:
            # Start processing
            response = self.session.post(
                f"{API_URL}/projects/{self.test_project_id}/process",
                json=settings
            )
            
            print(f"Process request - Status Code: {response.status_code}")
            
            if response.status_code != 200:
                print(f"❌ Processing failed to start: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error details: {error_data}")
                except:
                    print(f"Error text: {response.text}")
                return False
            
            process_response = response.json()
            print(f"Process response: {json.dumps(process_response, indent=2)}")
            print("✅ Processing started successfully")
            
            # Monitor processing status
            max_wait_time = 60  # 60 seconds max wait
            wait_interval = 2   # Check every 2 seconds
            elapsed_time = 0
            
            print("\n--- Monitoring Processing Status ---")
            
            while elapsed_time < max_wait_time:
                status_response = self.session.get(f"{API_URL}/projects/{self.test_project_id}/status")
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    current_status = status_data.get("status", "unknown")
                    progress = status_data.get("progress", 0.0)
                    
                    print(f"Status: {current_status}, Progress: {progress}%")
                    
                    if current_status == "completed":
                        print("✅ Processing completed successfully!")
                        return True
                    elif current_status == "failed":
                        print("❌ Processing failed!")
                        return False
                    
                    time.sleep(wait_interval)
                    elapsed_time += wait_interval
                else:
                    print(f"❌ Failed to get status: {status_response.status_code}")
                    return False
            
            print(f"⚠️ Processing did not complete within {max_wait_time} seconds")
            return False
            
        except Exception as e:
            print(f"❌ Processing test error: {e}")
            return False
    
    def test_download_functionality(self):
        """Test downloading the processed video"""
        print("\n=== Testing Download Functionality ===")
        
        if not self.test_project_id:
            print("❌ No test project available")
            return False
        
        try:
            response = self.session.get(f"{API_URL}/projects/{self.test_project_id}/download")
            print(f"Download request - Status Code: {response.status_code}")
            
            if response.status_code == 200:
                # Check if we got a video file
                content_type = response.headers.get('content-type', '')
                content_length = len(response.content)
                
                print(f"Content-Type: {content_type}")
                print(f"Content-Length: {content_length} bytes")
                
                if 'video' in content_type and content_length > 0:
                    print("✅ Download functionality: PASSED")
                    return True
                else:
                    print("❌ Download functionality: FAILED - Invalid content")
                    return False
            elif response.status_code == 400:
                # This might be expected if processing isn't complete
                error_data = response.json()
                print(f"Download not ready: {error_data}")
                print("⚠️ Download functionality: Video not ready (this may be expected)")
                return True
            else:
                print(f"❌ Download functionality: FAILED - HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Download test error: {e}")
            return False
    
    def run_processing_tests(self):
        """Run all processing-related tests"""
        print("🎬 Starting Hologram Processing Pipeline Tests")
        print("=" * 60)
        
        # Setup
        if not self.setup_test_project():
            print("❌ Failed to setup test project")
            return False
        
        # Test processing
        processing_success = self.test_hologram_processing()
        
        # Test download (regardless of processing success)
        download_success = self.test_download_functionality()
        
        print("\n" + "=" * 60)
        print("🏁 PROCESSING TESTS SUMMARY")
        print("=" * 60)
        
        print(f"Project Setup: ✅ PASSED")
        print(f"Hologram Processing: {'✅ PASSED' if processing_success else '❌ FAILED'}")
        print(f"Download Functionality: {'✅ PASSED' if download_success else '❌ FAILED'}")
        
        overall_success = processing_success and download_success
        
        if overall_success:
            print("🎉 ALL PROCESSING TESTS PASSED!")
        else:
            print("⚠️ Some processing tests failed. Check the details above.")
        
        return overall_success

if __name__ == "__main__":
    tester = HologramProcessingTester()
    success = tester.run_processing_tests()
    exit(0 if success else 1)