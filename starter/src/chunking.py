"""Deterministic chunks retaining normalized character offsets."""
import hashlib
import re
from .models import Chunk, DocumentPage


def make_chunk(page: DocumentPage, start: int, end: int) -> Chunk:
    text = page.text[start:end]
    key = f'{page.document_id}:{page.page}:{start}:{end}:{text}'
    return Chunk(hashlib.sha256(key.encode()).hexdigest(), page.document_id, page.source, page.page,
                 text, {**page.metadata, 'start': start, 'end': end})


def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError('Require size > 0 and 0 <= overlap < size')
    chunks = []
    for start in range(0, len(page.text), size-overlap):
        end = min(start+size, len(page.text))
        chunks.append(make_chunk(page, start, end))
        if end == len(page.text):
            break
    return chunks


def by_paragraph(page: DocumentPage, max_size: int) -> list[Chunk]:
    if max_size <= 0:
        raise ValueError('max_size must be positive')
    spans = []
    for paragraph in re.finditer(r'\S[\s\S]*?(?=\n\n|$)', page.text):
        start, end = paragraph.span()
        while end-start > max_size:
            cut = page.text.rfind(' ', start, start+max_size+1)
            cut = cut if cut > start else start+max_size
            spans.append((start, cut))
            start = cut + (page.text[cut:cut+1] == ' ')
        if start < end:
            spans.append((start, end))
    merged = []
    for start, end in spans:
        if merged and end-merged[-1][0] <= max_size:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    return [make_chunk(page, a, b) for a, b in merged]
