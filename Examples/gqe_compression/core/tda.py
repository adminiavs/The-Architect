#!/usr/bin/env python3
"""
Topological Data Analysis (TDA) for Universal Embedding

CRITICAL FIX 1: Do NOT hard-code human grammar (subject/verb/object).
The E8 Lattice is not a dictionary; it is a Topology of Relationships.

The Architect's Method: Use TDA to let geometry discover structure.

Key principle: Treat data as a stream of tokens and let topology determine
the embedding. This makes the system UNIVERSAL - works on text, DNA, code,
binary, or any sequential data without retraining.

Embedding dimensions:
- Dim 0: Eigenvector centrality (importance in network)
- Dim 1: Clustering coefficient (local connectivity)  
- Dim 2: Betweenness (bridge between communities)
- Dim 3-5: First 3 eigenvectors of graph Laplacian (spectral coordinates)
- Dim 6: Persistence (topological feature lifetime)
- Dim 7: φ-weighted position in token stream
- Phase: Angular position in persistent homology cycle

Author: The Architect
License: Public Domain
"""

import numpy as np
from typing import List, Tuple, Dict, Any, Union, Optional
from collections import Counter, defaultdict
import networkx as nx
from scipy.sparse.linalg import eigsh
from scipy.sparse import csr_matrix

try:
    from .phi_adic import PHI, PHI_INV
    from .e8_lattice import Spinor
except ImportError:
    from phi_adic import PHI, PHI_INV
    from e8_lattice import Spinor

# Precision
EPSILON = 1e-10


class Token:
    """
    A token in the data stream.
    
    Universal: Can represent a character, word, byte, nucleotide, etc.
    """
    def __init__(self, value: Any, position: int = 0):
        self.value = value
        self.position = position
    
    def __hash__(self):
        return hash(self.value)
    
    def __eq__(self, other):
        if isinstance(other, Token):
            return self.value == other.value
        return self.value == other
    
    def __repr__(self):
        return f"Token({self.value!r})"


def tokenize(data: Union[str, bytes, List], mode: str = 'auto') -> List[Token]:
    """
    Universal tokenizer that works on any sequential data.
    
    Args:
        data: Input data (string, bytes, or list)
        mode: Tokenization mode:
            - 'auto': Detect best mode
            - 'char': Character-level (for text)
            - 'word': Word-level (for text)
            - 'byte': Byte-level (for binary)
            - 'element': Element-level (for lists)
    
    Returns:
        List of Token objects
    """
    if mode == 'auto':
        if isinstance(data, bytes):
            mode = 'byte'
        elif isinstance(data, str):
            # Use word mode for longer texts, char for short
            mode = 'word' if len(data) > 100 else 'char'
        else:
            mode = 'element'
    
    tokens = []
    
    if mode == 'byte':
        for i, b in enumerate(data):
            tokens.append(Token(b, position=i))
    
    elif mode == 'char':
        for i, c in enumerate(data):
            tokens.append(Token(c, position=i))
    
    elif mode == 'word':
        # Simple word tokenization
        words = data.split()
        for i, w in enumerate(words):
            tokens.append(Token(w.lower(), position=i))
    
    elif mode == 'element':
        for i, elem in enumerate(data):
            tokens.append(Token(elem, position=i))
    
    return tokens


def build_cooccurrence_graph(
    tokens: List[Token], 
    window_size: int = 5,
    min_count: int = 1
) -> nx.Graph:
    """
    Build a co-occurrence graph from tokens.
    
    Nodes: Unique tokens
    Edges: Co-occurrence within sliding window
    Weights: PMI (Pointwise Mutual Information)
    
    Args:
        tokens: List of tokens
        window_size: Size of co-occurrence window
        min_count: Minimum token count to include
    
    Returns:
        NetworkX graph with weighted edges
    """
    G = nx.Graph()
    
    # Count token frequencies
    token_counts = Counter(t.value for t in tokens)
    total_tokens = len(tokens)
    
    # Filter by minimum count
    valid_tokens = {t for t, c in token_counts.items() if c >= min_count}
    
    # Count co-occurrences
    cooccur = defaultdict(int)
    for i in range(len(tokens)):
        if tokens[i].value not in valid_tokens:
            continue
        for j in range(i + 1, min(i + window_size + 1, len(tokens))):
            if tokens[j].value not in valid_tokens:
                continue
            # Order tokens consistently
            pair = tuple(sorted([tokens[i].value, tokens[j].value], key=str))
            cooccur[pair] += 1
    
    # Add nodes
    for token_val in valid_tokens:
        G.add_node(token_val, count=token_counts[token_val])
    
    # Add edges with PMI weights
    for (t1, t2), count in cooccur.items():
        if t1 == t2:
            continue
        
        # PMI = log(P(t1,t2) / (P(t1) * P(t2)))
        p_t1 = token_counts[t1] / total_tokens
        p_t2 = token_counts[t2] / total_tokens
        p_joint = count / (total_tokens * window_size)  # Approximate
        
        if p_joint > 0 and p_t1 > 0 and p_t2 > 0:
            pmi = np.log(p_joint / (p_t1 * p_t2 + EPSILON) + EPSILON)
            # Use positive PMI only
            weight = max(pmi, 0.0) + 0.1  # Small base weight
            G.add_edge(t1, t2, weight=weight, count=count)
    
    return G


