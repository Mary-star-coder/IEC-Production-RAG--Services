
"""
Compare two RAG chunking configurations using the golden dataset.

Measures:
- Hit Rate@5
- Recall@5
- Mean Reciprocal Rank (MRR)
- Answerable-question abstention count
- Unanswerable-question false acceptance count
- Average retrieval latency

Important:
Relevance is evaluated at page level, not exact chunk level.
The preferred dataset format includes relevant_pages for each question.
If relevant_pages is missing, the script falls back to mapping
relevant_chunk_ids through the existing production Qdrant collection.
"""

# ---------------------------------------------------------
# IMPORTS AND PROJECT PATHS
# ---------------------------------------------------------

import json
import sys
import time
from pathlib import Path
from uuid import uuid4

from qdrant_client import models

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Make the project root available for direct script execution.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ingestion.loader import load_document
from app.ingestion.chunker import chunk_documents

from app.ingestion.vector_store import (
    client,
    point_id,
    VECTOR_SIZE,
    COLLECTION_NAME,
)
from app.gemini import embed_texts

from app.evaluation.metrics import (
    hit_rate_at_k,
    recall_at_k,
    reciprocal_rank,
    mean_reciprocal_rank,
)


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

DATASET_PATH = (
    PROJECT_ROOT
    / "app"
    / "evaluation"
    / "golden_dataset.json"
)

SOURCE_FILE = (
    PROJECT_ROOT
    / "docs"
    / "main_notes.pdf"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "app"
    / "evaluation"
    / "chunking_comparison_results.json"
)

TOP_K = 5
SIMILARITY_THRESHOLD = 0.30

# Compare at least two different chunking configurations.
CONFIGURATIONS = [
    {
        "name": "A_800_150",
        "chunk_size": 800,
        "chunk_overlap": 150,
    },
    {
        "name": "B_500_100",
        "chunk_size": 500,
        "chunk_overlap": 100,
    },
]


# ---------------------------------------------------------
# GOLDEN DATASET VALIDATION
# ---------------------------------------------------------

def validate_dataset(dataset: list[dict]) -> None:
    """Validate required fields before starting the experiment."""

    if not isinstance(dataset, list) or not dataset:
        raise ValueError("The golden dataset must be a non-empty list.")

    seen_ids = set()

    for index, item in enumerate(dataset):
        if not isinstance(item, dict):
            raise ValueError(f"Dataset item {index} must be an object.")

        required_fields = {"id", "question", "answerable"}

        missing = required_fields - set(item)

        if missing:
            raise ValueError(
                f"Dataset item {index} is missing fields: {sorted(missing)}"
            )

        if not isinstance(item["question"], str) or not item["question"].strip():
            raise ValueError(
                f"Dataset item {index} has an empty question."
            )

        if not isinstance(item["answerable"], bool):
            raise ValueError(
                f"Dataset item {index} must have a boolean answerable value."
            )

        question_id = item["id"]

        if question_id in seen_ids:
            raise ValueError(
                f"Duplicate question ID in dataset: {question_id}"
            )

        seen_ids.add(question_id)


# ---------------------------------------------------------
# RELEVANCE MAPPING
# ---------------------------------------------------------

def get_relevant_pages(dataset: list[dict]) -> dict:
    """
    Build a mapping from question IDs to manually verified source pages.

    Preferred format:
        {
            "id": "q1",
            "question": "...",
            "answerable": true,
            "relevant_pages": [2, 5]
        }

    Backward-compatible format:
        relevant_chunk_ids are mapped to pages using the existing
        production Qdrant collection.
    """

    relevant_pages = {}

    # Prefer explicit page labels in the golden dataset.
    if all("relevant_pages" in item for item in dataset):
        for item in dataset:
            pages = item["relevant_pages"]

            if not isinstance(pages, list):
                raise ValueError(
                    f"relevant_pages must be a list for {item['id']}."
                )

            relevant_pages[item["id"]] = {
                int(page) for page in pages
            }

        return relevant_pages

    # Backward-compatible mapping from original chunk IDs in Qdrant.
    all_ids = sorted({
        chunk_id
        for item in dataset
        for chunk_id in item.get("relevant_chunk_ids", [])
    })

    if not all_ids:
        raise ValueError(
            "The dataset must contain relevant_pages or relevant_chunk_ids."
        )

    point_ids = [point_id(chunk_id) for chunk_id in all_ids]
    stored = client.retrieve(
        collection_name=COLLECTION_NAME,
        ids=point_ids,
        with_payload=True,
        with_vectors=False,
    )

    metadata_by_id = {
        record.payload["chunk_id"]: record.payload
        for record in stored
        if record.payload and "chunk_id" in record.payload
    }

    missing = set(all_ids) - set(metadata_by_id)

    if missing:
        raise ValueError(
            f"{len(missing)} verified chunk IDs are missing from Qdrant. "
            "Restore the original database or add relevant_pages "
            "to the golden dataset."
        )

    for item in dataset:
        pages = set()

        for chunk_id in item.get("relevant_chunk_ids", []):
            metadata = metadata_by_id[chunk_id]
            pages.add(int(metadata["page"]))

        relevant_pages[item["id"]] = pages

    return relevant_pages


