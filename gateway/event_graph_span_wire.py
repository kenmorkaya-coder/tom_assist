"""Experimental source-span transport, not enabled in any trained extractor.

The model chooses spans and semantic fields. Code materializes those exact spans
and declares only the entities explicitly referenced by model-selected fields.
There is no noun detection, role inference, missing-reference repair or guessing.
"""
from copy import deepcopy
import re
from gateway.typed_event_graph import VERSION as GRAPH_VERSION, validate_graph, obj

VERSION='tom-assist-span-wire/1'
ROOT_FIELDS=('version','predicates','conditions','events','links','unresolved')


def source_tokens(text):
    if not isinstance(text,str) or not 0<len(text)<=64000:
        raise ValueError('source length outside supported bounds')
    return [{'index':i,'text':m.group(),'start':m.start(),'end':m.end()}
            for i,m in enumerate(re.finditer(r'\w+|[^\w\s]',text))]


def source_table(text):
    """Deterministic lexical indexing only; this does not find clauses or entities."""
    return [{'index':r['index'],'text':r['text']} for r in source_tokens(text)]


def materialize_span(span,text,tokens):
    obj(span,('token_start','token_end'))
    start,end=span['token_start'],span['token_end']
    if type(start) is not int or type(end) is not int or not 0<=start<end<=len(tokens):
        raise ValueError('invalid source token span')
    first,last=tokens[start]['start'],tokens[end-1]['end']
    return {'start':first,'end':last,'quote':text[first:last]}


def to_wire(graph,text):
    """Encode authored graphs for representation tests or future training only."""
    graph=validate_graph(graph,text);tokens=source_tokens(text)
    starts={t['start']:t['index'] for t in tokens}
    ends={t['end']:t['index']+1 for t in tokens}
    def index_span(span):
        if span['start'] not in starts or span['end'] not in ends:
            raise ValueError('span is not aligned to lexical token boundaries')
        return {'token_start':starts[span['start']],'token_end':ends[span['end']]}
    names={}
    for entity in graph['entities']:
        candidates=[s for s in entity['mentions'] if s['quote']==entity['name']]
        if not candidates:
            raise ValueError('entity name needs an exact full-name mention')
        names[entity['id']]=index_span(candidates[0])
    result={k:deepcopy(graph[k]) for k in ROOT_FIELDS}
    result['version']=VERSION
    for predicate in result['predicates']:predicate['subject']=names[predicate['subject']]
    for event in result['events']:
        event['roles']={k:names[v] if v is not None else None for k,v in event['roles'].items()}
    def walk(value):
        if isinstance(value,dict):
            if set(value)=={'start','end','quote'}:return index_span(value)
            return {k:walk(v) for k,v in value.items()}
        if isinstance(value,list):return [walk(v) for v in value]
        return value
    return walk(result)


def bind(wire,text):
    """Materialize selected spans; validate all remaining graph references strictly."""
    obj(wire,ROOT_FIELDS)
    if wire['version']!=VERSION:raise ValueError('unsupported source-span wire version')
    tokens=source_tokens(text)
    graph=deepcopy(wire);graph['version']=GRAPH_VERSION
    entities=[];by_span={}
    def entity(span):
        evidence=materialize_span(span,text,tokens)
        key=(evidence['start'],evidence['end'])
        if key not in by_span:
            # Avoid collisions with model-declared predicate, condition, event or link IDs.
            used={r['id'] for table in ('predicates','conditions','events','links') for r in graph[table]}
            name=f'source_entity_{len(entities)+1}'
            while name in used:name+='_'
            by_span[key]=name
            entities.append({'id':name,'name':evidence['quote'],'mentions':[evidence]})
        return by_span[key]
    for predicate in graph['predicates']:predicate['subject']=entity(predicate['subject'])
    for event in graph['events']:
        event['roles']={k:entity(v) if v is not None else None for k,v in event['roles'].items()}
    def walk(value):
        if isinstance(value,dict):
            if 'token_start' in value or 'token_end' in value:return materialize_span(value,text,tokens)
            if any(k in value for k in ('start','end','quote')):
                raise ValueError('wire evidence must use token spans only')
            return {k:walk(v) for k,v in value.items()}
        if isinstance(value,list):return [walk(v) for v in value]
        return value
    graph=walk(graph);graph['entities']=entities
    return validate_graph(graph,text)
