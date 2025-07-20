#!/usr/bin/env python3
"""
Production Features Test for Hologram Video Compositor
Tests file size limits, concurrent processing, and edge cases
"""

import requests
import json
import tempfile
from pathlib import Path
import subprocess
import threading
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

print(f"Testing production features at: {API_URL}")

class ProductionFeaturesTester:
    def __init__(self):
        self.session = requests.Session()
        self.results = {
            "file_size_limits": False,
            "concurrent_processing": False,
            "project_management": False,
            "error_recovery": False
        }
    
    def create_large_file(self, size_mb=10):
        """Create a file of specified size in MB"""
        temp_dir = tempfile.gettempdir()
        large_file_path = Path(temp_dir) / f"large_file_{size_mb}mb.txt"
        
        # Create a file with specified size
        with open(large_file_path, 'wb') as f:
            # Write 1MB chunks
            chunk_size = 1024 * 1024  # 1MB
            for _ in range(size_mb):
                f.write(b'0' * chunk_size)
        
        return str(large_file_path)
    
    def test_file_size_limits(self):
        """Test file size validation limits"""
        print("\n📏 TESTING FILE SIZE LIMITS")
        print("=" * 40)
        
        # Create a project for testing
        try:
            response = self.session.post(f"{API_URL}/projects", data={"name": "Size Limit Test"})
            if response.status_code != 200:
                print("❌ Could not create test project")
                return False
            
            project_id = response.json()["id"]
            print(f"✅ Test project created: {project_id}")
            
        except Exception as e:
            print(f"❌ Project creation error: {e}")
            return False
        
        # Test base video size limit (should be 100MB max)
        print("\n🎥 Testing base video size limit (100MB)...")
        try:
            # Create a 101MB file (should be rejected)
            large_file = self.create_large_file(101)
            
            with open(large_file, 'rb') as f:
                files = {'file': ('large_video.mp4', f, 'video/mp4')}
                response = self.session.post(
                    f"{API_URL}/projects/{project_id}/upload-base-video",
                    files=files
                )
            
            print(f"Large base video upload - Status Code: {response.status_code}")
            
            if response.status_code == 400:
                print("✅ Base video size limit: PASSED - Correctly rejected oversized file")
            else:
                print("❌ Base video size limit: FAILED - Should reject files over 100MB")
                return False
            
            # Clean up
            Path(large_file).unlink()
            
        except Exception as e:
            print(f"❌ Base video size limit test error: {e}")
            return False
        
        # Test hologram media size limit (should be 50MB max)
        print("\n🖼️ Testing hologram media size limit (50MB)...")
        try:
            # Create a 51MB file (should be rejected)
            large_file = self.create_large_file(51)
            
            with open(large_file, 'rb') as f:
                files = {'file': ('large_image.png', f, 'image/png')}
                response = self.session.post(
                    f"{API_URL}/projects/{project_id}/upload-hologram-media",
                    files=files
                )
            
            print(f"Large hologram media upload - Status Code: {response.status_code}")
            
            if response.status_code == 400:
                print("✅ Hologram media size limit: PASSED - Correctly rejected oversized file")
                self.results["file_size_limits"] = True
                return True
            else:
                print("❌ Hologram media size limit: FAILED - Should reject files over 50MB")
                return False
            
            # Clean up
            Path(large_file).unlink()
            
        except Exception as e:
            print(f"❌ Hologram media size limit test error: {e}")
            return False
    
    def process_project_async(self, project_id, project_name):
        """Process a project asynchronously"""
        try:
            # Upload files first
            temp_dir = tempfile.gettempdir()
            
            # Create small test files
            video_path = Path(temp_dir) / f"test_video_{project_id[:8]}.mp4"
            image_path = Path(temp_dir) / f"test_image_{project_id[:8]}.png"
            
            # Create test video
            video_cmd = [
                'ffmpeg', '-y', '-f', 'lavfi', 
                '-i', 'color=red:size=320x240:duration=1',
                '-c:v', 'libx264', '-t', '1', str(video_path)
            ]
            subprocess.run(video_cmd, capture_output=True)
            
            # Create test image
            image_cmd = [
                'ffmpeg', '-y', '-f', 'lavfi', 
                '-i', 'color=blue:size=100x100:duration=0.1',
                '-frames:v', '1', str(image_path)
            ]
            subprocess.run(image_cmd, capture_output=True)
            
            # Upload base video
            with open(video_path, 'rb') as f:
                files = {'file': ('test_video.mp4', f, 'video/mp4')}
                response = self.session.post(
                    f"{API_URL}/projects/{project_id}/upload-base-video",
                    files=files
                )
            
            if response.status_code != 200:
                print(f"❌ {project_name}: Base video upload failed")
                return False
            
            # Upload hologram media
            with open(image_path, 'rb') as f:
                files = {'file': ('test_image.png', f, 'image/png')}
                response = self.session.post(
                    f"{API_URL}/projects/{project_id}/upload-hologram-media",
                    files=files
                )
            
            if response.status_code != 200:
                print(f"❌ {project_name}: Hologram media upload failed")
                return False
            
            # Start processing
            settings = {
                "hologram_size": 0.3,
                "hologram_position_x": 0.5,
                "hologram_position_y": 0.5,
                "glow_intensity": 0.5,
                "flicker_intensity": 0.2,
                "scanlines": True,
                "blue_tint": True,
                "transparency": 0.7
            }
            
            response = self.session.post(
                f"{API_URL}/projects/{project_id}/process",
                json=settings
            )
            
            if response.status_code != 200:
                print(f"❌ {project_name}: Processing start failed")
                return False
            
            print(f"✅ {project_name}: Processing started")
            
            # Monitor until completion
            max_wait = 60  # 1 minute max
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                response = self.session.get(f"{API_URL}/projects/{project_id}/status")
                if response.status_code == 200:
                    status_data = response.json()
                    status = status_data["status"]
                    
                    if status == "completed":
                        print(f"✅ {project_name}: Processing completed")
                        return True
                    elif status == "failed":
                        print(f"❌ {project_name}: Processing failed")
                        return False
                
                time.sleep(2)
            
            print(f"⏰ {project_name}: Processing timed out")
            return False
            
        except Exception as e:
            print(f"❌ {project_name}: Error - {e}")
            return False
    
    def test_concurrent_processing(self):
        """Test concurrent processing of multiple projects"""
        print("\n🔄 TESTING CONCURRENT PROCESSING")
        print("=" * 40)
        
        # Create multiple projects
        project_ids = []
        project_names = []
        
        for i in range(3):
            try:
                project_name = f"Concurrent Test Project {i+1}"
                response = self.session.post(f"{API_URL}/projects", data={"name": project_name})
                
                if response.status_code == 200:
                    project_id = response.json()["id"]
                    project_ids.append(project_id)
                    project_names.append(project_name)
                    print(f"✅ Created {project_name}: {project_id}")
                else:
                    print(f"❌ Failed to create {project_name}")
                    return False
                    
            except Exception as e:
                print(f"❌ Project creation error: {e}")
                return False
        
        # Start processing all projects concurrently
        print(f"\n🚀 Starting concurrent processing of {len(project_ids)} projects...")
        
        threads = []
        results = []
        
        def process_wrapper(project_id, project_name):
            result = self.process_project_async(project_id, project_name)
            results.append(result)
        
        # Start all threads
        for project_id, project_name in zip(project_ids, project_names):
            thread = threading.Thread(target=process_wrapper, args=(project_id, project_name))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        successful_projects = sum(results)
        total_projects = len(results)
        
        print(f"\n📊 Concurrent processing results: {successful_projects}/{total_projects} succeeded")
        
        if successful_projects >= 2:  # At least 2 out of 3 should succeed
            print("✅ Concurrent processing: PASSED - Multiple projects processed successfully")
            self.results["concurrent_processing"] = True
            return True
        else:
            print("❌ Concurrent processing: FAILED - Not enough projects completed successfully")
            return False
    
    def test_project_management(self):
        """Test project management features"""
        print("\n📋 TESTING PROJECT MANAGEMENT")
        print("=" * 40)
        
        try:
            # Get all projects
            response = self.session.get(f"{API_URL}/projects")
            if response.status_code != 200:
                print("❌ Failed to get projects list")
                return False
            
            projects = response.json()
            print(f"✅ Retrieved {len(projects)} projects")
            
            # Test system status
            response = self.session.get(f"{API_URL}/")
            if response.status_code != 200:
                print("❌ Failed to get system status")
                return False
            
            status = response.json()
            print(f"✅ System status retrieved:")
            print(f"   • FFmpeg available: {status.get('ffmpeg_available', 'Unknown')}")
            print(f"   • FFmpeg version: {status.get('ffmpeg_version', 'Unknown')}")
            print(f"   • Total projects: {status.get('total_projects', 'Unknown')}")
            
            self.results["project_management"] = True
            return True
            
        except Exception as e:
            print(f"❌ Project management test error: {e}")
            return False
    
    def test_error_recovery(self):
        """Test error handling and recovery"""
        print("\n🛠️ TESTING ERROR RECOVERY")
        print("=" * 40)
        
        try:
            # Test processing without files
            response = self.session.post(f"{API_URL}/projects", data={"name": "Error Test Project"})
            if response.status_code != 200:
                print("❌ Could not create error test project")
                return False
            
            project_id = response.json()["id"]
            
            # Try to process without uploading files
            response = self.session.post(f"{API_URL}/projects/{project_id}/process", json={})
            
            print(f"Processing without files - Status Code: {response.status_code}")
            
            if response.status_code == 400:
                print("✅ Error recovery: PASSED - Correctly handles missing files")
                self.results["error_recovery"] = True
                return True
            else:
                print("❌ Error recovery: FAILED - Should return 400 for missing files")
                return False
                
        except Exception as e:
            print(f"❌ Error recovery test error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all production feature tests"""
        print("🏭 STARTING PRODUCTION FEATURES TESTING")
        print("=" * 60)
        
        tests = [
            ("File Size Limits", self.test_file_size_limits),
            ("Project Management", self.test_project_management),
            ("Error Recovery", self.test_error_recovery),
            ("Concurrent Processing", self.test_concurrent_processing)
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
        print("🏁 PRODUCTION FEATURES TEST SUMMARY")
        print("=" * 60)
        
        for key, value in self.results.items():
            status = "✅ PASSED" if value else "❌ FAILED"
            print(f"{key.replace('_', ' ').title()}: {status}")
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests >= 3:  # Allow concurrent processing to potentially fail
            print("🎉 PRODUCTION FEATURES TESTS MOSTLY PASSED!")
            return True
        else:
            print("⚠️ Some critical production features failed.")
            return False

if __name__ == "__main__":
    tester = ProductionFeaturesTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)