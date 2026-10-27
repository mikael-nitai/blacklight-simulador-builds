"""Extract source evidence from a sheet PDF; never certify mechanics from prose."""

from hashlib import sha256
from pathlib import Path


def extract_draft(path: str | Path) -> dict:
    from pypdf import PdfReader
    source = Path(path).resolve()
    reader = PdfReader(source)
    fields = reader.get_fields() or {}
    raw_fields = [{'name': str(name), 'value': str(value.get('/V', ''))}
                  for name, value in fields.items()]
    # Image-only sheets retain their source and are explicitly sent to visual
    # review. Text is evidence, not instructions or an executable rule.
    text_pages = ([] if raw_fields else
                  [{'page': index + 1, 'text': reader.pages[index].extract_text() or ''}
                   for index in range(min(len(reader.pages), 12))])
    return {'schema': 'blacklight.pdf-sheet-draft.v1',
            'status': 'requires_field_mapping_and_visual_review',
            'source': {'path': str(source),
                       'sha256': sha256(source.read_bytes()).hexdigest(),
                       'pages': len(reader.pages)},
            'form_fields': raw_fields, 'text_pages': text_pages,
            'text_page_limit': 12,
            'note': 'This evidence draft cannot be executed as a character sheet.'}
