const API_URL = 'http://localhost:8000';
let currentResults = null;
let faceModal = null;

document.addEventListener('DOMContentLoaded', () => {
    // Initialize modal
    faceModal = new bootstrap.Modal(document.getElementById('faceModal'));
    
    // Event listeners
    document.getElementById('processBtn').addEventListener('click', processVideo);
    document.getElementById('videoUpload').addEventListener('change', handleVideoUpload);
    document.getElementById('searchFaces').addEventListener('input', searchFaces);
    document.getElementById('addFaceForm').addEventListener('submit', addKnownFace);
    document.getElementById('saveFaceName').addEventListener('click', saveFaceName);
    
    loadKnownFaces();
});

async function processVideo() {
    const fileInput = document.getElementById('videoUpload');
    if (!fileInput.files.length) {
        showStatus('Please select a video first', 'error');
        return;
    }

    showStatus('Processing video...', 'info');
    const btn = document.getElementById('processBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Processing...';

    try {
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);

        const response = await fetch(`${API_URL}/upload-video`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(error || 'Upload failed');
        }

        const data = await response.json();
        currentResults = data.results;
        
        showStatus('Processing complete!', 'success');
        displayFaces(currentResults.unique_faces);
        renderTimeline();

    } catch (error) {
        showStatus(`Error: ${error.message}`, 'error');
        console.error('Upload error:', error);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-play-circle"></i> Process Video';
    }
}

function handleVideoUpload(event) {
    const file = event.target.files[0];
    if (file) {
        document.getElementById('videoPlayer').src = URL.createObjectURL(file);
    }
}

function displayFaces(faces) {
    const container = document.getElementById('facesList');
    container.innerHTML = faces.map(face => `
        <div class="face-card" data-id="${face.id}">
            <img src="${API_URL}/get-face-image/${face.image_path}" alt="${face.name}">
            <div class="face-info">
                <span class="face-name">${face.name}</span>
                <button class="btn btn-sm btn-outline-primary edit-btn">
                    <i class="bi bi-pencil"></i>
                </button>
            </div>
        </div>
    `).join('');

    // Add event listeners
    document.querySelectorAll('.face-card').forEach(card => {
        card.addEventListener('click', () => showFaceDetails(card.dataset.id));
    });
}

function renderTimeline() {
    const timeline = document.getElementById('timeline');
    timeline.innerHTML = '';
    
    if (!currentResults) return;
    
    const duration = currentResults.video_info.duration;
    const appearances = {};
    
    currentResults.detections.forEach(det => {
        if (!appearances[det.face_id]) appearances[det.face_id] = [];
        appearances[det.face_id].push(det.time);
    });
    
    Object.entries(appearances).forEach(([faceId, times]) => {
        const face = currentResults.unique_faces.find(f => f.id === faceId);
        if (!face) return;
        
        times.forEach(time => {
            const marker = document.createElement('div');
            marker.className = 'timeline-marker';
            marker.style.left = `${(time / duration) * 100}%`;
            marker.style.backgroundColor = getColorForName(face.name);
            marker.title = `${face.name} at ${time.toFixed(1)}s`;
            marker.addEventListener('click', () => {
                document.getElementById('videoPlayer').currentTime = time;
            });
            timeline.appendChild(marker);
        });
    });
}

function showFaceDetails(faceId) {
    const face = currentResults.unique_faces.find(f => f.id === faceId);
    if (!face) return;
    
    document.getElementById('modalFaceImage').src = `${API_URL}/get-face-image/${face.image_path}`;
    document.getElementById('modalFaceName').value = face.name;
    document.getElementById('modalFaceName').dataset.faceId = faceId;
    
    const appearances = currentResults.detections
        .filter(d => d.face_id === faceId)
        .map(d => d.time);
    
    const timesList = document.getElementById('appearanceTimes');
    timesList.innerHTML = appearances.map(time => `
        <div class="list-group-item d-flex justify-content-between align-items-center">
            <span>${time.toFixed(2)} seconds</span>
            <button class="btn btn-sm btn-outline-primary" 
                    onclick="document.getElementById('videoPlayer').currentTime=${time}">
                <i class="bi bi-play"></i> Jump
            </button>
        </div>
    `).join('');
    
    faceModal.show();
}

async function saveFaceName() {
    const faceId = document.getElementById('modalFaceName').dataset.faceId;
    const newName = document.getElementById('modalFaceName').value;
    
    try {
        const response = await fetch(`${API_URL}/update-face`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                face_id: faceId,
                new_name: newName,
                results_path: currentResults.results_path
            })
        });
        
        if (!response.ok) throw new Error('Failed to update name');
        
        // Update local data
        const face = currentResults.unique_faces.find(f => f.id === faceId);
        if (face) face.name = newName;
        
        displayFaces(currentResults.unique_faces);
        renderTimeline();
        faceModal.hide();
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

async function loadKnownFaces() {
    try {
        const response = await fetch(`${API_URL}/list-known-faces`);
        const data = await response.json();
        
        const container = document.getElementById('knownFaces');
        container.innerHTML = data.names.map(name => `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <span>${name}</span>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteKnownFace('${name}')">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load known faces:', error);
    }
}

async function addKnownFace(e) {
    e.preventDefault();
    const name = document.getElementById('faceName').value;
    const file = document.getElementById('faceImage').files[0];
    
    if (!name || !file) return;
    
    try {
        const formData = new FormData();
        formData.append('name', name);
        formData.append('file', file);
        
        const response = await fetch(`${API_URL}/add-known-face`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) throw new Error('Failed to add face');
        
        document.getElementById('addFaceForm').reset();
        loadKnownFaces();
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

async function deleteKnownFace(name) {
    if (!confirm(`Delete ${name}?`)) return;
    
    try {
        const response = await fetch(`${API_URL}/delete-known-face/${encodeURIComponent(name)}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) throw new Error('Failed to delete face');
        
        loadKnownFaces();
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

function searchFaces() {
    const term = document.getElementById('searchFaces').value.toLowerCase();
    document.querySelectorAll('.face-card').forEach(card => {
        const name = card.querySelector('.face-name').textContent.toLowerCase();
        card.style.display = name.includes(term) ? 'flex' : 'none';
    });
}

function showStatus(message, type) {
    const status = document.getElementById('status');
    status.textContent = message;
    status.className = `alert alert-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'}`;
    status.classList.remove('d-none');
}

function getColorForName(name) {
    const colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF'];
    const hash = name.split('').reduce((a, b) => (a << 5) - a + b.charCodeAt(0), 0);
    return colors[Math.abs(hash) % colors.length];
}