# CodexRecorder user guide

[Installation](../README.md) · [中文](USAGE.zh-CN.md)

For local Codex on Windows, preview 0.2. This is a source application, not a standalone EXE; iOS is not supported yet.

## 1. First use: download, then warm up

Installing dependencies does not mean the models are ready. The first run downloads the speech model and about 500 MB of translation weights, loads them, and warms them up. Slow connections, larger models, or CPU-only devices may take minutes or longer.

| State | What to do |
| --- | --- |
| Setup is downloading | Keep the connection available and wait for completion. Follow the error message if a download fails. |
| “Loading and warming up speech model…” | Keep the service and panel open. Do not repeatedly start the service or request recording. Microphone recording has not started yet. |
| “GPU transcription” or “Local CPU transcription” | Models are ready; recording can begin. |
| “Recording” and an increasing timer | The microphone is capturing; you can speak. |
| “Processing” after Stop | Capture has ended. Wait for outstanding transcription, translation, and the summary. |

Run `node scripts/control.cjs status` from the project folder to check that `engine.status` is `ready`. A PC or service restart requires loading and warm-up again, usually without downloading cached weights. Later recordings reuse the warm models while the same service stays running.

## 2. Control recording from Codex

After installing the personal skill, use it in new chats in other local projects too. Open a new chat if a newly installed skill is not visible.

| Action | Example message |
| --- | --- |
| Start | `$codex-recorder Start recording` |
| Pause | “Pause recording” |
| Resume | “Resume recording” |
| Stop | “Stop recording” |

The repository-local skill is `$recorder`. Natural-language requests usually work; naming `$codex-recorder` makes selection explicit. Chat commands still take time for Codex to process.

Manually allow the microphone when first prompted. A start request is not proof that capture has begun: wait for the recording status and timer. You can also use Record, Pause, Resume, and Stop in the panel.

Pause stops capturing new speech while received audio continues processing. Stop triggers the summary after outstanding work finishes. GPT summaries need network access, valid Codex sign-in, and available account limits, and can take longer than local transcription. No API key is required.

## 3. Three independent language settings

| Setting | Purpose |
| --- | --- |
| Interface language | Chinese / English, applied immediately and remembered. Changes controls, status, labels, and common error messages. |
| Spoken language | The language you speak. Choose auto-detect or a specific language before recording. |
| Live translation / Translate into | Enable translation and select its target. You can change it during or after recording. |

Speech and translation choices include Chinese, English, Japanese, Korean, French, German, and Spanish. Changing the translation target retranslates earlier text and applies to new text; switching back reuses cached translations.

Interface language does not rewrite saved transcripts, translations, or summaries. Automatic summaries currently default to Chinese; there is no separate summary-language selector yet. Underlying error details may retain their original language.

## 4. Read, group, and copy text

- Display paragraphs default to about one minute; choose 30 seconds or two minutes if preferred. Recognition still updates on short chunks without waiting for a full paragraph.
- Transcript and summary areas have fixed heights and scroll internally. Processing updates do not resize the surrounding page; recognition can still revise words.
- **Copy original** copies the entire original transcript with paragraph breaks, without timestamps or translations.
- Select part of the transcript, including translations if wanted, and press Ctrl+C. Timestamps and processing labels are filtered from the selection.
- While text is selected, recording and saving continue; transcript redraw waits to avoid disrupting the selection. Deselect to see new updates.

## 5. Summaries and exports

After Stop, wait for transcription and translation to finish, then open Summary. A failed summary does not remove the recording or transcript. Resolve sign-in or network errors and use Retry summary, or ask the current Codex chat to summarize the saved transcript.

| Location or control | Contents |
| --- | --- |
| Export notes | Markdown transcript, selected translations, and any completed summary, including timing information. |
| Download audio | Received WAV audio for this session. |
| Project folder `data/<session-id>/` | `audio.wav`, `notes.md`, `session.json`, and audio chunks. |

A new recording replaces the record shown in the panel; older sessions remain in their own local folders. Keep the application folder and do not publish private `data` contents to GitHub.

Audio and local inference stay on this device. GPT summaries and GPT translation fallback send the relevant transcript text to OpenAI through your Codex sign-in.

## 6. Troubleshooting and updates

| Problem | Action |
| --- | --- |
| PowerShell blocks the scripts | Ask Codex to help, or use a process-only execution policy for the reviewed repository script: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1`. Use `install_skill.ps1` for the skill installer. No global policy change is needed. |
| Python / Node / Git command missing | Reopen the terminal after installation so PATH refreshes. For multiple Python installs, use `setup.ps1 -Python <full-path-to-python.exe>`. |
| Skill missing in another project | Run `.\scripts\install_skill.ps1` in the application folder, keep that folder in place, and open a new Codex chat. Copying only the repository skill is insufficient. |
| No transcript | Confirm the engine is ready, Recording is shown, and the timer and microphone meter respond. Check the selected system microphone. Silence does not produce text. |
| Summary cannot find Codex CLI | Check installation paths. Current versions recover from stale paths by checking PATH and the current desktop-bundled CLI; this does not necessarily mean sign-in expired. |
| Sign-in, network, or usage error | Follow the specific error. Check `codex login status`, resolve the issue, and retry the summary. |
| Updated code but old interface | An open page does not automatically load new JavaScript. **Stop and save the recording, then refresh the panel.** Do not refresh during capture. |
| Updating the application | Stop and save first. With local changes resolved, run `git pull --ff-only`. Ask Codex to check dependency changes and rerun the personal skill installer. If Python service code changed, safely restart the service, wait for warm-up, and refresh the panel. Preserve local settings and recordings. |

Keep the Codex browser panel open during recording. Crashes, forced closing, sleep, or power loss can lose the last unsent audio. Service restarts recover the latest saved session without automatically reopening the microphone.

## History, following, and PDF exports

- The transcript follows new content at the bottom. Scrolling up or selecting text suspends following; Back to latest resumes it.
- History shows saved transcripts and summaries without replacing an active capture. Details include summary retry and Open folder.
- Successful summaries generate an AI recording title, with a date fallback. Physical folders keep unique session IDs; titles are saved in `title.txt`.
- New records also save `transcript.txt` and `summary.md`. Exported `transcript.pdf` and `summary.pdf` are written into the same session folder. Older saved sessions can be exported too.
- Summary generation starts once original transcription is complete, independently of the translation backlog. Transient failures retry once; sign-in and quota errors do not. Brief Windows file locks are retried during saving.
- Update dependencies using `scripts/setup.ps1` for PDF support. Export after processing completes. Chinese and English PDFs have been verified; font coverage for other scripts has not been fully verified.