def compute_eigenvector_centrality(G: nx.Graph) -> Dict[Any, float]:
    """
    Compute eigenvector centrality for all nodes.
    
    High centrality = important/central in the network.
    
    Args:
        G: NetworkX graph
    
    Returns:
        Dictionary mapping nodes to centrality values
    """
    if G.number_of_nodes() == 0:
        return {}
    
    try:
        centrality = nx.eigenvector_centrality_numpy(G, weight='weight')
    except:
        # Fallback for disconnected graphs
        centrality = {n: 1.0 / G.number_of_nodes() for n in G.nodes()}
    
    return centrality


def compute_clustering_coefficient(G: nx.Graph) -> Dict[Any, float]:
    """
    Compute clustering coefficient for all nodes.
    
    High clustering = node's neighbors are connected to each other.
    
    Args:
        G: NetworkX graph
    
    Returns:
        Dictionary mapping nodes to clustering coefficients
    """
    return nx.clustering(G, weight='weight')


def compute_betweenness(G: nx.Graph) -> Dict[Any, float]:
    """
    Compute betweenness centrality for all nodes.
    
    High betweenness = node is a bridge between communities.
    
    Args:
        G: NetworkX graph
    
    Returns:
        Dictionary mapping nodes to betweenness values
    """
    if G.number_of_nodes() == 0:
        return {}
    
    return nx.betweenness_centrality(G, weight='weight')


def compute_laplacian_eigenvectors(G: nx.Graph, k: int = 3) -> Dict[Any, np.ndarray]:
    """
    Compute first k eigenvectors of graph Laplacian.
    
    These provide spectral coordinates for each node.
    
    Args:
        G: NetworkX graph
        k: Number of eigenvectors
    
    Returns:
        Dictionary mapping nodes to k-dimensional spectral coordinates
    """
    nodes = list(G.nodes())
    n = len(nodes)
    
    if n < k + 1:
        # Not enough nodes for k eigenvectors
        return {node: np.zeros(k) for node in nodes}
    
    # Get Laplacian
    L = nx.normalized_laplacian_matrix(G)
    L = csr_matrix(L, dtype=np.float64)
    
    try:
        # If k+1 >= n, use dense eigendecomposition to avoid sparse solver warning
        if k + 1 >= n:
            from scipy.linalg import eigh
            L_dense = L.toarray()
            eigenvalues, eigenvectors = eigh(L_dense)
            # Take the k+1 smallest
            eigenvalues = eigenvalues[:k+1]
            eigenvectors = eigenvectors[:, :k+1]
        else:
            # Get smallest eigenvalues (first is always 0)
            eigenvalues, eigenvectors = eigsh(L, k=k+1, which='SM')
        
        # Skip the first (constant) eigenvector
        coords = eigenvectors[:, 1:k+1]
        
        return {node: coords[i] for i, node in enumerate(nodes)}
    
    except Exception as e:
        return {node: np.zeros(k) for node in nodes}


def compute_persistence(G: nx.Graph) -> Dict[Any, float]:
    """
    Compute persistence (topological lifetime) for nodes.
    
    Simplified version: uses graph connectivity properties
    to estimate how "persistent" each node's features are.
    
    Args:
        G: NetworkX graph
    
    Returns:
        Dictionary mapping nodes to persistence values
    """
    # Simplified: use degree-normalized by neighbors' degrees
    persistence = {}
    
    for node in G.nodes():
        neighbors = list(G.neighbors(node))
        if len(neighbors) == 0:
            persistence[node] = 0.0
        else:
            # Persistence ~ how much the node contributes to structure
            node_degree = G.degree(node, weight='weight')
            neighbor_degrees = [G.degree(n, weight='weight') for n in neighbors]
            avg_neighbor = np.mean(neighbor_degrees) if neighbor_degrees else 1.0
            persistence[node] = node_degree / (avg_neighbor + EPSILON)
    
    # Normalize to [0, 1]
    max_pers = max(persistence.values()) if persistence else 1.0
    if max_pers > 0:
        persistence = {k: v / max_pers for k, v in persistence.items()}
    
    return persistence


