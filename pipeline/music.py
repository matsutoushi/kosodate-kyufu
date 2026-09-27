# -*- coding: utf-8 -*-
"""リールに入れる短いBGMを自作する(標準ライブラリだけ)。

31本すべて音声トラックがゼロで、投稿時にアプリで音源も付けられていない。
Instagramの音源ライブラリはこちらから触れないので、権利の問題が起きない音を
自分で合成して動画に焼き込む。狙いは「音があるかどうか」を一度試すこと。

方針:
  ・文字を読む動画なので、主役にならない音量にする(-24dBFS前後)
  ・不協和にならない範囲の簡単な進行(I - vi - IV - V)をやわらかい正弦波で鳴らす
  ・上に軽いベルのアルペジオ。打楽器は入れない(通知音と紛れるため)
  ・先頭と末尾はフェードして、切れ目を感じさせない
"""
import array
import math
import struct
import wave

SR = 44100
A4 = 440.0


def _freq(semitones_from_a4):
    return A4 * (2.0 ** (semitones_from_a4 / 12.0))


# C4=-9, E4=-5, G4=-2, A4=0 ... A4基準の半音数で持つ
CHORDS = [
    (-21, -9, -5, -2),   # C   (C3, C4, E4, G4)
    (-24, -12, -5, 0),   # Am  (A2, A3, E4, A4)
    (-17, -5, -2, 3),    # F   (F3, F4, A4, C5)
    (-14, -2, 2, 5),     # G   (G3, G4, B4, D5)
]
# ベルのアルペジオ(各コードで鳴らす音)
BELLS = [(3, 7, 10), (0, 4, 7), (5, 9, 12), (7, 11, 14)]


def _env(i, n, attack, release):
    """音の立ち上がりと減衰。ぶつ切りにするとノイズになるので必ず通す。"""
    if i < attack:
        return i / attack
    if i > n - release:
        return max(0.0, (n - i) / release)
    return 1.0


def make_bgm(path, seconds, bpm=80, gain=0.16):
    """seconds秒のBGMを作ってWAVで書き出す。"""
    spb = 60.0 / bpm            # 1拍の秒数
    bar = spb * 4               # 1小節(4拍)
    total = int(SR * seconds)
    buf = array.array("d", [0.0]) * total

    t_bar = 0.0
    k = 0
    while t_bar < seconds:
        ch = CHORDS[k % len(CHORDS)]
        bells = BELLS[k % len(BELLS)]
        start = int(t_bar * SR)
        n = min(int(bar * SR), total - start)
        if n <= 0:
            break
        # パッド(コードを伸ばす)
        for s in ch:
            f = _freq(s)
            for i in range(n):
                buf[start + i] += (0.16 * _env(i, n, SR * 0.25, SR * 0.35)
                                   * math.sin(2 * math.pi * f * i / SR))
        # ベル(拍に合わせて短く)
        for b_i, s in enumerate(bells):
            f = _freq(s)
            bs = start + int(spb * SR * (b_i + 1))
            bn = int(spb * SR * 0.9)
            if bs + bn > total:
                break
            for i in range(bn):
                e = _env(i, bn, SR * 0.01, bn * 0.9)
                buf[bs + i] += (0.10 * e * e
                                * (math.sin(2 * math.pi * f * i / SR)
                                   + 0.3 * math.sin(4 * math.pi * f * i / SR)))
        t_bar += bar
        k += 1

    # 全体の音量調整と、先頭・末尾のフェード
    peak = max(1e-9, max(abs(v) for v in buf))
    fade = int(SR * 0.8)
    out = array.array("h", [0]) * total
    for i in range(total):
        v = buf[i] / peak * gain
        if i < fade:
            v *= i / fade
        if i > total - fade:
            v *= max(0.0, (total - i) / fade)
        out[i] = int(max(-1.0, min(1.0, v)) * 32767)

    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(out.tobytes())
    return path


if __name__ == "__main__":
    import sys
    make_bgm(sys.argv[1] if len(sys.argv) > 1 else "bgm.wav", 30)
