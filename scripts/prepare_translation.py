"""Download pinned, data-only M2M100 CT2 weights (about 500 MB)."""
from pathlib import Path
import os
os.environ.setdefault('HF_HUB_DISABLE_XET','1')
from huggingface_hub import snapshot_download

root=Path(__file__).resolve().parents[1]
path=snapshot_download('gn64/M2M100_418M_CTranslate2',
    revision='18e406c615ef2991fa74d53734bf66b0a6b10cb4',
    local_dir=root/'models'/'m2m100',
    allow_patterns=['model.bin','config.json','sentencepiece.bpe.model','shared_vocabulary.json','README.md'])
print(path,flush=True)
