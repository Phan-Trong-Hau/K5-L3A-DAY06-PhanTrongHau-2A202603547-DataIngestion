"""Author and verify new question holdout before running strategy D."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from starter.src.ingestion import load_alice
ROOT=Path(__file__).resolve().parents[2]
pages=load_alice(ROOT/'data/alice.txt')
items=[
('II','In chapter II, which two objects did the White Rabbit carry when he returned?','White kid gloves and a large fan.','with a pair of white kid gloves in one hand and a large fan in the other',True),
('VI','Which part of the Cheshire Cat remained after the rest had disappeared?','The grin.','ending with the grin, which remained some time after the rest of it had gone.',False),
('VII','How far off was the Hatter’s watch?','Two days wrong.','“Two days wrong!” sighed the Hatter.',False),
('VII','What kind of butter did the March Hare claim he had used?','The best butter.','“It was the _best_ butter,” the March Hare meekly replied.',False),
('IX','In chapter IX, why was the schoolmaster called Tortoise?','Because he taught them.','“We called him Tortoise because he taught us,” said the Mock Turtle',True),
('IX','Why did the Gryphon say the classes were called lessons?','Because they lessen from day to day.','“That’s the reason they’re called lessons,” the Gryphon remarked: “because they lessen from day to day.”',False),
('VII','What were the names of the three sisters in the Dormouse story?','Elsie, Lacie, and Tillie.','their names were Elsie, Lacie, and Tillie',False),
('XI','In chapter XI, why did the jurors write their own names?','For fear of forgetting them before the trial ended.','“They’re putting down their names,” the Gryphon whispered in reply, “for fear they should forget them before the end of the trial.”',True),
('XII','What part of Alice’s clothing knocked over the jury-box?','The edge of her skirt.','she tipped over the jury-box with the edge of her skirt',False),
('XII','Who told Alice to wake up at the end?','Her sister.','“Wake up, Alice dear!” said her sister;',False),
]
rows=[]
for i,(chapter,question,answer,evidence,filtered) in enumerate(items,21):
 matches=[p for p in pages if p.metadata['chapter']==chapter and evidence in p.text]
 if not matches:raise ValueError(f'Missing evidence {i}')
 p=matches[0]
 rows.append(dict(id=f'q{i}',split='holdout',question=question,expected_answer=answer,gold_source_id='alice',gold_page=p.page,evidence_quote=evidence,filter={'chapter':chapter} if filtered else {},alternatives=[]))
(ROOT/'benchmark/extension_holdout.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
print(f'Verified {len(rows)} new questions before extension retrieval')
