"""
End-to-end validation of the Hybrid Search System
"""

import time
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.search import HybridSearch
from src.models import Document


def create_test_documents():
    """Create test documents for validation"""
    documents = [
        Document(
            id="1",
            title="Machine Learning Basics",
            content="Machine learning is a method of data analysis that automates analytical model building. "
                   "It is a branch of artificial intelligence based on the idea that systems can learn from data, "
                   "identify patterns and make decisions with minimal human intervention."
        ),
        Document(
            id="2",
            title="Deep Learning and Neural Networks",
            content="Deep learning is a type of machine learning that trains computers to do what comes naturally "
                   "to humans: learn by example. Deep learning is a key technology behind driverless cars, "
                   "enabling them to recognize a stop sign or to distinguish a pedestrian from a lamppost."
        ),
        Document(
            id="3",
            title="Natural Language Processing",
            content="Natural language processing (NLP) refers to the branch of computer science—and more specifically, "
                   "the branch of artificial intelligence or AI—concerned with giving computers the ability to "
                   "understand text and spoken words in much the same way human beings can."
        ),
        Document(
            id="4",
            title="Computer Vision Technology",
            content="Computer vision is a field of artificial intelligence that trains computers to interpret "
                   "and understand the visual world. Using digital images from cameras and videos and deep learning "
                   "models, machines can accurately identify and classify objects—and then react to what they 'see'."
        ),
        Document(
            id="5",
            title="Supervised vs Unsupervised Learning",
            content="Supervised learning and unsupervised learning are two main types of machine learning. "
                   "In supervised learning, the algorithm learns from labeled training data. In unsupervised learning, "
                   "the algorithm discovers patterns in unlabeled data without explicit guidance."
        ),
        Document(
            id="6",
            title="Neural Network Architecture",
            content="Neural networks are computing systems inspired by the biological neural networks that constitute "
                   "animal brains. An ANN is based on a collection of connected units or nodes called artificial neurons, "
                   "which loosely model the neurons in a biological brain."
        ),
        Document(
            id="7",
            title="AI Applications in Healthcare",
            content="Artificial intelligence in healthcare is an overarching term used to describe the use of "
                   "machine-learning algorithms and software, or artificial intelligence (AI), to emulate human "
                   "cognition in the analysis, presentation, and understanding of complex medical and healthcare data."
        ),
        Document(
            id="8",
            title="Transformers and Attention Mechanisms",
            content="The Transformer is a deep learning model introduced in 2017, used primarily in the field of "
                   "natural language processing (NLP). Unlike recurrent neural networks (RNNs), Transformers do not "
                   "require sequential processing of data and can process entire sequences in parallel."
        ),
    ]

    return documents


