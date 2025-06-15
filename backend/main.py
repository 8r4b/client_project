import os
import uuid
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import cv2
import face_recognition
import numpy as np

app = FastAPI()

# CORS for React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
KNOWN_FACES_DIR = BASE_DIR / "known_faces"
FACES_DIR = DATA_DIR / "faces"
for d in [DATA_DIR, KNOWN_FACES_DIR, FACES_DIR]:
    d.mkdir(exist_ok=True, parents=True)

class FaceRecognizer:
    def __init__(self):
        self.known_faces = []
        self.known_names = []
        self.load_known_faces()

    def load_known_faces(self):
        self.known_faces = []
        self.known_names = []
        for file in KNOWN_FACES_DIR.glob("*.*"):
            try:
                image = face_recognition.load_image_file(file)
                encodings = face_recognition.face_encodings(image)
                if encodings:
                    self.known_faces.append(encodings[0])
                    self.known_names.append(file.stem.replace("_", " ").title())
            except Exception as e:
                print(f"Error loading {file}: {str(e)}")

    def recognize_face(self, face_encoding):
        matches = face_recognition.compare_faces(self.known_faces, face_encoding, tolerance=0.6)
        name = "UNKNOWN"
        if True in matches:
            face_distances = face_recognition.face_distance(self.known_faces, face_encoding)
            best_match = np.argmin(face_distances)
            name = self.known_names[best_match]
        return name

face_recognizer = FaceRecognizer()

@app.post("/upload-video")
async def upload_video(file: UploadFile = File(...)):
    temp_path = DATA_DIR / f"temp_{uuid.uuid4()}{Path(file.filename).suffix}"
    with open(temp_path, "wb") as buffer:
        buffer.write(await file.read())
    results = process_video(temp_path)
    temp_path.unlink()
    return results

def process_video(video_path: Path):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise HTTPException(400, "Could not open video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    results = {
        "fps": fps,
        "detections": [],
        "unique_faces": []
    }
    frame_count = 0
    seen_names = set()
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        # Process every 10th frame for speed
        if frame_count % 10 != 0:
            frame_count += 1
            continue
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # Resize frame to 50% for faster processing
        small_frame = cv2.resize(rgb_frame, (0, 0), fx=0.5, fy=0.5)
        face_locations = face_recognition.face_locations(small_frame)
        face_encodings = face_recognition.face_encodings(small_frame, face_locations)
        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            # Scale face locations back to original frame size
            top *= 2
            right *= 2
            bottom *= 2
            left *= 2
            name = face_recognizer.recognize_face(face_encoding)
            face_id = str(uuid.uuid4())
            face_img = rgb_frame[top:bottom, left:right]
            face_path = FACES_DIR / f"{face_id}.jpg"
            cv2.imwrite(str(face_path), cv2.cvtColor(face_img, cv2.COLOR_RGB2BGR))
            if name not in seen_names:
                results["unique_faces"].append({
                    "id": face_id,
                    "name": name,
                    "image_path": f"/face-image/{face_id}.jpg"
                })
                seen_names.add(name)
            results["detections"].append({
                "frame": frame_count,
                "time": frame_count / fps,
                "face_id": face_id,
                "name": name,
                "location": [top, right, bottom, left]
            })
        frame_count += 1
    cap.release()
    return results

@app.post("/add-known-face")
async def add_known_face(name: str = Form(...), file: UploadFile = File(...)):
    safe_name = name.lower().replace(" ", "_")
    face_path = KNOWN_FACES_DIR / f"{safe_name}.jpg"
    with open(face_path, "wb") as buffer:
        buffer.write(await file.read())
    face_recognizer.load_known_faces()
    return {"status": "success", "name": name}

@app.get("/list-known-faces")
async def list_known_faces():
    known_faces = []
    for file in KNOWN_FACES_DIR.glob("*.*"):
        if file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
            known_faces.append(file.stem.replace("_", " ").title())
    return {"names": known_faces, "count": len(known_faces)}

@app.delete("/delete-known-face/{name}")
async def delete_known_face(name: str):
    safe_name = name.lower().replace(" ", "_")
    face_path = KNOWN_FACES_DIR / f"{safe_name}.jpg"
    if face_path.exists():
        face_path.unlink()
        face_recognizer.load_known_faces()
        return {"status": "success"}
    else:
        raise HTTPException(404, "Face not found")

@app.get("/face-image/{image_name}")
async def get_face_image(image_name: str):
    image_path = FACES_DIR / image_name
    if not image_path.exists():
        raise HTTPException(404, "Image not found")
    return FileResponse(image_path)