# ---------------------------------------------------------
# TEMPORARY COLLECTION PREPARATION
# ---------------------------------------------------------

def prepare_collection(config: dict, pages: list[dict]) -> tuple[str, int]:
    """Create a fresh temporary Qdrant collection for one configuration."""

    name = f"eval_{config['name'].lower()}_{uuid4().hex[:8]}"

    client.create_collection(
        collection_name=name,
        vectors_config=models.VectorParams(
            size=VECTOR_SIZE,
            distance=models.Distance.COSINE,
        ),
    )

    try:
        chunks = chunk_documents(
            pages,
            chunk_size=config["chunk_size"],
            chunk_overlap=config["chunk_overlap"],
        )

        texts = []
        payloads = []

        for chunk in chunks:
            text = chunk.get("text", "")

            if not isinstance(text, str) or not text.strip():
                continue

            texts.append(text.strip())
            payloads.append({
                "page": int(chunk["page"]),
                "position": int(chunk["position"]),
            })

        if texts:
            vectors = embed_texts(
                texts,
                task_type="RETRIEVAL_DOCUMENT",
            )
            client.upsert(
                collection_name=name,
                points=[
                    models.PointStruct(
                        id=str(uuid4()),
                        vector=vector,
                        payload=payload,
                    )
                    for vector, payload in zip(vectors, payloads)
                ],
                wait=True,
            )

        return name, len(texts)

    except Exception:
        try:
            client.delete_collection(collection_name=name)
        except Exception:
            pass

        raise


# ---------------------------------------------------------
# SINGLE CONFIGURATION EVALUATION
# ---------------------------------------------------------

