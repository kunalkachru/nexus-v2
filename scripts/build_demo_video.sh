#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${ROOT_DIR}/artifacts/demo-video"
TMP_DIR="${OUTPUT_DIR}/tmp"
SEGMENTS_DIR="${TMP_DIR}/narration_segments"
BASE_URL="${DEMO_BASE_URL:-http://127.0.0.1:7860}"

mkdir -p "${OUTPUT_DIR}" "${TMP_DIR}" "${SEGMENTS_DIR}"
rm -f "${SEGMENTS_DIR}"/*.aiff "${OUTPUT_DIR}/overlays/"*.png "${OUTPUT_DIR}/scene_plan.json" "${OUTPUT_DIR}/overlay_filter.txt" "${OUTPUT_DIR}/captions.srt" 2>/dev/null || true

if ! curl -fsS "${BASE_URL}/health" >/dev/null 2>&1; then
  echo "Expected a running app at ${BASE_URL}. Start it first, for example with ./scripts/docker_fresh.sh" >&2
  exit 1
fi

NARRATION_TXT="${OUTPUT_DIR}/narration.txt"
cat > "${NARRATION_TXT}" <<'EOF'
[Scene 1: Command Center]
NEXUS v2 opens in the Command Center. This is the live operational view of the product. Instead of starting with a wall of metrics, the interface leads with one active incident and a visible crew of autonomous agents. SENTINEL, PRISM, FORGE, and GUARDIAN are all shown as workers with clear roles, current tasks, and handoffs. The queue is still present, but it is intentionally secondary to the active incident story, so an operator can understand what the system is doing before diving into deeper detail.

[Scene 2: Inputs]
From here we open Inputs, which is the fastest path into the system. This screen is designed for raw incident intake. We can paste logs, stack traces, or operational notes, and the interface immediately normalizes them into structured evidence. In the demo, we load example logs so the service, severity, and likely error signature become visible before backend reasoning begins. This is important because it shows that NEXUS does not treat incident text as opaque data. It turns that text into a usable incident contract before handing it off to the agents.

[Scene 3: Incident Detail]
Once the logs are submitted, the app redirects directly into Incident Detail. This is the core product surface. SENTINEL classifies the incident, PRISM diagnoses the likely root cause, FORGE proposes the runbook, and GUARDIAN becomes the explicit governance gate. The handoff thread keeps that sequence visible so the system feels like a team of specialists working together, not a static dashboard. The product is also safe by default. Here we move to the visible BYO OpenAI key panel. Live reasoning is turned off, and if a user wants live OpenAI-backed behavior, they must bring their own key through this control. Now we approve the runbook, and the execution state moves cleanly through Guardian into an approved and executed outcome.

[Scene 4: Learning & Controls]
Finally, we open Learning and Controls. This screen makes the learning story easy to absorb. The reward curve shows thirty episodes of training, moving from a lower baseline to a stronger trained policy. The four-agent crew remains visible through the accuracy and summary metrics, and the governance posture stays present so learning never looks unbounded or unsafe. The result is a product that not only resolves incidents through a visible multi-agent flow, but also shows how that system improves over time without losing operator trust.
EOF

SCENE_1="${SEGMENTS_DIR}/01-command-center.aiff"
SCENE_2="${SEGMENTS_DIR}/02-inputs.aiff"
SCENE_3="${SEGMENTS_DIR}/03-incident-detail.aiff"
SCENE_4="${SEGMENTS_DIR}/04-learning-controls.aiff"

say -v Samantha -r 176 -o "${SCENE_1}" "NEXUS v2 opens in the Command Center. This is the live operational view of the product. Instead of starting with a wall of metrics, the interface leads with one active incident and a visible crew of autonomous agents. SENTINEL, PRISM, FORGE, and GUARDIAN are all shown as workers with clear roles, current tasks, and handoffs. The queue is still present, but it is intentionally secondary to the active incident story, so an operator can understand what the system is doing before diving into deeper detail."
say -v Samantha -r 176 -o "${SCENE_2}" "From here we open Inputs, which is the fastest path into the system. This screen is designed for raw incident intake. We can paste logs, stack traces, or operational notes, and the interface immediately normalizes them into structured evidence. In the demo, we load example logs so the service, severity, and likely error signature become visible before backend reasoning begins. This is important because it shows that NEXUS does not treat incident text as opaque data. It turns that text into a usable incident contract before handing it off to the agents."
say -v Samantha -r 176 -o "${SCENE_3}" "Once the logs are submitted, the app redirects directly into Incident Detail. This is the core product surface. SENTINEL classifies the incident, PRISM diagnoses the likely root cause, FORGE proposes the runbook, and GUARDIAN becomes the explicit governance gate. The handoff thread keeps that sequence visible so the system feels like a team of specialists working together, not a static dashboard. The product is also safe by default. Here we move to the visible BYO OpenAI key panel. Live reasoning is turned off, and if a user wants live OpenAI-backed behavior, they must bring their own key through this control. Now we approve the runbook, and the execution state moves cleanly through Guardian into an approved and executed outcome."
say -v Samantha -r 176 -o "${SCENE_4}" "Finally, we open Learning and Controls. This screen makes the learning story easy to absorb. The reward curve shows thirty episodes of training, moving from a lower baseline to a stronger trained policy. The four-agent crew remains visible through the accuracy and summary metrics, and the governance posture stays present so learning never looks unbounded or unsafe. The result is a product that not only resolves incidents through a visible multi-agent flow, but also shows how that system improves over time without losing operator trust."

printf "file '%s'\nfile '%s'\nfile '%s'\nfile '%s'\n" \
  "${SCENE_1}" "${SCENE_2}" "${SCENE_3}" "${SCENE_4}" > "${TMP_DIR}/narration_concat.txt"

ffmpeg -y -f concat -safe 0 -i "${TMP_DIR}/narration_concat.txt" -c:a aac -b:a 192k "${OUTPUT_DIR}/narration.m4a" >/dev/null 2>&1

export OUTPUT_DIR
python - <<'PY'
import json
import os
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

output_dir = Path(os.environ["OUTPUT_DIR"])
scene_text = [
    "NEXUS v2 opens in the Command Center. This is the live operational view of the product. Instead of starting with a wall of metrics, the interface leads with one active incident and a visible crew of autonomous agents. SENTINEL, PRISM, FORGE, and GUARDIAN are all shown as workers with clear roles, current tasks, and handoffs. The queue is still present, but it is intentionally secondary to the active incident story, so an operator can understand what the system is doing before diving into deeper detail.",
    "From here we open Inputs, which is the fastest path into the system. This screen is designed for raw incident intake. We can paste logs, stack traces, or operational notes, and the interface immediately normalizes them into structured evidence. In the demo, we load example logs so the service, severity, and likely error signature become visible before backend reasoning begins. This is important because it shows that NEXUS does not treat incident text as opaque data. It turns that text into a usable incident contract before handing it off to the agents.",
    "Once the logs are submitted, the app redirects directly into Incident Detail. This is the core product surface. SENTINEL classifies the incident, PRISM diagnoses the likely root cause, FORGE proposes the runbook, and GUARDIAN becomes the explicit governance gate. The handoff thread keeps that sequence visible so the system feels like a team of specialists working together, not a static dashboard. The product is also safe by default. Here we move to the visible BYO OpenAI key panel. Live reasoning is turned off, and if a user wants live OpenAI-backed behavior, they must bring their own key through this control. Now we approve the runbook, and the execution state moves cleanly through Guardian into an approved and executed outcome.",
    "Finally, we open Learning and Controls. This screen makes the learning story easy to absorb. The reward curve shows thirty episodes of training, moving from a lower baseline to a stronger trained policy. The four-agent crew remains visible through the accuracy and summary metrics, and the governance posture stays present so learning never looks unbounded or unsafe. The result is a product that not only resolves incidents through a visible multi-agent flow, but also shows how that system improves over time without losing operator trust.",
]
overlay_labels = [
    "Screen 1: Command Center",
    "Screen 2: Inputs and raw-log normalization",
    "Screen 3: Incident Detail and Guardian approval",
    "Screen 4: Learning & Controls",
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

scene_plan = {
    "scenes": [
        {
            "name": "command_center",
            "audio_duration_sec": durations[0],
            "video_duration_ms": int(max(durations[0], 30.0) * 1000),
        },
        {
            "name": "inputs",
            "audio_duration_sec": durations[1],
            "video_duration_ms": int(max(durations[1], 30.0) * 1000),
        },
        {
            "name": "incident_detail",
            "audio_duration_sec": durations[2],
            "video_duration_ms": int(max(durations[2], 40.0) * 1000),
        },
        {
            "name": "learning_controls",
            "audio_duration_sec": durations[3],
            "video_duration_ms": int(max(durations[3], 30.0) * 1000),
        },
    ]
}
(output_dir / "scene_plan.json").write_text(json.dumps(scene_plan, indent=2), encoding="utf-8")

def stamp(seconds: float) -> str:
    ms = round(seconds * 1000)
    h, rem = divmod(ms, 3600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

cursor = 0.0
entries = []
for index, text in enumerate(scene_text, start=1):
    start = cursor
    end = cursor + scene_plan["scenes"][index - 1]["video_duration_ms"] / 1000.0
    entries.append(f"{index}\n{stamp(start)} --> {stamp(end)}\n{text}\n")
    cursor = end
(output_dir / "captions.srt").write_text("\n".join(entries), encoding="utf-8")

font_path = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
font = ImageFont.truetype(font_path, 42)
small_font = ImageFont.truetype(font_path, 24)
overlay_dir = output_dir / "overlays"
overlay_dir.mkdir(parents=True, exist_ok=True)
for index, label in enumerate(overlay_labels, start=1):
    image = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((28, 548, 1252, 694), radius=30, fill=(8, 14, 28, 215))
    draw.text((64, 572), "NEXUS v2 Demo", font=small_font, fill=(133, 196, 255, 255))
    draw.text((64, 612), label, font=font, fill=(255, 255, 255, 255))
    image.save(overlay_dir / f"{index:02}.png")

filter_parts = []
last = "[0:v]"
cursor = 0.0
for idx, scene in enumerate(scene_plan["scenes"], start=1):
    duration = scene["video_duration_ms"] / 1000.0
    start = cursor
    end = cursor + duration
    out = f"[v{idx}]"
    filter_parts.append(
        f"{last}[{idx}:v]overlay=0:0:enable='between(t,{start:.3f},{end:.3f})'{out}"
    )
    last = out
    cursor = end
(output_dir / "overlay_filter.txt").write_text(";\n".join(filter_parts), encoding="utf-8")
PY

RAW_VIDEO_PATH="$(DEMO_SCENE_PLAN="${OUTPUT_DIR}/scene_plan.json" node "${ROOT_DIR}/scripts/generate_demo_video.mjs")"
cp "${RAW_VIDEO_PATH}" "${OUTPUT_DIR}/screen-recording.webm"

ffmpeg -y \
  -i "${OUTPUT_DIR}/screen-recording.webm" \
  -i "${OUTPUT_DIR}/overlays/01.png" \
  -i "${OUTPUT_DIR}/overlays/02.png" \
  -i "${OUTPUT_DIR}/overlays/03.png" \
  -i "${OUTPUT_DIR}/overlays/04.png" \
  -i "${OUTPUT_DIR}/narration.m4a" \
  -filter_complex_script "${OUTPUT_DIR}/overlay_filter.txt" \
  -map "[v4]" -map 5:a \
  -c:v libx264 -preset veryfast -crf 22 \
  -c:a aac -b:a 192k \
  -pix_fmt yuv420p \
  -shortest \
  "${OUTPUT_DIR}/nexus-v2-demo.mp4" >/dev/null 2>&1

echo "Built synced demo video:"
echo "  ${OUTPUT_DIR}/nexus-v2-demo.mp4"
echo "Narration text:"
echo "  ${NARRATION_TXT}"
echo "Captions:"
echo "  ${OUTPUT_DIR}/captions.srt"
