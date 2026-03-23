from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def load_loop_builder_module():
    """히어로 루프 생성 스크립트 모듈을 동적으로 불러온다."""
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "build_hero_timelapse_loop.py"
    spec = spec_from_file_location("build_hero_timelapse_loop", module_path)
    module = module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_find_brightness_cutoff_index_detects_first_bright_spike():
    """밝기 급등이 시작되는 첫 프레임 인덱스를 찾아야 한다."""
    module = load_loop_builder_module()
    brightness_values = [31.0, 31.2, 30.9, 31.1, 31.0, 40.5, 45.0]

    cutoff_index = module.find_brightness_cutoff_index(brightness_values, window_size=4, spike_ratio=1.18)

    assert cutoff_index == 5


def test_build_output_positions_spans_full_source_range():
    """출력 타임라인은 소스 구간 처음과 끝을 모두 포함해야 한다."""
    module = load_loop_builder_module()

    positions = module.build_output_positions(start_index=10, end_index=14, output_frame_count=9)

    assert positions[0] == 10
    assert positions[-1] == 14
    assert positions[4] == 12
