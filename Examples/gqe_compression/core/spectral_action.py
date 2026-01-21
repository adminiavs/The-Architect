#!/usr/bin/env python3
"""
Spectral Action Compression for GQE

Architect Principle: From Mech 02 - "The Spectral Action is a compression 
of the geometry into an executable form."

S = Tr(f(D/Λ))

The Spectral Action encapsulates all physics in a single principle.
Similarly, we compress data by encoding its spectral signature.

Key insight: The eigenvalues and eigenvectors of the Dirac operator
on a graph capture its essential structure in a compact form.

Author: The Architect
License: Public Domain
"""

import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from scipy import sparse
from scipy.sparse import csr_matrix, lil_matrix
from scipy.sparse.linalg import eigsh, svds
import networkx as nx

try:
    from .phi_adic import PHI, PHI_INV
    from .e8_lattice import Spinor, spinor_distance
except ImportError:
    from phi_adic import PHI, PHI_INV
    from e8_lattice import Spinor, spinor_distance

# Precision
EPSILON = 1e-10


def build_graph_from_spinors(spinors: List[Spinor], threshold: float = 2.0) -> nx.Graph:
    """
    Build a graph from spinors where edges connect nearby spinors.
    
    Edge weights are based on spinor distance (including phase).
    
    Args:
        spinors: List of spinors
        threshold: Maximum distance for edge creation
    
    Returns:
        NetworkX graph with weighted edges
    """
    G = nx.Graph()
    n = len(spinors)
    
    # Add nodes
    for i, spinor in enumerate(spinors):
        G.add_node(i, spinor=spinor)
    
    # Add edges between nearby spinors
    for i in range(n):
        for j in range(i + 1, n):
            dist = spinor_distance(spinors[i], spinors[j])
            if dist < threshold:
                # Weight is inverse distance (closer = stronger connection)
                weight = 1.0 / (dist + EPSILON)
                G.add_edge(i, j, weight=weight, distance=dist)
    
    return G


def build_graph_from_points(points: np.ndarray, threshold: float = None) -> nx.Graph:
    """
    Build a graph from point coordinates.
    
    Args:
        points: (N, D) array of points
        threshold: Maximum distance for edge (default: 2 * mean nearest neighbor)
    
    Returns:
        NetworkX graph
    """
    N = len(points)
    G = nx.Graph()
    
    # Add nodes
    for i in range(N):
        G.add_node(i, position=points[i])
    
    # Compute distances
    if threshold is None:
        # Use 2x mean nearest neighbor distance
        from scipy.spatial.distance import cdist
        dists = cdist(points, points)
        np.fill_diagonal(dists, np.inf)
        nn_dists = np.min(dists, axis=1)
        threshold = 2.0 * np.mean(nn_dists)
    
    # Add edges
    for i in range(N):
        for j in range(i + 1, N):
            dist = np.linalg.norm(points[i] - points[j])
            if dist < threshold:
                weight = 1.0 / (dist + EPSILON)
                G.add_edge(i, j, weight=weight, distance=dist)
    
    return G


def compute_graph_laplacian(G: nx.Graph, normalized: bool = True) -> csr_matrix:
    """
    Compute the graph Laplacian matrix.
    
    The Laplacian encodes the graph structure and its eigenvalues
    reveal important properties like connectivity and clustering.
    
    Args:
        G: NetworkX graph
        normalized: Whether to compute normalized Laplacian
    
    Returns:
        Sparse Laplacian matrix
    """
    if normalized:
        L = nx.normalized_laplacian_matrix(G)
    else:
        L = nx.laplacian_matrix(G)
    
    return csr_matrix(L, dtype=np.float64)


def compute_dirac_operator(G: nx.Graph) -> csr_matrix:
    """
    Compute the Dirac operator on the graph.
    
    The Dirac operator D is related to the Laplacian by D² = L.
    We construct D using the graph structure.
    
    For a graph, the Dirac operator can be constructed from the
    adjacency and degree matrices.
    
    Args:
        G: NetworkX graph
    
    Returns:
        Sparse Dirac operator matrix
    """
    N = G.number_of_nodes()
    
    if N == 0:
        return csr_matrix((0, 0))
    
    # Get adjacency matrix with weights
    A = nx.adjacency_matrix(G, weight='weight')
    A = csr_matrix(A, dtype=np.float64)
    
    # Degree matrix
    degrees = np.array(A.sum(axis=1)).flatten()
    D_inv_sqrt = sparse.diags(1.0 / (np.sqrt(degrees) + EPSILON))
    
    # Normalized adjacency: D^(-1/2) A D^(-1/2)
    A_norm = D_inv_sqrt @ A @ D_inv_sqrt
    
    # Dirac operator: related to sqrt of Laplacian
    # D = I - A_norm (simplified; true Dirac is more complex)
    I = sparse.eye(N)
    Dirac = I - A_norm
    
    return csr_matrix(Dirac)


