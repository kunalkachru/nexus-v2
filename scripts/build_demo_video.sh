#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${ROOT_DIR}/artifacts/demo-video"
TMP_DIR="${OUTPUT_DIR}/tmp"
SEGMENTS_DIR="${TMP_DIR}/narration_segments"
BASE_URL="${DEMO_BASE_URL:-http://127.0.0.1:7860}"

mkdir -p "${OUTPUT_DIR}" "${TMP_DIR}" "${SEGMENTS_DIR}"

if ! curl -fsS "${BASE_URL}/health" >/dev/null 2>&1; then
  echo "Expected a running app at ${BASE_URL}. Start it first, for example with ./scripts/docker_fresh.sh" >&2
  exit 1
fi

NARRATION_TXT="${OUTPUT_DIR}/narration.txt"
cat > "${NARRATION_TXT}" <<'EOF'
NEXUS v2 starts from raw incident intake.
Here, we load example logs and submit them as a live incident.

The system redirects straight into Incident Detail.
SENTINEL classifies the incident, PRISM diagnoses the root cause,
FORGE prepares the runbook, and GUARDIAN becomes the explicit safety gate.

The application is deterministic and safe by default.
If a user wants live reasoning, they can bring their own OpenAI key,
without exposing or spending the project owner's API credits.

Now we approve the runbook.
Guardian moves the incident into an approved and executed state,
so the operator can see the governance decision and the final outcome clearly.

Finally, we open Learning and Controls.
This view shows the reward curve across thirty episodes,
the improvement of the four-agent crew,
and the governance posture that stays visible while the system learns.
EOF

SEGMENT_1="${SEGMENTS_DIR}/01.aiff"
SEGMENT_2="${SEGMENTS_DIR}/02.aiff"
SEGMENT_3="${SEGMENTS_DIR}/03.aiff"
SEGMENT_4="${SEGMENTS_DIR}/04.aiff"
SEGMENT_5="${SEGMENTS_DIR}/05.aiff"

say -v Samantha -r 182 -o "${SEGMENT_1}" "NEXUS v2 starts from raw incident intake. Here, we load example logs and submit them as a live incident."
say -v Samantha -r 182 -o "${SEGMENT_2}" "The system redirects straight into Incident Detail. SENTINEL classifies the incident, PRISM diagnoses the root cause, FORGE prepares the runbook, and GUARDIAN becomes the explicit safety gate."
say -v Samantha -r 182 -o "${SEGMENT_3}" "The application is deterministic and safe by default. If a user wants live reasoning, they can bring their own OpenAI key, without exposing or spending the project owner's API credits."
say -v Samantha -r 182 -o "${SEGMENT_4}" "Now we approve the runbook. Guardian moves the incident into an approved and executed state, so the operator can see the governance decision and the final outcome clearly."
say -v Samantha -r 182 -o "${SEGMENT_5}" "Finally, we open Learning and Controls. This view shows the reward curve across thirty episodes, the improvement of the four agent crew, and the governance posture that stays visible while the system learns."

printf "file '%s'\nfile '%s'\nfile '%s'\nfile '%s'\nfile '%s'\n" \
  "${SEGMENT_1}" "${SEGMENT_2}" "${SEGMENT_3}" "${SEGMENT_4}" "${SEGMENT_5}" > "${TMP_DIR}/narration_concat.txt"

ffmpeg -y -f concat -safe 0 -i "${TMP_DIR}/narration_concat.txt" -c:a aac -b:a 192k "${OUTPUT_DIR}/narration.m4a" >/dev/null 2>&1

RAW_VIDEO_PATH="$(node "${ROOT_DIR}/scripts/generate_demo_video.mjs")"
cp "${RAW_VIDEO_PATH}" "${OUTPUT_DIR}/screen-recording.webm"

export OUTPUT_DIR
python - <<'PY'
import json
import os
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

