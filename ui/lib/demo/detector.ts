// In-browser port of the REAL acoustic detector (node-agent/sensors/acoustic.py).
// The DEMO feeds SYNTHETIC audio through THIS code — the same harmonic-comb / spectral-flatness
// logic that runs on hardware — so the confidences are produced by the actual algorithm, not
// hand-drawn. It is a SIMULATED SCENARIO (synthetic input), labeled as such in the UI.
//
// Feature values are all ratios (harmonic energy / total, geometric/arithmetic mean, band / total),
// so they are invariant to FFT normalization — this keeps parity with the numpy implementation.

const F0_MIN_HZ = 40;
const F0_MAX_HZ = 260;
const N_HARMONICS = 6;

export interface AcousticFeatures {
  harmonic_comb: number;
  harmonics_present: number;
  fundamental_hz: number;
  spectral_flatness: number;
  broadband_rotor: number;
  rms: number;
}

// ---- iterative radix-2 Cooley-Tukey FFT (in-place) ----
function fft(re: Float64Array, im: Float64Array): void {
  const n = re.length;
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) {
      [re[i], re[j]] = [re[j], re[i]];
      [im[i], im[j]] = [im[j], im[i]];
    }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const ang = (-2 * Math.PI) / len;
    const wpr = Math.cos(ang);
    const wpi = Math.sin(ang);
    for (let i = 0; i < n; i += len) {
      let wr = 1;
      let wi = 0;
      for (let k = 0; k < len / 2; k++) {
        const a = i + k;
        const b = i + k + len / 2;
        const tr = wr * re[b] - wi * im[b];
        const ti = wr * im[b] + wi * re[b];
        re[b] = re[a] - tr;
        im[b] = im[a] - ti;
        re[a] += tr;
        im[a] += ti;
        const nwr = wr * wpr - wi * wpi;
        wi = wr * wpi + wi * wpr;
        wr = nwr;
      }
    }
  }
}

function nextPow2(n: number): number {
  let p = 1;
  while (p < n) p <<= 1;
  return p;
}

// Return { freqs, psd } for the real one-sided spectrum, with a Hann window.
export function powerSpectrum(x: Float64Array, sr: number): { freqs: Float64Array; psd: Float64Array } {
  const N = nextPow2(x.length);
  const re = new Float64Array(N);
  const im = new Float64Array(N);
  let mean = 0;
  for (let i = 0; i < x.length; i++) mean += x[i];
  mean /= x.length;
  for (let i = 0; i < x.length; i++) {
    const w = 0.5 - 0.5 * Math.cos((2 * Math.PI * i) / (x.length - 1)); // Hann
    re[i] = (x[i] - mean) * w;
  }
  fft(re, im);
  const half = N / 2;
  const psd = new Float64Array(half + 1);
  const freqs = new Float64Array(half + 1);
  for (let k = 0; k <= half; k++) {
    psd[k] = re[k] * re[k] + im[k] * im[k];
    freqs[k] = (k * sr) / N;
  }
  return { freqs, psd };
}

export function spectralFlatness(psd: Float64Array): number {
  let logSum = 0;
  let arithSum = 0;
  const n = psd.length;
  for (let i = 0; i < n; i++) {
    const p = psd[i] + 1e-12;
    logSum += Math.log(p);
    arithSum += p;
  }
  const gm = Math.exp(logSum / n);
  const am = arithSum / n;
  return gm / am;
}

export function harmonicCombStrength(
  freqs: Float64Array,
  psd: Float64Array,
): { ratio: number; f0: number; nPresent: number } {
  const df = freqs[1] - freqs[0];
  let total = 0;
  for (let i = 0; i < psd.length; i++) total += psd[i];
  total += 1e-12;
  let bestRatio = 0;
  let bestF0 = 0;
  let bestPresent = 0;
  const step = Math.max(df, 1);
  for (let f0 = F0_MIN_HZ; f0 < F0_MAX_HZ; f0 += step) {
    const peaks: number[] = [];
    for (let h = 1; h <= N_HARMONICS; h++) {
      const fc = f0 * h;
      if (fc >= freqs[freqs.length - 1]) break;
      const idx = Math.round(fc / df);
      const lo = Math.max(0, idx - 1);
      const hi = Math.min(psd.length, idx + 2);
      let pk = 0;
      for (let i = lo; i < hi; i++) if (psd[i] > pk) pk = psd[i];
      peaks.push(pk);
    }
    if (peaks.length === 0) continue;
    let harmEnergy = 0;
    let maxPeak = 0;
    for (const p of peaks) {
      harmEnergy += p;
      if (p > maxPeak) maxPeak = p;
    }
    const ratio = harmEnergy / total;
    const thresh = 0.04 * maxPeak;
    let nPresent = 0;
    for (const p of peaks) if (p > thresh) nPresent++;
    const score = ratio * nPresent;
    if (score > bestRatio * Math.max(1, bestPresent)) {
      bestRatio = ratio;
      bestF0 = f0;
      bestPresent = nPresent;
    }
  }
  return { ratio: bestRatio, f0: bestF0, nPresent: bestPresent };
}

export function broadbandRotorEnergy(freqs: Float64Array, psd: Float64Array): number {
  let band = 0;
  let total = 0;
  for (let i = 0; i < psd.length; i++) {
    total += psd[i];
    if (freqs[i] >= 200 && freqs[i] <= 4000) band += psd[i];
  }
  return band / (total + 1e-12);
}

export function acousticFeatures(x: Float64Array, sr: number): AcousticFeatures {
  const { freqs, psd } = powerSpectrum(x, sr);
  const comb = harmonicCombStrength(freqs, psd);
  let sq = 0;
  let mean = 0;
  for (let i = 0; i < x.length; i++) mean += x[i];
  mean /= x.length;
  for (let i = 0; i < x.length; i++) sq += (x[i] - mean) * (x[i] - mean);
  return {
    harmonic_comb: comb.ratio,
    harmonics_present: comb.nPresent,
    fundamental_hz: comb.f0,
    spectral_flatness: spectralFlatness(psd),
    broadband_rotor: broadbandRotorEnergy(freqs, psd),
    rms: Math.sqrt(sq / x.length) + 1e-12,
  };
}

// Heuristic confidence in [0,1] + signature_class — a direct port of score_drone().
export function scoreDrone(f: AcousticFeatures): { confidence: number; signature: string } {
  const comb = f.harmonic_comb;
  const flat = f.spectral_flatness;
  const broad = f.broadband_rotor;
  const nPresent = f.harmonics_present;

  const combTerm = 1 - Math.exp(-comb / 0.06);
  const countGate = Math.min(1, Math.max(0, (nPresent - 1) / 2));
  const flatGate = Math.exp(-((flat - 0.35) ** 2) / (2 * 0.22 ** 2));
  const broadGate = Math.min(1, broad / 0.25);

  let conf = combTerm * countGate * (0.5 + 0.5 * flatGate) * (0.5 + 0.5 * broadGate);
  conf = Math.max(0, Math.min(1, conf));
  const signature = conf >= 0.45 ? 'multirotor_acoustic' : 'unknown';
  return { confidence: conf, signature };
}