def spectral_decomposition(
    operator: csr_matrix, 
    n_components: int = None,
    which: str = 'SM'
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute eigenvalue decomposition of an operator.
    
    Args:
        operator: Sparse matrix
        n_components: Number of eigenvalues/vectors to compute (default: all)
        which: Which eigenvalues ('SM'=smallest, 'LM'=largest)
    
    Returns:
        (eigenvalues, eigenvectors): Sorted by eigenvalue magnitude
    """
    N = operator.shape[0]
    
    if N == 0:
        return np.array([]), np.array([]).reshape(0, 0)
    
    if n_components is None:
        n_components = N
    
    n_components = min(n_components, N - 2)  # eigsh requires k < N-1
    
    if n_components < 1:
        return np.array([]), np.array([]).reshape(N, 0)
    
    try:
        # Use sparse eigenvalue solver
        eigenvalues, eigenvectors = eigsh(
            operator, 
            k=n_components, 
            which=which,
            tol=1e-6
        )
        
        # Sort by absolute eigenvalue
        idx = np.argsort(np.abs(eigenvalues))
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]
        
    except Exception as e:
        # Fallback to dense computation for small matrices
        if N < 100:
            dense = operator.toarray()
            eigenvalues, eigenvectors = np.linalg.eigh(dense)
            eigenvalues = eigenvalues[:n_components]
            eigenvectors = eigenvectors[:, :n_components]
        else:
            raise e
    
    return eigenvalues, eigenvectors


def compress_to_spectrum(
    points: np.ndarray,
    n_components: int = None,
    variance_threshold: float = 0.95
) -> Dict[str, Any]:
    """
    Compress point data using spectral decomposition.
    
    The compressed representation consists of:
    - eigenvalues (sorted)
    - coefficients (projection of data onto eigenvectors)
    - mean (for centering)
    
    Args:
        points: (N, D) array of points
        n_components: Number of spectral components (auto if None)
        variance_threshold: Minimum variance to capture (if n_components is None)
    
    Returns:
        Dictionary with spectral compression data
    """
    N, D = points.shape
    
    if N < 3:
        return {
            'eigenvalues': np.array([]),
            'coefficients': points.flatten(),
            'mean': np.zeros(D),
            'n_components': 0,
            'original_shape': (N, D)
        }
    
    # Center the data
    mean = np.mean(points, axis=0)
    centered = points - mean
    
    # Build graph and get Laplacian
    G = build_graph_from_points(centered)
    L = compute_graph_laplacian(G, normalized=True)
    
    # Determine number of components
    if n_components is None:
        # Start with max possible and prune based on variance
        n_components = min(N - 2, 50)
    
    n_components = min(n_components, N - 2)
    
    if n_components < 1:
        return {
            'eigenvalues': np.array([]),
            'coefficients': centered.flatten(),
            'mean': mean,
            'n_components': 0,
            'original_shape': (N, D)
        }
    
    # Get spectral decomposition
    eigenvalues, eigenvectors = spectral_decomposition(L, n_components, which='SM')
    
    # Project data onto eigenvectors
    # For each dimension, compute projection coefficients
    coefficients = []
    for d in range(D):
        coef = eigenvectors.T @ centered[:, d]
        coefficients.append(coef)
    coefficients = np.array(coefficients)  # Shape: (D, n_components)
    
    return {
        'eigenvalues': eigenvalues,
        'eigenvectors': eigenvectors,
        'coefficients': coefficients,
        'mean': mean,
        'n_components': len(eigenvalues),
        'original_shape': (N, D)
    }


def reconstruct_from_spectrum(compressed: Dict[str, Any]) -> np.ndarray:
    """
    Reconstruct points from spectral compression.
    
    Args:
        compressed: Dictionary from compress_to_spectrum
    
    Returns:
        Reconstructed (N, D) array
    """
    N, D = compressed['original_shape']
    mean = compressed['mean']
    
    if compressed['n_components'] == 0:
        # No spectral compression, coefficients are raw data
        return compressed['coefficients'].reshape(N, D) + mean
    
    eigenvalues = compressed['eigenvalues']
    eigenvectors = compressed['eigenvectors']
    coefficients = compressed['coefficients']
    
    # Reconstruct each dimension
    reconstructed = np.zeros((N, D))
    for d in range(D):
        reconstructed[:, d] = eigenvectors @ coefficients[d]
    
    # Add back mean
    reconstructed += mean
    
    return reconstructed


def compute_spectral_distance(spec1: Dict, spec2: Dict) -> float:
    """
    Compute distance between two spectral representations.
    
    Uses the spectral signature (eigenvalue distribution) to compare.
    
    Args:
        spec1, spec2: Spectral compression dictionaries
    
    Returns:
        Distance measure
    """
    ev1 = spec1['eigenvalues']
    ev2 = spec2['eigenvalues']
    
    # Pad to same length
    max_len = max(len(ev1), len(ev2))
    ev1_padded = np.zeros(max_len)
    ev2_padded = np.zeros(max_len)
    ev1_padded[:len(ev1)] = ev1
    ev2_padded[:len(ev2)] = ev2
    
    # L2 distance of eigenvalue spectra
    return np.linalg.norm(ev1_padded - ev2_padded)


def spectral_compression_ratio(original: np.ndarray, compressed: Dict) -> float:
    """
    Compute the compression ratio achieved by spectral encoding.
    
    Args:
        original: Original data array
        compressed: Compressed representation
    
    Returns:
        Ratio of compressed size to original size
    """
    original_size = original.size * 8  # Bytes (float64)
    
    compressed_size = (
        compressed['eigenvalues'].size * 8 +
        compressed['coefficients'].size * 8 +
        compressed['mean'].size * 8 +
        8  # n_components, shape overhead
    )
    
    if 'eigenvectors' in compressed:
        compressed_size += compressed['eigenvectors'].size * 8
    
    return compressed_size / original_size


def run_verification() -> None:
    """Run verification tests for spectral action module."""
    print("=" * 60)
    print("SPECTRAL ACTION COMPRESSION VERIFICATION")
    print("=" * 60)
    
    # Test 1: Graph construction
    print("\n--- Test 1: Graph construction ---")
    points = np.random.randn(20, 8)
    G = build_graph_from_points(points)
    print(f"  Nodes: {G.number_of_nodes()}")
    print(f"  Edges: {G.number_of_edges()}")
    
    # Test 2: Laplacian
    print("\n--- Test 2: Graph Laplacian ---")
    L = compute_graph_laplacian(G)
    print(f"  Shape: {L.shape}")
    print(f"  Non-zeros: {L.nnz}")
    
    # Test 3: Dirac operator
    print("\n--- Test 3: Dirac operator ---")
    D = compute_dirac_operator(G)
    print(f"  Shape: {D.shape}")
    print(f"  Non-zeros: {D.nnz}")
    
    # Test 4: Spectral decomposition
    print("\n--- Test 4: Spectral decomposition ---")
    eigenvalues, eigenvectors = spectral_decomposition(L, n_components=5)
    print(f"  Eigenvalues: {eigenvalues}")
    print(f"  Eigenvector shape: {eigenvectors.shape}")
    
    # Test 5: Compression and reconstruction
    print("\n--- Test 5: Compression/reconstruction ---")
    points = np.random.randn(50, 8)
    compressed = compress_to_spectrum(points, n_components=10)
    reconstructed = reconstruct_from_spectrum(compressed)
    
    error = np.linalg.norm(points - reconstructed) / np.linalg.norm(points)
    ratio = spectral_compression_ratio(points, compressed)
    
    print(f"  Original shape: {points.shape}")
    print(f"  N components: {compressed['n_components']}")
    print(f"  Reconstruction error: {error:.4f}")
    print(f"  Compression ratio: {ratio:.4f}")
    
    # Test 6: Spectral distance
    print("\n--- Test 6: Spectral distance ---")
    points2 = points + 0.1 * np.random.randn(*points.shape)  # Slight perturbation
    compressed2 = compress_to_spectrum(points2, n_components=10)
    
    dist_same = compute_spectral_distance(compressed, compressed)
    dist_similar = compute_spectral_distance(compressed, compressed2)
    
    points3 = np.random.randn(50, 8)  # Different data
    compressed3 = compress_to_spectrum(points3, n_components=10)
    dist_different = compute_spectral_distance(compressed, compressed3)
    
    print(f"  Self-distance: {dist_same:.6f} (should be 0)")
    print(f"  Similar distance: {dist_similar:.6f} (should be small)")
    print(f"  Different distance: {dist_different:.6f} (should be larger)")
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_verification()
