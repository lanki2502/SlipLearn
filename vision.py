
import cv2
import threading
import time
from ultralytics import YOLO


class VisionSystem:
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.cap = None

        self.latest_frame = None
        self.latest_detections = []

        self.lock = threading.Lock()
        self.running = False
        self.thread = None

        # Load the model only once
        self.model = YOLO("yolo11n.pt")

        self.camera_error = None

        # Speed settings
        self.frame_width = 416
        self.frame_height = 312
        self.image_size = 256
        self.confidence_threshold = 0.35

    def start(self):
        if self.running:
            return True

        self.cap = cv2.VideoCapture(
            self.camera_index,
            cv2.CAP_DSHOW
        )

        if not self.cap.isOpened():
            self.cap.release()
            self.cap = None
            self.camera_error = "Could not open camera"
            return False

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # Request a faster camera format where supported
        self.cap.set(cv2.CAP_PROP_FOURCC,
                     cv2.VideoWriter_fourcc(*"MJPG"))

        self.camera_error = None
        self.running = True

        self.thread = threading.Thread(
            target=self._camera_loop,
            daemon=True
        )
        self.thread.start()

        return True

    def _camera_loop(self):
        while self.running:
            try:
                ok, frame = self.cap.read()

                if not ok:
                    self.camera_error = "Camera frame unavailable"
                    time.sleep(0.05)
                    continue

                # Resize camera frame
                frame = cv2.resize(
                    frame,
                    (self.frame_width, self.frame_height),
                    interpolation=cv2.INTER_AREA
                )

                # Faster YOLO inference
                results = self.model.predict(
                    source=frame,
                    imgsz=self.image_size,
                    conf=self.confidence_threshold,
                    max_det=10,
                    verbose=False,
                    device="cpu"
                )

                detections = []

                for result in results:
                    for box in result.boxes:
                        x1, y1, x2, y2 = map(
                            int, box.xyxy[0].tolist()
                        )

                        class_id = int(box.cls[0])
                        confidence = float(box.conf[0])
                        label = self.model.names[class_id]

                        detections.append({
                            "label": label,
                            "confidence": round(
                                confidence * 100, 1
                            ),
                            "bbox": [
                                x1,
                                y1,
                                x2 - x1,
                                y2 - y1
                            ],
                            "center_px": [
                                (x1 + x2) // 2,
                                (y1 + y2) // 2
                            ]
                        })

                        cv2.rectangle(
                            frame,
                            (x1, y1),
                            (x2, y2),
                            (0, 220, 80),
                            2
                        )

                        text = (
                            f"{label} "
                            f"{confidence * 100:.0f}%"
                        )

                        cv2.putText(
                            frame,
                            text,
                            (x1, max(20, y1 - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            (0, 220, 80),
                            2
                        )

                with self.lock:
                    self.latest_frame = frame
                    self.latest_detections = detections

                self.camera_error = None

            except Exception as error:
                self.camera_error = str(error)
                time.sleep(0.1)

    def read(self):
        with self.lock:
            if self.latest_frame is None:
                return None, []

            return (
                self.latest_frame.copy(),
                list(self.latest_detections)
            )

    def stop(self):
        self.running = False

        if self.thread is not None:
            self.thread.join(timeout=3)
            self.thread = None

        if self.cap is not None:
            self.cap.release()
            self.cap = None

        with self.lock:
            self.latest_frame = None
            self.latest_detections = []
