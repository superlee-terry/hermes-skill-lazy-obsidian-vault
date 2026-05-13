---
categories:
- ffmpeg-video-truncation
description: Truncate video files using ffmpeg copy mode for fast, lossless clipping
name: ffmpeg-video-truncation
summary: Truncate video files using ffmpeg copy mode for fast, lossless clipping
triggers: []
---

# FFmpeg Video Truncation

Truncate (clip) a video file using ffmpeg without re-encoding.

## Command
```bash
ffmpeg -y -i input.mp4 -t <duration> -c copy -avoid_negative_ts 1 output.mp4
```

## Parameters
- `-y` — overwrite output without asking
- `-i` — input file
- `-t <seconds>` — duration to keep (everything from start)
- `-c copy` — **copy streams, do NOT re-encode** (fast, no quality loss)
- `-avoid_negative_ts 1` — fix timestamp issues
- `output.mp4` — output file

## Pitfall: Duration mismatch
`-c copy` copies the container format, not the exact duration. The output may be slightly longer than requested (up to a few hundred ms). Always verify with `ffprobe` if exact duration matters.

## Pitfall: Not all formats support `-c copy`
For fragmented MP4 (fMP4) or some HLS segments, `-c copy` may fail. In that case, re-encode with `-c:v libx264 -c:a aac` (slower but works).

## Pitfall: ffmpeg timeout
Large files can take time to seek. Use `timeout` or `subprocess.run(..., timeout=N)` to avoid hanging.

## Example: truncate to 10 minutes
```python
import subprocess
max_sec = 600  # 10 minutes
output = input_path.with_name(f"{input_path.stem}_truncated.mp4")
result = subprocess.run(
    ["ffmpeg", "-y", "-i", str(input_path), "-t", str(max_sec),
     "-c", "copy", "-avoid_negative_ts", "1", str(output)],
    capture_output=True, text=True, timeout=60,
)
```