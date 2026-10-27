# Validation of preview 0.2

Validated on Windows in a Codex desktop local session on 2026-10-28. The tested GPU was an NVIDIA GeForce RTX 5070 Laptop GPU (8 GB). CPU inference used four threads. This is a small synthetic-fixture check, not a broad quality benchmark.

## Timing

| Check | Measured result |
| --- | --- |
| Existing large-v3-turbo model, CPU, same 6-second clip | 5.722 s cold inference; 5.522 s warm |
| Same model and clip, CUDA | 1.796 s cold inference; 0.233 s warm |
| First text in simulated realtime feed | 2.781 s from beginning of feed |
| First local Chinese translation | 2.859 s from beginning of feed |
| Latest rolling-window recognition | 0.272 s; queue wait 0.000 s |
| Retranslate three historical rows into Spanish | 0.313 s |
| Return to cached Spanish translations | 0.016 s |

The realtime feed replays a synthetic English WAV as 2.4-second PCM packets into the local HTTP protocol. It includes capture-window accumulation and server processing, but **does not measure the OS microphone capture path or browser rendering**. Real microphone latency varies.

The fixture says that the first version launches next Friday, Alice finishes testing on Thursday, and the budget is $500. The final rolling transcript retained those facts. A naive short-chunk implementation had previously changed the amount; the rolling-context correction and a fixture assertion cover that regression.

Separate short Chinese-to-English/Japanese/Korean/French/German/Spanish samples translated locally in roughly 0.10–0.15 seconds after load and retained the tested amount. This does not establish broad translation accuracy.

## Language switching and concurrency

- Existing text is retranslated when translation is enabled or the target changes.
- Returning to a previously translated target uses the row cache.
- Revision checks stop obsolete results from replacing a newly selected language.
- An obsolete Codex translation request is cancelled when possible.
- Local translation and GPT summary processing use independent workers. A slow summary cannot hold the live translation queue.
- Queued speech recognition uses the latest translation setting when it publishes text.
- Draft text is revised with rolling context; stopping seals the final draft before summary generation.

## Automated checks

```powershell
python -m unittest discover -s tests -v
node --check web/panel.js
node --check web/pcm-worklet.js
node --check scripts/control.cjs
```

The unit suite currently has 18 tests. It uses only the standard library and mocked model calls. It covers audio idempotency, out-of-order rejection, WAV output, write failure, exports, restart recovery, historical translation, caches, language-switch races, request cancellation, sealing drafts, and summary/translation concurrency.

With the local service running, `node tests/smoke_http.cjs` checks origin and token rejection, export path limits, script delivery, and CSP. Microphone capture, pause, resume, and stop were also exercised through the Codex in-app browser. Controller integration confirmed that the panel acknowledged chat-originated commands.

## Optional model integration checks

Create the synthetic fixture on Windows:

```powershell
.\scripts\generate_sample.ps1
```

Run a second service to avoid touching a user's recording:

```powershell
.\.venv\Scripts\python.exe app/server.py --port 18765 --data-dir data/latency-test
```

From another terminal:

```powershell
.\.venv\Scripts\python.exe tests/smoke_latency.py
.\.venv\Scripts\python.exe tests/smoke_language_switch.py
```

These optional checks need installed models and, for the automatically requested summary, a usable Codex login. They use synthetic speech, not private recordings. `smoke_controls.cjs` requires an explicitly started and paused test microphone session on the main port; it resumes and stops that session.

## Not established by these tests

Long-recording stability, every supported language pair, dialects, overlapping speakers, iOS, native MCP App installation, packaged EXE distribution, and universal account eligibility remain unverified.
