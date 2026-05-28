//! XOR + popcount — AVX-512 when available, portable fallback.

#[cfg(all(target_arch = "x86_64", feature = "avx512"))]
pub fn popcount_xor(a: &[u8; super::HYPERVECTOR_BYTES], b: &[u8; super::HYPERVECTOR_BYTES]) -> u32 {
    use std::arch::x86_64::*;
    let mut total = 0u32;
    let chunks = super::HYPERVECTOR_BYTES / 64;
    unsafe {
        for i in 0..chunks {
            let off = i * 64;
            let va = _mm512_loadu_si512(a.as_ptr().add(off) as *const __m512i);
            let vb = _mm512_loadu_si512(b.as_ptr().add(off) as *const __m512i);
            let xored = _mm512_xor_si512(va, vb);
            total += _mm512_reduce_add_epi64(_mm512_popcnt_epi64(xored)) as u32;
        }
    }
    total
}

#[cfg(not(all(target_arch = "x86_64", feature = "avx512")))]
pub fn popcount_xor(a: &[u8; super::HYPERVECTOR_BYTES], b: &[u8; super::HYPERVECTOR_BYTES]) -> u32 {
    a.iter()
        .zip(b.iter())
        .map(|(x, y)| (x ^ y).count_ones())
        .sum()
}
