"""Restore an isolated native checkpoint before the original service entry point."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import urllib.parse

import pg0

source=Path('/restore')
installation=Path('/home/hindsight/.pg0/installation/18.1.0')
installation.parent.mkdir(parents=True,exist_ok=True)
shutil.copytree(source/'postgres-runtime',installation,dirs_exist_ok=True)
os.environ['LD_LIBRARY_PATH']=str(installation/'lib')
# This credential belongs only to the isolated, unpublished benchmark database.
info=pg0.start('hindsight',port=5432,username='hindsight',password='benchmark-local',database='hindsight')
uri=urllib.parse.urlsplit(info.uri)
env={**os.environ,'PGPASSWORD':urllib.parse.unquote(uri.password or '')}
base=['--host',uri.hostname,'--port',str(uri.port or 5432),'--username',urllib.parse.unquote(uri.username or ''),'--dbname',uri.path.lstrip('/')]
restore=subprocess.run([str(installation/'bin/pg_restore'),'--no-owner','--no-acl',*base,str(source/'checkpoint.dump')],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
if restore.returncode: raise RuntimeError('Native checkpoint restoration failed')
query=subprocess.run([str(installation/'bin/psql'),*base,'-Atc',"SELECT DISTINCT worker_id FROM async_operations WHERE status='processing' AND worker_id IS NOT NULL"],env=env,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
workers=query.stdout.splitlines()
if len(workers)!=1: raise RuntimeError('Expected one retained native worker identity')
os.environ['HINDSIGHT_API_WORKER_ID']=workers[0]
os.environ['HINDSIGHT_API_DATABASE_URL']=info.uri
os.environ['HF_HUB_OFFLINE']='1'
os.execv('/app/start-all.sh',['/app/start-all.sh'])
