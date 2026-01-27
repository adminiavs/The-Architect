#pragma once

#include "types.hpp"
#include <array>

namespace gqe {

/**
 * Static 4x8 Coxeter Projection Matrix based on Python reference (projection.py)
 */
class CoxeterProjection {
public:
    struct ProjectedSpinor {
        std::array<double, 4> parallel;
        std::array<double, 4> phason;
        double phase;
    };

private:
    // P_parallel and P_perp from Python QR orthonormalization
    static constexpr std::array<std::array<double, 8>, 4> P_PARALLEL = {{
        { -0.57206140281768425, -0.35355339059327368, -0.21850801222441052, -0.0, 0.21850801222441052, 0.35355339059327368, 0.57206140281768425, -0.0 },
        { 0.051745149179713602, -0.45269394634495375, 0.20489396194844767, -0.29954513357621931, 0.27978024534250251, 0.45269394634495363, -0.53641935647066363, 0.29954513357621931 },
        { 0.071191227989355205, 0.27296686619922195, -0.57032684747502893, -0.36855120926516216, 0.49897621477363635, -0.27296686619922195, 0.00015940471203757314, 0.36855120926516216 },
        { 0.28577380332470403, -0.1105619625670379, -0.040824829046386346, -0.43716059493812826, -0.61237243569579458, 0.11056196256703779, 0.36742346141747678, 0.43716059493812831 }
    }};

    static constexpr std::array<std::array<double, 8>, 4> P_PERP = {{
        { 0.065638919247266198, 0.33126429585347578, 0.67442753313132564, -0.38693517851762765, 0.37003322618929585, 0.026869988911446034, 0.37003322618929602, -0.082540871575597821 },
        { 0.25372117120889331, 0.51774454976281192, -0.23270055543582036, 0.16939017872961573, 0.01051030788653641, 0.76095541308516867, 0.010510307886536605, -0.073820684592741131 },
        { 0.68706710404257543, -0.4030942928333997, -0.018077014234717317, 0.37205006165048088, 0.33449504490392912, -0.050522233694753116, 0.33449504490392923, 0.019478002511834291 },
        { -0.2063715761347, 0.20749185984534185, 0.27203769765226726, 0.51623659298299196, 0.032833060758783665, -0.031712777048141919, 0.032833060758783603, 0.75544122987647566 }
    }};

    static inline std::array<double, 4> multiply(const std::array<std::array<double, 8>, 4>& mat,
                                                 const float* vec8) {
        std::array<double, 4> out{};
        for (int row = 0; row < 4; ++row) {
            double sum = 0.0;
            for (int col = 0; col < 8; ++col) {
                sum += mat[row][col] * static_cast<double>(vec8[col]);
            }
            out[row] = sum;
        }
        return out;
    }

public:
    // Project 8D spinor to 4D parallel space
    static inline Vector4D project(const Spinor8D& spinor) {
        auto parallel = multiply(P_PARALLEL, spinor.pos);
        return Vector4D(
            static_cast<float>(parallel[0]),
            static_cast<float>(parallel[1]),
            static_cast<float>(parallel[2]),
            static_cast<float>(parallel[3])
        );
    }

    // Project 8D spinor to 4D parallel and phason space
    static inline ProjectedSpinor project_with_phason(const Spinor8D& spinor) {
        ProjectedSpinor result;
        result.parallel = multiply(P_PARALLEL, spinor.pos);
        result.phason = multiply(P_PERP, spinor.pos);
        result.phase = static_cast<double>(spinor.phase);
        return result;
    }

    /**
     * Reconstruct an 8D spinor from its parallel and phason components.
     * THE PHYSICS: v_8d = P_parallel^T * v_parallel + P_perp^T * v_phason
     */
    static inline Spinor8D inverse_projection_with_phason(const std::array<double, 4>& parallel,
                                                          const std::array<double, 4>& phason,
                                                          double phase = 0.0) {
        std::array<float, 8> pos8{};
        for (int col = 0; col < 8; ++col) {
            double sum = 0.0;
            for (int row = 0; row < 4; ++row) {
                sum += P_PARALLEL[row][col] * parallel[row];
                sum += P_PERP[row][col] * phason[row];
            }
            pos8[col] = static_cast<float>(sum);
        }
        return Spinor8D(pos8, static_cast<float>(phase));
    }
};

} // namespace gqe
