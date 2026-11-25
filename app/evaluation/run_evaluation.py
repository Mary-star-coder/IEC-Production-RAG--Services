
"""
Compare two RAG chunking configurations using the golden evaluation dataset.

The experiment measures:
- Retrieval quality using Hit Rate@5, Recall@5, and MRR.
- Abstention behavior for answerable and unanswerable questions.
- Average retrieval latency.

Note:
Relevance is approximated at the page level by mapping manually verified
original chunk IDs to their source pages. This is not exact chunk-level
relevance evaluation.
"""

import json
import sys
import time
from pathlib import Path

# Resolve the project root and add it to Python's import path.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# Import document loading and chunking utilities.
from app.ingestion.loader import load_document
from app.ingestion.chunker import chunk_documents

# Import ChromaDB client, collection, and embedding function.
from app.ingestion.vector_store import (
    client,
    collection,
    embedding_function,
)

# Import retrieval evaluation metrics.
from app.evaluation.metrics import (
    hit_rate_at_k,
    recall_at_k,
    reciprocal_rank,
    mean_reciprocal_rank,
)

# Define input and output file paths.
DATASET_PATH = PROJECT_ROOT / "app" / "evaluation" / "golden_dataset.json"
SOURCE_FILE = PROJECT_ROOT / "docs" / "main_notes.pdf"
OUTPUT_PATH = (
    PROJECT_ROOT
    / "app"
    / "evaluation"
    / "chunking_comparison_results.json"
)

# Shared evaluation settings.
TOP_K = 5
SIMILARITY_THRESHOLD = 0.30

# Compare two chunk sizes and overlap settings.
CONFIGURATIONS = [
    {"name": "A_800_150", "chunk_size": 800, "chunk_overlap": 150},
    {"name": "B_500_100", "chunk_size": 500, "chunk_overlap": 100},
]


def get_relevant_pages(dataset):
    """Map existing verified chunk IDs to their original source pages."""

    # Collect all manually verified chunk IDs from the golden dataset.
    all_ids = sorted({
        chunk_id
        for item in dataset
        for chunk_id in item.get("relevant_chunk_ids", [])
    })

    if not all_ids:
        raise ValueError("No manually verified chunk IDs found.")

    # Retrieve metadata for the verified chunks from the existing collection.
    stored = collection.get(
        ids=all_ids,
        include=["metadatas"],
    )

    # Create a mapping between chunk IDs and their metadata.
    metadata_by_id = dict(zip(stored["ids"], stored["metadatas"]))

    # Stop evaluation if any verified chunk IDs are missing.
    missing = set(all_ids) - set(metadata_by_id)
    if missing:
        raise ValueError(
            f"{len(missing)} verified chunk IDs are missing "
            "from the existing ChromaDB. Check the database."
        )

    # Map each golden question to the pages containing its relevant chunks.
    relevant_pages = {}

    for item in dataset:
        pages = {
            metadata_by_id[chunk_id]["page"]
            for chunk_id in item.get("relevant_chunk_ids", [])
        }
        relevant_pages[item["id"]] = pages

    return relevant_pages


def prepare_collection(config, pages):
    """Create an isolated temporary collection for one configuration."""

    # Generate a unique collection name for this experiment configuration.
    name = f"eval_{config['name'].lower()}"

    # Delete an older temporary collection with the same name, if present.
    try:
        client.delete_collection(name)
    except Exception:
        pass

    # Create a fresh ChromaDB collection using cosine distance.
    eval_collection = client.create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
        embedding_function=embedding_function,
    )

    # Split the source pages into chunks using the current configuration.
    chunks = chunk_documents(
        pages,
        chunk_size=config["chunk_size"],
        chunk_overlap=config["chunk_overlap"],
    )

    # Prepare chunk IDs, text, and metadata for ChromaDB.
    ids = []
    documents = []
    metadatas = []

    for index, chunk in enumerate(chunks):
        ids.append(f"{name}_{index}")
        documents.append(chunk["text"])
        metadatas.append({
            "page": chunk["page"],
            "position": chunk["position"],
        })

    # Add all generated chunks to the temporary collection.
    if ids:
        eval_collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

    return eval_collection, len(chunks)


