// Interface strings are local and independent of speech/translation languages.
const RecorderI18n=(()=>{
 const en={
  '拾音':'Recorder','拾音 · Codex 录音笔':'CodexRecorder','预览版 0.2 · 稳定布局':'Preview 0.2 · Stable layout',
  '让对话留下来':'KEEP THE CONVERSATION','专心听，\n其余交给拾音。':'Listen closely.\nWe will take notes.','实时记录 · 双语对照 · 自动总结':'Live transcript · Translation · Summary',
  '准备录音':'Ready to record','正在录音':'Recording','已暂停':'Paused','正在整理':'Processing','录音已完成':'Recording complete','录音异常':'Recording error',
  '正在加载语音模型…':'Loading speech model…','GPU 低延迟转写':'GPU transcription','CPU 本地转写':'Local CPU transcription','语音模型加载失败':'Speech model failed to load','正在加载并预热语音模型…':'Loading and warming up speech model…',
  '● 开始录音':'● Record','Ⅱ 暂停':'Ⅱ Pause','▶ 继续':'▶ Resume','■ 停止':'■ Stop',
  '音频与转写保存在本机。GPT 翻译和总结使用你的 Codex 登录态，文字会发送给 OpenAI。':'Audio and transcripts are saved locally. GPT translation and summaries use your Codex sign-in and send text to OpenAI.',
  '界面语言':'Interface language','原文语言':'Spoken language','自动识别':'Auto-detect','中文':'Chinese','简体中文':'Simplified Chinese','实时翻译':'Live translation','原文下方显示译文':'Show translation below the original','翻译成':'Translate into',
  '切换语言后，已有内容与后续内容都会使用新语言。':'Changing the language translates both earlier and new text. ',
  '当前使用本地快速翻译。':'Fast local translation is active. ',
  '当前使用 GPT 翻译，网络请求可能需要较长时间。':'GPT translation is active; network requests may take longer. ',
  '已翻译过的语言直接复用。':'Previously translated languages are cached.',
  '实时文字':'Transcript','录音总结':'Summary','文字分段':'Paragraph length','约 30 秒':'About 30 seconds','约 1 分钟':'About 1 minute','约 2 分钟':'About 2 minutes','复制原文':'Copy original','已复制':'Copied',
  '文字会在这里慢慢展开':'Your transcript will appear here','开始录音后，通常每几秒出现一段。\n首次加载模型可能需要稍等。':'New words usually appear every few seconds.\nThe first model load may take a moment.',
  '结束录音后，自动整理':'Summarize when recording ends','摘要、要点、决定和待办。':'Overview, key points, decisions, and action items.',
  '重新生成总结':'Retry summary','导出笔记':'Export notes','下载录音':'Download audio','当前尚无录音':'No recording yet','等待开始录音':'Waiting to record',
  '正在录音 · 转写与翻译持续更新':'Recording · Transcript and translation are updating','已暂停 · 已收到的音频已保存':'Paused · Received audio is saved','正在整理转写、翻译与总结':'Finishing transcript, translation, and summary','部分译文未完成，原文已保留':'Some translations are incomplete; the original is saved','录音已完成 · 文字已同步':'Recording complete · Transcript is up to date',
  '正在等待语音，确认后的文字会显示在这里。':'Waiting for speech. Recognized words will appear here.',
  'Codex 正在整理总结…':'Codex is preparing the summary…','自动总结未完成，转写仍已保存。可以重新生成总结，或在聊天里继续整理。':'The summary failed, but your transcript is saved. Retry or ask Codex to summarize it in chat.',
  '正在补齐转写与翻译，随后自动总结…':'Finishing transcription and translation before summarizing…','结束录音后，自动整理摘要、要点和待办。':'Stop recording to generate an overview, key points, and action items.',
  '当前没有可复制的文字。':'There is no transcript to copy yet.','无法开始录音：':'Cannot start recording: ','停止时出错：':'Could not stop recording: ','复制失败，请选中文字后按 Ctrl+C：':'Copy failed. Select text and press Ctrl+C: ',
  '与本机服务连接中断：':'Connection to the local service was interrupted: ','请求失败':'Request failed',
  '麦克风已断开，正在保存已有内容。':'The microphone disconnected. Saving captured audio.',
  '本地服务已重启，麦克风已停止。请检查已保存的录音后重新开始。':'The service restarted and the microphone stopped. Check the saved recording before starting again.',
  '部分音频未成功保存，以下总结可能不完整。':'Some audio was not saved. The summary may be incomplete.',
  '音频上传到本机服务失败。请保持页面打开；已有音频已保存。':'Audio could not reach the local service. Keep this page open; earlier audio is saved. ',
  '最近一段：识别 {asr} 秒 · 排队 {queue} 秒':'Last chunk: ASR {asr}s · Queue {queue}s',' · 翻译 {seconds} 秒':' · Translation {seconds}s','已保存 {time} 音频 · 本机':'Saved {time} of audio · On this device',
  '麦克风音量':'Microphone level','总结失败：':'Summary failed: ',
  '找不到可用的 Codex CLI。请检查 Codex 安装或 local.settings.json 中的 codex 路径。':'Codex CLI was not found. Check the Codex installation or its path in local.settings.json.',
  'Codex 登录已失效，请执行 codex login 后重试。':'Codex sign-in expired. Run codex login and retry.',
  '当前账号请求额度或速率受限，请稍后重试。':'The account usage or rate limit was reached. Try again later.',
  '网络访问被拒绝（HTTP 403），请检查网络与 Codex 登录状态后重试。':'Network access was denied (HTTP 403). Check your connection and Codex sign-in.',
  'Codex 请求未完成，请检查登录状态、网络或账号额度。':'The Codex request did not finish. Check sign-in, network, or account limits.'
 };
 let language=localStorage.getItem('recorder.uiLanguage')||(/^zh\b/i.test(navigator.language)?'zh':'en');
 if(!['zh','en'].includes(language))language='en';
 function t(key,values={}){let value=language==='en'?(en[key]||key):key;return value.replace(/\{(\w+)\}/g,(match,name)=>values[name]??match);}
 function error(message){return String(message).split('\n').map(line=>{for(const prefix of ['总结失败：','无法开始录音：','停止时出错：','与本机服务连接中断：','复制失败，请选中文字后按 Ctrl+C：','音频上传到本机服务失败。请保持页面打开；已有音频已保存。']){if(line.startsWith(prefix))return t(prefix)+t(line.slice(prefix.length));}return t(line);}).join('\n');}
 function apply(){document.documentElement.lang=language==='zh'?'zh-CN':'en';document.title=t('拾音 · Codex 录音笔');document.querySelectorAll('[data-i18n]').forEach(el=>el.textContent=t(el.dataset.i18n));document.querySelectorAll('[data-i18n-aria]').forEach(el=>el.setAttribute('aria-label',t(el.dataset.i18nAria)));}
 function set(value){if(!['zh','en'].includes(value))return;language=value;localStorage.setItem('recorder.uiLanguage',value);apply();}
 function initialize(){document.querySelectorAll('body *').forEach(el=>{const text=el.textContent.trim();if(el.parentElement?.id==='ui-language')return;if(!el.children.length&&en[text]&&!el.hasAttribute('data-i18n'))el.dataset.i18n=text;});apply();}
 return {t,error,apply,set,initialize,get language(){return language},catalog:en};
})();
