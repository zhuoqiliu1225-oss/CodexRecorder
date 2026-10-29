# CodexRecorder · 拾音录音笔

[安装步骤](#安装运行) · [完整使用指南](docs/USAGE.zh-CN.md) · [English](README.md)

## 复制这段提示词，让 Codex 帮你安装

在 **Windows 版 Codex 的本地模式**中发送下面这段话。需要允许 Codex 运行本机命令、安装文件；普通 ChatGPT 网页聊天不能直接安装电脑程序。

```text
请帮我在这台 Windows 电脑上安装 https://github.com/zhuoqiliu1225-oss/CodexRecorder 。先读 README，检查 Python 3.11+、Node.js 18+、Git 和 Codex CLI，缺少的从官方来源安装，复用已有环境，不覆盖无关目录。
把完整项目下载到合适的固定目录，运行 scripts/setup.ps1 和 scripts/install_skill.ps1，再运行 node scripts/control.cjs serve，将返回的地址打开在 Codex 侧边浏览器中，但不要自动开始录音。
登录和系统授权由我完成，不需要 API Key。首次下载模型与冷启动暖机可能需要一些时间，请提前说明，等待 engine.status 为 ready 后再确认就绪，不要反复启动服务。最后告诉我如何用安装好的 $codex-recorder 技能开始、暂停和停止录音，并打开使用指南。
```

首次需要下载语音模型和约 **500 MB** 的翻译模型。个人技能会指向完整程序目录，请保留该目录。新装技能未出现时，开启一个新的 Codex 聊天；点击或说“开始录音”时才会请求麦克风权限。

> **第一次请预留下载与暖机时间。** 依赖安装完成后，首次启动还可能下载语音模型、加载语音与翻译模型并进行预热；慢网速或 CPU 设备可能需要数分钟或更久。看到“正在加载并预热语音模型…”时请等待，出现“GPU 低延迟转写”或“CPU 本地转写”、开始按钮可用后才算就绪。电脑或后台服务重启后仍需重新加载和暖机，模型已缓存时通常无需重新下载。

安装个人技能后，可在其他项目的新聊天里说“开始录音”；需要明确指定时发送 `$codex-recorder 开始录音`。后台服务会保留已预热的模型以加快后续启动，电脑重启后的首次使用仍需加载模型。面板默认按约 1 分钟合并文字段落，也可选择 30 秒或 2 分钟，短音频仍实时识别；选中文字复制时不含时间戳，选择期间暂停文字区域重绘以防选区被打断。

---

[English](README.md) · [验证与延迟说明](docs/validation.md)

Windows 优先的本地录音笔原型：在 Codex 聊天中发起录音，在侧边浏览器面板显示实时转写、可选翻译，停止后自动生成总结。

## 当前版本 0.2

- 界面语言支持中文与 English，可即时切换并记住选择；与识别语言、译文语言独立。该设置不会翻译已有录音或总结内容。
- 文字和总结采用固定高度的可滚动区域，录音期间状态提示保持不变，避免任务数和内容高度变化顶动页面。
- 浏览器麦克风采集，本地 16 kHz WAV 保存，暂停 / 继续 / 停止。
- faster-whisper 在本机转写，自动尝试 GPU、启动时预热。约 2.4 秒一次滚动识别，结合后续上下文修正截断词句；实时文字仍可能被修订。
- 录音中或结束后可开关翻译，选择中文、英文、日文、韩文、法文、德文、西班牙文。切换后已有内容补译、后续内容使用新语言，切回已翻译过的语言复用缓存。
- 默认本地多语种翻译用于实时显示；GPT 用于录后总结。本地模型未配置时，仍可通过用户自己已登录的 Codex CLI 翻译，但网络推理会明显更慢。
- 不读取、复制或分发登录令牌，无需 API Key。GPT 功能仍受账号权限、网络、使用限额影响。
- Markdown 笔记、JSON 转写记录、完整音频导出。
- 仓库内 Skill 提供聊天中的开始、暂停、继续和停止控制。

## 安装运行

**推荐方式：复制上方提示词，在 Windows Codex 的本地聊天中安装。** 如果希望手动安装，按以下顺序操作。

1. 准备 Windows、Python 3.11+、Node.js 18+、Git，以及官方 Codex CLI。没有独立 CLI 时，可让 Codex 检查其随应用安装的 CLI；普通 ChatGPT 网页聊天无法替你启动本机录音。
2. 在准备长期保留程序的目录打开 PowerShell，下载完整仓库。也可以在 GitHub 的 **Code → Download ZIP** 下载并解压，再进入包含 `README.md`、`app` 和 `scripts` 的那一层目录。不要只下载技能文件夹。

```powershell
git clone https://github.com/zhuoqiliu1225-oss/CodexRecorder.git
cd CodexRecorder
```

3. 检查运行环境和 ChatGPT 登录。尚未登录时执行 `codex login`，按官方提示完成登录；无需配置 API Key。

```powershell
python --version
node --version
git --version
codex login status
```

4. 安装本地依赖、下载翻译模型，并注册跨项目可用的个人技能。

```powershell
.\scripts\setup.ps1
.\scripts\install_skill.ps1
```

5. 启动服务并暖机，此命令不会开始录音。

```powershell
node scripts/control.cjs serve
node scripts/control.cjs status
```

让 Codex 将返回地址打开在右侧内置浏览器中。等待 `engine.status` 为 `ready`；首次下载或暖机较慢时保持页面和服务打开，不要反复运行 `start`。需要确认进度时再运行一次 `status`。

6. 在 Codex 中发送 `$codex-recorder 开始录音`，首次手动允许麦克风。确认面板显示“正在录音”且计时增加后再开始讲话。若新技能没有出现，开启一个新聊天；安装到个人目录后，其他本机项目的新聊天也可调用。

**安装完成的判断：** 引擎 ready、面板能打开、个人技能能被发现。是否成功生成 GPT 总结，还取决于你的 Codex 登录、网络和账号额度。

首次启动默认下载多语言 `base` 语音模型。可在 `local.settings.json` 中将 `model` 设置为本地 faster-whisper 模型目录，或可下载的模型名称。模型路径和本机 Python 路径只放在这个被 Git 忽略的文件中。配置示例见 `settings.example.json`。

安装脚本还会下载约 500 MB 的 M2M100 本地翻译权重。若暂时不下载，可运行 `scripts/setup.ps1 -SkipTranslationModel`，此时部分语言对需要等待 GPT。模型不会打包进源码 ZIP。

有 NVIDIA 显卡时 `device: auto` 会尝试 CUDA，缺少依赖时回退 CPU。已有 CUDA/cuDNN 库可通过 `cuda_library_dirs` 指定目录；无需改系统 PATH。详见 [faster-whisper 官方 GPU 依赖说明](https://github.com/SYSTRAN/faster-whisper#gpu)。

在 Codex 中打开仓库后使用 `$recorder` 或说“开始录音”。如果技能尚未被发现，重新打开聊天。由 Codex 在右侧内置浏览器打开命令返回的 URL；首次使用请手动允许麦克风。

想在其他项目的 Codex 聊天中也使用它，可运行 `.\scripts\install_skill.ps1`，安装个人技能 `$codex-recorder`。该脚本只写入技能和程序路径，不复制模型，也不会覆盖无关的已有技能目录。

也可以手动在 Codex 内置浏览器打开 `http://127.0.0.1:18764/`，点击开始录音。

```powershell
node scripts/control.cjs pause
node scripts/control.cjs resume
node scripts/control.cjs stop
node scripts/control.cjs status
```

## 工作方式与数据

侧边页面采集麦克风，将有序 PCM 片段发送到只监听 `127.0.0.1` 的 Python 服务。服务先保存音频，再排队转写。暂停期间关闭音频轨道输入；停止后等待已经提交的片段处理完成，再总结。页面失联超过 15 秒会结束会话并整理已收到的内容。尚在页面内的最后几秒音频在强制关闭、崩溃或断电时可能丢失。

录音、转写与本地翻译留在本机。需要 GPT 翻译兜底或生成总结时，对应文字会通过 Codex 发送给 OpenAI。账号登录由官方 CLI 自己管理。程序不会把录音音频发送给 OpenAI。

录音存储在 `data/<会话ID>/`：`audio.wav`、`session.json`、`notes.md`。这些文件与模型、配置、日志均被 Git 忽略。

本地翻译通过 `multilingual_model` 指定 M2M100 CT2 模型目录。旧的 `translation_model` 英译中适配器仍兼容。

本地翻译使用 [Meta M2M100](https://huggingface.co/facebook/m2m100_418M)，下载的是 [固定版本的 CT2 INT8 权重](https://huggingface.co/gn64/M2M100_418M_CTranslate2/tree/18e406c615ef2991fa74d53734bf66b0a6b10cb4)。原模型与来源见第三方项目页面；源码包不分发权重。

## 当前限制

- 这是 Windows 可运行原型，不是已上架插件；尚未支持 iOS。
- 原文和译文陆续显示，滚动识别仍可能修订已有文字。尚未做长录音、多说话人或全部语言的系统性准确率评估。
- 本地小型翻译模型可能不如 GPT 适合复杂长句；GPT 兜底依然可能需要数十秒，界面会明确标示当前翻译模式。
- 浏览器面板要保持打开。重载、休眠、设备拔出等异常仍需进一步完善。
- 不承诺所有免费 ChatGPT 账号可用；需要用户自己的 Codex CLI 登录可正常执行推理。
- 服务重启后恢复最近一次已保存记录；中断会话会显示提示，不会假装转写完整，也不会自动重新占用麦克风。音频与笔记仍在 data 目录。

## 开发验证

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node tests/test_panel.cjs
node tests/test_i18n.cjs
node tests/smoke_http.cjs
.\.venv\Scripts\python.exe scripts/package.py
```

完整验证方法与结果见 [验证说明](docs/validation.md)。包含本机操作的原始验证记录不随源码分发。

生成的 `dist/codex-recorder-0.2-windows-source.zip` 只包含源码与仓库技能，不包含录音、模型、本机配置或登录信息。它是源码预览包，尚不是免安装 EXE。解压后先安装运行环境，再用 Codex 打开该目录。

## 新增：历史记录、滚动跟随与 PDF

- 文字区滚动到底部时跟随新内容；向上阅读或选中文字时停止跟随。点击“回到最新”恢复。
- 点击“历史记录”查看旧录音、原文和总结，查看历史不会替换正在录音的会话。历史详情可重新生成总结或打开对应文件夹。
- 总结成功后由 AI 生成录音标题；失败时保留日期标题。物理文件夹仍用唯一时间编号，标题保存在 `title.txt`，避免同名和路径变化。
- 新记录额外保存 `transcript.txt`（原始转写）与 `summary.md`（总结）。导出的 `transcript.pdf` 和 `summary.pdf` 会保存回同一录音目录；旧记录也可导出。
- 停止后原文转写完成即可开始总结，不再等待翻译队列；暂时性错误自动重试一次，登录或额度错误不会反复重试。Windows 文件短暂占用会自动重试写入。
- PDF 导出需更新依赖：运行 `scripts/setup.ps1`。请等记录处理完成后导出；中文与英文已验证，其他文字的字体覆盖尚未完整验证。
