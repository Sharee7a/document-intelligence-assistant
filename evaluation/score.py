import argparse
import json
from pathlib import Path
from app.retrieval import retrieve


def evaluate(dataset, top_k=5):
    examples = [json.loads(line) for line in Path(dataset).read_text(encoding="utf-8").splitlines() if line.strip()]
    if not examples:
        raise ValueError("Evaluation JSONL is empty")
    hits = []
    reciprocal_ranks = []
    for row in examples:
        expected_pages = {int(page) for page in row["expected_pages"]}
        expected_doc = row.get("expected_document_id")
        expected_name = row.get("expected_filename")
        results = retrieve(row["question"], [expected_doc] if expected_doc else None, top_k)
        rank = next((i for i, item in enumerate(results, 1)
                     if item["page_number"] in expected_pages
                     and (not expected_name or item["filename"] == expected_name)), None)
        hits.append(rank is not None)
        reciprocal_ranks.append(1 / rank if rank else 0)
    report = {"examples": len(examples), "top_k": top_k,
              "page_recall_at_k": sum(hits) / len(hits),
              "mean_reciprocal_rank": sum(reciprocal_ranks) / len(reciprocal_ranks)}
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate document page retrieval from JSONL labels")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    evaluate(args.dataset, args.top_k)