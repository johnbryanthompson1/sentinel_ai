# sentinel_ai
Classroom engagement monitoring system using voice activity detection on Raspberry Pi with a ReSpeaker Mic Array.

Background
I'm a high school English teacher. One of the harder parts of the job is knowing whether a class is actually engaged or just quiet. Those aren't the same thing, and gut instinct only gets you so far after a long day.
I built this to see if a cheap edge device could give me something more objective — not surveillance, just signal. Is talking happening? How much? Compared to what?

What it does
Every 60 seconds, the script records audio, splits it into half-second frames, and computes the RMS energy of each frame. Frames above a dynamic threshold count as "active." That percentage gets logged to a CSV with a timestamp and an engagement label.
That's it. No cloud, no model inference, no data leaving the room.
Engagement levels:
LabelVoice activityHIGH40–100%MEDIUM15–39%LOW5–14%SILENT0–4%

Why not speaker diarization?
The original version used resemblyzer with DBSCAN clustering to count distinct voices. On the Pi 5, it didn't work well — embeddings clustered too tightly (cosine distances in the 0.22–0.24 range) to reliably separate speakers. The model couldn't tell one person from two.
Switching to RMS-based VAD was faster to calibrate, more stable across recordings, and honestly more useful. Whether students are talking matters more than exactly how many.

Hardware

Raspberry Pi 5
ReSpeaker Mic Array v3.0 (USB — no GPIO needed)


Setup
bashgit clone https://github.com/johnbryanthompson1/sentinel_ai.git
cd sentinel_ai
Check that your mic is detected:
basharecord -l
Note the card number. Open sentinel_voice.py and update this line if it's not 0:
pythonAUDIO_CARD = "0"
Then calibrate the baseline. Run the script in an empty room for a minute and watch the RMS output. Set BASELINE_THRESHOLD about 20–30 points above whatever the max is. This keeps HVAC noise and ambient hum from tripping the detector.

Running it
bashpython3 sentinel_voice.py
You'll see per-cycle output in the terminal. Results also write to engagement_log.csv. Stop it with Ctrl+C.

Does it work?
Tested in a live high school classroom in Shanghai across several class periods. High engagement registered during discussions; silent/low during independent work and tests. It held up consistently across 40-minute periods without needing manual resets.

What's next

Trend visualization across multiple days
Rolling baseline calibration
Canvas LMS integration


Author
John Thompson — high school English teacher, PhD (Texas Tech).
Building things at the intersection of education and AI.
