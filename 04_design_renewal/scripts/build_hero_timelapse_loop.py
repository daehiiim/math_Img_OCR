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
    parser.add_argument("--blend-seconds", type=float, default=0.6)
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


def build_output_positions(start_index: int, end_index: int, output_frame_count: int) -> list[float]:
    """출력 프레임이 소스 구간 전체를 균등하게 훑도록 위치를 만든다."""
    if output_frame_count <= 1:
        return [float(start_index)]
    return np.linspace(start_index, end_index, output_frame_count).tolist()


def calculate_full_resolution_flow(frame_a: np.ndarray, frame_b: np.ndarray, flow_scale: float = 0.25) -> np.ndarray:
    """두 프레임 사이의 저해상도 광류를 계산해 원본 해상도로 복원한다."""
    gray_a = cv2.cvtColor(frame_a, cv2.COLOR_BGR2GRAY)
    gray_b = cv2.cvtColor(frame_b, cv2.COLOR_BGR2GRAY)
    small_a = cv2.resize(gray_a, None, fx=flow_scale, fy=flow_scale, interpolation=cv2.INTER_AREA)
    small_b = cv2.resize(gray_b, None, fx=flow_scale, fy=flow_scale, interpolation=cv2.INTER_AREA)
    flow = cv2.calcOpticalFlowFarneback(small_a, small_b, None, 0.5, 3, 15, 3, 5, 1.2, 0)
    full_flow = cv2.resize(flow, (frame_a.shape[1], frame_a.shape[0]), interpolation=cv2.INTER_LINEAR)
    return full_flow * (1.0 / flow_scale)


def warp_frame_with_flow(frame: np.ndarray, flow: np.ndarray, strength: float) -> np.ndarray:
    """광류 방향으로 프레임을 이동시켜 중간 장면을 추정한다."""
    height, width = frame.shape[:2]
    grid_x, grid_y = np.meshgrid(np.arange(width, dtype=np.float32), np.arange(height, dtype=np.float32))
    map_x = grid_x + flow[..., 0].astype(np.float32) * strength
    map_y = grid_y + flow[..., 1].astype(np.float32) * strength
    return cv2.remap(frame, map_x, map_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def interpolate_frames(frame_a: np.ndarray, frame_b: np.ndarray, flow_cache: dict[tuple[int, int], np.ndarray], index_pair: tuple[int, int], fraction: float) -> np.ndarray:
    """두 프레임과 광류 캐시를 이용해 중간 프레임을 만든다."""
    if fraction <= 0:
        return frame_a.copy()
    if fraction >= 1:
        return frame_b.copy()
    flow = flow_cache.setdefault(index_pair, calculate_full_resolution_flow(frame_a, frame_b))
    inverse_key = (index_pair[1], index_pair[0])
    inverse_flow = flow_cache.setdefault(inverse_key, calculate_full_resolution_flow(frame_b, frame_a))
    warped_a = warp_frame_with_flow(frame_a, flow, fraction)
    warped_b = warp_frame_with_flow(frame_b, inverse_flow, 1.0 - fraction)
    return cv2.addWeighted(warped_a, 1.0 - fraction, warped_b, fraction, 0.0)


def render_output_frames(source_frames: list[np.ndarray], positions: list[float]) -> list[np.ndarray]:
    """소스 프레임과 보간 위치를 이용해 최종 출력 프레임 배열을 만든다."""
    flow_cache: dict[tuple[int, int], np.ndarray] = {}
    output_frames: list[np.ndarray] = []
    for position in positions:
        lower_index = int(np.floor(position))
        upper_index = min(lower_index + 1, len(source_frames) - 1)
        fraction = position - lower_index
        output_frames.append(
            interpolate_frames(
                source_frames[lower_index],
                source_frames[upper_index],
                flow_cache,
                (lower_index, upper_index),
                fraction,
            )
        )
    return output_frames


def blend_loop_tail(frames: list[np.ndarray], blend_frame_count: int) -> None:
    """마지막 구간을 첫 구간과 교차 블렌드해 루프 경계를 완화한다."""
    if blend_frame_count <= 0 or blend_frame_count >= len(frames):
        return
    total_frame_count = len(frames)
    for offset in range(blend_frame_count):
        alpha = (offset + 1) / (blend_frame_count + 1)
        tail_index = total_frame_count - blend_frame_count + offset
        frames[tail_index] = cv2.addWeighted(frames[tail_index], 1.0 - alpha, frames[offset], alpha, 0.0)


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
    output_frame_count = int(round(arguments.duration_seconds * arguments.output_fps))
    blend_frame_count = int(round(arguments.blend_seconds * arguments.output_fps))
    positions = build_output_positions(0, usable_end_index, output_frame_count)
    output_frames = render_output_frames(source_frames, positions)
    blend_loop_tail(output_frames, blend_frame_count)
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
    print(f"output_frame_count={output_frame_count}")
    print(f"blend_frame_count={blend_frame_count}")


def main() -> None:
    """명령행 실행 시 루프 자산 생성을 시작한다."""
    arguments = parse_args()
    build_loop_assets(arguments)


if __name__ == "__main__":
    main()
