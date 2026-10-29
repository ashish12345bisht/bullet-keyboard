"""Procedural gunshot synthesis. Every sound is generated with numpy, no sample files."""

import numpy as np

SR = 48000
VARIANTS = 6  # pre-rendered variations per gun so repeated keys don't sound identical


def _t(dur):
    return np.arange(int(SR * dur)) / SR


def _filter(x, lo=None, hi=None):
    """Band-limit a signal in the frequency domain with soft (2nd-order-ish) rolloffs."""
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(x.size, 1 / SR)
    gain = np.ones_like(f)
    if hi:
        gain /= 1 + (f / hi) ** 4
    if lo:
        gain /= 1 + (lo / np.maximum(f, 1)) ** 4
    return np.fft.irfft(spec * gain, x.size)


def _env(t, attack, decay):
    return np.minimum(t / attack, 1.0) * np.exp(-t / decay)


def _noise(rng, n):
    return rng.standard_normal(n)


def _thump(t, f0, f1, decay, sweep=0.03):
    freq = f1 + (f0 - f1) * np.exp(-t / sweep)
    phase = 2 * np.pi * np.cumsum(freq) / SR
    return np.sin(phase) * _env(t, 0.0005, decay)


def _place(out, x, at):
    i = int(at * SR)
    n = min(x.size, out.size - i)
    if n > 0:
        out[i:i + n] += x[:n]


def _gunshot(rng, dur, crack_decay, crack_hi, thump_f, thump_decay, tail_decay, tail_hi,
             crack_gain=1.0, thump_gain=0.8, tail_gain=0.35, echoes=(), clicks=(), drive=2.0):
    t = _t(dur)
    out = np.zeros(t.size)
    out += crack_gain * _filter(_noise(rng, t.size), lo=300, hi=crack_hi) * _env(t, 0.0003, crack_decay)
    out += thump_gain * _thump(t, *thump_f, thump_decay) * 3
    out += tail_gain * _filter(_noise(rng, t.size), hi=tail_hi) * _env(t, 0.004, tail_decay)
    dry = out.copy()
    for delay, gain in echoes:
        _place(out, _filter(dry, hi=tail_hi) * gain, delay)
    for at, gain in clicks:
        c = _t(0.012)
        _place(out, gain * _filter(_noise(rng, c.size), lo=2000, hi=9000) * _env(c, 0.0002, 0.002), at)
    out /= np.max(np.abs(out)) + 1e-9
    return np.tanh(out * drive) / np.tanh(drive)


def pistol(rng):
    return _gunshot(rng, 0.35, 0.018, 7000, (180, 70), 0.04, 0.09, 2500)


def revolver(rng):
    return _gunshot(rng, 0.6, 0.03, 6000, (140, 50), 0.07, 0.18, 2000,
                    tail_gain=0.5, echoes=[(0.11, 0.25)], drive=2.5)


def rifle(rng):
    return _gunshot(rng, 0.5, 0.025, 9000, (160, 60), 0.05, 0.14, 3000,
                    tail_gain=0.45, echoes=[(0.09, 0.2)], drive=2.5)


def smg(rng):
    return _gunshot(rng, 0.18, 0.01, 8000, (220, 90), 0.025, 0.045, 3500,
                    thump_gain=0.5, tail_gain=0.25, drive=1.8)


def shotgun(rng):
    return _gunshot(rng, 0.9, 0.05, 4000, (90, 35), 0.12, 0.3, 1500, crack_gain=1.2,
                    thump_gain=1.2, tail_gain=0.6, echoes=[(0.16, 0.3)], drive=3.0)


def sniper(rng):
    return _gunshot(rng, 1.4, 0.03, 11000, (110, 38), 0.1, 0.45, 1800, crack_gain=1.4,
                    thump_gain=1.0, tail_gain=0.55, echoes=[(0.22, 0.35), (0.5, 0.15)], drive=3.0)


def silenced(rng):
    t = _t(0.15)
    pfft = _filter(_noise(rng, t.size), lo=500, hi=2500) * _env(t, 0.001, 0.02)
    click = _filter(_noise(rng, t.size), lo=3000, hi=10000) * _env(t, 0.0002, 0.003) * 0.6
    out = pfft + click + 0.4 * _thump(t, 300, 120, 0.015)
    return out / (np.max(np.abs(out)) + 1e-9) * 0.7


def laser(rng):
    t = _t(0.22)
    freq = 250 + 2200 * np.exp(-t / 0.04)
    phase = 2 * np.pi * np.cumsum(freq) / SR
    out = np.tanh(3 * np.sin(phase)) * _env(t, 0.001, 0.06)
    return out * 0.6


# name -> (synth, auto-fire while key is held)
GUNS = {
    "pistol": (pistol, False),
    "revolver": (revolver, False),
    "rifle": (rifle, True),
    "smg": (smg, True),
    "shotgun": (shotgun, False),
    "sniper": (sniper, False),
    "silenced": (silenced, False),
    "laser": (laser, True),
}


def _vary(x, rng):
    """Small random pitch/gain shift via resampling."""
    rate = rng.uniform(0.93, 1.07)
    idx = np.arange(0, x.size - 1, rate)
    return np.interp(idx, np.arange(x.size), x) * rng.uniform(0.8, 1.0)


def render_all(seed=7):
    """Return {gun: [variant arrays (float32, -1..1)]}."""
    rng = np.random.default_rng(seed)
    bank = {}
    for name, (synth, _) in GUNS.items():
        base = synth(rng)
        bank[name] = [_vary(base, rng).astype(np.float32) for _ in range(VARIANTS)]
    return bank
