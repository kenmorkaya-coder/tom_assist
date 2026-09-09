"""Read-only token-boundary and detokenizer replay audit; no model generation."""
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from gateway.gemma_training_alignment import check_alignment
from validation.event_graph_v4.experiment import MODEL,DATA_DIR


def main():
    from mlx_lm.tokenizer_utils import load
    tokenizer=load(MODEL,tokenizer_config_extra={'local_files_only':True})
    results={}
    for split in ('train','valid'):
        rows=[json.loads(x) for x in (DATA_DIR/'training'/f'{split}.jsonl').read_text().splitlines()]
        max_length=0
        for row in rows:
            messages=row['messages']
            lengths=check_alignment(tokenizer,messages)
            max_length=max(max_length,lengths['total_tokens'])
            prefix=tokenizer.apply_chat_template(messages[:-1],tokenize=False,add_generation_prompt=True,enable_thinking=False)
            # Mirror the installed stream_generate string-prompt encoding branch.
            add_special=tokenizer.bos_token is None or not prefix.startswith(tokenizer.bos_token)
            actual_prefix=tokenizer.encode(prefix,add_special_tokens=add_special)
            expected_prefix=tokenizer.apply_chat_template(messages[:-1],return_dict=False,add_generation_prompt=True,enable_thinking=False)
            assert actual_prefix==expected_prefix
            answer=messages[-1]['content']
            ids=tokenizer.encode(answer,add_special_tokens=False)
            assert tokenizer.decode(ids)==answer
            decoder=tokenizer.detokenizer;decoder.reset();pieces=[]
            for token in ids:
                decoder.add_token(token);pieces.append(decoder.last_segment)
            decoder.finalize();pieces.append(decoder.last_segment)
            assert ''.join(pieces)==answer and decoder.text==answer
        results[split]={'records_verified':len(rows),'max_supervised_tokens':max_length,
            'inference_prefix_matches':True,'answer_roundtrip_matches':True,'streamed_answer_replay_matches':True}
    result={'status':'READ_ONLY_RUNTIME_AUDIT','new_generations':0,'training_updates':0,
        'detokenizer':type(tokenizer.detokenizer).__name__,'splits':results,
        'limitation':'Known-token replay tests decoding; historical generation token IDs were not saved, so this is not a reconstruction of their sampled token streams.'}
    out=ROOT/'.tmp/event-graph-binding-audit-001';out.mkdir(parents=True,exist_ok=True)
    with (out/'runtime.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
