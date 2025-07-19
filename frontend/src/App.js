import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [project, setProject] = useState(null);
  const [baseVideoFile, setBaseVideoFile] = useState(null);
  const [hologramFile, setHologramFile] = useState(null);
  const [processing, setProcessing] = useState(false);
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
  const [ffmpegAvailable, setFfmpegAvailable] = useState(false);
  
  const baseVideoRef = useRef(null);
  const hologramPreviewRef = useRef(null);

  useEffect(() => {
    checkBackendStatus();
  }, []);

  const checkBackendStatus = async () => {
    try {
      const response = await axios.get(`${API}/`);
      setFfmpegAvailable(response.data.ffmpeg_available);
    } catch (error) {
      console.error('Backend not available:', error);
    }
  };

  const createProject = async () => {
    try {
      const formData = new FormData();
      formData.append('name', `Hologram Project ${Date.now()}`);
      
      const response = await axios.post(`${API}/projects`, formData);
      setProject(response.data);
    } catch (error) {
      console.error('Error creating project:', error);
    }
  };

  const uploadBaseVideo = async (file) => {
    if (!project) return;
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      await axios.post(`${API}/projects/${project.id}/upload-base-video`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setBaseVideoFile(file);
    } catch (error) {
      console.error('Error uploading base video:', error);
    }
  };

  const uploadHologramMedia = async (file) => {
    if (!project) return;
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      await axios.post(`${API}/projects/${project.id}/upload-hologram-media`, formData);
      setHologramFile(file);
    } catch (error) {
      console.error('Error uploading hologram media:', error);
    }
  };

  const processVideo = async () => {
    if (!project || !baseVideoFile || !hologramFile) return;
    
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
          }
        } catch (error) {
          console.error('Error checking status:', error);
          setProcessing(false);
        }
      };
      
      pollStatus();
    } catch (error) {
      console.error('Error processing video:', error);
      setProcessing(false);
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
      link.download = `hologram_${project.id}.mp4`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading video:', error);
    }
  };

  const handleBaseVideoChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!project) {
        createProject().then(() => uploadBaseVideo(file));
      } else {
        uploadBaseVideo(file);
      }
    }
  };

  const handleHologramFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!project) {
        createProject().then(() => uploadHologramMedia(file));
      } else {
        uploadHologramMedia(file);
      }
    }
  };

  const updateSetting = (key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }));
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
          
          {!ffmpegAvailable && (
            <div className="mt-4 p-4 bg-red-500/20 border border-red-500/50 rounded-lg">
              <p className="text-red-300">⚠️ FFmpeg not detected. Video processing may not work properly.</p>
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
                  />
                  <label
                    htmlFor="base-video-upload"
                    className="flex items-center justify-center w-full h-32 border-2 border-dashed border-cyan-500/50 rounded-lg hover:border-cyan-400/80 cursor-pointer transition-colors bg-gray-800/30"
                  >
                    <div className="text-center">
                      <div className="text-4xl mb-2">🎬</div>
                      <p className="text-gray-300">
                        {baseVideoFile ? baseVideoFile.name : "Drop your base video here"}
                      </p>
                      <p className="text-sm text-gray-500">MP4, MOV, AVI supported</p>
                    </div>
                  </label>
                </div>
                
                {baseVideoFile && (
                  <div className="mt-3">
                    <video
                      ref={baseVideoRef}
                      src={URL.createObjectURL(baseVideoFile)}
                      controls
                      className="w-full max-h-40 rounded-lg"
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
                  />
                  <label
                    htmlFor="hologram-upload"
                    className="flex items-center justify-center w-full h-32 border-2 border-dashed border-purple-500/50 rounded-lg hover:border-purple-400/80 cursor-pointer transition-colors bg-gray-800/30"
                  >
                    <div className="text-center">
                      <div className="text-4xl mb-2">✨</div>
                      <p className="text-gray-300">
                        {hologramFile ? hologramFile.name : "Drop your hologram content here"}
                      </p>
                      <p className="text-sm text-gray-500">Images or videos</p>
                    </div>
                  </label>
                </div>
                
                {hologramFile && (
                  <div className="mt-3">
                    {hologramFile.type.startsWith('image/') ? (
                      <img
                        src={URL.createObjectURL(hologramFile)}
                        alt="Hologram preview"
                        className="w-full max-h-40 object-contain rounded-lg bg-gray-900"
                      />
                    ) : (
                      <video
                        ref={hologramPreviewRef}
                        src={URL.createObjectURL(hologramFile)}
                        controls
                        className="w-full max-h-40 rounded-lg"
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
                  {processing && (
                    <div className="mt-2">
                      <div className="w-full bg-gray-600 rounded-full h-2">
                        <div className="bg-cyan-500 h-2 rounded-full animate-pulse"></div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Action Buttons */}
              <div className="space-y-3">
                <button
                  onClick={processVideo}
                  disabled={!baseVideoFile || !hologramFile || processing}
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
              </div>
            </div>

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