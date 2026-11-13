"""Compose the five-source experiment from one normalized snapshot per source."""
import json
from pathlib import Path


def load_multidoc_pages(root: Path):
    pages=[]
    for name in ['nd69','nd42','sherlock']:
        pages.extend(json.loads((root/f'data/multidoc/{name}_pages.json').read_text()))
    for p in json.loads((root/'data/pages.json').read_text()):
        pages.append(dict(document_id='alice',source='https://www.gutenberg.org/ebooks/11',page=p['page'],text=p['text'],metadata={**p['metadata'],'document_type':'fiction','chapter_spans':[dict(start=0,end=len(p['text']),chapter=p['metadata']['chapter'])]}))
    pages.extend(json.loads((root/'data/vietnamese/pages.json').read_text()))
    return pages


def composed_bytes(root: Path):
    return (json.dumps(load_multidoc_pages(root),ensure_ascii=False,indent=2)+'\n').encode()
