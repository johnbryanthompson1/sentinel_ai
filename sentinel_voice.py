"""
sentinel_voice.py
Sentinel AI — Classroom Engagement Monitor

Uses RMS energy-based voice activity detection to measure real-time
student engagement. Designed for Raspberry Pi 5 + ReSpeaker Mic Array v3.0.

Author: John Thompson
"""

import subprocess
import wave
import numpy as np
import csv
import datetime
import os
import time
import signal

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
AUDIO_CARD = "0"                  # Change to match your arecord card number
RECORDING_DURATION = 60           # Seconds per monitoring cycle
FRAME_SIZE = 0.5                  # Seconds per analysis frame
AUDIO_FILE = "/tmp/sentinel_temp.wav"
LOG_FILE = "engagement_log.csv"

# Baseline silence threshold — calibrate by recording 60s of silence
# and setting this ~20-30 points above the max RMS you observe
BASELINE_THRESHOLD = 500          # Adjust after calibration

# Engagement level thresholds (voice activity %)
THRESHOLDS = {
    "HIGH":   (40, 100),
    "MEDIUM": (15, 39),
    "LOW":    (5,  14),
    "SILENT": (0,   4),
}

running = True

# ─────────────────────────────────────────────
# GRACEFUL SHUTDOWN
# ─────────────────────────────────────────────
def handle_exit(sig, frame):
    global running
    print("\n\n[Sentinel AI] Stopping monitor... final log saved.")
    running = False

signal.signal(signal.SIGINT, handle_exit)

# ─────────────────────────────────────────────
# INITIALIZE CSV LOG
# ─────────────────────────────────────────────
def init_log():
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",
                "voice_activity_pct",
                "engagement_level",
                "active_frames",
                "total_frames"
            ])

# ─────────────────────────────────────────────
# RECORD AUDIO
# ─────────────────────────────────────────────
def record_audio():
    cmd = [
        "arecord",
        "-D", f"plughw:{AUDIO_CARD},0",
        "-f", "S16_LE",
        "-r", "16000",
        "-c", "1",
        "-d", str(RECORDING_DURATION),
        AUDIO_FILE
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"    Recording error: {e}")
        return False

# ─────────────────────────────────────────────
# ANALYZE AUDIO — RMS VOICE ACTIVITY DETECTION
# ─────────────────────────────────────────────
def analyze_audio(filepath):
    try:
        with wave.open(filepath, 'rb') as wf:
            sample_rate = wf.getframerate()
            n_channels = wf.getnchannels()
            raw = wf.readframes(wf.getnframes())

        # Convert raw bytes to numpy array
        samples = np.frombuffer(raw, dtype=np.int16)

        # If stereo, take first channel only
        if n_channels > 1:
            samples = samples[::n_channels]

        # Split into frames
        frame_length = int(sample_rate * FRAME_SIZE)
        n_full_frames = len(samples) // frame_length

        # RMS energy per frame
        rms_values = np.array([
            np.sqrt(np.mean(samples[i * frame_length:(i + 1) * frame_length].astype(np.float64) ** 2))
            for i in range(n_full_frames)
        ])

        print(f"    Frames: {n_full_frames} ({FRAME_SIZE}s each)")
        print(f"    RMS range: {rms_values.min():.1f} – {rms_values.max():.1f} | Mean: {rms_values.mean():.1f}")

        # Dynamic threshold: mean + 1 std dev (adaptive per cycle)
        dynamic_threshold = max(BASELINE_THRESHOLD, rms_values.mean() + rms_values.std())
        print(f"    Activity threshold: {dynamic_threshold:.1f}")

        # Count active frames
        active_frames = int(np.sum(rms_values > dynamic_threshold))
        total_frames = n_full_frames
        voice_activity_pct = round((active_frames / total_frames) * 100, 1)

        print(f"    Active frames: {active_frames}/{total_frames} → {voice_activity_pct}% voice activity")

        # Map to engagement level
        engagement = "SILENT"
        for level, (low, high) in THRESHOLDS.items():
            if low <= voice_activity_pct <= high:
                engagement = level
                break

        return voice_activity_pct, engagement, active_frames, total_frames

    except Exception as e:
        print(f"    Analysis error: {e}")
        return 0.0, "ERROR", 0, 0

# ─────────────────────────────────────────────
# LOG RESULT
# ─────────────────────────────────────────────
def log_result(timestamp, voice_pct, engagement, active_frames, total_frames):
    with open(LOG_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, voice_pct, engagement, active_frames, total_frames])

# ─────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────
def main():
    global running

    print("=" * 50)
    print("  SENTINEL AI — Classroom Engagement Monitor")
    print("=" * 50)
    print(f"  Recording: {RECORDING_DURATION}s cycles | Card: {AUDIO_CARD}")
    print(f"  Frame size: {FRAME_SIZE}s | Log: {LOG_FILE}")
    print("  Press Ctrl+C to stop monitoring")
    print("=" * 50 + "\n")

    init_log()

    while running:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Recording for {RECORDING_DURATION} seconds...")

        if not record_audio():
            print("  Skipping this cycle due to recording error.\n")
            time.sleep(2)
            continue

        print("  Analyzing...")
        voice_pct, engagement, active, total = analyze_audio(AUDIO_FILE)

        if engagement == "ERROR":
            print("  Skipping this cycle due to analysis error.\n")
            continue

        log_result(timestamp, voice_pct, engagement, active, total)
        print(f"  ✓ Voice Activity: {voice_pct}% | Engagement: {engagement}\n")

        if os.path.exists(AUDIO_FILE):
            os.remove(AUDIO_FILE)

if __name__ == "__main__":
    main()
