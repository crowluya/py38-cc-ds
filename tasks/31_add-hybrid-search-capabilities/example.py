"""
Example usage of the Hybrid Search System
"""

from src.search import HybridSearch
from src.models import Document


def create_sample_documents():
    """Create sample documents for testing"""
    documents = [
        Document(
            id="1",
            title="Introduction to Machine Learning",
            content="Machine learning is a subset of artificial intelligence that focuses on algorithms "
                   "that can learn from data and make predictions or decisions."
        ),
        Document(
            id="2",
            title="Deep Learning with Neural Networks",
            content="Deep learning is a type of machine learning that uses neural networks with multiple "
                   "layers to model complex patterns in data. It has revolutionized computer vision and NLP."
        ),
        Document(
            id="3",
            title="Natural Language Processing",
            content="Natural language processing (NLP) is a branch of artificial intelligence that helps "
                   "computers understand, interpret and manipulate human language."
        ),
        Document(
            id="4",
            title="Computer Vision Applications",
            content="Computer vision enables machines to interpret and make decisions based on visual data. "
                   "Applications include image recognition, object detection, and autonomous vehicles."
        ),
        Document(
            id="5",
            title="Reinforcement Learning",
            content="Reinforcement learning is an area of machine learning concerned with how software agents "
                   "ought to take actions in an environment to maximize some notion of cumulative reward."
        ),
        Document(
            id="6",
            title="Supervised Learning Algorithms",
            content="Supervised learning is a type of machine learning where the model is trained on "
                   "labeled data. Common algorithms include linear regression, decision trees, and SVMs."
        ),
        Document(
            id="7",
            title="Unsupervised Learning Techniques",
            content="Unsupervised learning deals with finding hidden patterns in data without labeled examples. "
                   "Clustering and dimensionality reduction are common techniques."
        ),
        Document(
            id="8",
            title="Transformers in NLP",
            content="Transformer models have become the dominant architecture in NLP. They use self-attention "
                   "mechanisms to process sequential data more effectively than RNNs."
        ),
    ]

    return documents


def main():
    """Main example function"""
    print("=" * 80)
    print("Hybrid Search System - Example Usage")
    print("=" * 80)
    print()

    # Initialize search engine
    print("1. Initializing search engine...")
    search_engine = HybridSearch()

    # Create sample documents
    print("2. Creating sample documents...")
    documents = create_sample_documents()
    print(f"   Created {len(documents)} documents")

    # Index documents
    print("3. Indexing documents...")
    search_engine.index_documents(documents)
    print("   Indexing complete")
    print()

    # Example searches
    queries = [
        "machine learning algorithms",
        "neural networks and deep learning",
        "computer vision applications",
        "natural language understanding",
        "AI and data science"
    ]

    print("4. Running searches...")
    print("-" * 80)

    for i, query_text in enumerate(queries, 1):
        print(f"\nQuery {i}: '{query_text}'")
        print("-" * 40)

        # Hybrid search
        results = search_engine.search(query_text, k=3)

        print(f"Found {len(results)} results:")
        for j, result in enumerate(results, 1):
            print(f"\n  {j}. {result.document.title}")
            print(f"     Score: {result.score:.3f} "
                  f"(BM25: {result.bm25_score:.3f}, "
                  f"Semantic: {result.semantic_score:.3f})")
            print(f"     Content: {result.document.content[:100]}...")

    print()
    print("-" * 80)

    # Compare search methods
    print("\n5. Comparing search methods...")
    print("-" * 80)

    query = "artificial intelligence"
    print(f"\nQuery: '{query}'\n")

    # BM25 only
    print("BM25 Search:")
    bm25_results = search_engine.search_bm25_only(query, k=3)
    for j, result in enumerate(bm25_results, 1):
        print(f"  {j}. {result.document.title} (Score: {result.score:.3f})")

    print()

    # Semantic only
    print("Semantic Search:")
    semantic_results = search_engine.search_semantic_only(query, k=3)
    for j, result in enumerate(semantic_results, 1):
        print(f"  {j}. {result.document.title} (Score: {result.score:.3f})")

    print()

    # Hybrid search
    print("Hybrid Search:")
    hybrid_results = search_engine.search(query, k=3)
    for j, result in enumerate(hybrid_results, 1):
        print(f"  {j}. {result.document.title} (Score: {result.score:.3f})")

    print()
    print("-" * 80)

    # Show statistics
    print("\n6. Search Engine Statistics:")
    print("-" * 80)
    stats = search_engine.get_stats()
    for key, value in stats.items():
        if isinstance(value, dict):
            print(f"{key}:")
            for k, v in value.items():
                print(f"  {k}: {v}")
        else:
            print(f"{key}: {value}")

    print()
    print("=" * 80)
    print("Example complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
