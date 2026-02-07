# Sentinel AI: Classroom Engagement Monitor

A real-time classroom engagement monitoring system that uses voice activity detection to measure student participation. Designed for deployment on edge devices (Raspberry Pi) to provide privacy-preserving, low-latency engagement analytics.

## Problem Statement

Teachers need real-time feedback on classroom engagement to adjust their instruction dynamically. Traditional methods (visual observation, post-class surveys) are subjective, labor-intensive, and don't provide actionable data during the lesson. This system addresses that gap by quantifying vocal engagement automatically and unobtrusively.

## How It Works

Sentinel AI uses **signal processing-based voice activity detection (VAD)** rather than heavy machine learning models, optimized for resource-constrained edge computing:

1. **Continuous Audio Capture**: Records 60-second audio samples using a ReSpeaker Mic Array v3.0
2. **Frame-Based Analysis**: Splits each recording into 0.5-second frames (120 frames per cycle)
3. **RMS Energy Calculation**: Computes Root Mean Square energy for each frame as a proxy for loudness
4. **Threshold Classification**: Compares frame energy against a calibrated baseline (set above ambient noise floor)
5. **Engagement Scoring**: Calculates voice activity percentage and maps to engagement levels:
   - **0-10%**: SILENT
   - **10-30%**: LOW
   - **30-60%**: MEDIUM  
   - **60%+**: HIGH
6. **Data Logging**: Stores timestamped results in CSV format for analysis

### Technical Design Decision

**Why not ML-based speaker diarization?**

Initial development used `pyannote.audio` (via Hugging Face) for speaker counting with DBSCAN clustering. However, speaker embeddings failed to separate reliably on Raspberry Pi hardware—voice embedding distances clustered too tightly (0.22–0.24 cosine distance) to distinguish individual speakers.

**The pivot:** Switching to RMS-based voice activity detection provided:
      Reliable performance on constrained hardware
      Faster processing (no model loading overhead)
      Privacy preservation (no voice embeddings stored)
      More actionable metric (total engagement vs. speaker count)

This demonstrates **engineering judgment**: selecting the right tool for the problem constraints rather than defaulting to complex ML.

## Hardware Requirements

- **Raspberry Pi 5** (tested on Pi 5; Pi 4 should work)
- **ReSpeaker Mic Array v3.0** (or compatible USB microphone)
- **MicroSD card** (16GB+ recommended)

## Software Dependencies

```bash
# System packages
sudo apt-get update
sudo apt-get install alsa-utils

# Python packages
pip install numpy
```

## Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/johnbryanthompson1/sentinel_ai.git
   cd sentinel_ai
   ```

2. **Verify microphone detection:**
   ```bash
   arecord -l
   ```
   Note the card number for your microphone (e.g., `card 0`).

3. **Update audio device in code** (if needed):
   Edit `sentinel_voice.py` and set `AUDIO_CARD` to match your device:
   ```python
   AUDIO_CARD = "0"  # Change to your card number
   ```

4. **Calibrate noise threshold:**
   - Record 60 seconds of silence to establish ambient noise floor
   - Note the max RMS value from output
   - Set `BASELINE_THRESHOLD` in `sentinel_voice.py` ~20-30 points above that max

## Usage

Run the monitoring system:

```bash
python3 sentinel_voice.py
```

**Output:**
- Real-time console feedback showing voice activity % and engagement level
- Timestamped CSV log (`engagement_log.csv`) with detailed metrics

**To stop:** Press `Ctrl+C`

## Real-World Validation

Tested in live high school English classroom (Concordia International School Shanghai):
      High engagement detected during class discussions
      Silent/low engagement detected during independent work
      Reliable performance across 40-minute class periods


## Author

**John Thompson** 
Teacher & AI Researcher  
PhD Candidate, Texas Tech University  
Concordia International School Shanghai

## License

MIT License - See LICENSE file for details

---

*This project demonstrates practical application of edge AI for educational technology, with emphasis on privacy-preserving design, resource optimization, and real-world deployment constraints.*
