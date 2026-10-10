"""Expose the image's CPU reranker and a common tokenizer to the local experiment.

This runs in the official Hindsight image. No provider credentials are required.
"""
import asyncio
import json
import math
from http.server import BaseHTTPRequestHandler, HTTPServer
import tiktoken
from hindsight_api.engine.cross_encoder import create_cross_encoder_from_env

encoder = create_cross_encoder_from_env()
asyncio.run(encoder.initialize())
tokenizer = tiktoken.get_encoding('cl100k_base')


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.path == '/tokens':
            ids = tokenizer.encode(body['text'])
            cap = body.get('max_tokens', len(ids))
            result = {'count':len(ids), 'used':min(cap,len(ids)), 'text':tokenizer.decode(ids[:cap]), 'tokenizer':'cl100k_base'}
        else:
            documents=[d if isinstance(d,str) else d['text'] for d in body['documents']]
            scores=asyncio.run(encoder.predict([(body['query'],d) for d in documents]))
            result={'results':sorted([{'index':i,'relevance_score':1/(1+math.exp(-max(-700,min(700,float(s)))))} for i,s in enumerate(scores)],key=lambda r:-r['relevance_score']), 'usage':{'total_tokens':0}}
        data=json.dumps(result).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(data)


HTTPServer(('0.0.0.0',8899),Handler).serve_forever()
