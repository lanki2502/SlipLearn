"""Lightweight OpenCV vision system for SlipLearn.

Uses contour-based candidate localization so the dashboard can run without
large optional model packages. It does not claim semantic object recognition.
"""
import threading
import time

import cv2


class VisionSystem:
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.cap = None
        self.latest_frame = None
        self.latest_detections = []
        self.lock = threading.Lock()
        self.running = False
        self.thread = None
        self.camera_error = None
        self.frame_width = 640
        self.frame_height = 480
        self.min_contour_area = 700

    def start(self):
        if self.running:
            return True

        # CAP_ANY lets OpenCV select the available backend on Windows or Linux.
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            self.cap.release()
            self.cap = None
            self.camera_error = "Could not open camera on this host."
            return False

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.camera_error = None
        self.running = True
        self.thread = threading.Thread(target=self._camera_loop, daemon=True)
        self.thread.start()
        return True

    def _camera_loop(self):
        while self.running:
            try:
                if self.cap is None:
                    break

                ok, frame = self.cap.read()
                if not ok:
                    self.camera_error = "Camera frame unavailable."
                    time.sleep(0.05)
                    continue

                frame = cv2.resize(
                    frame,
                    (self.frame_width, self.frame_height),
                    interpolation=cv2.INTER_AREA,
                )

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                blurred = cv2.GaussianBlur(gray, (5, 5), 0)
                edges = cv2.Canny(blurred, 50, 150)
                contours, _ = cv2.findContours(
                    edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )

                detections = []
                candidates = sorted(
                    contours, key=cv2.contourArea, reverse=True
                )

                for contour in candidates:
                    area = float(cv2.contourArea(contour))
                    if area < self.min_contour_area:
                        continue

                    x, y, width, height = cv2.boundingRect(contour)
                    if width < 10 or height < 10:
                        continue

                    detections.append({
                        "label": "object candidate",
                        "confidence": None,
                        "bbox": [x, y, width, height],
                        "center_px": [x + width // 2, y + height // 2],
                        "area_px": int(area),
                    })

                    cv2.rectangle(
                        frame, (x, y), (x + width, y + height), (0, 220, 80), 2
                    )
                    cv2.putText(
                        frame,
                        "candidate",
                        (x, max(20, y - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 220, 80),
                        2,
                    )

                    if len(detections) >= 10:
                        break

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
            return self.latest_frame.copy(), list(self.latest_detections)

    def stop(self):
        self.running = False

        if self.thread is not None:
            self.thread.join(timeout=2)
            self.thread = None

        if self.cap is not None:
            self.cap.release()
            self.cap = None

        with self.lock:
            self.latest_frame = None
            self.latest_detections = []
