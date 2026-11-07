"""Synthesises every Crownless sound into assets/audio/.

    .venv\\Scripts\\python.exe tools\\audio\\make_audio.py

Sound effects are short 16-bit mono WAVs. The two piano themes are rendered as seamless stereo loops and saved
as OGG (needs imageio-ffmpeg). Everything is generated from code, so nothing here is borrowed from another game.
Needs numpy; the game itself does not.
"""

import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "audio"
SR = 44100
RNG = np.random.default_rng(7)


def seconds(length: float) -> np.ndarray:
    return np.arange(int(length * SR)) / SR


def lowpass(signal: np.ndarray, amount: float) -> np.ndarray:
    """One-pole low-pass; amount near 0 is darker."""
    out = np.empty_like(signal)
    value = 0.0
    for i, x in enumerate(signal):
        value += amount * (x - value)
        out[i] = value
    return out


def bandpass_noise(length: float, low: float, high: float) -> np.ndarray:
    n = int(length * SR)
    spectrum = np.fft.rfft(RNG.standard_normal(n))
    freqs = np.fft.rfftfreq(n, 1 / SR)
    spectrum[(freqs < low) | (freqs > high)] = 0
    noise = np.fft.irfft(spectrum, n)
    return noise / (np.max(np.abs(noise)) + 1e-9)


def sweep(t: np.ndarray, f0: float, f1: float, curve: float = 0.05) -> np.ndarray:
    """Sine whose pitch glides from f0 to f1 with an exponential curve (seconds)."""
    freq = f1 + (f0 - f1) * np.exp(-t / curve)
    return np.sin(2 * np.pi * np.cumsum(freq) / SR)


def normalise(signal: np.ndarray, peak: float = 0.89) -> np.ndarray:
    return signal * (peak / (np.max(np.abs(signal)) + 1e-9))


def fade_edges(signal: np.ndarray, attack: float = 0.002, release: float = 0.02) -> np.ndarray:
    a = max(1, int(attack * SR))
    r = max(1, int(release * SR))
    signal = signal.copy()
    signal[:a] *= np.linspace(0, 1, a)
    signal[-r:] *= np.linspace(1, 0, r)
    return signal


