from __future__ import annotations

import json

from analytics_workbook import build_glossary_documents_from_workbook, rebuild_glossary_json


def main() -> None:
    output_path = rebuild_glossary_json()
    documents = build_glossary_documents_from_workbook()
    print(f"Wrote {len(documents)} analytics documents to {output_path}")
    if documents:
        print(json.dumps(documents[0], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
