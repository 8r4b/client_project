import React, { useState, useRef } from "react";
import "./App.css";

const API = "http://localhost:8000";

function App() {
  const [videoFile, setVideoFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [detections, setDetections] = useState([]);
  const [uniqueFaces, setUniqueFaces] = useState([]);
  const [knownFaces, setKnownFaces] = useState([]);
  const [faceName, setFaceName] = useState("");
  const [faceImage, setFaceImage] = useState(null);
  const [status, setStatus] = useState("");
  const videoRef = useRef();

  // Upload video and process
  const handleVideoUpload = async () => {
    if (!videoFile) return;
    setUploading(true);
    setStatus("Processing video...");
    const formData = new FormData();
    formData.append("file", videoFile);
    const res = await fetch(`${API}/upload-video`, {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    setDetections(data.detections);
    setUniqueFaces(data.unique_faces);
    setUploading(false);
    setStatus("Done!");
  };

  // List known faces
  const fetchKnownFaces = async () => {
    const res = await fetch(`${API}/list-known-faces`);
    const data = await res.json();
    setKnownFaces(data.names);
  };

  // Add known face
  const handleAddFace = async (e) => {
    e.preventDefault();
    if (!faceName || !faceImage) return;
    const formData = new FormData();
    formData.append("name", faceName);
    formData.append("file", faceImage);
    await fetch(`${API}/add-known-face`, {
      method: "POST",
      body: formData,
    });
    setFaceName("");
    setFaceImage(null);
    fetchKnownFaces();
  };

  // Delete known face
  const handleDeleteFace = async (name) => {
    await fetch(`${API}/delete-known-face/${name}`, { method: "DELETE" });
    fetchKnownFaces();
  };

  React.useEffect(() => {
    fetchKnownFaces();
  }, []);

  return (
    <div className="app-container">
      <h2>Face Recognition System</h2>
      <div className="flex-row">
        <div className="flex-col">
          <div className="section">
            <h4>Upload and Process Video</h4>
            <input
              type="file"
              accept="video/*"
              onChange={(e) => setVideoFile(e.target.files[0])}
            />
            <button onClick={handleVideoUpload} disabled={uploading} style={{ marginLeft: 10 }}>
              {uploading ? "Processing..." : "Upload & Process"}
            </button>
            <div className="status">{status}</div>
            {detections.length > 0 && (
              <div>
                <h5>Detections</h5>
                <ul>
                  {detections.map((det, idx) => (
                    <li key={idx}>
                      Frame {det.frame}, Time {det.time.toFixed(2)}s, Name: {det.name}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {uniqueFaces.length > 0 && (
              <div>
                <h5>Unique Faces</h5>
                <div className="unique-faces">
                  {uniqueFaces.map((face) => (
                    <div key={face.id} className="face-card">
                      <img
                        src={`${API}${face.image_path}`}
                        alt={face.name}
                      />
                      <div>{face.name}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
        <div className="flex-col">
          <div className="section">
            <h4>Known Faces</h4>
            <form onSubmit={handleAddFace} style={{ marginBottom: 16 }}>
              <input
                type="text"
                placeholder="Name"
                value={faceName}
                onChange={(e) => setFaceName(e.target.value)}
                required
                style={{ marginRight: 8 }}
              />
              <input
                type="file"
                accept="image/*"
                onChange={(e) => setFaceImage(e.target.files[0])}
                required
                style={{ marginRight: 8 }}
              />
              <button type="submit">Add</button>
            </form>
            <div className="known-faces-list">
              {knownFaces.map((name) => (
                <div key={name} className="known-face-item">
                  {name}
                  <button onClick={() => handleDeleteFace(name)}>
                    Delete
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
export default App;