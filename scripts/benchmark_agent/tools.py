"""Read-only adapters over public ELF APIs, with explicit ablation boundaries."""
import copy
import json
import urllib.error


def schemas(condition):
    definitions=[('search_notes','Search stored memories. Returns note ids and summaries.',{'query':{'type':'string'}},['query']),
                 ('get_note','Read a memory including its derived structured fields. In source-enabled runs it includes original provenance.',{'note_id':{'type':'string'}},['note_id'])]
    if condition in ('source','both'):
        definitions += [('search_documents','Search original source records by subject, keywords or an evidence quote. Returns document and chunk pointers.',{'query':{'type':'string'}},['query']),
                        ('read_document','Read a verified original excerpt and its source metadata using a returned pointer.',{'doc_id':{'type':'string'},'chunk_id':{'type':'string'}},['doc_id','chunk_id'])]
    if condition in ('graph','both'):
        definitions += [('query_graph','Read outgoing facts for a subject by canonical name or a previously returned entity id. Traverse returned object entities with further queries, and inspect evidence_note_ids with get_note. Optional as_of is an RFC3339 timestamp.',{'surface':{'type':'string'},'entity_id':{'type':'string'},'as_of':{'type':'string'}},[])]
    return [{'type':'function','function':{'name':n,'description':d,'parameters':{'type':'object','properties':p,'required':r,'additionalProperties':False}}} for n,d,p,r in definitions]


def project_note(value,condition):
    value=copy.deepcopy(value)
    if condition not in ('source','both'):value.pop('source_ref',None)
    return value


def execute(api,condition,name,args):
    allowed={s['function']['name'] for s in schemas(condition)}
    if name not in allowed:raise ValueError('Tool unavailable in this condition')
    if name=='search_notes':return api('/v2/searches',{'mode':'planned_search','query':args['query'],'top_k':12,'candidate_k':60})
    if name=='get_note':return project_note(api('/v2/notes/'+args['note_id']),condition)
    if name=='search_documents':return api('/v2/docs/search/l0',{'query':args['query'],'top_k':12,'candidate_k':60,'explain':True})
    if name=='read_document':
        value=api('/v2/docs/excerpts',{'doc_id':args['doc_id'],'chunk_id':args['chunk_id'],'level':'L2','explain':True})
        if not value['verification']['verified']:raise ValueError('Source excerpt verification failed')
        return {'excerpt':value,'metadata':api('/v2/docs/'+args['doc_id'])}
    subject={'entity_id':args['entity_id']} if args.get('entity_id') else {'surface':args['surface']}
    return api('/v2/graph/query',{'subject':subject,'as_of':args.get('as_of'),'limit':50,'explain':True})


def safe_execute(api,condition,name,args):
    try:return execute(api,condition,name,args)
    except urllib.error.HTTPError as error:
        return {'error':{'http_status':error.code,'detail':error.read().decode()}}
    except (ValueError,KeyError) as error:return {'error':str(error)}
