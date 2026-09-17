"""Frozen causal-binding diagnosis, with no training or held-out claim."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import argparse
import json
import os
import time
from collections import defaultdict
from validation.event_graph_v1.build_corpus import Builder
from validation.event_graph_v16 import session as parent
from gateway.typed_event_graph import semantic_graph, validate_graph
from gateway.event_graph_span_wire import to_wire

HERE = Path(__file__).parent
PARENT = ROOT / '.tmp/event-graph-lora-v16-session-001'
FORMS = (
    ('active', '{s} causes {t}.', '{s} brings about {t}.'),
    ('passive', '{t} is caused by {s}.', '{t} is brought about by {s}.'),
    ('cause_cleft', 'The cause of {t} is {s}.', 'The cause responsible for {t} is {s}.'),
    ('process_cleft', 'The process bringing about {t} is {s}.', 'The process that causes {t} is {s}.'),
    ('result', '{t} results from {s}.', '{t} occurs as a result of {s}.'),
    ('effect', 'The effect of {s} is {t}.', '{s} has the following effect: {t}.'),
)


def rows():
    result = []
    for name, canonical, paraphrase in FORMS:
        for i, (a, b) in enumerate((
            ('Juniper Weir intake pumping', 'Juniper Weir surface movement'),
            ('Copper Arcade trench drainage', 'Copper Arcade footing displacement'),
            ('System Q17 operation', 'System R29 operation'),
            ('Unit Delta flow', 'Unit Delta flow restriction'),
        )):
            for v in range(3):
                source, target = (b, a) if v == 2 else (a, b)
                text = (paraphrase if v == 1 else canonical).format(s=source, t=target)
                g = Builder(text)
                src = g.entity(source); dst = g.entity(target)
                g.event('cause', roles={'source': src, 'target': dst}, modality='assertion')
                # Select the standalone entity occurrence, including overlapping names.
                for ent in g.graph['entities']:
                    q = ent['name']
                    starts = [j for j in range(len(text)) if text.startswith(q, j)]
                    other = target if q == source else source
                    starts = [j for j in starts if not (other.startswith(q) and text.startswith(other, j))]
                    assert len(starts) == 1
                    j = starts[0]; ent['mentions'] = [{'start': j, 'end': j + len(q), 'quote': q}]
                validate_graph(g.graph, text)
                result.append({'id': f'v17-{name}-{i}-{v}', 'group': f'v17-{name}-{i}',
                    'family': name, 'variant': ('canonical', 'paraphrase', 'contrast')[v],
                    'source': text, 'graph': g.graph})
    return result


def freeze(run):
    parent.verify(PARENT)
    corpus = rows()
    run.mkdir(parents=True, exist_ok=False)
    with (run / 'diagnostic.jsonl').open('x') as f:
        for row in corpus: f.write(json.dumps(row) + '\n')
    artifacts = {}
    for epoch in (0, 1):
        path = parent.adapter(PARENT, epoch)
        artifacts[str(path / 'adapters.safetensors')] = parent.prior.sha(path / 'adapters.safetensors')
        artifacts[str(path / 'adapter_config.json')] = parent.prior.sha(path / 'adapter_config.json')
    parent.prior.write_new(run / 'freeze.json', {
        'created_unix': time.time(), 'parent_freeze': parent.prior.sha(PARENT / 'freeze.json'),
        'files': {str(p): parent.prior.sha(p) for p in (Path(__file__).resolve(), HERE / 'PROTOCOL.md',
            ROOT / 'gateway/tests/test_event_graph_v17.py', run / 'diagnostic.jsonl')},
        'adapters': artifacts, 'rows': len(corpus), 'max_tokens': 4096,
        'purpose': 'diagnostic development comparison; no training, selection, or held-out verdict'})


def verify(run):
    f = json.loads((run / 'freeze.json').read_text())
    parent.verify(PARENT)
    assert parent.prior.sha(PARENT / 'freeze.json') == f['parent_freeze']
    for path, expected in {**f['files'], **f['adapters']}.items():
        assert parent.prior.sha(Path(path)) == expected, path
    return f


def score(corpus, predictions):
    assert len(predictions) == len(corpus)
    by_id = {p['id']: p for p in predictions}
    assert len(by_id) == len(corpus) and set(by_id) == {r['id'] for r in corpus}
    families = defaultdict(lambda: dict(total=0, valid=0, exact=0))
    details = []; groups = defaultdict(dict)
    for row in corpus:
        p = by_id[row['id']]; valid = 'graph' in p
        actual = semantic_graph(p['graph']) if valid else None
        exact = actual == semantic_graph(row['graph'])
        family = families[row['family']]
        family['total'] += 1; family['valid'] += valid; family['exact'] += exact
        details.append({'id': row['id'], 'exact': exact, 'valid': valid})
        groups[row['group']][row['variant']] = actual
    return dict(total=len(corpus), valid=sum(d['valid'] for d in details),
        exact=sum(d['exact'] for d in details), families=dict(families), details=details,
        groups=len(groups), paraphrase_equal=sum(g['canonical'] is not None and g['canonical'] == g['paraphrase'] for g in groups.values()),
        contrast_distinct=sum(g['canonical'] is not None and g['contrast'] is not None and g['canonical'] != g['contrast'] for g in groups.values()))


def evaluate(run, epoch):
    verify(run)
    from mlx_lm import load, stream_generate
    from mlx_lm.sample_utils import make_sampler
    import mlx.core as mx
    mx.random.seed(7)
    adapter = parent.adapter(PARENT, epoch)
    model, tokenizer = load(str(parent.prior.MODEL), adapter_path=str(adapter))
    corpus = [json.loads(x) for x in (run / 'diagnostic.jsonl').read_text().splitlines()]
    dest = run / f'epoch-{epoch}.jsonl'; sampler = make_sampler(temp=0.0)
    with dest.open('x') as out:
        for row in corpus:
            prompt = tokenizer.apply_chat_template([{'role': 'user', 'content': parent.prompt(row['source'])}],
                tokenize=False, add_generation_prompt=True, enable_thinking=False)
            chunks = list(stream_generate(model, tokenizer, prompt=prompt, max_tokens=4096, sampler=sampler))
            p = dict(id=row['id'], raw=''.join(c.text for c in chunks), token_ids=[int(c.token) for c in chunks],
                finish_reason=chunks[-1].finish_reason, eos_token_ids=sorted(tokenizer.eos_token_ids))
            try: p['graph'] = parent.parse_output(p['raw'], row['source'])
            except (ValueError, TypeError, KeyError, RecursionError) as exc: p['error'] = str(exc)
            out.write(json.dumps(p) + '\n'); out.flush()
            print(json.dumps({'epoch': epoch, 'completed_id': row['id']}), flush=True)
    report = score(corpus, [json.loads(x) for x in dest.read_text().splitlines()])
    report.update(epoch=epoch, cumulative_steps=(4380, 5172)[epoch],
        prediction_sha256=parent.prior.sha(dest), adapter_sha256=parent.prior.sha(adapter / 'adapters.safetensors'))
    parent.prior.write_new(run / f'epoch-{epoch}-report.json', report)


def main():
    p = argparse.ArgumentParser(); p.add_argument('command', choices=('freeze', 'run', 'evaluate'))
    p.add_argument('--run', type=Path, required=True); p.add_argument('--epoch', type=int, choices=(0, 1))
    args = p.parse_args(); run = args.run.resolve()
    if args.command == 'freeze': freeze(run); return
    if args.command == 'evaluate': evaluate(run, args.epoch); return
    import subprocess
    verify(run)
    parent.prior.write_new(run / 'started.json', {'time': time.time()})
    try:
        for epoch in (0, 1):
            (run / 'status.json').write_text(json.dumps({'status': 'RUNNING', 'epoch': epoch}))
            with (run / f'epoch-{epoch}.log').open('x') as log:
                subprocess.run([sys.executable, '-u', str(Path(__file__).resolve()), 'evaluate', '--run', str(run), '--epoch', str(epoch)],
                    stdout=log, stderr=subprocess.STDOUT, check=True)
        parent.prior.write_new(run / 'complete.json', {'status': 'DIAGNOSTIC_COMPLETE_UNREVIEWED', 'time': time.time()})
        (run / 'status.json').write_text(json.dumps({'status': 'COMPLETE_UNREVIEWED'}))
    except BaseException as exc:
        (run / 'status.json').write_text(json.dumps({'status': 'FAILED', 'error': str(exc)})); raise


if __name__ == '__main__': main()