def write_wav(name: str, signal: np.ndarray) -> None:
    data = np.clip(signal, -1, 1)
    channels = 1 if data.ndim == 1 else data.shape[1]
    pcm = (data * 32767).astype("<i2")
    with wave.open(str(OUT / name), "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(2)
        handle.setframerate(SR)
        handle.writeframes(pcm.tobytes())


# ------------------------------------------------------------------------------------------------ sound effects

def wood_knock(body: float, ring: float, click: float, length: float = 0.22, darkness: float = 1.0,
               weight: float = 0.0, hold: float = 0.030) -> np.ndarray:
    """A felt-bottomed piece landing on a wooden board: a pitched body, a woody ring and a contact click.
    weight adds a sub-octave thump under the body (a heavy piece on a thick board); hold is how long the body rings."""
    t = seconds(length)
    thump = sweep(t, body * 1.45, body, 0.010) * np.exp(-t / hold)
    sub = sweep(t, body * 0.75, body * 0.5, 0.02) * np.exp(-t / (hold * 1.5)) * weight
    tone = np.sin(2 * np.pi * ring * t) * np.exp(-t / 0.022) * 0.42
    tone += np.sin(2 * np.pi * ring * 2.31 * t) * np.exp(-t / 0.011) * 0.16
    contact = bandpass_noise(length, 1200 / darkness, 5200 / darkness) * np.exp(-t / 0.004) * click
    grain = bandpass_noise(length, 250, 1300) * np.exp(-t / 0.026) * 0.2
    return fade_edges(thump * 0.9 + sub + tone + contact + grain, 0.0005, 0.04)


def place(out: np.ndarray, at: float, sound: np.ndarray, gain: float = 1.0) -> None:
    i = int(at * SR)
    j = min(len(out), i + len(sound))
    if i < len(out):
        out[i:j] += sound[: j - i] * gain


def make_move(name: str, body: float, ring: float, darkness: float) -> None:
    """Heavy and solid: a low body that rings a little longer, with a sub thump underneath."""
    knock = wood_knock(body, ring, 0.5, 0.3, darkness=darkness, weight=0.75, hold=0.055)
    write_wav(name, normalise(knock, 0.85))


def make_capture(name: str, dark: float) -> None:
    """Three layers, so a capture never sounds like a move: the attacker slams down, the two pieces clack
    together, and the taken piece tumbles off the board. dark > 1 is the enemy's version: lower and grimmer."""
    out = np.zeros(int(0.42 * SR))
    slam = wood_knock(150 / dark, 500 / dark, 0.9, 0.34, darkness=dark, weight=1.0, hold=0.06)
    clack = wood_knock(340 / dark, 1350 / dark, 1.1, 0.16, darkness=dark, weight=0.0, hold=0.012)
    place(out, 0.0, slam)
    place(out, 0.014, clack, 0.85)
    for at, gain, pitch in ((0.095, 0.38, 1.0), (0.15, 0.24, 1.12), (0.192, 0.14, 1.25)):
        tumble = wood_knock(260 * pitch / dark, 1050 * pitch / dark, 0.7, 0.1, darkness=dark, hold=0.01)
        place(out, at, tumble, gain)
    t = seconds(len(out) / SR)
    out += sweep(t, 90 / dark, 45 / dark, 0.04) * np.exp(-t / 0.09) * 0.55  # weight of the blow
    write_wav(name, normalise(fade_edges(out, 0.0005, 0.05), 0.9))


def make_explosion() -> None:
    t = seconds(1.6)
    boom = sweep(t, 95, 28, 0.25) * np.exp(-t / 0.45)
    roar = lowpass(RNG.standard_normal(len(t)), 0.05) * np.exp(-t / 0.35) * 3.0
    crack = bandpass_noise(1.6, 1500, 7000) * np.exp(-t / 0.03) * 0.6
    crackle = (RNG.random(len(t)) > 0.9985) * RNG.uniform(-1, 1, len(t)) * np.exp(-t / 0.5) * 0.8
    write_wav("explosion.wav", normalise(fade_edges(boom + roar + crack + crackle, 0.001, 0.2), 0.9))


def bell(freq: float, length: float, decay: float) -> np.ndarray:
    t = seconds(length)
    partials = ((1.0, 1.0), (2.76, 0.45), (5.40, 0.22), (8.93, 0.10))
    out = sum(a * np.sin(2 * np.pi * freq * r * t) * np.exp(-t * (decay * (1 + i * 0.8))) for i, (r, a) in enumerate(partials))
    return out


def make_relic() -> None:
    length = 1.8
    out = np.zeros(int(length * SR))
    for start, freq, amp in ((0.0, 1318.5, 1.0), (0.07, 1975.5, 0.7), (0.14, 2637.0, 0.5)):
        tone = bell(freq, length - start, 2.6) * amp
        i = int(start * SR)
        out[i: i + len(tone)] += tone
    t = seconds(length)
    out += bandpass_noise(length, 4000, 11000) * np.exp(-t / 0.25) * 0.08 * (1 - np.exp(-t / 0.05))
    write_wav("relic.wav", normalise(fade_edges(out, 0.002, 0.3), 0.7))


def make_spawn() -> None:
    length = 0.9
    t = seconds(length)
    swell = np.sin(np.pi * np.clip(t / length, 0, 1)) ** 2
    out = np.zeros_like(t)
    for freq in (880.0, 1108.7, 1318.5, 1760.0):
        out += np.sin(2 * np.pi * freq * t * (1 + 0.02 * t)) * 0.25
    out *= swell
    out += bandpass_noise(length, 3000, 9000) * swell * 0.08
    write_wav("spawn.wav", normalise(fade_edges(out, 0.01, 0.1), 0.55))


def make_coin() -> None:
    length = 0.6
    out = np.zeros(int(length * SR))
    for start, freq in ((0.0, 2350.0), (0.075, 2960.0)):
        tone = bell(freq, length - start, 9.0)
        i = int(start * SR)
        out[i: i + len(tone)] += tone
    write_wav("coin.wav", normalise(fade_edges(out, 0.0005, 0.05), 0.6))


def make_click() -> None:
    """Pressing a wooden button: a crisp, short tok."""
    tok = wood_knock(520, 1700, 0.6, 0.1, weight=0.25, hold=0.014)
    write_wav("click.wav", normalise(tok, 0.5))


def make_hover() -> None:
    """The pointer brushing over something clickable: a tiny, high, quiet tick that never tires."""
    t = seconds(0.06)
    tick = wood_knock(1150, 3200, 0.2, 0.06, hold=0.006)
    tick += bandpass_noise(0.06, 5000, 11000) * np.exp(-t / 0.008) * 0.08
    write_wav("hover.wav", normalise(fade_edges(tick, 0.0005, 0.02), 0.3))


# ------------------------------------------------------------------------------------------------ piano

def midi_hz(note: float) -> float:
    return 440.0 * 2 ** ((note - 69) / 12)


_NOTE_CACHE: dict[tuple, np.ndarray] = {}


def piano_note(note: int, hold: float, velocity: float) -> np.ndarray:
    """Additive piano: stretched partials that fade faster the higher they are, two slightly detuned strings,
    a short hammer thump, and dampers on release."""
    key = (note, round(hold, 3), round(velocity, 2))
    cached = _NOTE_CACHE.get(key)
    if cached is not None:
        return cached
    f0 = midi_hz(note)
    release = 0.12
    length = hold + release + 0.05
    t = seconds(length)
    sustain = 3.2 * (220.0 / f0) ** 0.45
    brightness = 0.55 + 0.45 * velocity
    out = np.zeros_like(t)
    for n in range(1, 13):
        fn = f0 * n * np.sqrt(1 + 0.00035 * n * n)
        if fn > 16000:
            break
        amp = (1.0 / n ** 1.15) * brightness ** (n - 1)
        tau = sustain / (1 + 0.55 * (n - 1))
        for detune in (-0.0006, 0.0006):
            out += amp * 0.5 * np.sin(2 * np.pi * fn * (1 + detune) * t) * np.exp(-t / tau)
    hammer = bandpass_noise(length, 200, 3000) * np.exp(-t / 0.006) * 0.12 * velocity
    out = out + hammer
    out *= np.minimum(1.0, t / 0.002)
    damp = np.where(t < hold, 1.0, np.exp(-(t - hold) / (release / 3)))
    out *= damp * velocity
    _NOTE_CACHE[key] = out
    return out


def kick(velocity: float) -> np.ndarray:
    t = seconds(0.35)
    return (sweep(t, 120, 46, 0.03) * np.exp(-t / 0.12) + bandpass_noise(0.35, 1500, 5000) * np.exp(-t / 0.003) * 0.2) * velocity


def shaker(velocity: float) -> np.ndarray:
    t = seconds(0.09)
    return bandpass_noise(0.09, 6000, 14000) * np.exp(-t / 0.018) * np.minimum(1.0, t / 0.004) * velocity


def clap(velocity: float) -> np.ndarray:
    t = seconds(0.25)
    burst = bandpass_noise(0.25, 900, 4500)
    env = np.exp(-t / 0.06)
    for offset in (0.0, 0.011, 0.022):
        env += (t >= offset) * np.exp(-np.maximum(0, t - offset) / 0.006) * 0.6
    return burst * env * velocity * 0.5


class Track:
    def __init__(self, bpm: float, bars: int) -> None:
        self.beat = 60.0 / bpm
        self.length = bars * 4 * self.beat
        self.tail = 4.0
        n = int((self.length + self.tail) * SR)
        self.left = np.zeros(n)
        self.right = np.zeros(n)

    def add(self, beat: float, signal: np.ndarray, pan: float = 0.0, gain: float = 1.0) -> None:
        i = int(beat * self.beat * SR)
        j = min(len(self.left), i + len(signal))
        if i >= len(self.left):
            return
        part = signal[: j - i] * gain
        self.left[i:j] += part * np.sqrt(0.5 * (1 - pan))
        self.right[i:j] += part * np.sqrt(0.5 * (1 + pan))

    def note(self, beat: float, note: int, hold_beats: float, velocity: float) -> None:
        pan = max(-0.6, min(0.6, (note - 60) / 40))
        self.add(beat, piano_note(note, hold_beats * self.beat, velocity), pan)

    def chord(self, beat: float, notes, hold_beats: float, velocity: float, strum: float = 0.012) -> None:
        for i, note in enumerate(notes):
            self.note(beat + i * strum / self.beat, note, hold_beats, velocity * (1 - 0.06 * i))

    def render(self, path: Path, reverb: float = 0.2) -> None:
        loop = int(self.length * SR)
        stereo = []
        for channel, seed in ((self.left, 1), (self.right, 2)):
            dry = channel[:loop].copy()
            dry[: len(channel) - loop] += channel[loop:]  # wrap the tail into the start: seamless loop
            stereo.append(dry + reverb * circular_reverb(dry, seed))
        mix = np.stack(stereo, axis=1)
        mix = np.tanh(mix / (np.max(np.abs(mix)) + 1e-9) * 1.25) * 0.89
        temp = path.with_suffix(".wav")
        write_wav(temp.name, mix)
        encode_ogg(temp, path)
        temp.unlink()


def circular_reverb(dry: np.ndarray, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    length = int(2.2 * SR)
    t = np.arange(length) / SR
    ir = rng.standard_normal(length) * np.exp(-t / 0.55)
    ir = np.convolve(ir, np.ones(8) / 8, mode="same")  # soften the highs
    ir[: int(0.012 * SR)] = 0
    ir /= np.sqrt(np.sum(ir ** 2))
    n = len(dry)
    size = 1 << int(np.ceil(np.log2(n + length)))
    wet = np.fft.irfft(np.fft.rfft(np.concatenate([dry, dry]), size * 2) * np.fft.rfft(ir, size * 2), size * 2)
    return wet[n: 2 * n]


def encode_ogg(source: Path, target: Path) -> None:
    import imageio_ffmpeg

    subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(source), "-c:a", "libvorbis", "-q:a", "5", str(target)],
        check=True,
    )


