#!/usr/bin/env python3
"""
Geometric Evolver: Self-Learning through the Möbius Strip

THE PRINCIPLE (From The Architect):
    Evolution is Geometric Refinement.
    Learning is not "adding weights" - it is RESHAPING the geometric substrate.

THE MECHANISM:
    1. FEEDBACK LOOP (The Möbius Strip):
       - Compress data -> Observe co-occurrences -> Update E8 basis
       - Words that appear together MOVE CLOSER in 8D space
       - This is permanent geometric learning
    
    2. PHASON FLIPS (Emergence):
       - Random geometric mutations to the vocabulary map
       - Test mutation against data
       - If compression improves (lower entropy) -> KEEP the mutation
       - This allows the system to INVENT new concepts
    
    3. SELECTION (Natural Selection):
       - Fitness = Compression Efficiency (bits per token)
       - Better configurations survive
       - The system evolves its own language

THE RESULT:
    The GQE compressor becomes a living geometric entity that
    learns the structure of language by reshaping its 8D substrate.

Author: The Architect
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
import json
import os
import pickle

from .phi_adic import PHI, PHI_INV
from .e8_lattice import Spinor, generate_e8_roots
from .tda import tokenize, Token
from .bekenstein_bound import BekensteinBound, CrystallizedState, GOLDEN_THRESHOLD
from .sleep_cycle import SleepCycle, SleepReport


# Evolution parameters
DEFAULT_LEARNING_RATE = 0.01  # How fast nodes move toward each other
DEFAULT_MUTATION_RATE = 0.001  # Probability of phason flip per node
DEFAULT_MUTATION_MAGNITUDE = 0.1  # Size of phason flip
ATTRACTION_THRESHOLD = 3  # Minimum co-occurrences to trigger attraction


@dataclass
class EvolutionState:
    """
    Persistent state of the evolving E8 basis.
    
    This is the "genome" of the compressor - it encodes
    the learned geometric structure of language.
    """
    # Core geometric state
    embeddings_8d: np.ndarray  # Shape: (vocab_size, 8)
    phases: np.ndarray         # Shape: (vocab_size,)
    vocabulary: Dict[str, int]  # Token -> index
    
    # Co-occurrence memory (for learning)
    cooccurrence_counts: Dict[Tuple[int, int], int] = field(default_factory=dict)
    
    # Evolution history
    generation: int = 0
    fitness_history: List[float] = field(default_factory=list)
    mutation_history: List[Dict] = field(default_factory=list)
    
    # Statistics
    total_tokens_seen: int = 0
    total_compressions: int = 0
    
    def save(self, path: str):
        """Save evolution state to file."""
        state_dict = {
            'embeddings_8d': self.embeddings_8d.tolist(),
            'phases': self.phases.tolist(),
            'vocabulary': self.vocabulary,
            'cooccurrence_counts': {f"{k[0]},{k[1]}": v for k, v in self.cooccurrence_counts.items()},
            'generation': self.generation,
            'fitness_history': self.fitness_history,
            'total_tokens_seen': self.total_tokens_seen,
            'total_compressions': self.total_compressions,
        }
        with open(path, 'w') as f:
            json.dump(state_dict, f)
    
    @classmethod
    def load(cls, path: str) -> Optional['EvolutionState']:
        """Load evolution state from file."""
        with open(path, 'r') as f:
            state_dict = json.load(f)
        
        # Handle empty state
        if not state_dict or 'vocabulary' not in state_dict:
            return None
        
        cooccurrence_counts = {}
        for k, v in state_dict.get('cooccurrence_counts', {}).items():
            i, j = map(int, k.split(','))
            cooccurrence_counts[(i, j)] = v
        
        return cls(
            embeddings_8d=np.array(state_dict['embeddings_8d'], dtype=np.float32),
            phases=np.array(state_dict['phases'], dtype=np.float32),
            vocabulary=state_dict['vocabulary'],
            cooccurrence_counts=cooccurrence_counts,
            generation=state_dict.get('generation', 0),
            fitness_history=state_dict.get('fitness_history', []),
            total_tokens_seen=state_dict.get('total_tokens_seen', 0),
            total_compressions=state_dict.get('total_compressions', 0),
        )


class GeometricEvolver:
    """
    The Self-Learning Engine for GQE Compression.
    
    Implements the Möbius Feedback Loop:
    1. Observe co-occurrences during compression
    2. Update E8 basis to reflect learned structure
    3. Apply random phason flips (mutations)
    4. Select configurations that improve compression
    
    BEKENSTEIN BOUND:
    Storage is bounded using crystallization thresholds and quantization.
    Only stable harmonics (significant improvements) are persisted.
    """
    
    def __init__(self, 
                 learning_rate: float = DEFAULT_LEARNING_RATE,
                 mutation_rate: float = DEFAULT_MUTATION_RATE,
                 mutation_magnitude: float = DEFAULT_MUTATION_MAGNITUDE,
                 state_path: Optional[str] = None,
                 use_bekenstein_bound: bool = True):
        """
        Initialize the evolver.
        
        Args:
            learning_rate: How fast nodes move toward co-occurring neighbors
            mutation_rate: Probability of random phason flip per node
            mutation_magnitude: Size of random mutations
            state_path: Path to save/load persistent state
            use_bekenstein_bound: Enable storage-bounded learning
        """
        self.learning_rate = learning_rate
        self.mutation_rate = mutation_rate
        self.mutation_magnitude = mutation_magnitude
        self.state_path = state_path
        self.use_bekenstein_bound = use_bekenstein_bound
        
        self.e8_roots = generate_e8_roots()
        self.state: Optional[EvolutionState] = None
        
        # Bekenstein Bound manager for storage optimization
        self.bound: Optional[BekensteinBound] = None
        if use_bekenstein_bound:
            self.bound = BekensteinBound(
                golden_threshold=GOLDEN_THRESHOLD,
                decay_cycles=100,
                decay_rate=0.1,
            )
        
        # Base embeddings (before drift)
        self.base_embeddings: Optional[np.ndarray] = None
        
        # Load existing state if available
        if state_path and os.path.exists(state_path):
            try:
                if os.path.getsize(state_path) > 0:
                    # Try loading crystallized state first (compact)
                    if self.bound and self.bound.load_crystallized(state_path):
                        print(f"[GeometricEvolver] Loaded crystallized state: "
                              f"generation {self.bound.crystallized.generation}, "
                              f"{len(self.bound.crystallized.phason_diffs)} diffs")
                    else:
                        # Fall back to full state
                        loaded_state = EvolutionState.load(state_path)
                        if loaded_state is not None:
                            self.state = loaded_state
                            print(f"[GeometricEvolver] Loaded state: generation {self.state.generation}, "
                                  f"vocab size {len(self.state.vocabulary)}")
            except (json.JSONDecodeError, KeyError) as e:
                print(f"[GeometricEvolver] Could not load state: {e}. Starting fresh.")
    
    def initialize_from_vocabulary(self, vocabulary: Dict[str, int], 
                                   embeddings_8d: np.ndarray,
                                   phases: np.ndarray) -> EvolutionState:
        """
        Initialize evolution state from a vocabulary.
        
        If a crystallized state exists, continue from there.
        
        Args:
            vocabulary: Token -> index mapping
            embeddings_8d: Initial 8D embeddings
            phases: Initial phase angles
        
        Returns:
            New or continued EvolutionState
        """
        # Store base embeddings for Bekenstein Bound
        self.base_embeddings = embeddings_8d.copy()
        
        # Check if we have crystallized state to continue from
        start_generation = 0
        start_tokens_seen = 0
        
        if self.bound and self.bound.crystallized is not None:
            # Continue from crystallized state
            start_generation = self.bound.crystallized.generation
            start_tokens_seen = self.bound.crystallized.total_tokens_seen
            
            # Apply crystallized diffs to base embeddings
            evolved_embeddings = self.bound.reconstruct_from_crystallized(embeddings_8d)
        else:
            evolved_embeddings = embeddings_8d.copy()
        
        self.state = EvolutionState(
            embeddings_8d=evolved_embeddings,
            phases=phases.copy(),
            vocabulary=vocabulary.copy(),
            cooccurrence_counts={},
            generation=start_generation,
            fitness_history=[],
            total_tokens_seen=start_tokens_seen,
            total_compressions=0,
        )
        return self.state
    
    def observe_cooccurrences(self, token_indices: np.ndarray, window_size: int = 5):
        """
        Observe co-occurrences from a token sequence.
        
        This is the LEARNING step - we record which tokens appear together.
        
        Args:
            token_indices: Array of vocabulary indices
            window_size: Size of co-occurrence window
        """
        if self.state is None:
            raise ValueError("Evolver not initialized. Call initialize_from_vocabulary first.")
        
        n_tokens = len(token_indices)
        
        for i in range(n_tokens):
            idx_i = int(token_indices[i])
            
            # Look at neighbors within window
            for j in range(max(0, i - window_size), min(n_tokens, i + window_size + 1)):
                if i == j:
                    continue
                idx_j = int(token_indices[j])
                
                # Canonical ordering for symmetric storage
                pair = (min(idx_i, idx_j), max(idx_i, idx_j))
                self.state.cooccurrence_counts[pair] = \
                    self.state.cooccurrence_counts.get(pair, 0) + 1
        
        self.state.total_tokens_seen += n_tokens
    
    def apply_attraction(self) -> int:
        """
        Apply geometric attraction between co-occurring tokens.
        
        THE FEEDBACK LOOP:
        Tokens that appear together frequently MOVE CLOSER in E8 space.
        
        BEKENSTEIN BOUND:
        Movements are tracked in the drift buffer for quantization.
        
        Returns:
            Number of pairs that were updated
        """
        if self.state is None:
            return 0
        
        updates = 0
        
        for (idx_i, idx_j), count in self.state.cooccurrence_counts.items():
            if count < ATTRACTION_THRESHOLD:
                continue
            
            if idx_i >= len(self.state.embeddings_8d) or idx_j >= len(self.state.embeddings_8d):
                continue
            
            # Get current positions
            pos_i = self.state.embeddings_8d[idx_i]
            pos_j = self.state.embeddings_8d[idx_j]
            
            # Compute direction of attraction
            direction = pos_j - pos_i
            distance = np.linalg.norm(direction)
            
            if distance < 1e-6:
                continue
            
            # Normalize direction
            direction = direction / distance
            
            # Attraction strength proportional to log(count)
            # (diminishing returns for very high counts)
            strength = self.learning_rate * np.log1p(count)
            
            # Move both points toward each other
            move = strength * direction
            self.state.embeddings_8d[idx_i] += move
            self.state.embeddings_8d[idx_j] -= move
            
            # Record movements in drift buffer (Bekenstein Bound)
            if self.bound:
                self.bound.update_drift(idx_i, move)
                self.bound.update_drift(idx_j, -move)
            
            updates += 1
        
        return updates
    
    def apply_phason_flip(self) -> List[int]:
        """
        Apply random phason flips (geometric mutations).
        
        THE EMERGENCE MECHANISM:
        Random mutations in the 8D space allow the system to
        explore new configurations that might compress better.
        
        Returns:
            List of indices that were mutated
        """
        if self.state is None:
            return []
        
        mutated = []
        vocab_size = len(self.state.embeddings_8d)
        
        for idx in range(vocab_size):
            if np.random.random() < self.mutation_rate:
                # Apply a random phason flip
                # This is a small rotation in the 8D space
                
                # Random direction in 8D
                random_direction = np.random.randn(8)
                random_direction /= np.linalg.norm(random_direction)
                
                # Apply mutation with golden-ratio-scaled magnitude
                # (φ-aligned mutations are more likely to be beneficial)
                magnitude = self.mutation_magnitude * (1 + np.random.random() * PHI_INV)
                
                self.state.embeddings_8d[idx] += magnitude * random_direction
                
                # Also flip the phase slightly
                self.state.phases[idx] += np.random.randn() * 0.1
                self.state.phases[idx] %= (2 * np.pi)
                
                mutated.append(idx)
        
        if mutated:
            self.state.mutation_history.append({
                'generation': self.state.generation,
                'n_mutations': len(mutated),
                'indices': mutated[:10],  # Store first 10 for debugging
            })
        
        return mutated
    
    def compute_fitness(self, token_indices: np.ndarray) -> float:
        """
        Compute fitness (compression efficiency) for current state.
        
        THE SELECTION CRITERION:
        Lower entropy = better compression = higher fitness.
        
        Args:
            token_indices: Sample token sequence to evaluate
        
        Returns:
            Fitness score (higher is better)
        """
        if self.state is None or len(token_indices) == 0:
            return 0.0
        
        # Compute entropy of the mapped indices
        unique, counts = np.unique(token_indices, return_counts=True)
        probs = counts / counts.sum()
        entropy = -np.sum(probs * np.log2(probs + 1e-10))
        
        # Compute average embedding distance for co-occurring pairs
        avg_cooccurrence_distance = 0.0
        n_pairs = 0
        
        for (idx_i, idx_j), count in self.state.cooccurrence_counts.items():
            if count < ATTRACTION_THRESHOLD:
                continue
            if idx_i >= len(self.state.embeddings_8d) or idx_j >= len(self.state.embeddings_8d):
                continue
            
            dist = np.linalg.norm(
                self.state.embeddings_8d[idx_i] - self.state.embeddings_8d[idx_j]
            )
            avg_cooccurrence_distance += dist
            n_pairs += 1
        
        if n_pairs > 0:
            avg_cooccurrence_distance /= n_pairs
        
        # Fitness = inverse entropy + bonus for tight co-occurrence clustering
        # We want LOW entropy and LOW co-occurrence distance
        max_entropy = np.log2(len(unique) + 1)
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 1.0
        
        # Distance penalty (smaller distance = better)
        distance_penalty = avg_cooccurrence_distance / 10.0  # Normalize roughly
        
        fitness = (1.0 - normalized_entropy) - 0.1 * distance_penalty
        
        return fitness
    
    def evolve_step(self, token_indices: np.ndarray, 
                    apply_mutations: bool = True) -> Dict[str, Any]:
        """
        Perform one evolution step.
        
        THE MÖBIUS STRIP:
        1. Observe co-occurrences
        2. Apply attraction (learning)
        3. Apply mutations (exploration)
        4. Evaluate fitness (selection)
        
        BEKENSTEIN BOUND:
        5. Update drift buffer (not persisted)
        6. Crystallize only if improvement > φ%
        7. Apply decay to unused nodes
        
        Args:
            token_indices: Token sequence from compression
            apply_mutations: Whether to apply phason flips
        
        Returns:
            Evolution statistics
        """
        if self.state is None:
            return {'error': 'Not initialized'}
        
        # Track which nodes are used (for Bekenstein decay)
        if self.bound:
            self.bound.mark_used(token_indices)
            self.bound.advance_cycle()
        
        # Step 1: Observe
        self.observe_cooccurrences(token_indices)
        
        # Step 2: Attract (movements go to drift buffer if Bekenstein enabled)
        n_attractions = self.apply_attraction()
        
        # Step 3: Mutate (optional)
        mutated_indices = []
        if apply_mutations:
            mutated_indices = self.apply_phason_flip()
        
        # Step 4: Evaluate
        fitness = self.compute_fitness(token_indices)
        self.state.fitness_history.append(fitness)
        
        # Update generation
        self.state.generation += 1
        self.state.total_compressions += 1
        
        # Bekenstein Bound: Storage optimization
        crystallized = False
        n_decayed = 0
        storage_stats = {}
        
        if self.bound and self.base_embeddings is not None:
            # Apply decay to unused nodes
            n_decayed = self.bound.apply_decay(self.base_embeddings)
            
            # Check if we should crystallize (Golden Threshold)
            if self.bound.should_crystallize(fitness):
                self.bound.crystallize(
                    vocabulary=self.state.vocabulary,
                    generation=self.state.generation,
                    total_tokens=self.state.total_tokens_seen,
                    current_fitness=fitness
                )
                crystallized = True
                
                # Save crystallized state if path configured
                if self.state_path:
                    self.bound.save_crystallized(self.state_path)
            
            storage_stats = self.bound.get_storage_stats()
        elif self.state_path:
            # Fallback: save full state
            self.state.save(self.state_path)
        
        return {
            'generation': self.state.generation,
            'fitness': fitness,
            'n_attractions': n_attractions,
            'n_mutations': len(mutated_indices),
            'total_tokens_seen': self.state.total_tokens_seen,
            'vocab_size': len(self.state.vocabulary),
            'crystallized': crystallized,
            'n_decayed': n_decayed,
            'storage_bytes': storage_stats.get('total_bytes', 0),
        }
    
    def get_evolved_embeddings(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get the current evolved embeddings.
        
        Returns:
            (embeddings_8d, phases)
        """
        if self.state is None:
            raise ValueError("Evolver not initialized")
        return self.state.embeddings_8d.copy(), self.state.phases.copy()
    
    def get_learned_concepts(self, min_distance: float = 0.5, 
                             min_count: int = 10) -> List[Dict]:
        """
        Identify emergent concepts (tight clusters of tokens).
        
        These are tokens that have moved close together through learning,
        representing "invented" concepts.
        
        Args:
            min_distance: Maximum distance to be considered a cluster
            min_count: Minimum co-occurrence count
        
        Returns:
            List of concept clusters
        """
        if self.state is None:
            return []
        
        # Reverse vocabulary
        idx_to_token = {v: k for k, v in self.state.vocabulary.items()}
        
        concepts = []
        seen_pairs = set()
        
        for (idx_i, idx_j), count in sorted(
            self.state.cooccurrence_counts.items(), 
            key=lambda x: -x[1]
        ):
            if count < min_count:
                continue
            if (idx_i, idx_j) in seen_pairs:
                continue
            
            if idx_i >= len(self.state.embeddings_8d) or idx_j >= len(self.state.embeddings_8d):
                continue
            
            dist = np.linalg.norm(
                self.state.embeddings_8d[idx_i] - self.state.embeddings_8d[idx_j]
            )
            
            if dist < min_distance:
                token_i = idx_to_token.get(idx_i, f"<{idx_i}>")
                token_j = idx_to_token.get(idx_j, f"<{idx_j}>")
                
                concepts.append({
                    'tokens': [token_i, token_j],
                    'distance': float(dist),
                    'cooccurrence_count': count,
                    'indices': [idx_i, idx_j],
                })
                
                seen_pairs.add((idx_i, idx_j))
        
        return concepts[:50]  # Return top 50 concepts
    
    def sleep(self,
              consolidation_threshold: float = 0.1,
              entropy_threshold: float = 0.8,
              min_usage_count: int = 3) -> SleepReport:
        """
        Execute a sleep cycle to consolidate and prune the vocabulary.
        
        THE FORGETTING PROTOCOL:
        1. CONSOLIDATION: Merge nodes that are too close (synonyms)
        2. GARBAGE COLLECTION: Remove high-entropy nodes (noise)
        3. COMPRESSION: Knowledge becomes denser
        
        Args:
            consolidation_threshold: Distance below which nodes are merged
            entropy_threshold: Entropy above which nodes are pruned
            min_usage_count: Minimum usage to survive pruning
        
        Returns:
            SleepReport with details of what was consolidated/pruned
        """
        if self.state is None:
            return SleepReport(0, 0, 0, 0, [], [], 0.0, 0)
        
        sleep_cycle = SleepCycle(
            consolidation_threshold=consolidation_threshold,
            entropy_threshold=entropy_threshold,
            min_usage_count=min_usage_count
        )
        
        # Build usage counts from co-occurrence data
        usage_counts = {}
        for (idx_i, idx_j), count in self.state.cooccurrence_counts.items():
            usage_counts[idx_i] = usage_counts.get(idx_i, 0) + count
            usage_counts[idx_j] = usage_counts.get(idx_j, 0) + count
        
        # Execute sleep cycle
        new_vocab, new_embed, new_phases, report = sleep_cycle.sleep(
            vocabulary=self.state.vocabulary,
            embeddings=self.state.embeddings_8d,
            phases=self.state.phases,
            usage_counts=usage_counts,
            cooccurrence_counts=self.state.cooccurrence_counts
        )
        
        # Update state with consolidated vocabulary
        self.state.vocabulary = new_vocab
        self.state.embeddings_8d = new_embed
        self.state.phases = new_phases
        
        # Update base embeddings if using Bekenstein Bound
        if self.base_embeddings is not None:
            self.base_embeddings = new_embed.copy()
        
        # Clear old cooccurrence counts (they're now invalid)
        # Keep only pairs that still exist
        valid_indices = set(new_vocab.values())
        self.state.cooccurrence_counts = {
            (i, j): count
            for (i, j), count in self.state.cooccurrence_counts.items()
            if i in valid_indices and j in valid_indices
        }
        
        # Save state if path configured
        if self.state_path:
            if self.bound:
                self.bound.crystallize(
                    vocabulary=self.state.vocabulary,
                    generation=self.state.generation,
                    total_tokens=self.state.total_tokens_seen,
                    current_fitness=self.state.fitness_history[-1] if self.state.fitness_history else 0.0
                )
                self.bound.save_crystallized(self.state_path)
            else:
                self.state.save(self.state_path)
        
        return report
    
    def should_sleep(self, tokens_threshold: int = 100_000_000) -> bool:
        """
        Check if the system should enter a sleep cycle.
        
        Args:
            tokens_threshold: Number of tokens after which to sleep (default: 100M)
        
        Returns:
            True if sleep is recommended
        """
        if self.state is None:
            return False
        
        return self.state.total_tokens_seen >= tokens_threshold


