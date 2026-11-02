"""L4 Rules Knowledge Base RAG & Evaluation Domain Ontology engine."""
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load_rules():
    return json.loads((ROOT / 'data/rules_corpus.json').read_text(encoding='utf-8'))

def load_ontology():
    return json.loads((ROOT / 'data/ontology.json').read_text(encoding='utf-8'))

def load_event_weights():
    return json.loads((ROOT / 'data/event_weights.json').read_text(encoding='utf-8'))

def _tokenize(text):
    if not text:
        return []
    lowered = text.casefold()
    en_tokens = re.findall(r'[a-z0-9_.+-]+', lowered)
    zh_chars = re.findall(r'[一-鿿]', lowered)
    zh_bigrams = [zh_chars[i] + zh_chars[i + 1] for i in range(len(zh_chars) - 1)]
    return en_tokens + zh_chars + zh_bigrams

def search_rules(query_text, category=None, top_k=4):
    corpus = load_rules()
    docs = corpus.get('documents', [])
    if category:
        docs = [d for d in docs if d.get('category') == category]
    if not query_text or not str(query_text).strip():
        return {
            'version': corpus.get('version'),
            'query': query_text,
            'results': docs[:top_k],
            'total_docs': len(docs)
        }
    q_lower = str(query_text).casefold()
    q_tokens = set(_tokenize(q_lower))
    scored = []
    for d in docs:
        score = 0.0
        for kw in d.get('keywords', []):
            kw_l = kw.casefold()
            if kw_l in q_lower:
                score += 4.5
            elif any(t in kw_l for t in q_tokens if len(t) >= 2):
                score += 1.5
        doc_text = f"{d.get('title', '')} {d.get('summary', '')} {d.get('detail', '')}"
        d_tokens = set(_tokenize(doc_text))
        overlap = len(q_tokens & d_tokens)
        score += overlap * 0.35
        scored.append((score, d))
    scored.sort(key=lambda x: (-x[0], x[1]['rule_id']))
    selected = [
        {**doc, 'relevance_score': round(score, 3)}
        for score, doc in scored[:top_k]
        if score > 0
    ]
    if not selected:
        selected = [{**d, 'relevance_score': 0.1} for d in docs[:min(2, len(docs))]]
    return {
        'version': corpus.get('version'),
        'query': query_text,
        'results': selected,
        'total_docs': len(docs)
    }

def classify_intent_with_ontology(question):
    ont = load_ontology()
    q = (question or '').casefold()
    if any(k in q for k in ['如果', '假设', 'if线', 'what-if', 'what if', '未开赛', '谁拿mvp', '沙盘', '推演']):
        task_type = 'what_if_simulation'
    elif any(k in q for k in ['排名', 'top 20', 'top20', '榜单', '预测', '归因', '残差', '为什么排', '名次']):
        task_type = 'top20_ranking_attribution'
    elif any(k in q for k in ['只会', '刷弱队', '保枪', 'rws', '天梯', '软脚虾', '水分', '言论', '求证', '真假', '说法']):
        task_type = 'claim_verification'
    else:
        task_type = 'cross_role_comparison'
    routing = ont.get('task_routing_rules', {}).get(task_type, {})
    return {
        'task_type': task_type,
        'required_tools': routing.get('required_tools', ['T1_multi_tier_query']),
        'required_rules': routing.get('required_rules', ['RULE-TOP20-01']),
        'verifier_checks': routing.get('verifier_checks', ['check_sample_maps']),
        'ontology_version': ont.get('version')
    }