# chords as (bass note, right-hand voicing), A minor
AM, F, C, G, DM, E = (
    (45, (69, 72, 76)), (41, (65, 69, 72)), (48, (67, 72, 76)), (43, (67, 71, 74)), (38, (65, 69, 74)), (40, (68, 71, 76)),
)


def battle_theme() -> Track:
    """132 bpm. Driving left-hand octaves, syncopated chord stabs, then a hook melody; light kick and shaker."""
    track = Track(132, 32)
    progression = [AM, F, C, G, AM, F, DM, E]
    melody = [
        (76, None, 76, 74, 72, None, 71, 72), (69, None, None, 72, 77, None, 76, 74),
        (72, None, 72, 74, 76, None, 79, None), (74, None, None, None, 71, 72, 74, None),
        (76, None, 76, 74, 72, None, 71, 72), (69, None, 72, 77, 81, None, 79, 77),
        (77, None, 76, 74, 72, None, 74, None), (71, None, None, 68, 71, None, 76, None),
    ]
    stab_16ths = (0, 3, 6, 8, 11, 14)
    for bar in range(32):
        bass, voicing = progression[bar % 8]
        start = bar * 4
        section = bar // 8  # 0: A, 1: A', 2: B, 3: B'
        for eighth in range(8):
            note = bass if eighth % 2 == 0 else bass + 12
            accent = 0.72 if eighth == 0 else 0.58 if eighth % 2 == 0 else 0.5
            track.note(start + eighth * 0.5, note, 0.42, accent)
        if section in (0, 1):
            for i, step in enumerate(stab_16ths):
                velocity = 0.62 if i in (0, 3) else 0.48
                notes = voicing + ((voicing[-1] + 12,) if section == 1 else ())
                track.chord(start + step * 0.25, notes, 0.2, velocity)
        else:
            for eighth, note in enumerate(melody[bar % 8]):
                if note is None:
                    continue
                hold = 0.45
                for following in melody[bar % 8][eighth + 1:]:
                    if following is not None:
                        break
                    hold += 0.5
                track.note(start + eighth * 0.5, note, hold, 0.74)
                if section == 3:
                    track.note(start + eighth * 0.5, note - 12, hold, 0.5)
            for offbeat in (0.5, 1.5, 2.5, 3.5):
                track.chord(start + offbeat, tuple(n - 12 for n in voicing), 0.22, 0.34)
        if bar == 31:
            track.chord(start + 3.5, (64, 68, 71, 76), 0.5, 0.6)  # E turnaround back into the top
        for beat in (0, 2):
            track.add(start + beat, kick(0.55))
        for half in range(8):
            track.add(start + half * 0.5 + 0.25, shaker(0.18 if half % 2 else 0.12), pan=0.3)
        if section >= 2:
            for beat in (1, 3):
                track.add(start + beat, clap(0.45), pan=-0.1)
    return track