def run_validation():
    """Run end-to-end validation"""
    print("=" * 80)
    print("Hybrid Search System - End-to-End Validation")
    print("=" * 80)
    print()

    all_passed = True

    # Test 1: Initialization
    print("Test 1: Initializing search engine...")
    try:
        search_engine = HybridSearch()
        print("✓ PASS: Search engine initialized")
    except Exception as e:
        print(f"✗ FAIL: {e}")
        all_passed = False
    print()

    # Test 2: Document Indexing
    print("Test 2: Creating and indexing documents...")
    try:
        documents = create_test_documents()
        print(f"  Created {len(documents)} documents")

        start_time = time.time()
        search_engine.index_documents(documents)
        index_time = time.time() - start_time

        print(f"✓ PASS: Indexed {len(documents)} documents in {index_time:.2f}s")
    except Exception as e:
        print(f"✗ FAIL: {e}")
        all_passed = False
    print()

    # Test 3: BM25 Search
    print("Test 3: BM25 search...")
    try:
        query = "artificial intelligence machine learning"
        results = search_engine.search_bm25_only(query, k=5)

        if len(results) > 0:
            print(f"  Query: '{query}'")
            print(f"  Found {len(results)} results")
            print(f"  Top result: {results[0].document.title}")
            print(f"✓ PASS: BM25 search working")
        else:
            print("✗ FAIL: No BM25 results found")
            all_passed = False
    except Exception as e:
        print(f"✗ FAIL: {e}")
        all_passed = False
    print()

    # Test 4: Semantic Search
    print("Test 4: Semantic search...")
    try:
        query = "AI and neural networks"
        results = search_engine.search_semantic_only(query, k=5)

        if len(results) > 0:
            print(f"  Query: '{query}'")
            print(f"  Found {len(results)} results")
            print(f"  Top result: {results[0].document.title}")
            print(f"✓ PASS: Semantic search working")
        else:
            print("✗ FAIL: No semantic results found")
            all_passed = False
    except Exception as e:
        print(f"✗ FAIL: {e}")
        all_passed = False
    print()

    # Test 5: Hybrid Search
    print("Test 5: Hybrid search...")
    try:
        query = "deep learning computer vision"
        results = search_engine.search(query, k=5)

        if len(results) > 0:
            print(f"  Query: '{query}'")
            print(f"  Found {len(results)} results")
            print(f"  Top result: {results[0].document.title}")
            print(f"  Combined score: {results[0].score:.3f}")
            print(f"  BM25 score: {results[0].bm25_score:.3f}")
            print(f"  Semantic score: {results[0].semantic_score:.3f}")
            print(f"✓ PASS: Hybrid search working")
        else:
            print("✗ FAIL: No hybrid results found")
            all_passed = False
    except Exception as e:
        print(f"✗ FAIL: {e}")
        all_passed = False
    print()

    # Test 6: Query Expansion
    print("Test 6: Query expansion...")
    try:
        from src.search.expansion import QueryExpander
        from src.search.preprocessing import QueryPreprocessor

        preprocessor = QueryPreprocessor(search_engine.config)
        expander = QueryExpander(
            search_engine.config,
            preprocessor,
            search_engine.semantic_searcher.embedding_generator
        )

        from src.models import Query
        query_obj = Query(text="ML algorithms")
        expanded = expander.expand(query_obj)

        if expanded.expanded_terms:
            print(f"  Original: '{query_obj.text}'")
            print(f"  Expanded terms: {expanded.expanded_terms[:5]}")
            print(f"✓ PASS: Query expansion working")
        else:
            print("⚠ WARNING: No expanded terms (might be normal for short query)")
    except Exception as e:
        print(f"✗ FAIL: {e}")
        all_passed = False
    print()

    # Test 7: Score Fusion
    print("Test 7: Score fusion...")
    try:
        # Run all three methods
        query = "neural network architecture"
        bm25_results = search_engine.search_bm25_only(query, k=5)
        semantic_results = search_engine.search_semantic_only(query, k=5)
        hybrid_results = search_engine.search(query, k=5)

        if len(hybrid_results) > 0:
            # Check if hybrid combines both
            has_both = any(
                r.bm25_score > 0 and r.semantic_score > 0
                for r in hybrid_results
            )

            if has_both:
                print(f"  Query: '{query}'")
                print(f"  Hybrid results combine BM25 and semantic scores")
                print(f"✓ PASS: Score fusion working")
            else:
                print("⚠ WARNING: Fusion may not be combining scores properly")
        else:
            print("✗ FAIL: No hybrid results")
            all_passed = False
    except Exception as e:
        print(f"✗ FAIL: {e}")
        all_passed = False
    print()

    # Test 8: Performance
    print("Test 8: Performance benchmark...")
    try:
        queries = [
            "machine learning",
            "neural networks",
            "natural language processing",
            "computer vision",
            "deep learning"
        ]

        times = []
        for query in queries:
            start = time.time()
            results = search_engine.search(query, k=5)
            elapsed = time.time() - start
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        max_time = max(times)

        print(f"  Average query time: {avg_time*1000:.2f}ms")
        print(f"  Max query time: {max_time*1000:.2f}ms")

        if avg_time < 1.0:  # Less than 1 second
            print(f"✓ PASS: Performance acceptable")
        else:
            print(f"⚠ WARNING: Performance could be improved")
    except Exception as e:
        print(f"✗ FAIL: {e}")
        all_passed = False
    print()

    # Test 9: Save/Load Index
    print("Test 9: Save and load index...")
    try:
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            # Save
            index_path = os.path.join(tmpdir, "test_index")
            search_engine.save_index(index_path)

            # Create new engine and load
            new_engine = HybridSearch()
            new_engine.load_index(index_path)

            # Test search
            results = new_engine.search("machine learning", k=3)

            if len(results) > 0:
                print(f"✓ PASS: Index save/load working")
            else:
                print("✗ FAIL: Loaded index not working")
                all_passed = False
    except Exception as e:
        print(f"✗ FAIL: {e}")
        all_passed = False
    print()

    # Test 10: Statistics
    print("Test 10: Statistics...")
    try:
        stats = search_engine.get_stats()

        print(f"  Indexed: {stats['is_indexed']}")
        print(f"  Document count: {stats['document_count']}")
        print(f"  Embedding dim: {stats['embedding_dim']}")
        print(f"  Fusion strategy: {stats['config']['fusion_strategy']}")

        if stats['document_count'] == len(documents):
            print(f"✓ PASS: Statistics correct")
        else:
            print(f"✗ FAIL: Document count mismatch")
            all_passed = False
    except Exception as e:
        print(f"✗ FAIL: {e}")
        all_passed = False
    print()

    # Summary
    print("=" * 80)
    if all_passed:
        print("✓ ALL TESTS PASSED")
        print("=" * 80)
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(run_validation())