def embed_token_to_spinor(
    token_value: Any,
    graph: nx.Graph,
    centrality: Dict[Any, float] = None,
    clustering: Dict[Any, float] = None,
    betweenness: Dict[Any, float] = None,
    spectral_coords: Dict[Any, np.ndarray] = None,
    persistence: Dict[Any, float] = None,
    position: int = 0,
    total_tokens: int = 1
) -> Spinor:
    """
    Embed a token into an 8D spinor using topological features.
    
    Dimensions:
        0: Eigenvector centrality
        1: Clustering coefficient
        2: Betweenness centrality
        3-5: Spectral coordinates (first 3 Laplacian eigenvectors)
        6: Persistence
        7: φ-weighted position in stream
        
    Phase: Derived from position using golden angle
    
    Args:
        token_value: The token value to embed
        graph: Co-occurrence graph
        centrality: Pre-computed centrality (optional)
        clustering: Pre-computed clustering (optional)
        betweenness: Pre-computed betweenness (optional)
        spectral_coords: Pre-computed spectral coords (optional)
        persistence: Pre-computed persistence (optional)
        position: Token position in stream
        total_tokens: Total number of tokens
    
    Returns:
        8D Spinor
    """
    # Compute features if not provided
    if token_value not in graph.nodes():
        # Unknown token: return zero spinor
        return Spinor(np.zeros(8), phase=0.0)
    
    if centrality is None:
        centrality = compute_eigenvector_centrality(graph)
    if clustering is None:
        clustering = compute_clustering_coefficient(graph)
    if betweenness is None:
        betweenness = compute_betweenness(graph)
    if spectral_coords is None:
        spectral_coords = compute_laplacian_eigenvectors(graph, k=3)
    if persistence is None:
        persistence = compute_persistence(graph)
    
    # Build 8D position vector
    position_8d = np.zeros(8)
    
    # Dim 0: Eigenvector centrality
    position_8d[0] = centrality.get(token_value, 0.0)
    
    # Dim 1: Clustering coefficient
    position_8d[1] = clustering.get(token_value, 0.0)
    
    # Dim 2: Betweenness
    position_8d[2] = betweenness.get(token_value, 0.0)
    
    # Dim 3-5: Spectral coordinates
    spec = spectral_coords.get(token_value, np.zeros(3))
    position_8d[3:6] = spec[:3] if len(spec) >= 3 else np.pad(spec, (0, 3 - len(spec)))
    
    # Dim 6: Persistence
    position_8d[6] = persistence.get(token_value, 0.0)
    
    # Dim 7: φ-weighted position
    # Use golden ratio decay from start of document
    if total_tokens > 0:
        normalized_pos = position / total_tokens
        position_8d[7] = normalized_pos * PHI_INV  # Scale by golden ratio
    
    # Compute phase using golden angle
    # This ensures phases are optimally distributed (no clustering)
    golden_angle = 2 * np.pi * PHI_INV  # ≈ 137.5°
    phase = (position * golden_angle) % (2 * np.pi)
    
    return Spinor(position_8d, phase=phase)


def embed_all_tokens(
    tokens: List[Token],
    graph: nx.Graph = None,
    window_size: int = 5
) -> List[Spinor]:
    """
    Embed all tokens from a token stream into spinors.
    
    Args:
        tokens: List of tokens
        graph: Pre-built graph (built if None)
        window_size: Window size for graph building
    
    Returns:
        List of Spinors (one per token)
    """
    if graph is None:
        graph = build_cooccurrence_graph(tokens, window_size=window_size)
    
    # Pre-compute all features for efficiency
    centrality = compute_eigenvector_centrality(graph)
    clustering = compute_clustering_coefficient(graph)
    betweenness = compute_betweenness(graph)
    spectral_coords = compute_laplacian_eigenvectors(graph, k=3)
    persistence = compute_persistence(graph)
    
    total = len(tokens)
    spinors = []
    
    for token in tokens:
        spinor = embed_token_to_spinor(
            token.value,
            graph,
            centrality=centrality,
            clustering=clustering,
            betweenness=betweenness,
            spectral_coords=spectral_coords,
            persistence=persistence,
            position=token.position,
            total_tokens=total
        )
        spinors.append(spinor)
    
    return spinors


