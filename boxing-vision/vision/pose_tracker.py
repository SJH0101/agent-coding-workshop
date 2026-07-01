"""
MediaPipe Pose 래퍼 — 웹캠 프레임에서 관절 좌표 추출 및 시각화.
MediaPipe Tasks API (v0.10.x) 기반.
"""

from mediapipe import Image, ImageFormat
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    PoseLandmarker,
    PoseLandmarkerOptions,
    PoseLandmarksConnections,
)
import cv2


class PoseTracker:
    """MediaPipe PoseLandmarker를 사용해 프레임당 관절 좌표를 추출하고 그려주는 클래스."""

    def __init__(self, model_path: str = "assets/pose_landmarker_heavy.task",
                 min_detection_confidence: float = 0.5,
                 min_tracking_confidence: float = 0.5,
                 num_poses: int = 1):
        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            min_pose_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
            num_poses=num_poses,
        )
        self.detector = PoseLandmarker.create_from_options(options)

        # 상체 연결선만 필터링
        upper_indices = {0, 11, 12, 13, 14, 15, 16, 23, 24}
        self.connections = [
            c for c in PoseLandmarksConnections.POSE_LANDMARKS
            if c.start in upper_indices and c.end in upper_indices
        ]

        # 시각화 색상
        self._conn_color = (0, 255, 0)
        self._lm_color = (0, 0, 255)
        self._lm_radius = 5
        self._conn_thickness = 2

    def process_frame(self, frame):
        """
        BGR 프레임을 받아 PoseLandmarker로 처리하고,
        랜드마크가 그려진 프레임과 landmarks 리스트를 반환.
        landmarks: list[NormalizedLandmark] | None
        """
        height, width, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = Image(image_format=ImageFormat.SRGB, data=rgb)

        results = self.detector.detect(mp_image)

        landmarks = None
        if results.pose_landmarks and len(results.pose_landmarks) > 0:
            landmarks = results.pose_landmarks[0]
            self._draw_landmarks(frame, landmarks, width, height)

        return frame, landmarks

    def get_landmark_dict(self, landmarks, width: int, height: int):
        """
        list[NormalizedLandmark]를 {이름: {x, y, z, v}} 딕셔너리로 변환.
        좌표는 픽셀 단위. 복싱에 필요한 관절만 추출.
        """
        if landmarks is None:
            return None

        keys = {
            "nose": 0,
            "left_shoulder": 11, "right_shoulder": 12,
            "left_elbow": 13, "right_elbow": 14,
            "left_wrist": 15, "right_wrist": 16,
            "left_hip": 23, "right_hip": 24,
        }

        result = {}
        for name, idx in keys.items():
            p = landmarks[idx]
            result[name] = {
                "x": int(p.x * width),
                "y": int(p.y * height),
                "z": p.z,
                "v": p.visibility,
            }
        return result

    def _draw_landmarks(self, frame, landmarks, width: int, height: int):
        """관절 연결선과 랜드마크 점을 프레임에 직접 그림."""
        # 연결선
        for conn in self.connections:
            p1 = (int(landmarks[conn.start].x * width),
                  int(landmarks[conn.start].y * height))
            p2 = (int(landmarks[conn.end].x * width),
                  int(landmarks[conn.end].y * height))
            cv2.line(frame, p1, p2, self._conn_color, self._conn_thickness)

        # 랜드마크 점
        for idx in [0, 11, 12, 13, 14, 15, 16, 23, 24]:
            cx = int(landmarks[idx].x * width)
            cy = int(landmarks[idx].y * height)
            cv2.circle(frame, (cx, cy), self._lm_radius, self._lm_color, -1)

    def release(self):
        self.detector.close()
