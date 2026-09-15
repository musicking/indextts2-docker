"""Static regression checks for required audio.cpp production features."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class AudioCppBuildConfigTests(unittest.TestCase):
    def test_native_model_manager_is_explicitly_enabled(self):
        dockerfile = (ROOT / "docker/audio-cpp/Dockerfile").read_text()
        self.assertIn("-DAUDIOCPP_BUILD_NATIVE_MODEL_MANAGER=ON", dockerfile)

    def test_all_required_model_families_are_compiled(self):
        dockerfile = (ROOT / "docker/audio-cpp/Dockerfile").read_text()
        self.assertIn(
            '-DAUDIOCPP_MODELS="index_tts2;voxcpm2;qwen3_asr;qwen3_forced_aligner"',
            dockerfile,
        )


if __name__ == "__main__":
    unittest.main()
