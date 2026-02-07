import subprocess
import numpy as np
import wave
import warnings
import datetime
import time
import csv
import signal
import sys
import os

warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
RECORDING_DURATION = 60       # seconds per cycle
AUDIO_FILE = "temp_recording.wav"
LOG_FILE = "engagement_log.csv"
AUDIO_CARD = 0                # Change this if ReSpeaker card number changes (check with: arecord -l)
FRAME_SIZE = 0.5              # seconds per analysis frame
BASELINE_THRESHOLD = 200      # Fixed RMS threshold above silence noise floor (~45 mean, ~106 max).
                              # Calibrated from silence test. Adjust if you move rooms.

# ─────────────────────────────────────────────
# ENGAGEMENT THRESHOLDS (voice activity %)
# ─────────────────────────────────────────────
# Adjust these based on how your classroom sounds in practice
THRESHOLDS = {
    "SILENT":   (0, 5),
    "LOW":      (6, 25),
    "MODERATE": (26, 50),
    "HIGH":     (51, 75),
    "VERY HIGH":(76, 100)
}

# ─────────────────────────────────────────────
# GRACEFUL EXIT ON CTRL+C
# ─────────────────────────────────────────────
running = True

def handle_exit(sig, frame):
    global running
    running = False
    print("\nMonitoring stopped.")
    print(f"Engagement data saved to: {LOG_FILE}")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)

# ─────────────────────────────────────────────
# SETUP: Create or open CSV log file
# ─────────────────────────────────────────────
def init_log():
    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "voice_activity_pct", "engagement_level", "active_frames", "total_frames"])
    print(f"Logging to: {LOG_FILE}")

# ─────────────────────────────────────────────
# RECORD AUDIO
# ─────────────────────────────────────────────
def record_audio():
    """Record audio using arecord from the ReSpeaker mic array."""
    record_command = [
        "arecord",
        "-D", f"plughw:{AUDIO_CARD},0",
        "-f", "cd",          # CD quality: 16-bit, 44100 Hz, stereo
        "-d", str(RECORDING_DURATION),
        AUDIO_FILE
    ]
    result = subprocess.run(record_command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  Recording error: {result.stderr}")
        return False
    return True

# ─────────────────────────────────────────────
# ANALYZE AUDIO: Voice Activity Detection
# ─────────────────────────────────────────────
def analyze_audio(audio_file):
    """
    Detect voice activity using RMS energy thresholding.

    How it works:
    1. Read the .wav file into a numpy array of sample amplitudes.
    2. Split the audio into short frames (FRAME_SIZE seconds each).
    3. Compute the RMS (Root Mean Square) energy of each frame.
       RMS is a good proxy for loudness / signal power.
    4. Compare each frame's RMS against a fixed BASELINE_THRESHOLD,
       calibrated from a silence test (set just above the noise floor).
       Frames above this threshold are classified as "active" (speech).
    5. Voice activity % = (active frames / total frames) * 100.
    """
    try:
        # --- Read the WAV file ---
        with wave.open(audio_file, 'rb') as wav_file:
            sample_rate = wav_file.getframerate()
            n_channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            n_frames = wav_file.getnframes()
            raw_data = wav_file.readframes(n_frames)

        print(f"    Audio: {sample_rate}Hz, {n_channels}ch, {n_frames} samples")

        # --- Convert raw bytes to numpy array ---
        # sampwidth 2 = 16-bit signed integers
        audio_data = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32)

        # If stereo, average channels down to mono
        if n_channels > 1:
            audio_data = audio_data.reshape(-1, n_channels).mean(axis=1)
            print(f"    Converted {n_channels}-channel to mono")

        # --- Split into frames and compute RMS per frame ---
        samples_per_frame = int(sample_rate * FRAME_SIZE)
        n_full_frames = len(audio_data) // samples_per_frame

        if n_full_frames == 0:
            print("    Not enough audio data to analyze")
            return 0.0, "SILENT", 0, 0

        rms_values = []
        for i in range(n_full_frames):
            frame = audio_data[i * samples_per_frame : (i + 1) * samples_per_frame]
            rms = np.sqrt(np.mean(frame ** 2))
            rms_values.append(rms)

        rms_values = np.array(rms_values)
        print(f"    Analyzed {n_full_frames} frames ({FRAME_SIZE}s each)")
        print(f"    RMS range: {rms_values.min():.1f} – {rms_values.max():.1f} | Mean: {rms_values.mean():.1f}")

        # --- Fixed baseline threshold (calibrated from silence test) ---
        print(f"    Activity threshold: {BASELINE_THRESHOLD} (fixed baseline)")

        # --- Count active frames ---
        active_frames = int(np.sum(rms_values > BASELINE_THRESHOLD))
        total_frames = n_full_frames
        voice_activity_pct = round((active_frames / total_frames) * 100, 1)

        print(f"    Active frames: {active_frames}/{total_frames} → {voice_activity_pct}% voice activity")

        # --- Map to engagement level ---
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
# LOG RESULTS TO CSV
# ─────────────────────────────────────────────
def log_result(timestamp, voice_activity_pct, engagement, active_frames, total_frames):
    with open(LOG_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, voice_activity_pct, engagement, active_frames, total_frames])

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

        # Record
        if not record_audio():
            print("  Skipping this cycle due to recording error.\n")
            time.sleep(2)
            continue

        # Analyze
        print("  Analyzing...")
        voice_pct, engagement, active, total = analyze_audio(AUDIO_FILE)

        if engagement == "ERROR":
            print("  Skipping this cycle due to analysis error.\n")
            continue

        # Log
        log_result(timestamp, voice_pct, engagement, active, total)

        # Display
        print(f"  ✓ Voice Activity: {voice_pct}% | Engagement: {engagement}\n")

        # Clean up temp file
        if os.path.exists(AUDIO_FILE):
            os.remove(AUDIO_FILE)

if __name__ == "__main__":
    main()
