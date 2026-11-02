"""Original standalone entry point from the upstream repository."""

from src.integration.drowsiness_monitor import run_monitor


if __name__ == "__main__":
    run_monitor(camera_index=0, threshold=15)
