import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [project, setProject] = useState(null);
  const [baseVideoFile, setBaseVideoFile] = useState(null);
  const [baseVideoInfo, setBaseVideoInfo] = useState(null);
  const [hologramFile, setHologramFile] = useState(null);
  const [hologramInfo, setHologramInfo] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [uploadingBase, setUploadingBase] = useState(false);
  const [uploadingHologram, setUploadingHologram] = useState(false);
  const [settings, setSettings] = useState({
    hologram_size: 0.3,
    hologram_position_x: 0.5,
    hologram_position_y: 0.5,
    glow_intensity: 0.7,
    flicker_intensity: 0.3,
    scanlines: true,
    blue_tint: true,
    rotation_angle: 0.0,
    transparency: 0.7
  });
  const [status, setStatus] = useState(null);
  const [systemStatus, setSystemStatus] = useState(null);
  const [errors, setErrors] = useState([]);
  
  const baseVideoRef = useRef(null);
  const hologramPreviewRef = useRef(null);

  useEffect(() => {
    checkSystemStatus();
  }, []);

  const addError = (message) => {
    setErrors(prev => [...prev.slice(-4), { id: Date.now(), message }]);
    setTimeout(() => {
      setErrors(prev => prev.filter(err => err.id !== Date.now()));
    }, 5000);
  };

  const checkSystemStatus = async () => {
    try {
      const response = await axios.get(`${API}/`);
      setSystemStatus(response.data);
    } catch (error) {
      console.error('Backend not available:', error);
      addError('Backend connection failed. Please refresh the page.');
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const createProject = async () => {
    try {
      const formData = new FormData();
      formData.append('name', `Hologram Project ${new Date().toLocaleDateString()}`);
      
      const response = await axios.post(`${API}/projects`, formData);
      setProject(response.data);
      return response.data;
    } catch (error) {
      console.error('Error creating project:', error);
      addError('Failed to create project. Please try again.');
      return null;
    }
  };

  const uploadBaseVideo = async (file, projectId = null) => {
    const targetProject = projectId || project;
    if (!targetProject) return;
    
    try {
      setUploadingBase(true);
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await axios.post(
        `${API}/projects/${targetProject.id}/upload-base-video`,
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: (progressEvent) => {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            console.log(`Base video upload progress: ${percentCompleted}%`);
          }
        }
      );
      
      setBaseVideoFile(file);
      setBaseVideoInfo(response.data);
      
      // Create video preview
      if (baseVideoRef.current) {
        baseVideoRef.current.src = URL.createObjectURL(file);
      }
      
    } catch (error) {
      console.error('Error uploading base video:', error);
      if (error.response?.status === 400) {
        addError(error.response.data.detail || 'Invalid video file. Please upload MP4, MOV, or AVI files only.');
      } else {
        addError('Failed to upload base video. Please try again.');
      }
    } finally {
      setUploadingBase(false);
    }
  };

  const uploadHologramMedia = async (file, projectId = null) => {
    const targetProject = projectId || project;
    if (!targetProject) return;
    
    try {
      setUploadingHologram(true);
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await axios.post(
        `${API}/projects/${targetProject.id}/upload-hologram-media`,
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: (progressEvent) => {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            console.log(`Hologram media upload progress: ${percentCompleted}%`);
          }
        }
      );
      
      setHologramFile(file);
      setHologramInfo(response.data);
      
      // Create preview
      if (file.type.startsWith('image/')) {
        const imgUrl = URL.createObjectURL(file);
        console.log('Created image preview:', imgUrl);
      } else if (file.type.startsWith('video/') && hologramPreviewRef.current) {
        hologramPreviewRef.current.src = URL.createObjectURL(file);
      }
      
    } catch (error) {
      console.error('Error uploading hologram media:', error);
      if (error.response?.status === 400) {
        addError(error.response.data.detail || 'Invalid file. Please upload images (PNG, JPG) or videos (MP4, MOV).');
      } else {
        addError('Failed to upload hologram media. Please try again.');
      }
    } finally {
      setUploadingHologram(false);
    }
  };

  const processVideo = async () => {
    if (!project || !baseVideoFile || !hologramFile) return;
    
    if (!systemStatus?.ffmpeg_available) {
      addError('FFmpeg is not available. Cannot process video.');
      return;
    }
    
    try {
      setProcessing(true);
      await axios.post(`${API}/projects/${project.id}/process`, settings);
      
      // Poll for status
      const pollStatus = async () => {
        try {
          const response = await axios.get(`${API}/projects/${project.id}/status`);
          setStatus(response.data);
          
          if (response.data.status === 'processing') {
            setTimeout(pollStatus, 2000);
          } else {
            setProcessing(false);
            if (response.data.status === 'failed') {
              addError(`Processing failed: ${response.data.error_message || 'Unknown error'}`);
            }
          }
        } catch (error) {
          console.error('Error checking status:', error);
          setProcessing(false);
          addError('Error checking processing status');
        }
      };
      
      pollStatus();
    } catch (error) {
      console.error('Error processing video:', error);
      setProcessing(false);
      if (error.response?.status === 503) {
        addError('Video processing service unavailable. Please try again later.');
      } else {
        addError('Failed to start video processing. Please check your files and try again.');
      }
    }
  };

  const downloadVideo = async () => {
    if (!project || status?.status !== 'completed') return;
    
    try {
      const response = await axios.get(`${API}/projects/${project.id}/download`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      
      // Get filename from response headers or use default
      const contentDisposition = response.headers['content-disposition'];
      let filename = `hologram_${project.id}.mp4`;
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }
      
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading video:', error);
      addError('Failed to download video. Please try again.');
    }
  };

  const handleBaseVideoChange = async (e) => {
    const file = e.target.files[0];
    if (file) {
      // Validate file size (100MB limit)
      if (file.size > 100 * 1024 * 1024) {
        addError('Video file too large. Maximum size is 100MB.');
        return;
      }
      
      let targetProject = project;
      if (!targetProject) {
        targetProject = await createProject();
        if (!targetProject) return;
      }
      
      await uploadBaseVideo(file, targetProject);
    }
  };

  const handleHologramFileChange = async (e) => {
    const file = e.target.files[0];
    if (file) {
      // Validate file size (50MB limit)
      if (file.size > 50 * 1024 * 1024) {
        addError('Media file too large. Maximum size is 50MB.');
        return;
      }
      
      let targetProject = project;
      if (!targetProject) {
        targetProject = await createProject();
        if (!targetProject) return;
      }
      
      await uploadHologramMedia(file, targetProject);
    }
  };

  const updateSetting = (key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const resetProject = () => {
    setProject(null);
    setBaseVideoFile(null);
    setBaseVideoInfo(null);
    setHologramFile(null);
    setHologramInfo(null);
    setStatus(null);
    setProcessing(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900">
      {/* Header */}
      <div className="bg-black/50 backdrop-blur-sm border-b border-cyan-500/30">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-600">
            🚀 Sci-Fi Hologram Compositor
          </h1>
          <p className="text-gray-300 mt-2">Create stunning holographic effects for your videos</p>
          
          {/* System Status */}
          {systemStatus && (
            <div className="mt-4">
              {!systemStatus.ffmpeg_available ? (
                <div className="p-4 bg-red-500/20 border border-red-500/50 rounded-lg">
                  <p className="text-red-300">⚠️ FFmpeg not detected. Video processing may not work properly.</p>
                  <button 
                    onClick={checkSystemStatus}
                    className="mt-2 px-3 py-1 bg-red-500/30 text-red-200 rounded hover:bg-red-500/50 transition-colors text-sm"
                  >
                    Retry Check
                  </button>
                </div>
              ) : (
                <div className="p-3 bg-green-500/20 border border-green-500/50 rounded-lg">
                  <p className="text-green-300 text-sm">
                    ✅ System Ready - FFmpeg {systemStatus.ffmpeg_version} | {systemStatus.total_projects} projects created
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Error Messages */}
          {errors.length > 0 && (
            <div className="mt-4 space-y-2">
              {errors.map((error) => (
                <div key={error.id} className="p-3 bg-red-500/20 border border-red-500/50 rounded-lg">
                  <p className="text-red-300 text-sm">❌ {error.message}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          
          {/* Upload Section */}
          <div className="space-y-6">
            <div className="bg-gray-800/50 backdrop-blur-sm border border-cyan-500/30 rounded-xl p-6">
              <h2 className="text-2xl font-bold text-cyan-400 mb-4">📹 Upload Files</h2>
              
              {/* Base Video Upload */}
              <div className="mb-6">
                <label className="block text-gray-300 mb-2">Base Video (Background)</label>
                <div className="relative">
                  <input
                    type="file"
                    accept="video/*"
                    onChange={handleBaseVideoChange}
                    className="hidden"
                    id="base-video-upload"
                    disabled={uploadingBase}
                  />
                  <label
                    htmlFor="base-video-upload"
                    className={`flex items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer transition-colors ${
                      uploadingBase 
                        ? 'border-yellow-500/50 bg-yellow-500/10' 
                        : baseVideoFile 
                          ? 'border-green-500/50 bg-green-500/10 hover:border-green-400/80' 
                          : 'border-cyan-500/50 bg-gray-800/30 hover:border-cyan-400/80'
                    }`}
                  >
                    <div className="text-center">
                      <div className="text-4xl mb-2">
                        {uploadingBase ? '⏳' : baseVideoFile ? '✅' : '🎬'}
                      </div>
                      <p className="text-gray-300">
                        {uploadingBase 
                          ? 'Uploading base video...' 
                          : baseVideoFile 
                            ? baseVideoInfo?.filename || baseVideoFile.name
                            : "Drop your base video here"
                        }
                      </p>
                      <p className="text-sm text-gray-500">
                        {uploadingBase 
                          ? 'Please wait...' 
                          : baseVideoInfo 
                            ? `${baseVideoInfo.size} uploaded` 
                            : 'MP4, MOV, AVI supported (max 100MB)'
                        }
                      </p>
                    </div>
                  </label>
                </div>
                
                {baseVideoFile && !uploadingBase && (
                  <div className="mt-3">
                    <video
                      ref={baseVideoRef}
                      controls
                      className="w-full max-h-40 rounded-lg border border-cyan-500/30"
                      onLoadedMetadata={() => {
                        if (baseVideoRef.current) {
                          console.log('Base video loaded:', {
                            duration: baseVideoRef.current.duration,
                            videoWidth: baseVideoRef.current.videoWidth,
                            videoHeight: baseVideoRef.current.videoHeight
                          });
                        }
                      }}
                    />
                  </div>
                )}
              </div>

              {/* Hologram Media Upload */}
              <div>
                <label className="block text-gray-300 mb-2">Hologram Media</label>
                <div className="relative">
                  <input
                    type="file"
                    accept="image/*,video/*"
                    onChange={handleHologramFileChange}
                    className="hidden"
                    id="hologram-upload"
                    disabled={uploadingHologram}
                  />
                  <label
                    htmlFor="hologram-upload"
                    className={`flex items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer transition-colors ${
                      uploadingHologram 
                        ? 'border-yellow-500/50 bg-yellow-500/10' 
                        : hologramFile 
                          ? 'border-green-500/50 bg-green-500/10 hover:border-green-400/80' 
                          : 'border-purple-500/50 bg-gray-800/30 hover:border-purple-400/80'
                    }`}
                  >
                    <div className="text-center">
                      <div className="text-4xl mb-2">
                        {uploadingHologram ? '⏳' : hologramFile ? '✅' : '✨'}
                      </div>
                      <p className="text-gray-300">
                        {uploadingHologram 
                          ? 'Uploading hologram media...' 
                          : hologramFile 
                            ? hologramInfo?.filename || hologramFile.name
                            : "Drop your hologram content here"
                        }
                      </p>
                      <p className="text-sm text-gray-500">
                        {uploadingHologram 
                          ? 'Please wait...' 
                          : hologramInfo 
                            ? `${hologramInfo.size} - ${hologramInfo.type || 'Unknown type'}`
                            : 'Images or videos (max 50MB)'
                        }
                      </p>
                    </div>
                  </label>
                </div>
                
                {hologramFile && !uploadingHologram && (
                  <div className="mt-3">
                    {hologramFile.type.startsWith('image/') ? (
                      <img
                        src={URL.createObjectURL(hologramFile)}
                        alt="Hologram preview"
                        className="w-full max-h-40 object-contain rounded-lg bg-gray-900 border border-purple-500/30"
                      />
                    ) : (
                      <video
                        ref={hologramPreviewRef}
                        controls
                        className="w-full max-h-40 rounded-lg border border-purple-500/30"
                        onLoadedMetadata={() => {
                          if (hologramPreviewRef.current) {
                            console.log('Hologram video loaded:', {
                              duration: hologramPreviewRef.current.duration,
                              videoWidth: hologramPreviewRef.current.videoWidth,
                              videoHeight: hologramPreviewRef.current.videoHeight
                            });
                          }
                        }}
                      />
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Settings Panel */}
            <div className="bg-gray-800/50 backdrop-blur-sm border border-cyan-500/30 rounded-xl p-6">
              <h2 className="text-2xl font-bold text-cyan-400 mb-4">⚙️ Hologram Settings</h2>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-gray-300 mb-2">Size: {(settings.hologram_size * 100).toFixed(0)}%</label>
                  <input
                    type="range"
                    min="0.1"
                    max="1.0"
                    step="0.1"
                    value={settings.hologram_size}
                    onChange={(e) => updateSetting('hologram_size', parseFloat(e.target.value))}
                    className="w-full accent-cyan-500"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-gray-300 mb-2">Position X: {(settings.hologram_position_x * 100).toFixed(0)}%</label>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.1"
                      value={settings.hologram_position_x}
                      onChange={(e) => updateSetting('hologram_position_x', parseFloat(e.target.value))}
                      className="w-full accent-cyan-500"
                    />
                  </div>
                  <div>
                    <label className="block text-gray-300 mb-2">Position Y: {(settings.hologram_position_y * 100).toFixed(0)}%</label>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.1"
                      value={settings.hologram_position_y}
                      onChange={(e) => updateSetting('hologram_position_y', parseFloat(e.target.value))}
                      className="w-full accent-cyan-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-gray-300 mb-2">Glow Intensity: {(settings.glow_intensity * 100).toFixed(0)}%</label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={settings.glow_intensity}
                    onChange={(e) => updateSetting('glow_intensity', parseFloat(e.target.value))}
                    className="w-full accent-cyan-500"
                  />
                </div>

                <div>
                  <label className="block text-gray-300 mb-2">Flicker Intensity: {(settings.flicker_intensity * 100).toFixed(0)}%</label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={settings.flicker_intensity}
                    onChange={(e) => updateSetting('flicker_intensity', parseFloat(e.target.value))}
                    className="w-full accent-cyan-500"
                  />
                </div>

                <div>
                  <label className="block text-gray-300 mb-2">Transparency: {(settings.transparency * 100).toFixed(0)}%</label>
                  <input
                    type="range"
                    min="0.1"
                    max="1"
                    step="0.1"
                    value={settings.transparency}
                    onChange={(e) => updateSetting('transparency', parseFloat(e.target.value))}
                    className="w-full accent-cyan-500"
                  />
                </div>

                <div className="flex items-center space-x-6">
                  <label className="flex items-center text-gray-300">
                    <input
                      type="checkbox"
                      checked={settings.blue_tint}
                      onChange={(e) => updateSetting('blue_tint', e.target.checked)}
                      className="mr-2 accent-cyan-500"
                    />
                    Blue Tint
                  </label>
                  <label className="flex items-center text-gray-300">
                    <input
                      type="checkbox"
                      checked={settings.scanlines}
                      onChange={(e) => updateSetting('scanlines', e.target.checked)}
                      className="mr-2 accent-cyan-500"
                    />
                    Scanlines
                  </label>
                </div>
              </div>
            </div>
          </div>

          {/* Preview and Process Section */}
          <div className="space-y-6">
            <div className="bg-gray-800/50 backdrop-blur-sm border border-cyan-500/30 rounded-xl p-6">
              <h2 className="text-2xl font-bold text-cyan-400 mb-4">🎭 Process & Export</h2>
              
              {/* Status Display */}
              {status && (
                <div className="mb-4 p-4 rounded-lg bg-gray-700/50 border border-gray-600">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-300">Status:</span>
                    <span className={`font-semibold ${
                      status.status === 'completed' ? 'text-green-400' : 
                      status.status === 'processing' ? 'text-yellow-400' : 
                      status.status === 'failed' ? 'text-red-400' : 'text-gray-400'
                    }`}>
                      {status.status.toUpperCase()}
                    </span>
                  </div>
                  <div className="mt-2 text-sm text-gray-400">
                    {status.message}
                  </div>
                  {processing && status.progress > 0 && (
                    <div className="mt-3">
                      <div className="flex justify-between text-sm text-gray-400 mb-1">
                        <span>Progress</span>
                        <span>{status.progress.toFixed(1)}%</span>
                      </div>
                      <div className="w-full bg-gray-600 rounded-full h-2">
                        <div 
                          className="bg-cyan-500 h-2 rounded-full transition-all duration-500"
                          style={{ width: `${status.progress}%` }}
                        ></div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Action Buttons */}
              <div className="space-y-3">
                <button
                  onClick={processVideo}
                  disabled={!baseVideoFile || !hologramFile || processing || uploadingBase || uploadingHologram || !systemStatus?.ffmpeg_available}
                  className="w-full bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-bold py-3 px-6 rounded-lg disabled:from-gray-600 disabled:to-gray-700 disabled:cursor-not-allowed hover:from-cyan-600 hover:to-blue-700 transition-colors"
                >
                  {processing ? (
                    <span className="flex items-center justify-center">
                      <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Processing Hologram...
                    </span>
                  ) : (
                    '✨ Create Hologram Effect'
                  )}
                </button>

                {status?.status === 'completed' && (
                  <button
                    onClick={downloadVideo}
                    className="w-full bg-gradient-to-r from-green-500 to-emerald-600 text-white font-bold py-3 px-6 rounded-lg hover:from-green-600 hover:to-emerald-700 transition-colors"
                  >
                    📥 Download Hologram Video
                  </button>
                )}

                {project && (
                  <button
                    onClick={resetProject}
                    className="w-full bg-gradient-to-r from-gray-600 to-gray-700 text-white font-bold py-2 px-6 rounded-lg hover:from-gray-700 hover:to-gray-800 transition-colors text-sm"
                  >
                    🔄 Start New Project
                  </button>
                )}
              </div>
            </div>

            {/* Project Info */}
            {project && (
              <div className="bg-gray-800/50 backdrop-blur-sm border border-cyan-500/30 rounded-xl p-6">
                <h3 className="text-xl font-bold text-cyan-400 mb-3">📋 Project Details</h3>
                <div className="space-y-2 text-sm text-gray-300">
                  <p><span className="text-gray-400">Project ID:</span> {project.id}</p>
                  <p><span className="text-gray-400">Created:</span> {new Date(project.created_at).toLocaleString()}</p>
                  {baseVideoInfo && (
                    <p><span className="text-gray-400">Base Video:</span> {baseVideoInfo.filename} ({baseVideoInfo.size})</p>
                  )}
                  {hologramInfo && (
                    <p><span className="text-gray-400">Hologram Media:</span> {hologramInfo.filename} ({hologramInfo.size})</p>
                  )}
                </div>
              </div>
            )}

            {/* Info Panel */}
            <div className="bg-gray-800/50 backdrop-blur-sm border border-cyan-500/30 rounded-xl p-6">
              <h3 className="text-xl font-bold text-cyan-400 mb-3">🌟 How It Works</h3>
              <div className="space-y-2 text-gray-300 text-sm">
                <p>• Upload a base video as your background scene</p>
                <p>• Add any image or video to be transformed into a hologram</p>
                <p>• Adjust settings to control the holographic effects</p>
                <p>• Click "Create Hologram Effect" to process your video</p>
                <p>• Download your sci-fi masterpiece!</p>
              </div>
              
              <div className="mt-4 p-3 bg-blue-500/20 border border-blue-500/50 rounded-lg">
                <p className="text-blue-300 text-sm">
                  💡 <strong>Pro Tip:</strong> Try different transparency and glow settings for unique effects. Animated GIFs work great as hologram content!
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;