"""Black–Scholes in numpy (no scipy here): price, delta, implied vol by bisection."""
import numpy as np

def _erfc(x):   # Numerical Recipes erfcc, fractional error < 1.2e-7
    z = np.abs(x); t = 1.0 / (1.0 + 0.5 * z)
    r = t * np.exp(-z * z - 1.26551223 + t * (1.00002368 + t * (0.37409196 + t * (0.09678418 + t * (-0.18628806
        + t * (0.27886807 + t * (-1.13520398 + t * (1.48851587 + t * (-0.82215223 + t * 0.17087277)))))))))
    return np.where(x >= 0, r, 2.0 - r)

def ncdf(x):
    return 0.5 * _erfc(-x / np.sqrt(2.0))

def _d1(S, K, T, r, q, sig):
    return (np.log(S / K) + (r - q + 0.5 * sig * sig) * T) / (sig * np.sqrt(T))

def price(S, K, T, r, q, sig, cp):
    d1 = _d1(S, K, T, r, q, sig); d2 = d1 - sig * np.sqrt(T)
    call = S * np.exp(-q * T) * ncdf(d1) - K * np.exp(-r * T) * ncdf(d2)
    put = K * np.exp(-r * T) * ncdf(-d2) - S * np.exp(-q * T) * ncdf(-d1)
    return np.where(cp > 0, call, put)

def delta(S, K, T, r, q, sig, cp):
    d1 = _d1(S, K, T, r, q, sig)
    return np.where(cp > 0, np.exp(-q * T) * ncdf(d1), -np.exp(-q * T) * ncdf(-d1))

def iv(px, S, K, T, r, q, cp):
    lo = np.full(np.shape(px), 0.01); hi = np.full(np.shape(px), 4.0)
    for _ in range(60):
        mid = 0.5 * (lo + hi); p = price(S, K, T, r, q, mid, cp)
        hi = np.where(p > px, mid, hi); lo = np.where(p > px, lo, mid)
    ok = (price(S, K, T, r, q, np.full(np.shape(px), 0.01), cp) < px) & (price(S, K, T, r, q, np.full(np.shape(px), 4.0), cp) > px)
    return np.where(ok, 0.5 * (lo + hi), np.nan)
