"""Register the complete application as a personal Codex skill."""
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPOSITORY='https://github.com/zhuoqiliu1225-oss/CodexRecorder'

def install(destination):
    destination=Path(destination).expanduser()
    if not (ROOT/'app/server.py').is_file():raise ValueError('Install the full repository first.')
    marker=destination/'installation.json'
    if destination.is_symlink():raise ValueError('Refusing a symlink destination.')
    if destination.exists():
        if not marker.is_file() or json.loads(marker.read_text(encoding='utf-8')).get('repository')!=REPOSITORY:
            raise ValueError('Destination is not managed by CodexRecorder; no files changed.')
    content=(ROOT/'.agents/skills/recorder/SKILL.md').read_text(encoding='utf-8')
    content=content.replace('name: recorder','name: codex-recorder').replace('仓库根目录是此技能目录的上三级。','先读取此技能目录的 installation.json；projectRoot 字段是已安装程序的完整根目录。')
    destination.mkdir(parents=True,exist_ok=True)
    (destination/'SKILL.md').write_text(content,encoding='utf-8')
    marker.write_text(json.dumps({'repository':REPOSITORY,'projectRoot':str(ROOT),'version':'0.2'},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Installed codex-recorder:',destination)
    print('Keep the application folder. Open a new Codex chat to discover the skill.')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--destination',type=Path,default=Path.home()/'.agents/skills/codex-recorder')
    install(parser.parse_args().destination)
