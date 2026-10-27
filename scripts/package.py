"""Build a source-only preview ZIP; private data, settings and models are excluded."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root=Path(__file__).resolve().parents[1]
dest=root/'dist'
dest.mkdir(exist_ok=True)
output=dest/'codex-recorder-0.2-windows-source.zip'
folders=['app','web','scripts','tests','.agents','docs','.github']
files=[root/name for name in ['README.md','README.zh-CN.md','THIRD_PARTY_NOTICES.md','requirements.txt','settings.example.json','.gitignore','.gitattributes']]
for name in folders:
    files.extend(p for p in (root/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
with ZipFile(output,'w',ZIP_DEFLATED) as archive:
    for file in sorted(files):
        archive.write(file,Path('codex-recorder')/file.relative_to(root))
print(output)