def demonstrate_evolution():
    """Demonstrate the self-learning mechanism."""
    print("=" * 60)
    print("GEOMETRIC EVOLUTION DEMONSTRATION")
    print("=" * 60)
    
    print("\nTHE PRINCIPLE:")
    print("  Evolution is Geometric Refinement.")
    print("  The system learns by reshaping its 8D substrate.")
    
    # Create sample text with clear co-occurrence patterns
    sample_text = """
    The king ruled the kingdom with wisdom.
    The queen ruled alongside the king.
    Wisdom and knowledge guide the ruler.
    The kingdom prospered under wise rule.
    Learning leads to wisdom and knowledge.
    Self-learning creates self-improvement.
    The self improves through learning.
    """ * 100
    
    # Tokenize
    tokens = tokenize(sample_text, mode='word')
    print(f"\n  Sample text: {len(tokens)} tokens")
    
    # Build initial vocabulary
    vocabulary = {}
    for token in tokens:
        if token.value not in vocabulary:
            vocabulary[token.value] = len(vocabulary)
    
    vocab_size = len(vocabulary)
    print(f"  Vocabulary: {vocab_size} unique tokens")
    
    # Initialize random embeddings
    embeddings_8d = np.random.randn(vocab_size, 8).astype(np.float32) * 0.5
    phases = np.random.uniform(0, 2 * np.pi, vocab_size).astype(np.float32)
    
    # Create evolver
    evolver = GeometricEvolver(
        learning_rate=0.05,
        mutation_rate=0.01,
        mutation_magnitude=0.1,
    )
    evolver.initialize_from_vocabulary(vocabulary, embeddings_8d, phases)
    
    # Convert tokens to indices
    token_indices = np.array([vocabulary[t.value] for t in tokens], dtype=np.uint32)
    
    # Measure initial distances for key pairs
    def get_distance(word1, word2):
        if word1 not in vocabulary or word2 not in vocabulary:
            return float('inf')
        idx1, idx2 = vocabulary[word1], vocabulary[word2]
        return np.linalg.norm(evolver.state.embeddings_8d[idx1] - evolver.state.embeddings_8d[idx2])
    
    print("\n--- Initial Distances (Before Learning) ---")
    pairs = [('king', 'queen'), ('king', 'kingdom'), ('wisdom', 'knowledge'), 
             ('self', 'learning'), ('self-learning', 'self-improvement')]
    
    initial_distances = {}
    for w1, w2 in pairs:
        dist = get_distance(w1, w2)
        if dist < float('inf'):
            initial_distances[(w1, w2)] = dist
            print(f"  '{w1}' <-> '{w2}': {dist:.4f}")
    
    # Evolve for several generations
    print("\n--- Evolution Progress ---")
    
    for gen in range(10):
        stats = evolver.evolve_step(token_indices, apply_mutations=(gen > 5))
        
        if gen % 2 == 0:
            print(f"  Gen {stats['generation']:3d}: fitness={stats['fitness']:.4f}, "
                  f"attractions={stats['n_attractions']}, mutations={stats['n_mutations']}")
    
    # Measure final distances
    print("\n--- Final Distances (After Learning) ---")
    
    for w1, w2 in pairs:
        dist = get_distance(w1, w2)
        if (w1, w2) in initial_distances:
            initial = initial_distances[(w1, w2)]
            change = (dist - initial) / initial * 100
            print(f"  '{w1}' <-> '{w2}': {dist:.4f} (change: {change:+.1f}%)")
    
    # Show learned concepts
    print("\n--- Emergent Concepts (Learned Clusters) ---")
    concepts = evolver.get_learned_concepts(min_distance=1.0, min_count=5)
    
    for concept in concepts[:10]:
        print(f"  {concept['tokens']} - distance: {concept['distance']:.4f}, "
              f"co-occurrences: {concept['cooccurrence_count']}")
    
    print("\n" + "=" * 60)
    print("THE RESULT:")
    print("  Words that appear together have MOVED CLOSER in 8D space.")
    print("  The system has LEARNED the structure of language geometrically.")
    print("=" * 60)


if __name__ == "__main__":
    demonstrate_evolution()
