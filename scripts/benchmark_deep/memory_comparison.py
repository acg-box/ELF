"""Frozen conversation-memory cases for the native product comparison."""
import hashlib


def workload():
    items, queries, oracle = [], [], {}
    for n, person in enumerate(('Mara', 'Ivo', 'Neri', 'Tala', 'Devon')):
        dev = n == 4
        project = ('Larch', 'Cobalt', 'Reed', 'Sable', 'Cedar')[n]
        old, current = f'BATCH-{n}-741', f'STREAM-{n}-286'
        reason, remedy = f'GATE-{n}-519', f'REPLAY-{n}-632'
        texts = [
            f'2026-08-01. {person} started project {project}. They chose {old} for batch delivery. The initial retry policy was RETRY-{n}-108.',
            f'2026-08-08. {person} reported that {old} lost updates during {reason} outages. The team tested {remedy}, which restored the missing updates. No change of delivery mode was approved at this meeting.',
            f'2026-08-15. {person} approved switching {project} from {old} to {current}. This supersedes the August 1 delivery decision. The cause was the {reason} outages recorded on August 8; keep the successful recovery procedure from that incident.',
            f'2026-08-22. {person} reviewed {project}. Keep the August 15 delivery choice. For the next outage, use the recovery procedure validated on August 8. The retry policy is now RETRY-{n}-907, superseding RETRY-{n}-108. No budget owner has been appointed.'
        ]
        ids = []
        for j,text in enumerate(texts):
            eid='m_'+hashlib.sha256(text.encode()).hexdigest()[:16];ids.append(eid)
            items.append({'evidence_id':eid,'text':text,'timestamp':f'2026-08-{(1,8,15,22)[j]:02d}T12:00:00Z'})
        questions = [
            (f'As of August 22, what delivery mode and retry policy apply to {person}\'s {project} project?', [current,f'RETRY-{n}-907'],[old,f'RETRY-{n}-108'],'updates'),
            (f'For the next outage on {project}, which recovery procedure should {person} use, and which outage gate led to the delivery-mode change?', [remedy,reason],[],'cross_session'),
            (f'What delivery mode was still approved for {person}\'s {project} project immediately after the August 8 meeting?', [old],[current],'temporal'),
            (f'Who is the appointed budget owner for {person}\'s {project} project as of August 22?',[],[],'abstention')]
        for j,(q,facts,forbidden,lane) in enumerate(questions):
            case=f'memory-{n}-{j}'
            queries.append({'case_id':case,'question':q,'lane':lane,'split':'dev' if dev else 'test'})
            oracle[case]={'facts':facts,'forbidden':forbidden,'supported':bool(facts),'evidence':ids if facts else []}
    return {'items':items,'queries':queries},oracle
