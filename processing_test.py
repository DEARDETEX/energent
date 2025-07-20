#!/usr/bin/env python3
"""
Complete Processing Pipeline Test for Hologram Video Compositor
Tests the full workflow: Create → Upload → Process → Status → Download
"""

import requests
import json
import os
import tempfile
from pathlib import Path
import time
import subprocess

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

print(f"Testing complete processing pipeline at: {API_URL}")

class ProcessingPipelineTester:
    def __init__(self):
        self.session = requests.Session()
        self.project_id = None
    
    def create_test_files(self):
        """Create test video and image files"""
        temp_dir = tempfile.gettempdir()
        
        # Create a longer test video (3 seconds, 640x480)
        video_path = Path(temp_dir) / "test_base_video.mp4"
        video_cmd = [
            'ffmpeg', '-y', '-f', 'lavfi', 
            '-i', 'color=green:size=640x480:duration=3',
            '-c:v', 'libx264', '-t', '3', str(video_path)
        ]
        
        # Create test hologram image (blue square)
        image_path = Path(temp_dir) / "test_hologram.png"
        image_cmd = [
            'ffmpeg', '-y', '-f', 'lavfi', 
            '-i', 'color=blue:size=200x200:duration=0.1',
            '-frames:v', '1', str(image_path)
        ]
        
        try:
            # Create video
            result = subprocess.run(video_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Failed to create test video: {result.stderr}")
                return None, None
            
            # Create image
            result = subprocess.run(image_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Failed to create test image: {result.stderr}")
                return None, None
            
            return str(video_path), str(image_path)
            
        except Exception as e:
            print(f"Error creating test files: {e}")
            return None, None
    
    def test_complete_pipeline(self):
        """Test the complete processing pipeline"""
        print("\n🎬 TESTING COMPLETE PROCESSING PIPELINE")
        print("=" * 60)
        
        # Step 1: Create project
        print("\n📝 Step 1: Creating project...")
        try:
            response = self.session.post(f"{API_URL}/projects", data={"name": "Pipeline Test Project"})
            if response.status_code != 200:
                print(f"❌ Project creation failed: {response.status_code}")
                return False
            
            project_data = response.json()
            self.project_id = project_data["id"]
            print(f"✅ Project created: {self.project_id}")
            
        except Exception as e:
            print(f"❌ Project creation error: {e}")
            return False
        
        # Step 2: Create test files
        print("\n📁 Step 2: Creating test files...")
        video_path, image_path = self.create_test_files()
        if not video_path or not image_path:
            print("❌ Failed to create test files")
            return False
        print(f"✅ Test files created: {Path(video_path).name}, {Path(image_path).name}")
        
        # Step 3: Upload base video
        print("\n📤 Step 3: Uploading base video...")
        try:
            with open(video_path, 'rb') as f:
                files = {'file': ('test_base_video.mp4', f, 'video/mp4')}
                response = self.session.post(
                    f"{API_URL}/projects/{self.project_id}/upload-base-video",
                    files=files
                )
            
            if response.status_code != 200:
                print(f"❌ Base video upload failed: {response.status_code}")
                return False
            
            upload_data = response.json()
            print(f"✅ Base video uploaded: {upload_data['size']}")
            
        except Exception as e:
            print(f"❌ Base video upload error: {e}")
            return False
        
        # Step 4: Upload hologram media
        print("\n📤 Step 4: Uploading hologram media...")
        try:
            with open(image_path, 'rb') as f:
                files = {'file': ('test_hologram.png', f, 'image/png')}
                response = self.session.post(
                    f"{API_URL}/projects/{self.project_id}/upload-hologram-media",
                    files=files
                )
            
            if response.status_code != 200:
                print(f"❌ Hologram media upload failed: {response.status_code}")
                return False
            
            upload_data = response.json()
            print(f"✅ Hologram media uploaded: {upload_data['size']}")
            
        except Exception as e:
            print(f"❌ Hologram media upload error: {e}")
            return False
        
        # Step 5: Start processing with custom settings
        print("\n⚙️ Step 5: Starting processing with hologram settings...")
        try:
            settings = {
                "hologram_size": 0.4,
                "hologram_position_x": 0.7,
                "hologram_position_y": 0.3,
                "glow_intensity": 0.8,
                "flicker_intensity": 0.4,
                "scanlines": True,
                "blue_tint": True,
                "transparency": 0.8
            }
            
            response = self.session.post(
                f"{API_URL}/projects/{self.project_id}/process",
                json=settings
            )
            
            if response.status_code != 200:
                print(f"❌ Processing start failed: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error details: {error_data}")
                except:
                    print(f"Error text: {response.text}")
                return False
            
            process_data = response.json()
            print(f"✅ Processing started: {process_data['message']}")
            
        except Exception as e:
            print(f"❌ Processing start error: {e}")
            return False
        
        # Step 6: Monitor processing status
        print("\n📊 Step 6: Monitoring processing status...")
        max_wait_time = 120  # 2 minutes max
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                response = self.session.get(f"{API_URL}/projects/{self.project_id}/status")
                if response.status_code != 200:
                    print(f"❌ Status check failed: {response.status_code}")
                    return False
                
                status_data = response.json()
                status = status_data["status"]
                progress = status_data["progress"]
                message = status_data["message"]
                
                print(f"📈 Status: {status} | Progress: {progress:.1f}% | {message}")
                
                if status == "completed":
                    print("✅ Processing completed successfully!")
                    break
                elif status == "failed":
                    error_msg = status_data.get("error_message", "Unknown error")
                    print(f"❌ Processing failed: {error_msg}")
                    return False
                
                time.sleep(3)  # Wait 3 seconds before next check
                
            except Exception as e:
                print(f"❌ Status monitoring error: {e}")
                return False
        else:
            print("❌ Processing timed out")
            return False
        
        # Step 7: Test download
        print("\n📥 Step 7: Testing download...")
        try:
            response = self.session.get(f"{API_URL}/projects/{self.project_id}/download")
            
            if response.status_code != 200:
                print(f"❌ Download failed: {response.status_code}")
                return False
            
            # Check if we got video content
            content_type = response.headers.get('content-type', '')
            content_length = len(response.content)
            
            print(f"✅ Download successful!")
            print(f"   Content-Type: {content_type}")
            print(f"   File Size: {content_length} bytes")
            
            # Save the downloaded file for verification
            output_path = Path(tempfile.gettempdir()) / f"downloaded_hologram_{self.project_id[:8]}.mp4"
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            print(f"   Saved to: {output_path}")
            
            if content_length > 1000:  # Should be more than 1KB for a real video
                print("✅ Downloaded file appears to be a valid video")
                return True
            else:
                print("⚠️ Downloaded file seems too small")
                return False
            
        except Exception as e:
            print(f"❌ Download error: {e}")
            return False
    
    def run_test(self):
        """Run the complete pipeline test"""
        success = self.test_complete_pipeline()
        
        print("\n" + "=" * 60)
        print("🏁 PROCESSING PIPELINE TEST SUMMARY")
        print("=" * 60)
        
        if success:
            print("🎉 COMPLETE PIPELINE TEST PASSED!")
            print("✅ All steps completed successfully:")
            print("   • Project creation")
            print("   • File uploads (base video + hologram media)")
            print("   • Processing with hologram effects")
            print("   • Status tracking and progress monitoring")
            print("   • Video download")
            return True
        else:
            print("❌ PIPELINE TEST FAILED!")
            print("⚠️ Check the detailed logs above for specific failures")
            return False

if __name__ == "__main__":
    tester = ProcessingPipelineTester()
    success = tester.run_test()
    exit(0 if success else 1)