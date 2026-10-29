# macOS setup / macOS 安装

**Status:** macOS adaptation is implemented; hardware microphone, Codex browser permission, and latency require a real Mac acceptance test. Windows remains the previously tested platform. This does not add iPhone support.

## 中文快速开始

也可在 Mac 的本地 Codex 中直接发送：

```text
请在这台 Mac 上安装 https://github.com/zhuoqiliu1225-oss/CodexRecorder 。先读 docs/MACOS.md，检查 Python 3.11+、Node.js 18+、Git 与 Codex CLI，复用已有环境，在固定目录下载完整项目。运行 bash scripts/setup.sh 和 bash scripts/install_skill.sh，再运行 node scripts/control.cjs serve，打开返回的侧边面板。首次下载和 CPU 暖机需要等待，不要自动开始录音。请让我自己完成登录和麦克风授权，最后按指南验证状态，不需要 API Key。
```

需要 macOS 上的本地 Codex、Python 3.11+、Node.js 18+、Git，以及可以正常执行推理的 Codex CLI ChatGPT 登录。先通过 `python3 --version` 和 `node --version` 检查环境。

在准备长期保留项目的目录打开终端：

```bash
git clone https://github.com/zhuoqiliu1225-oss/CodexRecorder.git
cd CodexRecorder
codex login status
# 尚未登录时执行 codex login，使用 ChatGPT 登录。
bash scripts/setup.sh
bash scripts/install_skill.sh
node scripts/control.cjs serve
node scripts/control.cjs status
```

让 Codex 在内置浏览器打开返回地址，等待 `engine.status` 为 `ready`。首次会下载模型并加载暖机，可能需要数分钟或更久。随后在新聊天中发送 `$codex-recorder 开始录音`，手动允许麦克风，并在面板显示正在录音、计时和音量变化后讲话。

- macOS 当前使用 CPU 转写与翻译，未接入 Metal / MPS / MLX 加速。默认语音模型是 `base`；Windows 独显性能数据不适用于 Mac。
- 不要复制 Windows 的 `.venv`、`local.settings.json` 或绝对模型路径到 Mac；使用独立的克隆目录与虚拟环境。
- 指定 Python 时使用 `PYTHON=/完整路径/python3 bash scripts/setup.sh`。暂时跳过翻译模型下载可用 `bash scripts/setup.sh --skip-translation-model`，但 GPT 翻译兜底会更慢。
- 个人技能写入 `~/.agents/skills/codex-recorder/`，指向完整项目目录。换项目可在新聊天中调用。
- “打开文件夹”在 Finder 中打开对应记录目录；历史记录及 PDF 导出逻辑与 Windows 相同。
- 发生权限问题时检查 macOS 系统设置中的麦克风权限，并确认当前 Codex 浏览器支持麦克风访问。不要绕过系统授权提示。

## English quick start

Use local Codex on macOS with Python 3.11+, Node.js 18+, Git, and the official Codex CLI signed in with ChatGPT. Clone the full repository, run `bash scripts/setup.sh`, register the personal skill with `bash scripts/install_skill.sh`, and start with `node scripts/control.cjs serve`.

Wait for the engine to become ready, then ask `$codex-recorder` to start recording and manually grant microphone permission. This implementation uses CPU inference, not Apple GPU acceleration. Use a fresh environment rather than copying Windows virtual environments or machine settings. The personal skill lives under `~/.agents/skills/codex-recorder/`; keep the cloned application folder.

## Mac acceptance checklist / 真机验收

- Fresh installation on the actual CPU architecture and Python version; dependency downloads succeed.
- Engine loads, reports CPU and the actual translation mode; cold-start time is recorded.
- Codex side browser obtains the Mac microphone; audio meter and duration respond.
- Pause, resume, stop, translation-language switching, bottom following, and selected-text copying work.
- GPT summary succeeds using the user's CLI sign-in; AI title appears in history.
- Finder opens the correct folder and both PDFs download and render correctly.
- Restarting the background service recovers saved data without starting capture automatically.

Mobile is a separate future version: the requested phone product must run without a computer. The macOS changes do not claim to provide that capability.
