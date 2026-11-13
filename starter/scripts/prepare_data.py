"""Freeze verified evidence and source manifest BEFORE running retrieval."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from starter.src.ingestion import load_alice

ROOT = Path(__file__).resolve().parents[2]
pages = load_alice(ROOT/'data/alice.txt')
# Questions/evidence authored from source, never generated from retrieval output.
items = [
('I', 'What label was on the empty jar Alice found while falling?', 'ORANGE MARMALADE', 'it was labelled “ORANGE MARMALADE”, but to her great disappointment it was empty', False),
('I', 'Why did Alice avoid dropping the jar?', 'She feared killing somebody below.', 'she did not like to drop the jar for fear of killing somebody underneath', False),
('I', 'What did Alice check before tasting the bottle?', 'Whether it was marked poison.', '“and see whether it’s marked ‘_poison_’ or not”', False),
('I', 'How were the words on the small cake written?', 'EAT ME was marked in currants.', 'the words “EAT ME” were beautifully marked in currants.', False),
('III', 'In chapter III, what did Alice distribute as race prizes?', 'Comfits, one per participant.', 'pulled out a box of comfits, (luckily the salt water had not got into it), and handed them round as prizes. There was exactly one a-piece, all round.', True),
('III', 'What prize did the Dodo present to Alice?', 'A thimble.', 'the Dodo solemnly presented the thimble', False),
('IV', 'Where did Alice think the falling Rabbit might have landed?', 'A cucumber-frame or something similar.', 'it had fallen into a cucumber-frame, or something of the sort.', False),
('VI', 'In chapter VI, what explanation did the Duchess give for her cat grinning?', 'It was a Cheshire cat.', '“It’s a Cheshire cat,” said the Duchess, “and that’s why.', True),
('VII', 'What kind of well appears in the Dormouse story?', 'A treacle-well.', 'The Dormouse again took a minute or two to think about it, and then said, “It was a treacle-well.”', False),
('VII', 'What time was it always, according to the Hatter?', 'Six o’clock.', 'It’s always six o’clock now.', False),
('VII', 'Why could the tea party never wash the dishes between rounds?', 'It was always tea-time.', '“it’s always tea-time, and we’ve no time to wash the things between whiles.”', False),
('VIII', 'Which living creatures served as balls and mallets in croquet?', 'Hedgehogs and flamingoes.', 'the balls were live hedgehogs, the mallets live flamingoes', False),
('IX', 'In chapter IX, what were the four branches of Arithmetic?', 'Ambition, Distraction, Uglification, Derision.', 'the different branches of Arithmetic—Ambition, Distraction, Uglification, and Derision.', True),
('IX', 'Who taught Drawling and how often did the teacher visit?', 'An old conger-eel, once a week.', 'the Drawling-master was an old conger-eel, that used to come once a week', False),
('X', 'In the dance song, what creature was treading on the whiting’s tail?', 'A porpoise.', '“There’s a porpoise close behind us, and he’s treading on my tail.', False),
('XI', 'In chapter XI, what did the Duchess’s cook carry into court?', 'A pepper-box.', 'The next witness was the Duchess’s cook. She carried the pepper-box in her hand', True),
('XI', 'What did the cook claim tarts were mostly made of?', 'Pepper.', '“What are tarts made of?”\n\n“Pepper, mostly,” said the cook.', False),
('XII', 'Under Rule Forty-two, who had to leave the court?', 'All persons more than a mile high.', 'Rule Forty-two. _All persons more than a mile high to leave the court_.', False),
('XII', 'Did the Queen want the verdict or the sentence first?', 'Sentence first, verdict afterwards.', '“No, no!” said the Queen. “Sentence first—verdict afterwards.”', False),
('XI', 'Who was accused in the rhyme of stealing the Queen’s tarts?', 'The Knave of Hearts.', 'The Knave of Hearts, he stole those tarts', False),
]
questions = []
for i, (chapter, question, answer, evidence, filtered) in enumerate(items, 1):
    matching = [p for p in pages if p.metadata['chapter'] == chapter and evidence in p.text]
    if not matching:
        raise ValueError(f'Evidence absent: {i}: {evidence}')
    p = matching[0]
    questions.append(dict(id=f'q{i:02}', split='dev' if i<=15 else 'test', question=question,
        expected_answer=answer, gold_source_id=p.document_id, gold_page=p.page,
        evidence_quote=evidence, filter={'chapter': chapter} if filtered else {},
        alternatives=[{'source_id': x.document_id, 'page': x.page, 'evidence_quote': evidence} for x in matching[1:]]))
manifest = dict(source_id='alice', title="Alice’s Adventures in Wonderland", author='Lewis Carroll (1832–1898)',
    source_path_or_url='https://www.gutenberg.org/ebooks/11.txt.utf-8', local_path='data/alice.txt',
    license_or_permission='Public domain literary text; full Project Gutenberg license retained in original download. Author died 1898; source declares public domain in USA.',
    accessed_at=datetime.now(timezone.utc).isoformat(), source_version='Gutenberg last updated June 26, 2025; Millennium Fulcrum Edition 3.0',
    sha256=hashlib.sha256((ROOT/'data/alice.txt').read_bytes()).hexdigest(),
    physical_pages=None, unit_rule='Sequential normalized paragraph groups >=1500 characters within each chapter; final short remainder merged backwards. Exclude cover, contents, illustrations and license.',
    content_units=len(pages), pages=[dict(page=p.page, characters=len(p.text), **p.metadata) for p in pages])
(ROOT/'data/manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
(ROOT/'data/pages.json').write_text(json.dumps([dict(page=p.page,text=p.text,metadata=p.metadata) for p in pages],ensure_ascii=False,indent=2)+'\n')
(ROOT/'benchmark/questions.json').write_text(json.dumps(questions,ensure_ascii=False,indent=2)+'\n')
print(f'Validated {len(pages)} content units, {len(questions)} evidence quotes')
