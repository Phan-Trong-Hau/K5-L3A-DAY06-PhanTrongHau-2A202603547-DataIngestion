"""Unicode normalization and traceable PDF/text ingestion."""
import re
import unicodedata
import warnings
from pathlib import Path
from .models import DocumentPage


def normalize_text(text: str) -> str:
    text = unicodedata.normalize('NFC', text).replace('\r\n', '\n').replace('\r', '\n')
    return '\n\n'.join(re.sub(r'\s+', ' ', p).strip() for p in re.split(r'\n\s*\n', text) if p.strip())


def load_pdf(path: Path, document_id: str, source: str) -> list[DocumentPage]:
    from pypdf import PdfReader
    pages = []
    for i, page in enumerate(PdfReader(path).pages, 1):
        text = normalize_text(page.extract_text() or '')
        if not text:
            warnings.warn(f'{path}: physical page {i} has no extractable text; OCR required')
        pages.append(DocumentPage(document_id, source, i, text))
    return pages


def load_alice(path: Path) -> list[DocumentPage]:
    """Sequential units >=1500 chars, paragraph boundaries, never cross chapters."""
    raw = path.read_text(encoding='utf-8')
    body = raw.split('*** START OF THE PROJECT GUTENBERG EBOOK', 1)[1].split('*** END OF THE PROJECT GUTENBERG EBOOK', 1)[0]
    chapters = list(re.finditer(r'^CHAPTER ([IVX]+)\.\s*\n([^\n]+)', body, re.M))
    pages = []
    for i, match in enumerate(chapters):
        text = normalize_text(body[match.end():chapters[i+1].start() if i+1 < len(chapters) else len(body)])
        blocks, pending = [], ''
        for paragraph in text.split('\n\n'):
            pending += ('\n\n' if pending else '') + paragraph
            if len(pending) >= 1500:
                blocks.append(pending)
                pending = ''
        if pending:
            if blocks:
                blocks[-1] += '\n\n' + pending
            else:
                blocks = [pending]
        offset = 0
        for block in blocks:
            pages.append(DocumentPage('alice', 'https://www.gutenberg.org/ebooks/11', len(pages)+1, block,
                {'chapter': match[1], 'chapter_title': match[2].strip(), 'chapter_start': offset, 'language': 'en'}))
            offset += len(block) + 2
    if len(pages) < 30 or any(len(p.text) < 1500 for p in pages):
        raise ValueError('Corpus must contain >=30 units of >=1500 normalized characters')
    return pages
