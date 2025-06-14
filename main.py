import os
import uuid
import json
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import cv2
import face_recognition
import numpy as np

os.environ['DLIB_USE_CUDA'] = '0'
# Initialize app
app = FastAPI()

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:9000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory setup
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
KNOWN_FACES_DIR = BASE_DIR / "known_faces"
TEMP_DIR = DATA_DIR / "temp"
FACES_DIR = DATA_DIR / "faces"

# Create directories
for dir in [DATA_DIR, KNOWN_FACES_DIR, TEMP_DIR, FACES_DIR]:
    dir.mkdir(parents=True, exist_ok=True)

class FaceRecognizer:
    def __init__(self):
        self.known_encodings = []
        self.known_names = []
        self.load_known_faces()

    def load_known_faces(self):
        """Load known faces from directory"""
        self.known_encodings = []
        self.known_names = []
        for file in KNOWN_FACES_DIR.glob("*.*"):
            if file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                try:
                    image = face_recognition.load_image_file(file)
                    encoding = face_recognition.face_encodings(image)[0]
                    self.known_encodings.append(encoding)
                    self.known_names.append(file.stem.replace("_", " ").title())
                except Exception as e:
                    print(f"Error loading {file}: {e}")

    def recognize(self, face_encoding):
        """Recognize a face against known faces"""
        if not self.known_encodings:
            return "UNKNOWN"
            
        matches = face_recognition.compare_faces(
            self.known_encodings, 
            face_encoding,
            tolerance=0.6
        )
        name = "UNKNOWN"
        
        if True in matches:
            face_distances = face_recognition.face_distance(
                self.known_encodings,
                face_encoding
            )
            best_match = np.argmin(face_distances)
            name = self.known_names[best_match]
        
        return name

recognizer = FaceRecognizer()

@app.post("/upload-video")
async def upload_video(file: UploadFile = File(...)):
    """Handle video upload and processing"""
    temp_path = None
    try:
        # Validate file type
        if not file.filename.lower().endswith(('.mp4', '.mov', '.avi')):
            raise HTTPException(400, "Only MP4/MOV/AVI files allowed")

        # Save to temp file
        temp_path = TEMP_DIR / f"temp_{uuid.uuid4()}{Path(file.filename).suffix}"
        with open(temp_path, "wb") as buffer:
            contents = await file.read()
            buffer.write(contents)

        # Process video
        results = process_video(temp_path)
        
        # Save results
        results_path = DATA_DIR / f"results_{uuid.uuid4()}.json"
        with open(results_path, "w") as f:
            json.dump(results, f, indent=2)
        
        return JSONResponse({
            "status": "success",
            "results": results,
            "results_path": results_path.name
        })

    except Exception as e:
        raise HTTPException(500, f"Processing failed: {str(e)}")
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()

def process_video(video_path: Path):
    """Process video to detect faces"""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError("Could not open video file")
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    results = {
        "video_info": {
            "fps": fps,
            "duration": cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
        },
        "detections": [],
        "unique_faces": []
    }

    frame_count = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % 5 == 0:  # Process every 5th frame
            try:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                face_locations = face_recognition.face_locations(rgb_frame)
                face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

                for (top, right, bottom, left), encoding in zip(face_locations, face_encodings):
                    name = recognizer.recognize(encoding)
                    face_id = str(uuid.uuid4())
                    face_path = FACES_DIR / f"{face_id}.jpg"
                    cv2.imwrite(str(face_path), cv2.cvtColor(rgb_frame[top:bottom, left:right], cv2.COLOR_RGB2BGR))
                    
                    face_data = {
                        "id": face_id,
                        "name": name,
                        "image_path": str(face_path.relative_to(DATA_DIR))
                    }

                    if not any(f["name"] == name for f in results["unique_faces"]):
                        results["unique_faces"].append(face_data)

                    results["detections"].append({
                        "frame": frame_count,
                        "time": frame_count / fps,
                        "face_id": face_id,
                        "location": [top, right, bottom, left]
                    })
            except Exception as e:
                print(f"Error processing frame {frame_count}: {e}")
                continue

        frame_count += 1

    cap.release()
    return results

@app.post("/update-face")
async def update_face(
    face_id: str = Form(...),
    new_name: str = Form(...),
    results_path: str = Form(...)
):
    """Update a face's name"""
    try:
        json_path = DATA_DIR / results_path
        with open(json_path, "r") as f:
            results = json.load(f)

        # Update in unique_faces
        for face in results["unique_faces"]:
            if face["id"] == face_id:
                face["name"] = new_name
                break

        # Update in detections
        for detection in results["detections"]:
            if detection["face_id"] == face_id:
                detection["name"] = new_name

        with open(json_path, "w") as f:
            json.dump(results, f, indent=2)

        return {"status": "success"}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/list-known-faces")
async def list_known_faces():
    """List all known faces"""
    return {
        "names": recognizer.known_names,
        "count": len(recognizer.known_names)
    }

@app.post("/add-known-face")
async def add_known_face(
    name: str = Form(...),
    file: UploadFile = File(...)
):
    """Add a new known face"""
    try:
        safe_name = name.lower().replace(" ", "_")
        face_path = KNOWN_FACES_DIR / f"{safe_name}.jpg"
        
        with open(face_path, "wb") as buffer:
            buffer.write(await file.read())
        
        recognizer.load_known_faces()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/get-face-image/{image_path:path}")
async def get_face_image(image_path: str):
    """Serve face images"""
    image_path = DATA_DIR / image_path
    if not image_path.exists():
        raise HTTPException(404, "Image not found")
    return FileResponse(image_path)