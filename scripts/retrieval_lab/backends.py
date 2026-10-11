"""Native database adapters. Authority and application semantics stay outside this lab."""
import re
import time
from collections import defaultdict
import infinity
from infinity.common import NetworkAddress, ConflictType
from infinity.index import IndexInfo, IndexType
import psycopg
from pgvector.psycopg import register_vector
from qdrant_client import QdrantClient, models

HOST = 'host.docker.internal'
DIM = 1536


def lexical(text):
    return ' '.join(re.findall(r'[a-z0-9_]+|[\u3400-\u9fff]|[^\W\d_]+', text.casefold()))


def rrf(lists, k=10):
    scores = defaultdict(float)
    for rows in lists:
        for rank, identity in enumerate(rows, 1):
            scores[identity] += 1 / (60 + rank)
    return sorted(scores, key=lambda identity: (-scores[identity], identity))[:k]


class Qdrant:
    def __init__(self, name):
        self.name = name
        self.client = QdrantClient(host=HOST, port=19865, grpc_port=19866, prefer_grpc=True, timeout=600, cloud_inference=True)

    def create(self, rows, vectors, hybrid=False):
        if self.client.collection_exists(self.name):
            raise ValueError('Refuse to replace an existing benchmark collection')
        self.client.create_collection(self.name, vectors_config={'dense': models.VectorParams(size=DIM, distance=models.Distance.COSINE)},
            sparse_vectors_config={'bm25': models.SparseVectorParams(modifier=models.Modifier.IDF)} if hybrid else None,
            hnsw_config=models.HnswConfigDiff(m=16, ef_construct=200, max_indexing_threads=4, full_scan_threshold=10),
            optimizers_config=models.OptimizersConfigDiff(indexing_threshold=1, max_optimization_threads=1), shard_number=1)
        self.client.create_payload_index(self.name, 'tenant', models.PayloadSchemaType.INTEGER, wait=True)
        for offset in range(0, len(rows), 256):
            points=[]
            for row, vector in zip(rows[offset:offset+256], vectors[offset:offset+256]):
                value={'dense':vector.tolist()}
                if hybrid: value['bm25']=models.Document(text=lexical(row['text']), model='qdrant/bm25')
                points.append(models.PointStruct(id=row['id'], vector=value, payload={'tenant':row['tenant']}))
            self.client.upsert(self.name, points=points, wait=True)
        start=time.monotonic()
        while True:
            state=self.client.get_collection(self.name)
            if state.status == models.CollectionStatus.GREEN and (len(rows)<1000 or state.indexed_vectors_count >= len(rows)):
                return {'points':state.points_count,'indexed_vectors':state.indexed_vectors_count}
            if time.monotonic()-start>900:raise TimeoutError(str(state))
            time.sleep(1)

    def search(self, vector, tenant=None, ef=64, k=10):
        fil=models.Filter(must=[models.FieldCondition(key='tenant',match=models.MatchValue(value=tenant))]) if tenant is not None else None
        return [x.id for x in self.client.query_points(self.name, query=vector.tolist(), using='dense',query_filter=fil,
            search_params=models.SearchParams(hnsw_ef=ef),limit=k,with_payload=False,with_vectors=False).points]

    def text(self, query, tenant, k=60):
        fil=models.Filter(must=[models.FieldCondition(key='tenant',match=models.MatchValue(value=tenant))])
        return [x.id for x in self.client.query_points(self.name,query=models.Document(text=lexical(query),model='qdrant/bm25'),using='bm25',query_filter=fil,limit=k,with_payload=False).points]

    def close(self):
        self.client.close()

    def delete(self, identity):
        self.client.delete(self.name, points_selector=models.PointIdsList(points=[identity]),wait=True)


class Infinity:
    def __init__(self, name):
        self.name=name
        self.client=infinity.connect(NetworkAddress(HOST,19869))
        self.db=self.client.get_database('default_db')
        self.table=None

    def create(self, rows, vectors, hybrid=False):
        schema={'id':{'type':'integer'},'tenant':{'type':'integer'},'vec':{'type':f'vector,{DIM},float'}}
        if hybrid:schema['body']={'type':'varchar'}
        self.table=self.db.create_table(self.name,schema,ConflictType.Error)
        for offset in range(0,len(rows),256):
            batch=[]
            for row,vector in zip(rows[offset:offset+256],vectors[offset:offset+256]):
                item={'id':row['id'],'tenant':row['tenant'],'vec':vector.tolist()}
                if hybrid:item['body']=lexical(row['text'])
                batch.append(item)
            self.table.insert(batch)
        self.table.create_index('tenant_idx',IndexInfo('tenant',IndexType.Secondary),ConflictType.Error)
        self.table.create_index('dense_idx',IndexInfo('vec',IndexType.Hnsw,{'m':'16','ef_construction':'200','metric':'cosine','encode':'plain'}),ConflictType.Error)
        if hybrid:self.table.create_index('text_idx',IndexInfo('body',IndexType.FullText,{'analyzer':'standard'}),ConflictType.Error)
        return {'rows':len(rows),'index_created':True}

    def get(self):
        if self.table is None:self.table=self.db.get_table(self.name)
        return self.table

    def search(self, vector, tenant=None, ef=64, k=10):
        query=self.get().output(['id']).match_dense('vec',vector.tolist(),'float','cosine',k,{'ef':str(ef)})
        if tenant is not None:query=query.filter('tenant = '+str(int(tenant)))
        result=query.to_result()
        return result[0]['id']

    def text(self, query, tenant, k=60):
        return self.get().output(['id']).match_text('body',lexical(query),k).filter('tenant = '+str(int(tenant))).to_result()[0]['id']

    def close(self):
        self.client.disconnect()

    def delete(self, identity):
        self.get().delete('id = '+str(int(identity)))