def evaluate_configuration(
    config: dict,
    dataset: list[dict],
    pages: list[dict],
    relevant_pages: dict,
) -> dict:
    """Evaluate retrieval quality and latency for one configuration."""

    eval_collection_name = None

    try:
        eval_collection_name, chunk_count = prepare_collection(
            config,
            pages,
        )

        metric_rows = []
        question_results = []

        abstained_count = 0
        answerable_abstained = 0
        unanswerable_not_abstained = 0
        total_latency = 0.0

        # Evaluate every question using the temporary collection.
        for item in dataset:
            start_time = time.perf_counter()

            if chunk_count:
                query_vector = embed_texts(
                    [item["question"]],
                    task_type="RETRIEVAL_QUERY",
                )[0]
                results = client.query_points(
                    collection_name=eval_collection_name,
                    query=query_vector,
                    limit=min(TOP_K, chunk_count),
                    with_payload=True,
                    with_vectors=False,
                )

                points = results.points

            else:
                points = []

            latency = time.perf_counter() - start_time
            total_latency += latency

            # Convert retrieved results to page and similarity records.
            matches = []

            for point in points:
                metadata = point.payload or {}
                similarity = max(
                    0.0,
                    min(1.0, float(point.score)),
                )

                matches.append({
                    "page": int(metadata["page"]),
                    "similarity": similarity,
                })

            # Apply the same abstention threshold used by the service.
            abstained = (
                not matches
                or max(
                    match["similarity"] for match in matches
                ) < SIMILARITY_THRESHOLD
            )

            if abstained:
                abstained_count += 1

            if item["answerable"] and abstained:
                answerable_abstained += 1

            if not item["answerable"] and not abstained:
                unanswerable_not_abstained += 1

            # Page-level retrieval metrics are calculated only where
            # manually verified relevance labels are available.
            relevant = relevant_pages.get(item["id"], set())

            retrieved_pages = [
                match["page"] for match in matches
            ]

            if relevant:
                hit = hit_rate_at_k(
                    retrieved_pages,
                    relevant,
                    TOP_K,
                )

                recall = recall_at_k(
                    retrieved_pages,
                    relevant,
                    TOP_K,
                )

                rr = reciprocal_rank(
                    retrieved_pages,
                    relevant,
                )

                metric_rows.append({
                    "hit_rate_at_5": hit,
                    "recall_at_5": recall,
                    "reciprocal_rank": rr,
                })

            # Store retrieved_pages here so MRR calculation can use them.
            question_results.append({
                "question_id": item["id"],
                "answerable": item["answerable"],
                "retrieved_pages": retrieved_pages,
                "relevant_pages": sorted(relevant),
                "abstained": abstained,
                "latency_seconds": round(latency, 4),
            })

        # -------------------------------------------------
        # AGGREGATE METRICS
        # -------------------------------------------------

        if metric_rows:
            verified_pairs = [
                (
                    row["retrieved_pages"],
                    row["relevant_pages"],
                )
                for row in question_results
                if row["relevant_pages"]
            ]

            metrics = {
                "verified_question_count": len(metric_rows),
                "hit_rate_at_5": sum(
                    row["hit_rate_at_5"] for row in metric_rows
                ) / len(metric_rows),
                "recall_at_5": sum(
                    row["recall_at_5"] for row in metric_rows
                ) / len(metric_rows),
                "mrr": mean_reciprocal_rank(verified_pairs),
            }

        else:
            metrics = {
                "verified_question_count": 0,
                "hit_rate_at_5": None,
                "recall_at_5": None,
                "mrr": None,
            }

        average_latency = (
            total_latency / len(dataset)
            if dataset
            else 0.0
        )

        return {
            "configuration": config,
            "chunk_count": chunk_count,
            "retrieval_metrics": metrics,
            "total_questions": len(dataset),
            "abstained_count": abstained_count,
            "answerable_questions_abstained": answerable_abstained,
            "unanswerable_questions_not_abstained": (
                unanswerable_not_abstained
            ),
            "average_retrieval_latency_seconds": round(
                average_latency,
                4,
            ),
            "question_results": question_results,
        }

    finally:
        # Always remove the temporary collection, even if evaluation fails.
        if eval_collection_name is not None:
            try:
                client.delete_collection(
                    collection_name=eval_collection_name
                )
            except Exception:
                print(
                    "Warning: Could not remove temporary collection:",
                    eval_collection_name,
                )


# ---------------------------------------------------------
# COMPLETE EVALUATION RUNNER
# ---------------------------------------------------------

def evaluate() -> dict:
    """Run all configurations and save their comparison results."""

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Golden dataset not found: {DATASET_PATH}"
        )

    if not SOURCE_FILE.exists():
        raise FileNotFoundError(
            f"Source PDF not found: {SOURCE_FILE}"
        )

    # Load and validate the golden questions.
    with DATASET_PATH.open("r", encoding="utf-8") as file:
        dataset = json.load(file)

    validate_dataset(dataset)

    print("Loading source document...")
    pages = load_document(str(SOURCE_FILE))

    print("Source pages:", len(pages))
    print("Golden questions:", len(dataset))

    # Build the manually verified relevance mapping.
    print("\nPreparing relevance labels...")
    relevant_page_mapping = get_relevant_pages(dataset)

    results = []

    for config in CONFIGURATIONS:
        print(f"\nRunning configuration: {config['name']}")

        result = evaluate_configuration(
            config,
            dataset,
            pages,
            relevant_page_mapping,
        )

        results.append(result)

        print("Chunks:", result["chunk_count"])
        print("Retrieval metrics:", result["retrieval_metrics"])
        print(
            "Average retrieval latency:",
            result["average_retrieval_latency_seconds"],
        )
        print(
            "Answerable questions incorrectly rejected:",
            result["answerable_questions_abstained"],
        )
        print(
            "Unanswerable questions not rejected:",
            result["unanswerable_questions_not_abstained"],
        )

    # Create the output directory if it does not already exist.
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = {
        "evaluation_method": (
            "Page-level relevance proxy based on manually verified "
            "source pages. This is not exact chunk-level relevance."
        ),
        "top_k": TOP_K,
        "similarity_threshold": SIMILARITY_THRESHOLD,
        "configurations": results,
    }

    # Save reproducible experiment results.
    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(
            output,
            file,
            indent=4,
            ensure_ascii=False,
        )

    print("\n===== CHUNKING COMPARISON COMPLETE =====")
    print("Results saved to:", OUTPUT_PATH)

    return output


# ---------------------------------------------------------
# SCRIPT ENTRY POINT
# ---------------------------------------------------------

if __name__ == "__main__":
    evaluate()
