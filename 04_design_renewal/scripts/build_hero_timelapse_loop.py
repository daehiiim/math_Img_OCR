from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np


EXPECTED_ERRORS = {
    "ffmpeg_missing": "루프 자산 생성 도구가 없어 작업을 완료할 수 없습니다.",
    "source_read_failed": "원본 자산 분석 또는 재인코딩 중 오류가 발생해 새 루프 자산 생성이 중단되었습니다.",
    "encode_failed": "비디오 인코딩 중 오류가 발생해 새 루프 자산 생성이 중단되었습니다.",
}

DEFAULT_SOURCE_PATH = Path(r"D:\03_PROJECT\05_mathOCR\04_new_design\star-timelapse.mp4")
DEFAULT_MP4_PATH = Path(r"D:\03_PROJECT\05_mathOCR\04_design_renewal\src\assets\home\hero-timelapse.mp4")
DEFAULT_WEBM_PATH = Path(r"D:\03_PROJECT\05_mathOCR\04_design_renewal\src\assets\home\hero-timelapse.webm")
DEFAULT_POSTER_PATH = Path(r"D:\03_PROJECT\05_mathOCR\04_design_renewal\src\assets\home\hero-timelapse-poster.jpg")


def parse_args() -> argparse.Namespace:
    """루프 자산 생성에 필요한 실행 인자를 해석한다."""
    parser = argparse.ArgumentParser(description="공개 홈 히어로용 15초 루프 자산을 다시 생성한다.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE_PATH)
    parser.add_argument("--mp4-output", type=Path, default=DEFAULT_MP4_PATH)
    parser.add_argument("--webm-output", type=Path, default=DEFAULT_WEBM_PATH)
    parser.add_argument("--poster-output", type=Path, default=DEFAULT_POSTER_PATH)
    parser.add_argument("--duration-seconds", type=float, default=15.0)
    parser.add_argument("--output-fps", type=float, default=25.0)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    return parser.parse_args()


def resolve_ffmpeg_executable() -> str:
    """사용 가능한 ffmpeg 실행 파일 경로를 찾는다."""
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return ffmpeg_path
    try:
        import imageio_ffmpeg
    except ImportError as error:
        raise RuntimeError(EXPECTED_ERRORS["ffmpeg_missing"]) from error
    return imageio_ffmpeg.get_ffmpeg_exe()


def run_ffmpeg_command(command: list[str]) -> None:
    """ffmpeg 명령을 실행하고 실패 시 한국어 예외를 던진다."""
    completed = subprocess.run(command, check=False, capture_output=True, text=True, shell=False)
    if completed.returncode == 0:
        return
    stderr_text = completed.stderr.strip()
    raise RuntimeError(f"{EXPECTED_ERRORS['encode_failed']}\n{stderr_text}")


def load_resized_frames(source_path: Path, target_size: tuple[int, int]) -> tuple[list[np.ndarray], list[float], float]:
    """원본 비디오를 읽어 목표 해상도의 프레임과 밝기 배열을 만든다."""
    capture = cv2.VideoCapture(str(source_path))
    fps = capture.get(cv2.CAP_PROP_FPS) or 0.0
    if not fps:
        raise RuntimeError(EXPECTED_ERRORS["source_read_failed"])
    frames: list[np.ndarray] = []
    brightness_values: list[float] = []
    while True:
        is_ready, frame = capture.read()
        if not is_ready:
            break
        resized_frame = cv2.resize(frame, target_size, interpolation=cv2.INTER_AREA)
        frames.append(resized_frame)
        brightness_values.append(float(resized_frame.mean()))
    capture.release()
    if not frames:
        raise RuntimeError(EXPECTED_ERRORS["source_read_failed"])
    return frames, brightness_values, fps


def find_brightness_cutoff_index(brightness_values: list[float], window_size: int = 12, spike_ratio: float = 1.07) -> int:
    """밝기 급등이 시작되는 첫 프레임 인덱스를 반환한다."""
    if len(brightness_values) <= window_size:
        return len(brightness_values) - 1
    for index in range(window_size, len(brightness_values)):
        previous_window = brightness_values[index - window_size : index]
        baseline = sum(previous_window) / len(previous_window)
        if brightness_values[index] > baseline * spike_ratio:
            return index
    return len(brightness_values) - 1


def build_repeated_frame_indices(start_index: int, end_index: int, output_frame_count: int) -> list[int]:
    """루프 구간 인덱스를 출력 길이만큼 반복 배치한다."""
    loop_indices = list(range(start_index, end_index))
    if not loop_indices:
        raise RuntimeError(EXPECTED_ERRORS["source_read_failed"])
    output_indices: list[int] = []
    while len(output_indices) < output_frame_count:
        remaining_count = output_frame_count - len(output_indices)
        output_indices.extend(loop_indices[:remaining_count])
    return output_indices


def build_gray_thumbnails(source_frames: list[np.ndarray], usable_end_index: int) -> list[np.ndarray]:
    """루프 경계 비교용 저해상도 그레이스케일 프레임을 만든다."""
    thumbnails: list[np.ndarray] = []
    for frame in source_frames[: usable_end_index + 1]:
        resized_frame = cv2.resize(frame, (320, 180), interpolation=cv2.INTER_AREA)
        thumbnails.append(cv2.cvtColor(resized_frame, cv2.COLOR_BGR2GRAY))
    return thumbnails


def measure_frame_difference(frame_a: np.ndarray, frame_b: np.ndarray) -> float:
    """두 저해상도 프레임의 평균 차이를 계산한다."""
    return float(np.mean(np.abs(frame_a.astype(np.int16) - frame_b.astype(np.int16))))


def find_best_loop_bounds(source_frames: list[np.ndarray], usable_end_index: int, min_loop_frames: int = 95, max_start_index: int = 12) -> tuple[int, int]:
    """자연스럽게 이어지는 원본 프레임 구간의 시작과 끝을 찾는다."""
    thumbnails = build_gray_thumbnails(source_frames, usable_end_index)
    best_score: float | None = None
    best_bounds = (0, min(len(thumbnails), min_loop_frames))
    for start_index in range(0, min(max_start_index, usable_end_index - min_loop_frames) + 1):
        for end_index in range(start_index + min_loop_frames, usable_end_index + 1):
            difference = measure_frame_difference(thumbnails[start_index], thumbnails[end_index])
            duration_score = (end_index - start_index) * 0.02
            score = difference - duration_score
            if best_score is None or score < best_score:
                best_score = score
                best_bounds = (start_index, end_index)
    return best_bounds


def select_output_frames(source_frames: list[np.ndarray], frame_indices: list[int]) -> list[np.ndarray]:
    """반복 인덱스 목록을 실제 출력 프레임 배열로 변환한다."""
    return [source_frames[index].copy() for index in frame_indices]


def write_frame_sequence(temp_directory: Path, frames: list[np.ndarray]) -> None:
    """ffmpeg 입력용 PNG 프레임 시퀀스를 임시 디렉터리에 저장한다."""
    for index, frame in enumerate(frames):
        frame_path = temp_directory / f"frame-{index:04d}.png"
        cv2.imwrite(str(frame_path), frame)


def encode_mp4(ffmpeg_path: str, temp_directory: Path, fps: float, output_path: Path) -> None:
    """PNG 시퀀스를 웹 호환 MP4 파일로 인코딩한다."""
    command = [
        ffmpeg_path,
        "-y",
        "-framerate",
        f"{fps:.2f}",
        "-i",
        str(temp_directory / "frame-%04d.png"),
        "-c:v",
        "libx264",
        "-preset",
        "slow",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    run_ffmpeg_command(command)


def encode_webm(ffmpeg_path: str, temp_directory: Path, fps: float, output_path: Path) -> None:
    """PNG 시퀀스를 브라우저용 WebM 파일로 인코딩한다."""
    command = [
        ffmpeg_path,
        "-y",
        "-framerate",
        f"{fps:.2f}",
        "-i",
        str(temp_directory / "frame-%04d.png"),
        "-c:v",
        "libvpx-vp9",
        "-crf",
        "28",
        "-b:v",
        "0",
        "-pix_fmt",
        "yuv420p",
        str(output_path),
    ]
    run_ffmpeg_command(command)


def write_poster(output_path: Path, frame: np.ndarray) -> None:
    """대표 프레임을 JPEG poster 이미지로 저장한다."""
    cv2.imwrite(str(output_path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 92])


def ensure_parent_directories(*paths: Path) -> None:
    """출력 파일 상위 디렉터리를 미리 생성한다."""
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)


def build_loop_assets(arguments: argparse.Namespace) -> None:
    """원본 영상에서 새 히어로 루프 자산 세 종류를 생성한다."""
    ffmpeg_path = resolve_ffmpeg_executable()
    target_size = (arguments.width, arguments.height)
    source_frames, brightness_values, source_fps = load_resized_frames(arguments.source, target_size)
    cutoff_index = find_brightness_cutoff_index(brightness_values)
    safety_margin_frames = int(round(source_fps * 0.4))
    usable_end_index = max(cutoff_index - safety_margin_frames, 1)
    loop_start_index, loop_end_index = find_best_loop_bounds(source_frames, usable_end_index)
    output_frame_count = int(round(arguments.duration_seconds * arguments.output_fps))
    frame_indices = build_repeated_frame_indices(loop_start_index, loop_end_index, output_frame_count)
    output_frames = select_output_frames(source_frames, frame_indices)
    ensure_parent_directories(arguments.mp4_output, arguments.webm_output, arguments.poster_output)
    with tempfile.TemporaryDirectory(prefix="hero-loop-") as temp_directory_name:
        temp_directory = Path(temp_directory_name)
        write_frame_sequence(temp_directory, output_frames)
        encode_mp4(ffmpeg_path, temp_directory, arguments.output_fps, arguments.mp4_output)
        encode_webm(ffmpeg_path, temp_directory, arguments.output_fps, arguments.webm_output)
    write_poster(arguments.poster_output, output_frames[int(len(output_frames) * 0.2)])
    print(f"source_fps={source_fps:.2f}")
    print(f"cutoff_index={cutoff_index}")
    print(f"safety_margin_frames={safety_margin_frames}")
    print(f"usable_end_index={usable_end_index}")
    print(f"loop_start_index={loop_start_index}")
    print(f"loop_end_index={loop_end_index}")
    print(f"loop_duration_frames={loop_end_index - loop_start_index}")
    print(f"output_frame_count={output_frame_count}")


def main() -> None:
    """명령행 실행 시 루프 자산 생성을 시작한다."""
    arguments = parse_args()
    build_loop_assets(arguments)


if __name__ == "__main__":
    main()