def menu_theme() -> Track:
    """88 bpm. Rolling broken chords and a slow, searching melody: for menus, the shop and the win screen."""
    track = Track(88, 16)
    progression = [AM, F, C, E, AM, F, DM, E, AM, F, C, E, F, DM, E, AM]
    melody = {8: (76, 4), 9: (77, 2), 9.5: (76, 2), 10: (79, 4), 11: (71, 4), 12: (81, 3), 12.75: (79, 1),
              13: (77, 4), 14: (76, 2), 14.5: (74, 2), 15: (69, 4)}
    for bar in range(16):
        bass, voicing = progression[bar]
        start = bar * 4
        track.note(start, bass, 3.8, 0.5)
        track.note(start, bass + 7 if bass + 7 not in (45, 52) else bass + 12, 3.8, 0.3)
        rolling = (voicing[0] - 12, voicing[1] - 12, voicing[2] - 12, voicing[0], voicing[2] - 12, voicing[1] - 12, voicing[0] - 12, voicing[1])
        for eighth, note in enumerate(rolling):
            track.note(start + eighth * 0.5, note, 0.9, 0.36 if eighth else 0.44)
    for bar, (note, beats) in melody.items():
        track.note(bar * 4, note, beats, 0.6)
    return track


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    make_move("move.wav", 165, 560, 1.0)
    make_move("move_enemy.wav", 135, 470, 1.35)
    make_capture("capture.wav", 1.0)
    make_capture("capture_enemy.wav", 1.3)
    make_explosion()
    make_relic()
    make_spawn()
    make_coin()
    make_click()
    make_hover()
    print("sound effects written", flush=True)
    stingers = {
        "battle_start.wav": [(0.0, n, 0.6, 0.8) for n in (45, 57, 64, 69, 72)],
        "victory.wav": [(0.0, 69, 0.4, 0.7), (0.12, 73, 0.4, 0.7), (0.24, 76, 0.4, 0.72), (0.36, 81, 1.6, 0.8),
                        (0.36, 57, 1.6, 0.6), (0.36, 64, 1.6, 0.55)],
        "defeat.wav": [(0.0, 64, 0.5, 0.55), (0.35, 60, 0.5, 0.5), (0.7, 57, 2.2, 0.55), (0.7, 45, 2.2, 0.5), (0.7, 52, 2.2, 0.4)],
    }
    for name, notes in stingers.items():
        length = max(start + hold for start, _note, hold, _vel in notes) + 1.2
        out = np.zeros(int(length * SR))
        for start, note, hold, velocity in notes:
            tone = piano_note(note, hold, velocity)
            i = int(start * SR)
            out[i: i + len(tone)] += tone[: len(out) - i]
        if name == "battle_start.wav":
            hit = kick(0.9)
            out[: len(hit)] += hit
        write_wav(name, normalise(fade_edges(out, 0.001, 0.3), 0.8))
    print("stingers written", flush=True)
    battle_theme().render(OUT / "theme_battle.ogg", reverb=0.16)
    print("battle theme written", flush=True)
    menu_theme().render(OUT / "theme_menu.ogg", reverb=0.28)
    print("menu theme written", flush=True)


if __name__ == "__main__":
    sys.exit(main())