class Postgres:
    def __init__(self,name):
        assert re.fullmatch('[a-z0-9_]+',name)
        self.name=name
        self.client=psycopg.connect(host=HOST,port=19867,user='postgres',password='lab-only-local',dbname='postgres',autocommit=True)
        self.client.execute('CREATE EXTENSION IF NOT EXISTS vector')
        register_vector(self.client)
        self.client.execute("SET hnsw.iterative_scan = 'strict_order'")
        self.client.execute('SET max_parallel_workers_per_gather = 4')

    def create(self,rows,vectors,hybrid=False):
        self.client.execute('CREATE EXTENSION IF NOT EXISTS vector')
        self.client.execute(f'CREATE TABLE {self.name} (id integer PRIMARY KEY, tenant integer NOT NULL, vec vector({DIM}), body text, lex tsvector)')
        with self.client.cursor().copy(f'COPY {self.name} (id,tenant,vec,body) FROM STDIN') as copy:
            for row,vector in zip(rows,vectors):
                copy.write_row((row['id'],row['tenant'],str(vector.tolist()),lexical(row.get('text','')) if hybrid else ''))
        self.client.execute("SET maintenance_work_mem = '1GB'")
        self.client.execute('SET max_parallel_maintenance_workers = 4')
        self.client.execute(f'CREATE INDEX ON {self.name} USING hnsw (vec vector_cosine_ops) WITH (m=16,ef_construction=200)')
        self.client.execute(f'CREATE INDEX ON {self.name} (tenant)')
        if hybrid:
            self.client.execute(f"UPDATE {self.name} SET lex=to_tsvector('simple',body)")
            self.client.execute(f'CREATE INDEX ON {self.name} USING gin(lex)')
        self.client.execute(f'ANALYZE {self.name}')
        return {'rows':self.client.execute(f'SELECT count(*) FROM {self.name}').fetchone()[0],'pgvector':self.client.execute("SELECT extversion FROM pg_extension WHERE extname='vector'").fetchone()[0]}

    def search(self,vector,tenant=None,ef=64,k=10):
        if getattr(self, 'ef', None) != ef:
            self.client.execute('SELECT set_config(%s,%s,false)',('hnsw.ef_search',str(ef)))
            self.ef = ef
        # Use the PostgreSQL planner, including exact filtered scans when it prefers them.
        where='' if tenant is None else 'WHERE tenant = %s'
        args=() if tenant is None else (tenant,)
        return [r[0] for r in self.client.execute(f'SELECT id FROM {self.name} {where} ORDER BY vec <=> %s::vector LIMIT %s',(*args,vector,k)).fetchall()]

    def text(self,query,tenant,k=60):
        terms=sorted(set(lexical(query).split()))
        tsquery=' | '.join("'"+word+"'" for word in terms)
        return [r[0] for r in self.client.execute(f"SELECT id FROM {self.name}, to_tsquery('simple', %s) q WHERE tenant=%s AND lex @@ q ORDER BY ts_rank_cd(lex,q) DESC,id LIMIT %s",(tsquery,tenant,k)).fetchall()]

    def close(self):
        self.client.close()

    def delete(self,identity):
        self.client.execute(f'DELETE FROM {self.name} WHERE id=%s',(identity,))


    def plans(self, vector):
        return {
            'unfiltered': self.client.execute(f'EXPLAIN (FORMAT JSON) SELECT id FROM {self.name} ORDER BY vec <=> %s::vector LIMIT 10', (vector,)).fetchone()[0],
            'filtered': self.client.execute(f'EXPLAIN (FORMAT JSON) SELECT id FROM {self.name} WHERE tenant=0 ORDER BY vec <=> %s::vector LIMIT 10', (vector,)).fetchone()[0],
            'relation_bytes': self.client.execute('SELECT pg_total_relation_size(%s)', (self.name,)).fetchone()[0],
        }


BACKENDS={'qdrant':Qdrant,'infinity':Infinity,'postgres':Postgres}
