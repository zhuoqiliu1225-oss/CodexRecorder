"""M2M100 inference using SentencePiece tokens and CTranslate2 only."""
from pathlib import Path
import ctranslate2
import sentencepiece


class MultilingualTranslator:
    def __init__(self, model_path, device='cpu'):
        path=Path(model_path)
        self.tokenizer=sentencepiece.SentencePieceProcessor(model_proto=(path/'sentencepiece.bpe.model').read_bytes())
        self.model=ctranslate2.Translator(str(path),device=device,
            compute_type='float16' if device=='cuda' else 'int8',intra_threads=4)

    def translate(self,text,source,target):
        tokens=self.tokenizer.encode(text,out_type=str)
        batches=[[f'__{source}__',*tokens[i:i+240],'</s>'] for i in range(0,len(tokens),240)]
        if not batches:
            return ''
        results=self.model.translate_batch(batches,target_prefix=[[f'__{target}__'] for _ in batches],
            beam_size=2,max_decoding_length=512,max_input_length=0)
        values=[]
        for result in results:
            generated=[t for t in result.hypotheses[0] if t not in ('</s>','<s>','<pad>') and not (t.startswith('__') and t.endswith('__'))]
            values.append(self.tokenizer.decode(generated).replace('\u2581',' ').strip())
        return ' '.join(values).strip()
