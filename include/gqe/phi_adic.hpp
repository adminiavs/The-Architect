#pragma once

#include "constants.hpp"
#include <vector>
#include <cmath>
#include <algorithm>
#include <cstdint>

namespace gqe {

/**
 * THE PHYSICS: Phi-adic Number System (Base-Phi)
 * Uses the Zeckendorf representation where no two consecutive 1s appear.
 */
class PhiAdicNumber {
public:
    std::vector<int8_t> digits;           // Integer part: d_0, d_1, ... (phi^0, phi^1, ...)
    std::vector<int8_t> fractional_digits; // Fractional part: d_-1, d_-2, ... (phi^-1, phi^-2, ...)
    bool negative;

    PhiAdicNumber() : negative(false) {}

    float to_float() const {
        float value = 0.0f;
        
        // Integer part uses Fibonacci numbers (Zeckendorf)
        std::vector<float> fibs = {1.0f, 2.0f};
        while (fibs.size() < digits.size()) {
            fibs.push_back(fibs.back() + fibs[fibs.size() - 2]);
        }

        for (size_t i = 0; i < digits.size(); ++i) {
            if (digits[i]) value += fibs[i];
        }

        // Fractional part uses negative powers of phi
        float power = 1.0f / PHI;
        for (size_t i = 0; i < fractional_digits.size(); ++i) {
            if (fractional_digits[i]) value += power;
            power /= PHI;
        }

        return negative ? -value : value;
    }

    // Zeckendorf normalization (no consecutive 1s)
    void normalize() {
        bool changed = true;
        while (changed) {
            changed = false;
            
            // Handle consecutive 1s: phi^n + phi^(n+1) = phi^(n+2)
            for (size_t i = 0; i + 1 < digits.size(); ++i) {
                if (digits[i] == 1 && digits[i+1] == 1) {
                    digits[i] = 0;
                    digits[i+1] = 0;
                    if (i + 2 >= digits.size()) digits.push_back(0);
                    digits[i+2]++;
                    changed = true;
                }
            }
            
            // Handle digits > 1
            for (size_t i = 0; i < digits.size(); ++i) {
                while (digits[i] > 1) {
                    digits[i] -= 2;
                    if (i + 2 >= digits.size()) digits.push_back(0);
                    digits[i+2]++;
                    if (i > 0) digits[i-1]++;
                    else {
                        // Carry to fractional part if needed (simplified)
                    }
                    changed = true;
                }
            }
        }
        
        // Remove trailing zeros
        while (digits.size() > 1 && digits.back() == 0) digits.pop_back();
    }

    static PhiAdicNumber encode(float n, int max_precision = 32) {
        PhiAdicNumber res;
        res.negative = n < 0;
        n = std::abs(n);

        int int_part = static_cast<int>(n);
        float frac_part = n - int_part;

        // Encode integer part (Greedy Fibonacci)
        if (int_part > 0) {
            std::vector<int> fibs = {1, 2};
            while (fibs.back() < int_part) {
                fibs.push_back(fibs.back() + fibs[fibs.size() - 2]);
            }
            res.digits.resize(fibs.size(), 0);
            for (int i = fibs.size() - 1; i >= 0; --i) {
                if (fibs[i] <= int_part) {
                    res.digits[i] = 1;
                    int_part -= fibs[i];
                }
            }
        } else {
            res.digits = {0};
        }

        // Encode fractional part
        float power = 1.0f / PHI;
        for (int i = 0; i < max_precision; ++i) {
            if (frac_part < 1e-7f) break;
            if (frac_part >= power - 1e-7f) {
                res.fractional_digits.push_back(1);
                frac_part -= power;
            } else {
                res.fractional_digits.push_back(0);
            }
            power /= PHI;
        }

        return res;
    }
};

} // namespace gqe
