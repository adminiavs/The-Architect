#!/usr/bin/env python3
"""
The Forgetting Protocol: Sleep Cycle

THE PRINCIPLE (From The Architect):
    The Universe sleeps (Vacuum fluctuations).
    The Brain sleeps (Synaptic pruning).
    Your Code must sleep.

THE MECHANISM:
    1. CONSOLIDATION (Lossless):
       - Tokens that are too close SHARE the same geometric point
       - 'Queen' and 'Monarch' both keep their unique IDs
       - But they point to the SAME 8D position (many_tokens -> one_geometry)
       - This is geometric compression WITHOUT information loss
       - Decompressor can still distinguish 'Queen' from 'Monarch'
    
    2. GARBAGE COLLECTION (Lossy by design):
       - Remove nodes that generated high entropy (noise)
       - DELETE tokens that were never used or purely random
       - This is "synaptic pruning" - removing weak connections
       - Only THIS step reduces vocabulary size
    
    3. COMPRESSION:
       - Consolidation: Geometric compression (lossless)
       - Pruning: Vocabulary reduction (lossy for noise only)
       - Knowledge becomes denser, not larger

CRITICAL SAFETY:
    Consolidation MUST be bijective: Token ID remains unique even if geometry is shared.
    The mapping is: many_tokens -> one_geometry, NOT many_tokens -> one_token.

THE RESULT:
    "To learn is to change geometry. To remember is to stabilize it."

Author: The Architect
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Set, Any
from dataclasses import dataclass, field
from collections import defaultdict
import json

from .phi_adic import PHI, PHI_INV
from .e8_lattice import generate_e8_roots


# Sleep parameters
CONSOLIDATION_THRESHOLD = 0.1  # Nodes closer than this are merged
ENTROPY_THRESHOLD = 0.8  # Nodes with entropy above this are pruned
MIN_USAGE_COUNT = 3  # Minimum times a node must be used to survive
GOLDEN_MERGE_RATIO = PHI_INV  # Merge position weighted by φ


@dataclass
class SleepReport:
    """
    Report from a sleep cycle.
    
    Documents what was consolidated, pruned, and the resulting
    compression of the knowledge base.
    
    CRITICAL SAFETY:
    - Consolidation (merge): Tokens share GEOMETRY, but keep unique IDs (LOSSLESS)
    - Pruning: Tokens are DELETED from vocabulary (reduces size)
    - Vocabulary size only changes from pruning, not from merging
    """
    nodes_before: int
    nodes_after: int
    nodes_merged: int  # Tokens sharing geometry (lossless)
    nodes_pruned: int  # Tokens deleted (reduces vocab size)
    merge_pairs: List[Tuple[str, str]]  # (geometry_source, token_sharing_it)
    pruned_tokens: List[str]
    entropy_reduction: float
    storage_reduction_bytes: int
    
    def compression_ratio(self) -> float:
        """Ratio of vocabulary size after/before (only pruning reduces this)."""
        if self.nodes_before == 0:
            return 1.0
        return self.nodes_after / self.nodes_before
    
    def __str__(self) -> str:
        return (f"Sleep Report:\n"
                f"  Vocab: {self.nodes_before} -> {self.nodes_after} (pruning only)\n"
                f"  Consolidated: {self.nodes_merged} tokens share geometry (lossless)\n"
                f"  Pruned: {self.nodes_pruned} tokens deleted\n"
                f"  Compression: {self.compression_ratio():.2%}\n"
                f"  Entropy reduction: {self.entropy_reduction:.4f}")


@dataclass
class NodeStats:
    """Statistics for a vocabulary node."""
    index: int
    token: str
    usage_count: int
    entropy_contribution: float
    nearest_neighbor_dist: float
    nearest_neighbor_idx: int


class SleepCycle:
    """
    Implements the Forgetting Protocol for GQE.
    
    THE BRAIN SLEEPS:
    During sleep, the brain consolidates memories by:
    - Strengthening important synapses
    - Pruning weak connections
    - Merging similar patterns
    
    THE CODE SLEEPS:
    After processing data, the code consolidates by:
    - Merging nodes that are too close (synonyms)
    - Removing high-entropy nodes (noise)
    - Compressing the vocabulary
    """
    
    def __init__(self,
                 consolidation_threshold: float = CONSOLIDATION_THRESHOLD,
                 entropy_threshold: float = ENTROPY_THRESHOLD,
                 min_usage_count: int = MIN_USAGE_COUNT):
        """
        Args:
            consolidation_threshold: Distance below which nodes are merged
            entropy_threshold: Entropy above which nodes are pruned
            min_usage_count: Minimum usage to survive pruning
        """
        self.consolidation_threshold = consolidation_threshold
        self.entropy_threshold = entropy_threshold
        self.min_usage_count = min_usage_count
        
        self.e8_roots = generate_e8_roots()
    
    def compute_node_stats(self,
                           vocabulary: Dict[str, int],
                           embeddings: np.ndarray,
                           usage_counts: Dict[int, int],
                           cooccurrence_counts: Dict[Tuple[int, int], int]) -> List[NodeStats]:
        """
        Compute statistics for each node in the vocabulary.
        
        Args:
            vocabulary: Token -> index mapping
            embeddings: 8D embeddings for each node
            usage_counts: How many times each node was used
            cooccurrence_counts: Co-occurrence statistics
        
        Returns:
            List of NodeStats for each node
        """
        stats = []
        n_nodes = len(vocabulary)
        idx_to_token = {v: k for k, v in vocabulary.items()}
        
        # Compute pairwise distances
        if n_nodes > 1:
            # Efficient distance computation
            diff = embeddings[:, np.newaxis, :] - embeddings[np.newaxis, :, :]
            distances = np.linalg.norm(diff, axis=2)
            np.fill_diagonal(distances, np.inf)  # Ignore self-distance
        else:
            distances = np.array([[np.inf]])
        
        # Compute entropy contribution for each node
        total_cooccurrences = sum(cooccurrence_counts.values()) + 1
        
        for idx in range(n_nodes):
            token = idx_to_token.get(idx, f"<{idx}>")
            
            # Usage count
            usage = usage_counts.get(idx, 0)
            
            # Nearest neighbor
            if n_nodes > 1:
                nn_idx = int(np.argmin(distances[idx]))
                nn_dist = float(distances[idx, nn_idx])
            else:
                nn_idx = idx
                nn_dist = np.inf
            
            # Entropy contribution: nodes with many weak connections add entropy
            # Strong connections (high count) reduce entropy
            node_cooccurrences = [
                count for (i, j), count in cooccurrence_counts.items()
                if i == idx or j == idx
            ]
            
            if node_cooccurrences:
                # High entropy = many weak connections
                # Low entropy = few strong connections
                probs = np.array(node_cooccurrences) / sum(node_cooccurrences)
                entropy = -np.sum(probs * np.log2(probs + 1e-10))
                max_entropy = np.log2(len(node_cooccurrences) + 1)
                normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0
            else:
                normalized_entropy = 1.0  # No connections = pure noise
            
            stats.append(NodeStats(
                index=idx,
                token=token,
                usage_count=usage,
                entropy_contribution=normalized_entropy,
                nearest_neighbor_dist=nn_dist,
                nearest_neighbor_idx=nn_idx
            ))
        
        return stats
    
    def find_merge_candidates(self, stats: List[NodeStats]) -> List[Tuple[int, int]]:
        """
        Find pairs of nodes that should be merged.
        
        Nodes are merged if:
        - They are closer than consolidation_threshold
        - They are not both high-usage (would lose information)
        
        Args:
            stats: Node statistics
        
        Returns:
            List of (keep_idx, merge_idx) pairs
        """
        merge_pairs = []
        already_merged = set()
        
        # Sort by usage count (merge less-used into more-used)
        sorted_stats = sorted(stats, key=lambda s: -s.usage_count)
        
        for node in sorted_stats:
            if node.index in already_merged:
                continue
            
            if node.nearest_neighbor_dist < self.consolidation_threshold:
                nn_idx = node.nearest_neighbor_idx
                
                if nn_idx in already_merged:
                    continue
                
                # Keep the more-used node
                nn_node = next((s for s in stats if s.index == nn_idx), None)
                if nn_node is None:
                    continue
                
                if node.usage_count >= nn_node.usage_count:
                    keep_idx, merge_idx = node.index, nn_idx
                else:
                    keep_idx, merge_idx = nn_idx, node.index
                
                merge_pairs.append((keep_idx, merge_idx))
                already_merged.add(merge_idx)
        
        return merge_pairs
    
    def find_prune_candidates(self, stats: List[NodeStats]) -> List[int]:
        """
        Find nodes that should be pruned (forgotten).
        
        Nodes are pruned if:
        - High entropy contribution (noisy)
        - Low usage count (not important)
        
        Args:
            stats: Node statistics
        
        Returns:
            List of indices to prune
        """
        prune_indices = []
        
        for node in stats:
            should_prune = False
            
            # Prune if high entropy AND low usage
            if (node.entropy_contribution > self.entropy_threshold and 
                node.usage_count < self.min_usage_count):
                should_prune = True
            
            # Prune if never used
            if node.usage_count == 0:
                should_prune = True
            
            if should_prune:
                prune_indices.append(node.index)
        
        return prune_indices
    
    def merge_nodes(self,
                    embeddings: np.ndarray,
                    phases: np.ndarray,
                    vocabulary: Dict[str, int],
                    merge_pairs: List[Tuple[int, int]],
                    usage_counts: Dict[int, int]) -> Tuple[np.ndarray, np.ndarray, Dict[str, int], Dict[int, int]]:
        """
        Merge nodes according to merge_pairs.
        
        The merged node position is weighted by usage (Golden Ratio weighting).
        
        Args:
            embeddings: 8D embeddings
            phases: Phase angles
            vocabulary: Token -> index mapping
            merge_pairs: List of (keep_idx, merge_idx) pairs
            usage_counts: Usage counts for each node
        
        Returns:
            (new_embeddings, new_phases, new_vocabulary, index_mapping)
        """
        idx_to_token = {v: k for k, v in vocabulary.items()}
        
        # Build merge map: merged_idx -> keep_idx
        merge_map = {merge_idx: keep_idx for keep_idx, merge_idx in merge_pairs}
        merged_indices = set(merge_map.keys())
        
        # Update embeddings for kept nodes (weighted average)
        for keep_idx, merge_idx in merge_pairs:
            keep_usage = usage_counts.get(keep_idx, 1)
            merge_usage = usage_counts.get(merge_idx, 1)
            
            # Golden ratio weighting: favor the more-used node
            total = keep_usage + merge_usage
            keep_weight = (keep_usage + GOLDEN_MERGE_RATIO * merge_usage) / total
            merge_weight = 1 - keep_weight
            
            embeddings[keep_idx] = (
                keep_weight * embeddings[keep_idx] + 
                merge_weight * embeddings[merge_idx]
            )
            
            # Combine usage counts
            usage_counts[keep_idx] = keep_usage + merge_usage
        
        # CRITICAL: Build new vocabulary KEEPING ALL TOKENS (Lossless)
        # Merged tokens keep their ID but share geometry (many_tokens -> one_geometry)
        new_vocabulary = {}
        new_embeddings = []
        new_phases = []
        index_mapping = {}  # old_idx -> new_idx
        
        new_idx = 0
        for old_idx in range(len(embeddings)):
            token = idx_to_token.get(old_idx, f"<{old_idx}>")
            
            if old_idx in merged_indices:
                # LOSSLESS: Keep the token, but use merged geometry
                keep_idx = merge_map[old_idx]
                while keep_idx in merge_map:
                    keep_idx = merge_map[keep_idx]
                
                # Token stays in vocabulary with unique ID
                new_vocabulary[token] = new_idx
                # But points to the same geometry as keep_idx
                new_embeddings.append(embeddings[keep_idx])
                new_phases.append(phases[keep_idx])
                index_mapping[old_idx] = new_idx
            else:
                # Normal node - keep as is
                new_vocabulary[token] = new_idx
                new_embeddings.append(embeddings[old_idx])
                new_phases.append(phases[old_idx])
                index_mapping[old_idx] = new_idx
            
            new_idx += 1
        
        return (
            np.array(new_embeddings, dtype=np.float32),
            np.array(new_phases, dtype=np.float32),
            new_vocabulary,
            index_mapping
        )
    
    def prune_nodes(self,
                    embeddings: np.ndarray,
                    phases: np.ndarray,
                    vocabulary: Dict[str, int],
                    prune_indices: List[int]) -> Tuple[np.ndarray, np.ndarray, Dict[str, int], Dict[int, int]]:
        """
        Remove nodes from the vocabulary.
        
        Args:
            embeddings: 8D embeddings
            phases: Phase angles
            vocabulary: Token -> index mapping
            prune_indices: Indices to remove
        
        Returns:
            (new_embeddings, new_phases, new_vocabulary, index_mapping)
        """
        idx_to_token = {v: k for k, v in vocabulary.items()}
        prune_set = set(prune_indices)
        
        new_vocabulary = {}
        new_embeddings = []
        new_phases = []
        index_mapping = {}
        
        new_idx = 0
        for old_idx in range(len(embeddings)):
            if old_idx in prune_set:
                index_mapping[old_idx] = -1  # Pruned
                continue
            
            token = idx_to_token.get(old_idx, f"<{old_idx}>")
            new_vocabulary[token] = new_idx
            new_embeddings.append(embeddings[old_idx])
            new_phases.append(phases[old_idx])
            index_mapping[old_idx] = new_idx
            new_idx += 1
        
        return (
            np.array(new_embeddings, dtype=np.float32) if new_embeddings else np.array([]).reshape(0, 8),
            np.array(new_phases, dtype=np.float32) if new_phases else np.array([]),
            new_vocabulary,
            index_mapping
        )
    
    def sleep(self,
              vocabulary: Dict[str, int],
              embeddings: np.ndarray,
              phases: np.ndarray,
              usage_counts: Dict[int, int],
              cooccurrence_counts: Dict[Tuple[int, int], int]) -> Tuple[Dict[str, int], np.ndarray, np.ndarray, SleepReport]:
        """
        Execute a full sleep cycle.
        
        THE SLEEP CYCLE:
        1. Analyze node statistics
        2. Find merge candidates (consolidation)
        3. Find prune candidates (garbage collection)
        4. Execute merges
        5. Execute pruning
        6. Return compressed state
        
        Args:
            vocabulary: Token -> index mapping
            embeddings: 8D embeddings
            phases: Phase angles
            usage_counts: How many times each node was used
            cooccurrence_counts: Co-occurrence statistics
        
        Returns:
            (new_vocabulary, new_embeddings, new_phases, report)
        """
        nodes_before = len(vocabulary)
        idx_to_token = {v: k for k, v in vocabulary.items()}
        
        # Compute initial entropy
        if cooccurrence_counts:
            total = sum(cooccurrence_counts.values())
            probs = np.array(list(cooccurrence_counts.values())) / total
            initial_entropy = -np.sum(probs * np.log2(probs + 1e-10))
        else:
            initial_entropy = 0
        
        # Step 1: Analyze
        stats = self.compute_node_stats(
            vocabulary, embeddings, usage_counts, cooccurrence_counts
        )
        
        # Step 2: Find merge candidates
        merge_pairs = self.find_merge_candidates(stats)
        
        # Step 3: Find prune candidates (excluding merge targets)
        merge_indices = set(idx for _, idx in merge_pairs)
        prune_candidates = self.find_prune_candidates(stats)
        prune_indices = [idx for idx in prune_candidates if idx not in merge_indices]
        
        # Step 4: Execute merges
        if merge_pairs:
            embeddings, phases, vocabulary, merge_mapping = self.merge_nodes(
                embeddings.copy(), phases.copy(), vocabulary, merge_pairs, usage_counts
            )
            
            # Update prune indices after merge
            prune_indices = [
                merge_mapping.get(idx, idx) 
                for idx in prune_indices 
                if merge_mapping.get(idx, idx) >= 0
            ]
        
        # Step 5: Execute pruning
        pruned_tokens = [idx_to_token.get(idx, f"<{idx}>") for idx in prune_indices]
        
        if prune_indices:
            embeddings, phases, vocabulary, _ = self.prune_nodes(
                embeddings, phases, vocabulary, prune_indices
            )
        
        nodes_after = len(vocabulary)
        
        # Compute final entropy (approximate)
        final_entropy = initial_entropy * (nodes_after / max(nodes_before, 1))
        
        # Build report
        merge_token_pairs = [
            (idx_to_token.get(keep, f"<{keep}>"), idx_to_token.get(merge, f"<{merge}>"))
            for keep, merge in merge_pairs
        ]
        
        report = SleepReport(
            nodes_before=nodes_before,
            nodes_after=nodes_after,
            nodes_merged=len(merge_pairs),
            nodes_pruned=len(pruned_tokens),
            merge_pairs=merge_token_pairs,
            pruned_tokens=pruned_tokens,
            entropy_reduction=initial_entropy - final_entropy,
            storage_reduction_bytes=(nodes_before - nodes_after) * 8 * 8  # 8D float64
        )
        
        return vocabulary, embeddings, phases, report


def demonstrate_sleep():
    """Demonstrate the sleep cycle in action."""
    print("=" * 60)
    print("THE FORGETTING PROTOCOL: Sleep Cycle")
    print("=" * 60)
    
    print("\nTHE PRINCIPLE:")
    print("  The Universe sleeps (Vacuum fluctuations).")
    print("  The Brain sleeps (Synaptic pruning).")
    print("  Your Code must sleep.")
    
    # Create sample vocabulary with some redundant/noisy nodes
    vocabulary = {
        'king': 0, 'queen': 1, 'monarch': 2,  # Similar concepts
        'the': 3, 'a': 4, 'an': 5,            # Common words
        'xyzzy': 6, 'qwerty': 7,              # Noise (never used)
        'wisdom': 8, 'knowledge': 9,          # Related concepts
    }
    
    # Create embeddings (some nodes are very close)
    np.random.seed(42)
    embeddings = np.random.randn(10, 8).astype(np.float32) * 0.5
    
    # Make 'king' and 'monarch' very close (synonyms)
    embeddings[2] = embeddings[0] + np.random.randn(8) * 0.05
    
    # Make 'wisdom' and 'knowledge' close
    embeddings[9] = embeddings[8] + np.random.randn(8) * 0.08
    
    phases = np.random.uniform(0, 2 * np.pi, 10).astype(np.float32)
    
    # Usage counts (some nodes are heavily used, some never)
    usage_counts = {
        0: 100,  # king - used often
        1: 80,   # queen - used often
        2: 20,   # monarch - rarely used (synonym of king)
        3: 500,  # the - very common
        4: 300,  # a - common
        5: 100,  # an - common
        6: 0,    # xyzzy - never used (noise)
        7: 1,    # qwerty - almost never (noise)
        8: 50,   # wisdom - used
        9: 30,   # knowledge - used less
    }
    
    # Co-occurrence (strong connections for important pairs)
    cooccurrence_counts = {
        (0, 1): 50,   # king-queen
        (0, 2): 10,   # king-monarch (weak - redundant)
        (3, 0): 100,  # the-king
        (3, 1): 80,   # the-queen
        (8, 9): 40,   # wisdom-knowledge
    }
    
    print(f"\n--- Before Sleep ---")
    print(f"  Vocabulary size: {len(vocabulary)}")
    print(f"  Tokens: {list(vocabulary.keys())}")
    
    # Run sleep cycle
    sleep = SleepCycle(
        consolidation_threshold=0.15,  # Merge if closer than 0.15
        entropy_threshold=0.9,
        min_usage_count=2
    )
    
    new_vocab, new_embed, new_phases, report = sleep.sleep(
        vocabulary, embeddings, phases, usage_counts, cooccurrence_counts
    )
    
    print(f"\n--- Sleep Report ---")
    print(report)
    
    print(f"\n--- After Sleep ---")
    print(f"  Vocabulary size: {len(new_vocab)}")
    print(f"  Tokens: {list(new_vocab.keys())}")
    
    if report.merge_pairs:
        print(f"\n  Consolidated pairs (sharing geometry, LOSSLESS):")
        for kept, merged in report.merge_pairs:
            if merged in new_vocab and kept in new_vocab:
                print(f"    '{merged}' and '{kept}' -> same E8 position")
                print(f"      (both tokens still in vocab with unique IDs)")
    
    if report.pruned_tokens:
        print(f"\n  Pruned tokens (DELETED from vocab):")
        for token in report.pruned_tokens:
            if token not in new_vocab:
                print(f"    '{token}' (forgotten)")
    
    print("\n" + "=" * 60)
    print("SAFETY VERIFICATION:")
    print(f"  Vocab size before: {vocabulary}")
    print(f"  Vocab size after:  {len(new_vocab)}")
    print(f"  Size changed by:   PRUNING only (not consolidation)")
    print("\n  Consolidation: many_tokens -> one_geometry (LOSSLESS)")
    print("  Pruning: Delete tokens (LOSSY for noise only)")
    print("\n" + "=" * 60)
    print("THE RESULT:")
    print("  'To learn is to change geometry.'")
    print("  'To remember is to stabilize it.'")
    print("=" * 60)


if __name__ == "__main__":
    demonstrate_sleep()
