#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Hologram Video Compositor
Tests all critical API endpoints and functionality
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

print(f"Testing backend API at: {API_URL}")

class HologramAPITester:
    def __init__(self):
        self.session = requests.Session()
        self.test_project_id = None
        self.results = {
            "ffmpeg_detection": False,
            "project_creation": False,
            "project_retrieval": False,
            "base_video_upload": False,
            "hologram_media_upload": False,
            "status_tracking": False,
            "file_validation": False,
            "error_handling": False
        }
    
    def create_test_video_file(self, filename="test_video.mp4"):
        """Create a small test video file using FFmpeg if available"""
        temp_dir = tempfile.gettempdir()
        video_path = Path(temp_dir) / filename
        
        # Create a simple test video (1 second, 320x240, red background)
        cmd = [
            'ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=red:size=320x240:duration=1',
            '-c:v', 'libx264', '-t', '1', str(video_path)
        ]
        
        try:
            import subprocess
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and video_path.exists():
                return str(video_path)
        except Exception as e:
            print(f"Could not create test video: {e}")
        
        return None
    
    def create_test_image_file(self, filename="test_image.png"):
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
    
    def test_ffmpeg_detection(self):
        """Test 1: FFmpeg Detection via GET /api/"""
        print("\n=== Testing FFmpeg Detection ===")
        try:
            response = self.session.get(f"{API_URL}/")
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
                
                if "ffmpeg_available" in data:
                    ffmpeg_available = data["ffmpeg_available"]
                    print(f"FFmpeg Available: {ffmpeg_available}")
                    
                    if ffmpeg_available:
                        self.results["ffmpeg_detection"] = True
                        print("✅ FFmpeg detection: PASSED")
                        return True
                    else:
                        print("❌ FFmpeg detection: FAILED - FFmpeg not available")
                        return False
                else:
                    print("❌ FFmpeg detection: FAILED - ffmpeg_available field missing")
                    return False
            else:
                print(f"❌ FFmpeg detection: FAILED - HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ FFmpeg detection: ERROR - {e}")
            return False
    
    def test_project_creation(self):
        """Test 2: Project Creation via POST /api/projects"""
        print("\n=== Testing Project Creation ===")
        try:
            project_data = {"name": "Hologram Test Project"}
            response = self.session.post(f"{API_URL}/projects", data=project_data)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
                
                if "id" in data and "name" in data:
                    self.test_project_id = data["id"]
                    print(f"Project ID: {self.test_project_id}")
                    self.results["project_creation"] = True
                    print("✅ Project creation: PASSED")
                    return True
                else:
                    print("❌ Project creation: FAILED - Missing required fields")
                    return False
            else:
                print(f"❌ Project creation: FAILED - HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error details: {error_data}")
                except:
                    print(f"Error text: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Project creation: ERROR - {e}")
            return False
    
    def test_project_retrieval(self):
        """Test 3: Project Retrieval"""
        print("\n=== Testing Project Retrieval ===")
        
        # Test getting all projects
        try:
            response = self.session.get(f"{API_URL}/projects")
            print(f"Get all projects - Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Projects count: {len(data)}")
                if len(data) > 0:
                    print("✅ Get all projects: PASSED")
                else:
                    print("⚠️ Get all projects: No projects found")
            else:
                print(f"❌ Get all projects: FAILED - HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Get all projects: ERROR - {e}")
            return False
        
        # Test getting specific project
        if self.test_project_id:
            try:
                response = self.session.get(f"{API_URL}/projects/{self.test_project_id}")
                print(f"Get specific project - Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"Project data: {json.dumps(data, indent=2)}")
                    self.results["project_retrieval"] = True
                    print("✅ Project retrieval: PASSED")
                    return True
                else:
                    print(f"❌ Get specific project: FAILED - HTTP {response.status_code}")
                    return False
            except Exception as e:
                print(f"❌ Get specific project: ERROR - {e}")
                return False
        else:
            print("❌ Project retrieval: FAILED - No test project ID available")
            return False
    
    def test_file_uploads(self):
        """Test 4: File Upload System"""
        print("\n=== Testing File Upload System ===")
        
        if not self.test_project_id:
            print("❌ File uploads: FAILED - No test project available")
            return False
        
        # Create test files
        test_video_path = self.create_test_video_file()
        test_image_path = self.create_test_image_file()
        
        if not test_video_path:
            print("❌ File uploads: FAILED - Could not create test video file")
            return False
        
        if not test_image_path:
            print("❌ File uploads: FAILED - Could not create test image file")
            return False
        
        # Test base video upload
        try:
            with open(test_video_path, 'rb') as f:
                files = {'file': ('test_video.mp4', f, 'video/mp4')}
                response = self.session.post(
                    f"{API_URL}/projects/{self.test_project_id}/upload-base-video",
                    files=files
                )
            
            print(f"Base video upload - Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Base video upload response: {json.dumps(data, indent=2)}")
                self.results["base_video_upload"] = True
                print("✅ Base video upload: PASSED")
            else:
                print(f"❌ Base video upload: FAILED - HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error details: {error_data}")
                except:
                    print(f"Error text: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Base video upload: ERROR - {e}")
            return False
        
        # Test hologram media upload
        try:
            with open(test_image_path, 'rb') as f:
                files = {'file': ('test_image.png', f, 'image/png')}
                response = self.session.post(
                    f"{API_URL}/projects/{self.test_project_id}/upload-hologram-media",
                    files=files
                )
            
            print(f"Hologram media upload - Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Hologram media upload response: {json.dumps(data, indent=2)}")
                self.results["hologram_media_upload"] = True
                print("✅ Hologram media upload: PASSED")
                return True
            else:
                print(f"❌ Hologram media upload: FAILED - HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error details: {error_data}")
                except:
                    print(f"Error text: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Hologram media upload: ERROR - {e}")
            return False
    
    def test_file_validation(self):
        """Test 5: File Upload Validation"""
        print("\n=== Testing File Upload Validation ===")
        
        if not self.test_project_id:
            print("❌ File validation: FAILED - No test project available")
            return False
        
        # Create a text file to test validation
        temp_dir = tempfile.gettempdir()
        text_file_path = Path(temp_dir) / "test.txt"
        with open(text_file_path, 'w') as f:
            f.write("This is not a video or image file")
        
        try:
            # Test uploading invalid file type to base video endpoint
            with open(text_file_path, 'rb') as f:
                files = {'file': ('test.txt', f, 'text/plain')}
                response = self.session.post(
                    f"{API_URL}/projects/{self.test_project_id}/upload-base-video",
                    files=files
                )
            
            print(f"Invalid base video upload - Status Code: {response.status_code}")
            
            if response.status_code == 400:
                print("✅ Base video validation: PASSED - Correctly rejected non-video file")
            else:
                print(f"❌ Base video validation: FAILED - Should reject non-video files")
                return False
            
            # Test uploading invalid file type to hologram media endpoint
            with open(text_file_path, 'rb') as f:
                files = {'file': ('test.txt', f, 'text/plain')}
                response = self.session.post(
                    f"{API_URL}/projects/{self.test_project_id}/upload-hologram-media",
                    files=files
                )
            
            print(f"Invalid hologram media upload - Status Code: {response.status_code}")
            
            if response.status_code == 400:
                self.results["file_validation"] = True
                print("✅ Hologram media validation: PASSED - Correctly rejected invalid file")
                return True
            else:
                print(f"❌ Hologram media validation: FAILED - Should reject invalid files")
                return False
                
        except Exception as e:
            print(f"❌ File validation: ERROR - {e}")
            return False
        finally:
            # Clean up test file
            if text_file_path.exists():
                text_file_path.unlink()
    
    def test_status_tracking(self):
        """Test 6: Status Tracking"""
        print("\n=== Testing Status Tracking ===")
        
        if not self.test_project_id:
            print("❌ Status tracking: FAILED - No test project available")
            return False
        
        try:
            response = self.session.get(f"{API_URL}/projects/{self.test_project_id}/status")
            print(f"Status tracking - Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Status response: {json.dumps(data, indent=2)}")
                
                required_fields = ["project_id", "status", "progress", "message"]
                if all(field in data for field in required_fields):
                    self.results["status_tracking"] = True
                    print("✅ Status tracking: PASSED")
                    return True
                else:
                    print("❌ Status tracking: FAILED - Missing required fields")
                    return False
            else:
                print(f"❌ Status tracking: FAILED - HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Status tracking: ERROR - {e}")
            return False
    
    def test_error_handling(self):
        """Test 7: Error Handling"""
        print("\n=== Testing Error Handling ===")
        
        try:
            # Test getting non-existent project
            fake_project_id = "non-existent-project-id"
            response = self.session.get(f"{API_URL}/projects/{fake_project_id}")
            print(f"Non-existent project - Status Code: {response.status_code}")
            
            if response.status_code == 404:
                print("✅ Error handling: PASSED - Correctly returns 404 for non-existent project")
                self.results["error_handling"] = True
                return True
            else:
                print(f"❌ Error handling: FAILED - Should return 404 for non-existent project")
                return False
                
        except Exception as e:
            print(f"❌ Error handling: ERROR - {e}")
            return False
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting Hologram Video Compositor Backend API Tests")
        print("=" * 60)
        
        tests = [
            ("FFmpeg Detection", self.test_ffmpeg_detection),
            ("Project Creation", self.test_project_creation),
            ("Project Retrieval", self.test_project_retrieval),
            ("File Uploads", self.test_file_uploads),
            ("File Validation", self.test_file_validation),
            ("Status Tracking", self.test_status_tracking),
            ("Error Handling", self.test_error_handling)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed_tests += 1
            except Exception as e:
                print(f"❌ {test_name}: CRITICAL ERROR - {e}")
        
        print("\n" + "=" * 60)
        print("🏁 TEST SUMMARY")
        print("=" * 60)
        
        for key, value in self.results.items():
            status = "✅ PASSED" if value else "❌ FAILED"
            print(f"{key.replace('_', ' ').title()}: {status}")
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED!")
            return True
        else:
            print("⚠️ Some tests failed. Check the details above.")
            return False

if __name__ == "__main__":
    tester = HologramAPITester()
    success = tester.run_all_tests()
    exit(0 if success else 1)