output_dir = Path(os.environ["OUTPUT_DIR"])
segments = [
    "NEXUS v2 starts from raw incident intake. Here, we load example logs and submit them as a live incident.",
    "The system redirects straight into Incident Detail. SENTINEL classifies the incident, PRISM diagnoses the root cause, FORGE prepares the runbook, and GUARDIAN becomes the explicit safety gate.",
    "The application is deterministic and safe by default. If a user wants live reasoning, they can bring their own OpenAI key, without exposing or spending the project owner's API credits.",
    "Now we approve the runbook. Guardian moves the incident into an approved and executed state, so the operator can see the governance decision and the final outcome clearly.",
    "Finally, we open Learning and Controls. This view shows the reward curve across thirty episodes, the improvement of the four agent crew, and the governance posture that stays visible while the system learns.",
]
overlay_labels = [
    "Step 1: Load example logs and create a live incident",
    "Step 2: Watch SENTINEL, PRISM, FORGE, and GUARDIAN collaborate",
    "Safe by default: deterministic mode and optional BYO OpenAI key",
    "Step 3: Approve the runbook through Guardian",
    "Step 4: Review training progress across 30 episodes",
]

segment_paths = sorted((output_dir / "tmp" / "narration_segments").glob("*.aiff"))
durations = []
for path in segment_paths:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    durations.append(float(json.loads(result.stdout)["format"]["duration"]))

def stamp(seconds: float) -> str:
    ms = round(seconds * 1000)
    h, rem = divmod(ms, 3600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

cursor = 0.0
entries = []
for index, (text, duration) in enumerate(zip(segments, durations), start=1):
    start = cursor
    end = cursor + duration
    entries.append(f"{index}\n{stamp(start)} --> {stamp(end)}\n{text}\n")
    cursor = end

(output_dir / "captions.srt").write_text("\n".join(entries), encoding="utf-8")

font_path = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
font = ImageFont.truetype(font_path, 38)
small_font = ImageFont.truetype(font_path, 24)

overlay_dir = output_dir / "overlays"
overlay_dir.mkdir(parents=True, exist_ok=True)
for index, label in enumerate(overlay_labels, start=1):
    image = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((32, 560, 1248, 688), radius=28, fill=(12, 18, 32, 205))
    draw.text((64, 580), "NEXUS v2 Demo", font=small_font, fill=(133, 196, 255, 255))
    draw.text((64, 614), label, font=font, fill=(255, 255, 255, 255))
    image.save(overlay_dir / f"{index:02}.png")

filter_parts = []
last = "[0:v]"
for idx, duration in enumerate(durations, start=1):
    start = sum(durations[: idx - 1])
    end = start + duration
    input_index = idx
    out = f"[v{idx}]"
    filter_parts.append(
        f"{last}[{input_index}:v]overlay=0:0:enable='between(t,{start:.3f},{end:.3f})'{out}"
    )
    last = out

(output_dir / "overlay_filter.txt").write_text(";\n".join(filter_parts), encoding="utf-8")
PY

ffmpeg -y \
  -i "${OUTPUT_DIR}/screen-recording.webm" \
  -i "${OUTPUT_DIR}/overlays/01.png" \
  -i "${OUTPUT_DIR}/overlays/02.png" \
  -i "${OUTPUT_DIR}/overlays/03.png" \
  -i "${OUTPUT_DIR}/overlays/04.png" \
  -i "${OUTPUT_DIR}/overlays/05.png" \
  -i "${OUTPUT_DIR}/narration.m4a" \
  -filter_complex_script "${OUTPUT_DIR}/overlay_filter.txt" \
  -map "[v5]" -map 6:a \
  -c:v libx264 -preset veryfast -crf 22 \
  -c:a aac -b:a 192k \
  -pix_fmt yuv420p \
  -shortest \
  "${OUTPUT_DIR}/nexus-v2-demo.mp4" >/dev/null 2>&1

echo "Built demo video:"
echo "  ${OUTPUT_DIR}/nexus-v2-demo.mp4"
echo "Narration text:"
echo "  ${NARRATION_TXT}"
echo "Captions:"
echo "  ${OUTPUT_DIR}/captions.srt"