def embed_text_to_spinors(text: str, mode: str = 'word') -> Tuple[List[Spinor], nx.Graph, Dict]:
    """
    High-level function to embed text into spinors.
    
    Args:
        text: Input text
        mode: Tokenization mode ('word', 'char')
    
    Returns:
        (spinors, graph, metadata) tuple
    """
    tokens = tokenize(text, mode=mode)
    graph = build_cooccurrence_graph(tokens)
    spinors = embed_all_tokens(tokens, graph)
    
    metadata = {
        'n_tokens': len(tokens),
        'n_unique': graph.number_of_nodes(),
        'n_edges': graph.number_of_edges(),
        'mode': mode
    }
    
    return spinors, graph, metadata


def run_verification() -> None:
    """Run verification tests for TDA module."""
    print("=" * 60)
    print("TOPOLOGICAL DATA ANALYSIS VERIFICATION")
    print("=" * 60)
    
    # Test text
    test_text = """
    The quick brown fox jumps over the lazy dog.
    The dog was sleeping peacefully in the sun.
    A fox is quick and clever, while a dog is loyal.
    The sun was shining bright over the peaceful meadow.
    """
    
    # Test 1: Tokenization
    print("\n--- Test 1: Tokenization ---")
    tokens_word = tokenize(test_text, mode='word')
    tokens_char = tokenize("hello", mode='char')
    tokens_byte = tokenize(b"\x00\x01\x02", mode='byte')
    
    print(f"  Word tokens: {len(tokens_word)}")
    print(f"  Char tokens: {len(tokens_char)}")
    print(f"  Byte tokens: {len(tokens_byte)}")
    print(f"  Sample tokens: {[t.value for t in tokens_word[:5]]}")
    
    # Test 2: Graph construction
    print("\n--- Test 2: Co-occurrence graph ---")
    graph = build_cooccurrence_graph(tokens_word, window_size=5)
    print(f"  Nodes: {graph.number_of_nodes()}")
    print(f"  Edges: {graph.number_of_edges()}")
    
    # Test 3: Topological features
    print("\n--- Test 3: Topological features ---")
    centrality = compute_eigenvector_centrality(graph)
    clustering = compute_clustering_coefficient(graph)
    betweenness = compute_betweenness(graph)
    
    # Find most central token
    if centrality:
        most_central = max(centrality, key=centrality.get)
        print(f"  Most central: '{most_central}' ({centrality[most_central]:.4f})")
    
    # Test 4: Spectral coordinates
    print("\n--- Test 4: Spectral coordinates ---")
    spectral = compute_laplacian_eigenvectors(graph, k=3)
    if spectral:
        sample_token = list(spectral.keys())[0]
        print(f"  Sample coords for '{sample_token}': {spectral[sample_token]}")
    
    # Test 5: Token embedding
    print("\n--- Test 5: Token embedding ---")
    spinor = embed_token_to_spinor('the', graph, position=0, total_tokens=len(tokens_word))
    print(f"  Spinor for 'the': {spinor}")
    
    # Test 6: Full embedding
    print("\n--- Test 6: Full text embedding ---")
    spinors, _, metadata = embed_text_to_spinors(test_text, mode='word')
    print(f"  Total spinors: {len(spinors)}")
    print(f"  Unique tokens: {metadata['n_unique']}")
    
    # Test 7: Spinor distances
    print("\n--- Test 7: Semantic distances ---")
    from e8_lattice import spinor_distance
    
    # Embed specific words
    s_the = embed_token_to_spinor('the', graph)
    s_dog = embed_token_to_spinor('dog', graph)
    s_fox = embed_token_to_spinor('fox', graph)
    s_sun = embed_token_to_spinor('sun', graph)
    
    print(f"  dist('dog', 'fox'): {spinor_distance(s_dog, s_fox):.4f}")
    print(f"  dist('dog', 'sun'): {spinor_distance(s_dog, s_sun):.4f}")
    print(f"  (Semantically similar words should have smaller distance)")
    
    # Test 8: Universal data (bytes)
    print("\n--- Test 8: Universal embedding (bytes) ---")
    binary_data = b"ATCGATCGATCG" * 10  # DNA-like
    tokens_dna = tokenize(binary_data, mode='byte')
    graph_dna = build_cooccurrence_graph(tokens_dna)
    print(f"  DNA-like bytes: {len(tokens_dna)} tokens, {graph_dna.number_of_nodes()} unique")
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_verification()
