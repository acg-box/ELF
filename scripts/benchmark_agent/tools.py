"""Read-only adapters over public ELF APIs, with explicit ablation boundaries."""
import copy
import urllib.error
import urllib.parse


def schemas(condition,grounded=False):
    if condition=='initial':return []
    definitions=[('search_notes','Search stored memories. Returns note ids and summaries.',{'query':{'type':'string'}},['query']),
                 ('get_note','Read a memory including its derived structured fields. In source-enabled runs it includes original provenance.',{'note_id':{'type':'string'}},['note_id'])]
    if condition!='initial':
        definitions += [('get_search','Widen an existing search session before issuing another query when its first results are incomplete. Reuses cached candidates without a new embedding. Start with top_k 24; maximum 60.',{'search_id':{'type':'string'},'top_k':{'type':'integer','minimum':1,'maximum':60}},['search_id'])]
    if condition in ('source','both'):
        definitions += [('search_documents','Search original source records by subject, keywords or an evidence quote. Returns document and chunk pointers.',{'query':{'type':'string'}},['query']),
                        ('read_document','Read a verified original excerpt using exactly one selector: chunk_id OR position, never both.',{'doc_id':{'type':'string'},'chunk_id':{'type':'string'},'position':{'type':'object','properties':{'start':{'type':'integer'},'end':{'type':'integer'}},'required':['start','end']},'content_hash':{'type':'string'}},['doc_id'])]
    if condition in ('graph','both'):
        definitions += [('query_graph','Read outgoing facts for a subject by canonical name or a previously returned entity id. Traverse returned object entities with further queries, and inspect evidence_note_ids with get_note. Optional as_of is an RFC3339 timestamp.',{'surface':{'type':'string'},'entity_id':{'type':'string'},'as_of':{'type':'string'}},[])]
    result=[{'type':'function','function':{'name':n,'description':d,'parameters':{'type':'object','properties':p,'required':r,'additionalProperties':False}}} for n,d,p,r in definitions]
    if grounded:
        for tool in result:
            if tool['function']['name']=='read_document':tool['function']['parameters']['oneOf']=[{'required':['chunk_id'],'not':{'required':['position']}},{'required':['position'],'not':{'required':['chunk_id']}}]
            if tool['function']['name']=='get_note' and condition in ('source','both'):tool['function']['description']='Read a derived memory together with bounded verified ORIGINAL source context, subject, time, hashes, and byte offsets. Prefer this before fuzzy source search. Sources are authoritative records of what was stated, not proof that every assertion is true.'
    return result


def project_note(value,condition):
    value=copy.deepcopy(value)
    if condition not in ('source','both'):value.pop('source_ref',None)
    return value


def execute(api,condition,name,args,grounded=False):
    allowed={s['function']['name'] for s in schemas(condition)}
    if name not in allowed:raise ValueError('Tool unavailable in this condition')
    if name=='search_notes':return search_view(api('/v2/searches',{'mode':'planned_search','query':args['query'],'top_k':12,'candidate_k':60}))
    if name=='get_search':
        count=int(args.get('top_k',24))
        if not 1<=count<=60:raise ValueError('top_k must be between 1 and 60')
        return search_view(api('/v2/searches/'+urllib.parse.quote(args['search_id'],safe='')+'?top_k='+str(count)+'&touch=false'))
    if name=='get_note':
        if grounded and condition in ('source','both'):
            result=api('/v2/notes/'+args['note_id']+'/evidence')
            return {**result['note'],'source_evidence':result['sources'],'source_evidence_complete':result['complete']}
        return project_note(api('/v2/notes/'+args['note_id']),condition)
    if name=='search_documents':return api('/v2/docs/search/l0',{'query':args['query'],'top_k':12,'candidate_k':60,'explain':False})
    if name=='read_document':
        selector={k:args[k] for k in ('chunk_id','position') if k in args}
        if len(selector)!=1:raise ValueError('Supply exactly one returned chunk or byte-position selector')
        value=api('/v2/docs/excerpts',{'doc_id':args['doc_id'],**selector,'level':'L2','explain':False})
        if not value['verification']['verified']:raise ValueError('Source excerpt verification failed')
        if args.get('content_hash') and args['content_hash']!=value['verification']['content_hash']:raise ValueError('Source pointer content hash mismatch')
        return {'excerpt':value,'metadata':api('/v2/docs/'+args['doc_id'])}
    subject={'entity_id':args['entity_id']} if args.get('entity_id') else {'surface':args['surface']}
    return api('/v2/graph/query',{'subject':subject,'as_of':args.get('as_of'),'limit':50,'explain':False})


def safe_execute(api,condition,name,args,grounded=False):
    try:return execute(api,condition,name,args,grounded)
    except urllib.error.HTTPError as error:
        return {'error':{'http_status':error.code,'detail':error.read().decode()}}
    except (ValueError,KeyError) as error:return {'error':str(error)}


def search_view(result):
    """Keep native evidence and cached-session identity; omit internal ranking traces."""
    return {k:result[k] for k in ('search_id','items','total','has_more') if k in result}
