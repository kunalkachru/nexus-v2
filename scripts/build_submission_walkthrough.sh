#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${ROOT_DIR}/artifacts/demo-video"
TMP_DIR="${OUTPUT_DIR}/tmp"
SEGMENTS_DIR="${TMP_DIR}/submission_narration_segments"
BASE_URL="${DEMO_BASE_URL:-http://127.0.0.1:7860}"
FINAL_VIDEO_PATH="${OUTPUT_DIR}/nexus-v2-submission-walkthrough.mp4"
NARRATION_TXT="${OUTPUT_DIR}/submission-walkthrough-narration.txt"
NARRATION_M4A="${OUTPUT_DIR}/submission-walkthrough-narration.m4a"
SCENE_PLAN_PATH="${OUTPUT_DIR}/submission-scene-plan.json"
CAPTIONS_PATH="${OUTPUT_DIR}/submission-walkthrough-captions.srt"
FILTER_PATH="${OUTPUT_DIR}/submission-walkthrough-overlay-filter.txt"
RAW_VIDEO_COPY="${OUTPUT_DIR}/submission-walkthrough-screen-recording.webm"

mkdir -p "${OUTPUT_DIR}" "${TMP_DIR}" "${SEGMENTS_DIR}"
rm -f "${SEGMENTS_DIR}"/*.aiff "${OUTPUT_DIR}/overlays/"*.png "${SCENE_PLAN_PATH}" "${FILTER_PATH}" "${CAPTIONS_PATH}" "${NARRATION_M4A}" "${RAW_VIDEO_COPY}" 2>/dev/null || true

if ! curl -fsS "${BASE_URL}/health" >/dev/null 2>&1; then
  echo "Expected a running app at ${BASE_URL}. Start it first, for example with ./scripts/docker_fresh.sh" >&2
  exit 1
fi

cat > "${NARRATION_TXT}" <<'EOF'
[Scene 1: Problem and Command Center]
NEXUS v2 is built for SRE, platform, and engineering teams that still manage incidents across fragmented tools. Alerts live in one system, logs in another, dashboards somewhere else, and approvals often happen in chat or tribal memory. That slows triage, makes remediation harder to trust, and leaves weak auditability after the incident is over. NEXUS opens in the Command Center to solve that fragmentation. Instead of a KPI wall, the product leads with one live incident and a visible crew of four agents. SENTINEL, PRISM, FORGE, and GUARDIAN show who is working, what they are doing, and where the next handoff goes. Judges should notice that the queue stays secondary while the active incident story stays front and center.

[Scene 2: Inputs and user workflow]
Now we move into Inputs, which shows how a user starts the workflow. An operator can paste raw logs, stack traces, or operational notes into the intake screen. In this example we load sample logs so the UI can surface the detected service, severity, and signature before deeper reasoning begins. That step matters because NEXUS does not treat incident text as an opaque blob. It converts raw evidence into a structured incident object that the agent crew can act on. For the user, this reduces the time spent stitching together context by hand and turns a messy signal stream into a cleaner operational starting point.

[Scene 3: Incident Detail, live reasoning, and governance]
After submission, the app redirects directly into Incident Detail, which is the flagship surface of the product. This is where the user sees the four-agent collaboration model in action. SENTINEL classifies the incident, PRISM diagnoses likely root cause, FORGE proposes the remediation path, and GUARDIAN decides whether the action should move forward safely. Judges should pay special attention to the handoff thread because it makes the reasoning chain visible instead of collapsing everything into one opaque AI answer. From there we move to the Bring your own OpenAI key panel. The public deployment is safe by default, live reasoning is off, and users only unlock OpenAI-backed behavior by providing their own key for their own session. No shared server-side OPENAI_API_KEY is required for the public demo. Finally, we approve the runbook, and the execution state moves through GUARDIAN into a governed, auditable outcome.

[Scene 4: Learning, RL, and what gets stronger over time]
The last screen is Learning and Controls. This is where NEXUS starts to look less like a static incident assistant and more like a system that can improve over time. The reward curve shows how training performance moves across thirty episodes, and the agent improvement section shows whether the crew is getting better at the work it performs. The governance summary stays visible beside that learning story so optimization never becomes detached from control. Judges should pay attention to this combination: visible multi-agent reasoning, explicit governance, and a learning layer that can improve prioritization and runbook choice over time. That is the product direction behind NEXUS: governed multi-agent incident response that becomes more useful with every reviewed outcome.
EOF

SCENE_1="${SEGMENTS_DIR}/01-problem-command-center.aiff"
SCENE_2="${SEGMENTS_DIR}/02-inputs-user-workflow.aiff"
SCENE_3="${SEGMENTS_DIR}/03-incident-detail-governance.aiff"
SCENE_4="${SEGMENTS_DIR}/04-learning-rl.aiff"

say -v Samantha -r 168 -o "${SCENE_1}" "NEXUS v2 is built for SRE, platform, and engineering teams that still manage incidents across fragmented tools. Alerts live in one system, logs in another, dashboards somewhere else, and approvals often happen in chat or tribal memory. That slows triage, makes remediation harder to trust, and leaves weak auditability after the incident is over. NEXUS opens in the Command Center to solve that fragmentation. Instead of a KPI wall, the product leads with one live incident and a visible crew of four agents. SENTINEL, PRISM, FORGE, and GUARDIAN show who is working, what they are doing, and where the next handoff goes. Judges should notice that the queue stays secondary while the active incident story stays front and center."
say -v Samantha -r 168 -o "${SCENE_2}" "Now we move into Inputs, which shows how a user starts the workflow. An operator can paste raw logs, stack traces, or operational notes into the intake screen. In this example we load sample logs so the UI can surface the detected service, severity, and signature before deeper reasoning begins. That step matters because NEXUS does not treat incident text as an opaque blob. It converts raw evidence into a structured incident object that the agent crew can act on. For the user, this reduces the time spent stitching together context by hand and turns a messy signal stream into a cleaner operational starting point."
say -v Samantha -r 168 -o "${SCENE_3}" "After submission, the app redirects directly into Incident Detail, which is the flagship surface of the product. This is where the user sees the four-agent collaboration model in action. SENTINEL classifies the incident, PRISM diagnoses likely root cause, FORGE proposes the remediation path, and GUARDIAN decides whether the action should move forward safely. Judges should pay special attention to the handoff thread because it makes the reasoning chain visible instead of collapsing everything into one opaque AI answer. From there we move to the Bring your own OpenAI key panel. The public deployment is safe by default, live reasoning is off, and users only unlock OpenAI-backed behavior by providing their own key for their own session. No shared server-side OPENAI API key is required for the public demo. Finally, we approve the runbook, and the execution state moves through GUARDIAN into a governed, auditable outcome."
say -v Samantha -r 168 -o "${SCENE_4}" "The last screen is Learning and Controls. This is where NEXUS starts to look less like a static incident assistant and more like a system that can improve over time. The reward curve shows how training performance moves across thirty episodes, and the agent improvement section shows whether the crew is getting better at the work it performs. The governance summary stays visible beside that learning story so optimization never becomes detached from control. Judges should pay attention to this combination: visible multi-agent reasoning, explicit governance, and a learning layer that can improve prioritization and runbook choice over time. That is the product direction behind NEXUS: governed multi-agent incident response that becomes more useful with every reviewed outcome."

printf "file '%s'\nfile '%s'\nfile '%s'\nfile '%s'\n" \
  "${SCENE_1}" "${SCENE_2}" "${SCENE_3}" "${SCENE_4}" > "${TMP_DIR}/submission-narration-concat.txt"

ffmpeg -y -f concat -safe 0 -i "${TMP_DIR}/submission-narration-concat.txt" -c:a aac -b:a 192k "${NARRATION_M4A}" >/dev/null 2>&1

export OUTPUT_DIR SCENE_PLAN_PATH CAPTIONS_PATH FILTER_PATH
python - <<'PY'
import json
import os
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

output_dir = Path(os.environ["OUTPUT_DIR"])
scene_plan_path = Path(os.environ["SCENE_PLAN_PATH"])
captions_path = Path(os.environ["CAPTIONS_PATH"])
filter_path = Path(os.environ["FILTER_PATH"])

scene_text = [
    "NEXUS v2 is built for SRE, platform, and engineering teams that still manage incidents across fragmented tools. Alerts live in one system, logs in another, dashboards somewhere else, and approvals often happen in chat or tribal memory. That slows triage, makes remediation harder to trust, and leaves weak auditability after the incident is over. NEXUS opens in the Command Center to solve that fragmentation. Instead of a KPI wall, the product leads with one live incident and a visible crew of four agents. SENTINEL, PRISM, FORGE, and GUARDIAN show who is working, what they are doing, and where the next handoff goes. Judges should notice that the queue stays secondary while the active incident story stays front and center.",
    "Now we move into Inputs, which shows how a user starts the workflow. An operator can paste raw logs, stack traces, or operational notes into the intake screen. In this example we load sample logs so the UI can surface the detected service, severity, and signature before deeper reasoning begins. That step matters because NEXUS does not treat incident text as an opaque blob. It converts raw evidence into a structured incident object that the agent crew can act on. For the user, this reduces the time spent stitching together context by hand and turns a messy signal stream into a cleaner operational starting point.",
    "After submission, the app redirects directly into Incident Detail, which is the flagship surface of the product. This is where the user sees the four-agent collaboration model in action. SENTINEL classifies the incident, PRISM diagnoses likely root cause, FORGE proposes the remediation path, and GUARDIAN decides whether the action should move forward safely. Judges should pay special attention to the handoff thread because it makes the reasoning chain visible instead of collapsing everything into one opaque AI answer. From there we move to the Bring your own OpenAI key panel. The public deployment is safe by default, live reasoning is off, and users only unlock OpenAI-backed behavior by providing their own key for their own session. No shared server-side OPENAI_API_KEY is required for the public demo. Finally, we approve the runbook, and the execution state moves through GUARDIAN into a governed, auditable outcome.",
    "The last screen is Learning and Controls. This is where NEXUS starts to look less like a static incident assistant and more like a system that can improve over time. The reward curve shows how training performance moves across thirty episodes, and the agent improvement section shows whether the crew is getting better at the work it performs. The governance summary stays visible beside that learning story so optimization never becomes detached from control. Judges should pay attention to this combination: visible multi-agent reasoning, explicit governance, and a learning layer that can improve prioritization and runbook choice over time. That is the product direction behind NEXUS: governed multi-agent incident response that becomes more useful with every reviewed outcome.",
]
overlay_labels = [
    "Problem, users, and the Command Center",
    "Raw-log intake and structured incident creation",
    "Incident Detail, BYO key safety, and Guardian approval",
    "Learning, governance, and RL value",
]
segment_paths = sorted((output_dir / "tmp" / "submission_narration_segments").glob("*.aiff"))
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
            "name": "problem_command_center",
            "audio_duration_sec": durations[0],
            "video_duration_ms": int(max(durations[0], 45.0) * 1000),
        },
        {
            "name": "inputs_user_workflow",
            "audio_duration_sec": durations[1],
            "video_duration_ms": int(max(durations[1], 38.0) * 1000),
        },
        {
            "name": "incident_detail_governance",
            "audio_duration_sec": durations[2],
            "video_duration_ms": int(max(durations[2], 72.0) * 1000),
        },
        {
            "name": "learning_rl",
            "audio_duration_sec": durations[3],
            "video_duration_ms": int(max(durations[3], 44.0) * 1000),
        },
    ]
}
scene_plan_path.write_text(json.dumps(scene_plan, indent=2), encoding="utf-8")

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
captions_path.write_text("\n".join(entries), encoding="utf-8")

font_path = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
font = ImageFont.truetype(font_path, 42)
small_font = ImageFont.truetype(font_path, 24)
overlay_dir = output_dir / "overlays"
overlay_dir.mkdir(parents=True, exist_ok=True)
for index, label in enumerate(overlay_labels, start=1):
    image = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((28, 548, 1252, 694), radius=30, fill=(8, 14, 28, 215))
    draw.text((64, 572), "NEXUS v2 Submission Walkthrough", font=small_font, fill=(133, 196, 255, 255))
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
filter_path.write_text(";\n".join(filter_parts), encoding="utf-8")
PY

RAW_VIDEO_PATH="$(DEMO_SCENE_PLAN="${SCENE_PLAN_PATH}" node "${ROOT_DIR}/scripts/generate_demo_video.mjs")"
cp "${RAW_VIDEO_PATH}" "${RAW_VIDEO_COPY}"

ffmpeg -y \
  -i "${RAW_VIDEO_COPY}" \
  -i "${OUTPUT_DIR}/overlays/01.png" \
  -i "${OUTPUT_DIR}/overlays/02.png" \
  -i "${OUTPUT_DIR}/overlays/03.png" \
  -i "${OUTPUT_DIR}/overlays/04.png" \
  -i "${NARRATION_M4A}" \
  -filter_complex_script "${FILTER_PATH}" \
  -map "[v4]" -map 5:a \
  -c:v libx264 -preset veryfast -crf 22 \
  -c:a aac -b:a 192k \
  -pix_fmt yuv420p \
  -shortest \
  "${FINAL_VIDEO_PATH}" >/dev/null 2>&1

echo "Built submission walkthrough video:"
echo "  ${FINAL_VIDEO_PATH}"
echo "Narration text:"
echo "  ${NARRATION_TXT}"
echo "Captions:"
echo "  ${CAPTIONS_PATH}"
