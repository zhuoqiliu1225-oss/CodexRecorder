# Third-party components

CodexRecorder downloads model weights separately; weights are not included in the source ZIP or Git repository. Dependencies and models retain their original licenses.

| Component | Role | Upstream |
| --- | --- | --- |
| faster-whisper | Local transcription | https://github.com/SYSTRAN/faster-whisper |
| CTranslate2 | Local inference | https://github.com/OpenNMT/CTranslate2 |
| SentencePiece | Translation tokenization | https://github.com/google/sentencepiece |
| M2M100 418M | Multilingual translation model; upstream model card identifies MIT | https://huggingface.co/facebook/m2m100_418M |
| M2M100 CT2 INT8 conversion | Data-only download, pinned to revision `18e406c615ef2991fa74d53734bf66b0a6b10cb4` | https://huggingface.co/gn64/M2M100_418M_CTranslate2 |
| OpenAI Whisper and separately selected converted models | Speech recognition weights | https://github.com/openai/whisper |
| Codex CLI | Optional GPT translation fallback and automatic summaries using the user's login | https://github.com/openai/codex |

Read the upstream license files and model cards when redistributing any of these components. Existing machine-specific model paths are not part of the repository.
