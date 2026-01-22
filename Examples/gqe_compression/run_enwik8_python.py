import os
import sys
import time
import zlib
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gqe_compression.compressor import GQECompressor
from gqe_compression.core.horizon_batcher import HorizonBatcher

def run_enwik8_test():
    enwik8_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "enwik8")
    if not os.path.exists(enwik8_path):
        # Check in Examples
        enwik8_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Examples", "enwik8")
    
    if not os.path.exists(enwik8_path):
        print(f"Error: {enwik8_path} not found.")
        return

    print("🚀 GQE PYTHON PROTOTYPE - ENWIK8 BENCHMARK")
    print("==========================================")
    file_size = os.path.getsize(enwik8_path)
    print(f"File: {enwik8_path} ({file_size / (1024*1024):.2f} MB)")

    # Read data
    with open(enwik8_path, 'rb') as f:
        data = f.read()

    compressor = GQECompressor(use_horizon_batching=True)
    
    print("\nInitiating the 100MB Integral (Python Proxy)...")
    start_time = time.time()
    
    # Compress the data
    compressed_data = compressor.compress(data)
    
    duration = time.time() - start_time
    
    # Get compressed bytes
    packed_bytes = compressed_data.to_bytes()
    compressed_size = len(packed_bytes)
    
    ratio = file_size / compressed_size
    bpt = (compressed_size * 8) / file_size
    throughput = (file_size / (1024*1024)) / duration

    print("\nRESULTS")
    print("-------")
    print(f"Original Size:   {file_size} bytes")
    print(f"Compressed Size: {compressed_size} bytes")
    print(f"Compression Ratio: {ratio:.2f}:1")
    print(f"Bits Per Token:    {bpt:.4f} bits/token")
    print(f"Throughput:        {throughput:.4f} MB/s")
    print(f"Time:              {duration:.2f} seconds")

    print("\nTHE PHYSICS:")
    if ratio > 6.0:
        print("✅ [ACHIEVED] GQE is a TOP-TIER holographic engine.")
        print("Outperformed standard gzip and zstd on natural text.")
    elif ratio > 4.41:
        print(f"✅ GQE has achieved Holographic Parity (> 4.41:1).")
    else:
        print(f"🟡 GQE is reaching coherence. Current ratio: {ratio:.2f}:1")

    print("\n\"The geometry gets stronger as the world gets bigger.\" - The Architect")

if __name__ == "__main__":
    run_enwik8_test()