def evaluate_configuration(config, dataset, pages, relevant_pages):
    """Evaluate retrieval quality and latency for one chunking configuration."""

    # Build a temporary vector collection for this configuration.
    eval_collection, chunk_count = prepare_collection(config, pages)

    # Initialize metric and abstention counters.
    metric_rows = []
    abstained_count = 0
    answerable_abstained = 0
    unanswerable_not_abstained = 0
    total_latency = 0.0
    question_results = []

    # Evaluate every question in the golden dataset.
    for item in dataset:
        start_time = time.perf_counter()

        # Retrieve the top-k most relevant chunks for the question.
        results = eval_collection.query(
            query_texts=[item["question"]],
            n_results=min(TOP_K, chunk_count),
            include=["documents", "metadatas", "distances"],
        )

        # Measure retrieval time for this question.
        latency = time.perf_counter() - start_time
        total_latency += latency

        # Extract retrieved chunk metadata and cosine distances.
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        # Convert cosine distances into bounded similarity scores.
        matches = [
            {
                "page": metadata["page"],
                "similarity": max(0.0, min(1.0, 1.0 - distance)),
            }
            for metadata, distance in zip(metadatas, distances)
        ]

        # Abstain if no chunks were retrieved or all scores are below threshold.
        abstained = (
            not matches
            or max(match["similarity"] for match in matches)
            < SIMILARITY_THRESHOLD
        )

        if abstained:
            abstained_count += 1

        # Track answerable questions that were incorrectly rejected.
        if item["answerable"] and abstained:
            answerable_abstained += 1

        # Track unanswerable questions that were not rejected.
        if not item["answerable"] and not abstained:
            unanswerable_not_abstained += 1

        # Calculate retrieval metrics only for questions with verified relevance.
        relevant = relevant_pages.get(item["id"], set())

        if relevant:
            retrieved_pages = [match["page"] for match in matches]

            hit = hit_rate_at_k(
                retrieved_pages, list(relevant), TOP_K
            )
            recall = recall_at_k(
                retrieved_pages, list(relevant), TOP_K
            )
            rr = reciprocal_rank(
                retrieved_pages, list(relevant)
            )

            metric_rows.append({
                "hit_rate_at_5": hit,
                "recall_at_5": recall,
                "reciprocal_rank": rr,
            })

        # Save the retrieval outcome and latency for this question.
        question_results.append({
            "question_id": item["id"],
            "retrieved_pages": [m["page"] for m in matches],
            "abstained": abstained,
            "latency_seconds": round(latency, 4),
        })

    # Calculate average retrieval metrics across verified questions.
    if metric_rows:
        verified_pairs = [
            (
                [
                    page
                    for page in row["retrieved_pages"]
                ],
                list(relevant_pages[row["question_id"]]),
            )
            for row in question_results
            if row["question_id"] in relevant_pages
            and relevant_pages[row["question_id"]]
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
        # Return null metrics if no questions have verified relevance.
        metrics = {
            "verified_question_count": 0,
            "hit_rate_at_5": None,
            "recall_at_5": None,
            "mrr": None,
        }

    # Collect all experiment results in one dictionary.
    result = {
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
            total_latency / len(dataset), 4
        ),
        "question_results": question_results,
    }

    # Remove the temporary collection after the experiment finishes.
    try:
        client.delete_collection(eval_collection.name)
    except Exception:
        pass

    return result


def evaluate():
    """Run the chunking comparison and save the experiment results."""

    # Load the golden evaluation questions.
    with DATASET_PATH.open("r", encoding="utf-8") as file:
        dataset = json.load(file)

    # Confirm that the source PDF is available.
    if not SOURCE_FILE.exists():
        raise FileNotFoundError(
            f"Source PDF not found: {SOURCE_FILE}"
        )

    # Extract text and page information from the source document.
    print("Loading source document...")
    pages = load_document(str(SOURCE_FILE))

    print("Source pages:", len(pages))
    print("Golden questions:", len(dataset))

    # Map verified original chunks to their source pages.
    print("\nMapping verified chunk IDs to source pages...")
    relevant_pages = get_relevant_pages(dataset)

    results = []

    # Run the evaluation separately for each chunking configuration.
    for config in CONFIGURATIONS:
        print(f"\nRunning configuration: {config['name']}")

        result = evaluate_configuration(
            config,
            dataset,
            pages,
            relevant_pages,
        )

        results.append(result)

        # Print the key metrics for the current configuration.
        print("Chunks:", result["chunk_count"])
        print("Metrics:", result["retrieval_metrics"])
        print("Average latency:", result["average_retrieval_latency_seconds"])

    # Document the evaluation method and experiment settings.
    output = {
        "evaluation_method": (
            "Page-level relevance proxy based on manually verified "
            "original chunk IDs. This is not exact chunk-level relevance."
        ),
        "top_k": TOP_K,
        "similarity_threshold": SIMILARITY_THRESHOLD,
        "configurations": results,
    }

    # Save the comparison results as formatted JSON.
    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(output, file, indent=4)

    print("\n===== CHUNKING COMPARISON COMPLETE =====")
    print("Results saved to:", OUTPUT_PATH)


# Run the evaluation when this file is executed directly.
if __name__ == "__main__":
    evaluate()
