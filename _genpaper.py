import math, struct, zlib, os

W = H = 320
base = (143, 184, 224)  # #8fb8e0

def hash2(x, y):
    n = (x * 374761393 + y * 668265263) ^ 0x9E3779B9
    n = (n ^ (n >> 13)) * 1274126177
    n = n ^ (n >> 16)
    return (n & 0xFFFFFF) / 0xFFFFFF

def sm(t):
    return t * t * (3 - 2 * t)

def noise(x, y):
    x0 = int(x); y0 = int(y); xf = x - x0; yf = y - y0
    v00 = hash2(x0, y0); v10 = hash2(x0 + 1, y0)
    v01 = hash2(x0, y0 + 1); v11 = hash2(x0 + 1, y0 + 1)
    u = sm(xf); v = sm(yf)
    return (v00 * (1 - u) + v10 * u) * (1 - v) + (v01 * (1 - u) + v11 * u) * v

def fbm(x, y, oct=4):
    a = 0.0; amp = 0.5; freq = 1.0
    for _ in range(oct):
        a += noise(x * freq, y * freq) * amp
        freq *= 2.0; amp *= 0.5
    return a

# pass 1: build float field
field = [[0.0] * W for _ in range(H)]
for y in range(H):
    for x in range(W):
        # large pulp mottling
        mottle = fbm(x * 0.02, y * 0.02, 3) - 0.5
        # directional fibers: stretch along x (horizontal-ish), a few orientations
        f1 = (noise(x * 0.9, y * 0.08) - 0.5) * 0.9      # long horizontal fibers
        f2 = (noise(x * 0.08, y * 0.9) - 0.5) * 0.5      # long vertical fibers
        f3 = (noise(x * 0.5 + 11, y * 0.5 - 7) - 0.5) * 0.4  # diagonal
        # break fibers into streaks using a warped sine
        warp = fbm(x * 0.05, y * 0.05, 2)
        streak = math.sin((y * 0.6 + warp * 8.0)) * 0.06
        streak += math.sin((x * 0.5 + warp * 6.0)) * 0.04
        v = mottle * 0.8 + (f1 + f2 + f3) * 0.35 + streak
        field[y][x] = v

# soft blur (3x3 box) to kill static look
blur = [[0.0] * W for _ in range(H)]
for y in range(H):
    for x in range(W):
        s = 0.0; c = 0
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                xx = (x + dx) % W; yy = (y + dy) % H
                s += field[yy][xx]; c += 1
        blur[y][x] = s / c
field = blur

# optional 2nd blur pass
for _ in range(1):
    b2 = [[0.0] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            s = 0.0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    s += field[(y + dy) % H][(x + dx) % W]
            b2[y][x] = s / 9.0
    field = b2

px = [[(0, 0, 0) for _ in range(W)] for _ in range(H)]
for y in range(H):
    for x in range(W):
        v = field[y][x]
        # map v (~ -1..1) to color delta
        r = base[0] + v * 46
        g = base[1] + v * 38
        b = base[2] + v * 30
        # very subtle pulp speckle (not static)
        s = hash2(x * 3 + 5, y * 3 + 9)
        if s > 0.992:
            r += 16; g += 14; b += 12
        elif s < 0.006:
            r -= 12; g -= 11; b -= 9
        px[y][x] = (max(0, min(255, int(r))), max(0, min(255, int(g))), max(0, min(255, int(b))))

def chunk(typ, data):
    c = struct.pack(">I", len(data)) + typ + data
    crc = zlib.crc32(typ + data) & 0xFFFFFFFF
    return c + struct.pack(">I", crc)

raw = bytearray()
for y in range(H):
    raw.append(0)
    for x in range(W):
        r, g, b = px[y][x]
        raw += bytes((r, g, b))
sig = b"\x89PNG\r\n\x1a\n"
ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
out = sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")
open("paper.png", "wb").write(out)
print("wrote paper.png", os.path.getsize("paper.png"), "bytes")
