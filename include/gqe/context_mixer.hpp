#pragma once

#include "types.hpp"
#include "constants.hpp"
#include "bekenstein_arena.hpp"
#include <array>
#include <vector>
#include <algorithm>
#include <execution>
#include <numeric>

namespace gqe {

/**
 * THE PHYSICS: Geometric Parallel Mixer - Context-aware geometric operations.
 *
 * This mixer performs parallel geometric transformations that respect:
 * - Golden ratio weighting (φ-based attention)
 * - Fibonacci sequence iteration patterns
 * - Entropic gravity constraints
 * - Holographic coherence principles
 */

class GeometricContextMixer {
public:
    using MixWeights = std::array<float, FIB_8>;  // 8 attention weights
    using ContextVector = std::array<float, FIB_13>; // 13-dimensional context

    struct MixResult {
        Vector8D primary_output;
        std::array<Vector8D, FIB_5> parallel_outputs; // 5 parallel streams
        float coherence_score;
        float entropy_reduction;
    };

private:
    // Golden ratio attention weights (φ^n scaling)
    static constexpr MixWeights GOLDEN_WEIGHTS = {
        1.0f / PHI,        // φ⁻¹ ≈ 0.618
        1.0f,              // φ⁰ = 1.0
        PHI,               // φ¹ ≈ 1.618
        PHI * PHI,         // φ² ≈ 2.618
        PHI * PHI * PHI,   // φ³ ≈ 4.236
        PHI * PHI * PHI * PHI,     // φ⁴ ≈ 6.854
        PHI * PHI * PHI * PHI * PHI, // φ⁵ ≈ 11.090
        PHI * PHI * PHI * PHI * PHI * PHI  // φ⁶ ≈ 17.944
    };

    BekensteinArena& arena_;
    FibonacciBuffer<FIB_21> context_buffer_; // 2MB coherent buffer

public:
    GeometricContextMixer(BekensteinArena& arena) : arena_(arena) {}

    /**
     * Mix multiple geometric contexts using golden ratio weighting
     */
    MixResult mix_contexts(const std::vector<Vector8D>& contexts,
                          const ContextVector& global_context = {}) {

        EntropyFreeScope entropy_guard(arena_); // No allocations during mixing

        MixResult result{};
        size_t num_contexts = contexts.size();

        if (num_contexts == 0) {
            result.coherence_score = 0.0f;
            result.entropy_reduction = 0.0f;
            return result;
        }

        // Allocate temporary workspace from Fibonacci buffer
        auto* weights = context_buffer_.allocate<float>(num_contexts);
        auto* temp_vectors = context_buffer_.allocate<Vector8D>(FIB_5);

        // Compute golden ratio weights for each context
        compute_attention_weights(weights, num_contexts, global_context);

        // Perform geometric mixing with parallel streams
        mix_geometric_streams(contexts, weights, temp_vectors, result);

        // Compute coherence and entropy metrics
        result.coherence_score = compute_coherence_score(contexts, result.primary_output);
        result.entropy_reduction = compute_entropy_reduction(contexts, result.primary_output);

        context_buffer_.reset(); // Clean up for next operation

        return result;
    }

    /**
     * Parallel geometric transformation with Fibonacci iteration
     */
    std::vector<Vector8D> transform_geometric_batch(
        const std::vector<Vector8D>& inputs,
        const std::array<std::function<Vector8D(const Vector8D&)>, FIB_3>& transforms) {

        EntropyFreeScope entropy_guard(arena_);

        std::vector<Vector8D> outputs(inputs.size());

        // Fibonacci iteration pattern (1, 2, 3, 5, 8, 13...)
        std::array<size_t, FIB_5> iteration_counts = {FIB_1, FIB_2, FIB_3, FIB_5, FIB_8};

        // Parallel transformation with golden ratio scheduling
        std::transform(std::execution::par_unseq,
                      inputs.begin(), inputs.end(),
                      outputs.begin(),
                      [this, &transforms, &iteration_counts](const Vector8D& input) {
                          return apply_fibonacci_transforms(input, transforms, iteration_counts);
                      });

        return outputs;
    }

private:
    /**
     * Compute attention weights using golden ratio scaling
     */
    void compute_attention_weights(float* weights, size_t num_contexts,
                                  const ContextVector& global_context) {

        // Base weights using golden ratio powers
        for (size_t i = 0; i < num_contexts && i < GOLDEN_WEIGHTS.size(); ++i) {
            weights[i] = GOLDEN_WEIGHTS[i % GOLDEN_WEIGHTS.size()];
        }

        // Modulate by global context if provided
        if (!global_context.empty()) {
            float context_norm = std::sqrt(std::inner_product(
                global_context.begin(), global_context.end(),
                global_context.begin(), 0.0f));

            if (context_norm > 0.0f) {
                float context_factor = PHI_INV / (1.0f + context_norm); // Normalized modulation
                for (size_t i = 0; i < num_contexts; ++i) {
                    weights[i] *= (1.0f + context_factor);
                }
            }
        }

        // Normalize weights
        float weight_sum = std::accumulate(weights, weights + num_contexts, 0.0f);
        if (weight_sum > 0.0f) {
            float norm_factor = 1.0f / weight_sum;
            for (size_t i = 0; i < num_contexts; ++i) {
                weights[i] *= norm_factor;
            }
        }
    }

