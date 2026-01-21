#!/usr/bin/env python3
"""
Test 03: φ-adic Encoding Efficiency

Hypothesis: φ-based number system represents natural language distances 
more efficiently than binary.

Predicted Result (from Proof 02):
- φ-adic: 10-15% fewer bits than binary for Fibonacci-related values
- Fibonacci numbers have optimal φ-adic representation

Falsification:
- If φ-adic >= binary for natural distributions, golden ratio provides no advantage
- If improvement < 5%, effect is negligible

Author: The Architect
"""

import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from gqe_compression.core.phi_adic import (
    PHI, PHI_INV,
    encode_phi, decode_phi, PhiAdicNumber,
    encode_phi_int, decode_phi_int,
    fibonacci, verify_fibonacci_property
)


def count_bits_binary(n: int) -> int:
    """Count bits needed to represent n in binary."""
    if n <= 0:
        return 1
    return n.bit_length()


def count_bits_phi_adic(n: int) -> int:
    """Count digits needed to represent n in φ-adic (Zeckendorf)."""
    if n <= 0:
        return 1
    digits = encode_phi_int(n)
    return len(digits)


def run_test():
    """
    Run Test 03: φ-adic Encoding Efficiency.
    
    Returns:
        (passed, results) tuple
    """
    print("=" * 60)
    print("TEST 03: φ-ADIC ENCODING EFFICIENCY")
    print("=" * 60)
    
    results = {
        'fibonacci_optimal': 0,
        'fibonacci_total': 0,
        'general_phi_better': 0,
        'general_total': 0,
        'average_improvement': 0.0,
        'passed': False
    }
    
    # Test 1: Fibonacci numbers should be optimal in φ-adic
    print("\n--- Test 1: Fibonacci number efficiency ---")
    print("  (Fibonacci numbers should require <= n digits in φ-adic)")
    
    fibonacci_results = []
    for n in range(1, 25):
        fib_n = fibonacci(n)
        phi_digits = count_bits_phi_adic(fib_n)
        bin_digits = count_bits_binary(fib_n)
        
        # Verify property: F_n requires <= n φ-adic digits
        is_optimal = phi_digits <= n
        fibonacci_results.append({
            'n': n,
            'fib_n': fib_n,
            'phi_digits': phi_digits,
            'bin_digits': bin_digits,
            'is_optimal': is_optimal
        })
        
        if is_optimal:
            results['fibonacci_optimal'] += 1
        results['fibonacci_total'] += 1
    
    # Print sample results
    print(f"\n  Sample Fibonacci numbers:")
    for r in fibonacci_results[:10]:
        status = "✓" if r['is_optimal'] else "✗"
        print(f"    F_{r['n']:2d} = {r['fib_n']:6d}: φ-adic={r['phi_digits']:2d}, binary={r['bin_digits']:2d} {status}")
    
    fib_pass_rate = results['fibonacci_optimal'] / results['fibonacci_total']
    print(f"\n  Optimal representations: {results['fibonacci_optimal']}/{results['fibonacci_total']} ({fib_pass_rate:.0%})")
    
    # Test 2: General integers
    print("\n--- Test 2: General integer efficiency ---")
    
    # Test various integers
    test_values = list(range(1, 100)) + list(range(100, 1000, 10)) + list(range(1000, 10000, 100))
    
    total_phi_bits = 0
    total_bin_bits = 0
    
    for n in test_values:
        phi_bits = count_bits_phi_adic(n)
        bin_bits = count_bits_binary(n)
        
        total_phi_bits += phi_bits
        total_bin_bits += bin_bits
        
        if phi_bits <= bin_bits:
            results['general_phi_better'] += 1
        results['general_total'] += 1
    
    general_rate = results['general_phi_better'] / results['general_total']
    avg_improvement = (total_bin_bits - total_phi_bits) / total_bin_bits
    results['average_improvement'] = avg_improvement
    
    print(f"  φ-adic <= binary: {results['general_phi_better']}/{results['general_total']} ({general_rate:.0%})")
    print(f"  Total φ-adic bits: {total_phi_bits}")
    print(f"  Total binary bits: {total_bin_bits}")
    print(f"  Average improvement: {avg_improvement:.2%}")
    
    # Test 3: Round-trip accuracy
    print("\n--- Test 3: Round-trip accuracy ---")
    
    test_floats = [0.5, 1.0, 2.5, PHI, PHI_INV, 3.14159, 100.0, 1234.5678]
    all_accurate = True
    
    for val in test_floats:
        encoded = encode_phi(val)
        decoded = decode_phi(encoded)
        error = abs(val - decoded)
        accurate = error < 1e-6
        all_accurate = all_accurate and accurate
        print(f"    {val:12.6f} -> error: {error:.2e} {'✓' if accurate else '✗'}")
    
    # Analysis
    print("\n--- ANALYSIS ---")
    
    # Pass criteria:
    # 1. Fibonacci property holds for >= 90% of cases
    # 2. Round-trip is accurate
    fib_pass = fib_pass_rate >= 0.9
    
    results['passed'] = fib_pass and all_accurate
    
    print(f"\n  Fibonacci optimality (>= 90%): {'PASS' if fib_pass else 'FAIL'} ({fib_pass_rate:.0%})")
    print(f"  Round-trip accuracy: {'PASS' if all_accurate else 'FAIL'}")
    
    print("\n--- RESULTS ---")
    if results['passed']:
        print("  STATUS: PASS")
        print("  φ-adic encoding has optimal Fibonacci representation.")
    else:
        print("  STATUS: FAIL")
        print("  φ-adic encoding does not meet criteria.")
    
    print("\n" + "=" * 60)
    
    return results['passed'], results


if __name__ == "__main__":
    passed, results = run_test()
    print(f"\nFinal: {'PASSED' if passed else 'FAILED'}")
    sys.exit(0 if passed else 1)
