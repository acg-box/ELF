"""Replay frozen extraction and exact 4096d inputs; forward only new embeddings."""
import gzip
import hashlib
import json
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def signature(messages):
    return hashlib.sha256(json.dumps(messages,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


class Replay:
    def __init__(self, receipt_file, upstream, token, log, query_receipts=None, live_extraction=False, reuse_receipts=()):
        self.extractions={}; self.vectors={}; self.upstream=upstream; self.token=token; self.log=log
        self.lock=threading.Lock(); self.live_extraction=live_extraction
        for line in gzip.decompress(receipt_file.read_bytes()).splitlines():
            row=json.loads(line);request,response=row['request'],row['response']
            if 'input' in request:
                if request.get('dimensions')!=4096:continue
                inputs=request['input'] if isinstance(request['input'],list) else [request['input']]
                for item in response.get('data',[]):
                    assert len(item['embedding'])==4096
                    self.vectors.setdefault(inputs[item['index']],(item['embedding'],row['ordinal']))
            elif request.get('messages') and request['messages'][0]['content'].startswith('You are a memory extraction engine'):
                choice=response.get('choices',[{}])[0]
                if choice.get('finish_reason') in ('error','length'):continue
                try:
                    content=json.loads(choice['message']['content'])
                    if not isinstance(content.get('notes'),list):continue
                except (KeyError,TypeError,ValueError):continue
                # Later successful replay of an identical source supersedes a failed attempt.
                self.extractions[signature(request['messages'])]=(response,row['ordinal'])
        for receipt in reuse_receipts:
            for line in gzip.decompress(receipt.read_bytes()).splitlines():
                row=json.loads(line);request,response=row['request'],row['response']
                if 'input' not in request or request.get('dimensions')!=4096:continue
                inputs=request['input'] if isinstance(request['input'],list) else [request['input']]
                for item in response.get('data',[]):
                    assert len(item['embedding'])==4096
                    self.vectors.setdefault(inputs[item['index']],(item['embedding'],row['ordinal']))
        if query_receipts is not None:
            for path in sorted(query_receipts.glob('*.json'),key=lambda p:int(p.stem)):
                row=json.loads(path.read_text());request,response=row['request'],row['response']
                if 'input' not in request or request.get('dimensions')!=4096:continue
                inputs=request['input'] if isinstance(request['input'],list) else [request['input']]
                for item in response.get('data',[]):
                    assert len(item['embedding'])==4096
                    self.vectors.setdefault(inputs[item['index']],(item['embedding'],int(path.stem)))

    def record(self,row):
        with self.lock:
            with self.log.open('a') as stream:stream.write(json.dumps(row)+'\n')

    def resolve(self,path,body):
        if path.endswith('/chat/completions'):
            key=signature(body['messages'])
            if self.live_extraction:
                request=urllib.request.Request(self.upstream.rstrip('/')+'/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+self.token})
                with urllib.request.urlopen(request,timeout=3600) as result:response=json.load(result)
                self.record({'kind':'extraction','request_sha256':key,'response_id':response.get('id'),'replayed':False})
                return response
            if key not in self.extractions:raise ValueError('Frozen extraction request mismatch: '+key)
            response,ordinal=self.extractions[key]
            self.record({'kind':'extraction','request_sha256':key,'receipt_ordinal':ordinal,'replayed':True})
            return response
        if not path.endswith('/embeddings'):raise ValueError('Unsupported fixture endpoint')
        inputs=body['input'] if isinstance(body['input'],list) else [body['input']]
        if all(text in self.vectors for text in inputs):
            self.record({'kind':'embedding','inputs':[{'sha256':hashlib.sha256(t.encode()).hexdigest(),'receipt_ordinal':self.vectors[t][1]} for t in inputs],'replayed':True})
            return {'object':'list','model':'qwen/qwen3-embedding-8b','data':[{'object':'embedding','index':i,'embedding':self.vectors[t][0]} for i,t in enumerate(inputs)],'usage':{'prompt_tokens':0,'total_tokens':0,'cost':0}}
        request=urllib.request.Request(self.upstream.rstrip('/')+'/embeddings',data=json.dumps(body).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+self.token})
        with urllib.request.urlopen(request,timeout=3600) as result:response=json.load(result)
        for item in response['data']:
            assert len(item['embedding'])==4096
            self.vectors.setdefault(inputs[item['index']],(item['embedding'],'current-budget-ledger'))
        self.record({'kind':'embedding','replayed':False,'inputs':len(inputs)})
        return response

    def start(self):
        owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                if self.headers.get('Authorization')!='Bearer '+owner.token:
                    self.send_error(401);return
                try:
                    body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    value=owner.resolve(self.path,body);status=200
                except Exception as error:
                    value={'error':{'message':str(error).replace(owner.token,'[redacted]')}};status=422
                raw=json.dumps(value).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(raw)
        self.server=ThreadingHTTPServer(('0.0.0.0',0),Handler)
        threading.Thread(target=self.server.serve_forever,daemon=True).start()
        return 'http://127.0.0.1:'+str(self.server.server_port)+'/v1'