    /**
     * Mix geometric streams using weighted combination
     */
    void mix_geometric_streams(const std::vector<Vector8D>& contexts,
                              const float* weights,
                              Vector8D* temp_vectors,
                              MixResult& result) {

        // Primary output: weighted sum
        result.primary_output = {0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f};
        for (size_t i = 0; i < contexts.size(); ++i) {
            for (int j = 0; j < 8; ++j) {
                result.primary_output.data[j] += contexts[i].data[j] * weights[i];
            }
        }

        // Parallel outputs: different geometric projections
        for (int stream = 0; stream < FIB_5; ++stream) {
            float phase = 2.0f * M_PI * stream / FIB_5; // Golden angle spacing

            for (int j = 0; j < 8; ++j) {
                float weighted_sum = 0.0f;
                for (size_t i = 0; i < contexts.size(); ++i) {
                    // Apply phase rotation for each parallel stream
                    float rotated_weight = weights[i] * std::cos(phase + j * PHI_INV);
                    weighted_sum += contexts[i].data[j] * rotated_weight;
                }
                result.parallel_outputs[stream].data[j] = weighted_sum;
            }
        }
    }

    /**
     * Apply Fibonacci-pattern transforms to a single vector
     */
    Vector8D apply_fibonacci_transforms(
        const Vector8D& input,
        const std::array<std::function<Vector8D(const Vector8D&)>, FIB_3>& transforms,
        const std::array<size_t, FIB_5>& iteration_counts) {

        Vector8D current = input;

        // Apply each transform with Fibonacci iteration counts
        for (int t = 0; t < FIB_3; ++t) {  // 3 transforms
            for (size_t iter = 0; iter < iteration_counts[t % FIB_5]; ++iter) {
                current = transforms[t](current);
            }
        }

        return current;
    }

    /**
     * Compute coherence score between inputs and output
     */
    float compute_coherence_score(const std::vector<Vector8D>& inputs,
                                 const Vector8D& output) {

        if (inputs.empty()) return 0.0f;

        float total_coherence = 0.0f;
        for (const auto& input : inputs) {
            float dot_product = 0.0f;
            float input_norm_sq = 0.0f;
            float output_norm_sq = 0.0f;

            for (int i = 0; i < 8; ++i) {
                dot_product += input.data[i] * output.data[i];
                input_norm_sq += input.data[i] * input.data[i];
                output_norm_sq += output.data[i] * output.data[i];
            }

            if (input_norm_sq > 0.0f && output_norm_sq > 0.0f) {
                float cosine_sim = dot_product / std::sqrt(input_norm_sq * output_norm_sq);
                total_coherence += std::max(0.0f, cosine_sim); // Only positive coherence
            }
        }

        return total_coherence / inputs.size();
    }

    /**
     * Compute entropy reduction achieved by mixing
     */
    float compute_entropy_reduction(const std::vector<Vector8D>& inputs,
                                   const Vector8D& output) {

        // Entropy of output distribution
        float output_entropy = 0.0f;
        float output_norm_sq = 0.0f;
        for (float x : output.data) {
            output_norm_sq += x * x;
        }

        if (output_norm_sq > 0.0f) {
            for (float x : output.data) {
                if (x != 0.0f) {
                    float p = (x * x) / output_norm_sq;
                    output_entropy -= p * std::log2(p);
                }
            }
        }

        // Average entropy of inputs
        float avg_input_entropy = 0.0f;
        for (const auto& input : inputs) {
            float input_entropy = 0.0f;
            float input_norm_sq = 0.0f;
            for (float x : input.data) {
                input_norm_sq += x * x;
            }

            if (input_norm_sq > 0.0f) {
                for (float x : input.data) {
                    if (x != 0.0f) {
                        float p = (x * x) / input_norm_sq;
                        input_entropy -= p * std::log2(p);
                    }
                }
            }
            avg_input_entropy += input_entropy;
        }
        avg_input_entropy /= inputs.size();

        // Entropy reduction (positive = more ordered)
        return avg_input_entropy - output_entropy;
    }
};

} // namespace gqe