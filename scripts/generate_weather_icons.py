#!/usr/bin/env python3
"""
Generate filled & colored, subtly-animated, *3D-styled*, self-contained SVG
weather icons for the yr.no / MET Norway symbol set used by forecastmanager.

Style: the soft puffy look (multi-bump clouds, light palette) with added depth
via gradient shading, soft drop shadows and highlights. Each SVG is standalone
(embedded <style>, <defs>, gradients, filters + CSS @keyframes) so the animation
and shading run even when referenced via <img src="...svg">.

All 83 symbol codes are covered from one set of building blocks, matching each
existing PNG name 1:1.
"""

import os
import sys
import math

ICON_DIR = sys.argv[1] if len(sys.argv) > 1 else "."

# unique-id counter, reset per file
_uid = 0
def nid(prefix):
    global _uid
    _uid += 1
    return f"{prefix}{_uid}"

# ---------------------------------------------------------------------------
# Shared <style> (animation keyframes)
# ---------------------------------------------------------------------------
STYLE = """
  .spin{transform-box:fill-box;transform-origin:center;animation:spin 26s linear infinite}
  .pulse{transform-box:fill-box;transform-origin:center;animation:pulse 4s ease-in-out infinite}
  .glow{animation:glow 4s ease-in-out infinite}
  .drift{transform-box:fill-box;transform-origin:center;animation:drift 7s ease-in-out infinite}
  .drift2{transform-box:fill-box;transform-origin:center;animation:drift 9s ease-in-out infinite}
  .rain{animation:fall 1.5s linear infinite}
  .snow{animation:snowfall 3.2s linear infinite}
  .bolt{transform-box:fill-box;transform-origin:center;animation:flash 3.6s ease-in-out infinite}
  .fog{transform-box:fill-box;transform-origin:center;animation:fogdrift 5s ease-in-out infinite}
  @keyframes spin{to{transform:rotate(360deg)}}
  @keyframes pulse{0%,100%{transform:scale(1)}50%{transform:scale(1.06)}}
  @keyframes glow{0%,100%{opacity:.85}50%{opacity:1}}
  @keyframes drift{0%,100%{transform:translateX(-2px)}50%{transform:translateX(2px)}}
  @keyframes fall{0%{transform:translateY(-3px);opacity:0}20%{opacity:1}80%{opacity:1}100%{transform:translateY(13px);opacity:0}}
  @keyframes snowfall{0%{transform:translateY(-3px) translateX(0);opacity:0}20%{opacity:1}100%{transform:translateY(14px) translateX(3px);opacity:0}}
  @keyframes flash{0%,90%,100%{opacity:.25}92%{opacity:1}94%{opacity:.35}96%{opacity:1}}
  @keyframes fogdrift{0%,100%{transform:translateX(-3px)}50%{transform:translateX(3px)}}
"""

# ---------------------------------------------------------------------------
# Shared <defs>: gradients + soft drop-shadow filter (3D depth)
# ---------------------------------------------------------------------------
DEFS = """
  <filter id="ds" x="-40%" y="-40%" width="180%" height="180%">
    <feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="#21425f" flood-opacity="0.30"/>
  </filter>
  <filter id="dsSoft" x="-50%" y="-50%" width="200%" height="200%">
    <feDropShadow dx="0" dy="1.4" stdDeviation="1.2" flood-color="#1c3a55" flood-opacity="0.35"/>
  </filter>
  <radialGradient id="sunG" cx="38%" cy="32%" r="72%">
    <stop offset="0%" stop-color="#FFEC93"/>
    <stop offset="55%" stop-color="#FFC831"/>
    <stop offset="100%" stop-color="#F2A012"/>
  </radialGradient>
  <radialGradient id="twiG" cx="38%" cy="32%" r="72%">
    <stop offset="0%" stop-color="#FFC585"/>
    <stop offset="55%" stop-color="#FF8A3D"/>
    <stop offset="100%" stop-color="#E85C2A"/>
  </radialGradient>
  <radialGradient id="moonG" cx="35%" cy="30%" r="80%">
    <stop offset="0%" stop-color="#FBEFA0"/>
    <stop offset="100%" stop-color="#E7C440"/>
  </radialGradient>
  <linearGradient id="rainG" x1="0" y1="0" x2="0.4" y2="1">
    <stop offset="0%" stop-color="#7FC0F3"/>
    <stop offset="100%" stop-color="#2C73C4"/>
  </linearGradient>
  <radialGradient id="snowG" cx="35%" cy="30%" r="75%">
    <stop offset="0%" stop-color="#FFFFFF"/>
    <stop offset="100%" stop-color="#CADEF2"/>
  </radialGradient>
  <linearGradient id="boltG" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#FFD740"/>
    <stop offset="100%" stop-color="#F08A00"/>
  </linearGradient>
"""

# cloud gradient stops (top -> bottom)
CLOUD_LIGHT = ("#FCFEFF", "#C3D3E3")
CLOUD_GREY = ("#DCE5EE", "#93A7BB")
FOG = "#8E9EB0"
SNOW_EDGE = "#7FA2C6"
RAY = "#FFC533"
RAY_TWI = "#FF8A3D"

# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------

def sun(cx, cy, r, grad="sunG", ray=RAY, animate=True):
    rl_in, rl_out = r + 4, r + 11
    lines = []
    for i in range(8):
        a = math.radians(i * 45)
        x1, y1 = cx + rl_in * math.cos(a), cy + rl_in * math.sin(a)
        x2, y2 = cx + rl_out * math.cos(a), cy + rl_out * math.sin(a)
        lines.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>')
    spin = ' class="spin"' if animate else ""
    pulse = ' class="pulse"' if animate else ""
    return (
        f'<g{spin} stroke="{ray}" stroke-width="3.4" stroke-linecap="round">'
        + "".join(lines) + "</g>"
        f'<g{pulse} filter="url(#ds)">'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#{grad})"/>'
        f'<ellipse cx="{cx-r*0.33:.1f}" cy="{cy-r*0.36:.1f}" rx="{r*0.42:.1f}" ry="{r*0.30:.1f}" fill="#FFFFFF" opacity="0.35"/>'
        f"</g>"
    )


def moon(cx, cy, r, animate=True):
    R, r2 = r, r * 0.82
    top = (cx + r * 0.30, cy - R + 1)
    bot = (cx + r * 0.30, cy + R - 1)
    d = (f"M{top[0]:.1f},{top[1]:.1f} "
         f"A{R:.1f},{R:.1f} 0 1 0 {bot[0]:.1f},{bot[1]:.1f} "
         f"A{r2:.1f},{r2:.1f} 0 1 1 {top[0]:.1f},{top[1]:.1f} Z")
    cls = ' class="glow"' if animate else ""
    return (
        f'<g{cls} filter="url(#ds)">'
        f'<path d="{d}" fill="url(#moonG)"/>'
        f'<ellipse cx="{cx-r*0.18:.1f}" cy="{cy-r*0.3:.1f}" rx="{r*0.22:.1f}" ry="{r*0.32:.1f}" fill="#FFFFFF" opacity="0.30"/>'
        f"</g>"
    )


def cloud(cx, by, s=1.0, grad=CLOUD_LIGHT, drift="drift"):
    """Soft puffy cloud (multi-bump silhouette) with unified vertical gradient
    shading + drop shadow + highlight for a 3D look. (cx, by)=bottom-center."""
    def S(v):
        return v * s
    cid = nid("cl")
    gid = nid("cg")
    # silhouette shapes (overlapping bumps + flat base)
    shapes = (
        f'<rect x="{cx-S(26):.1f}" y="{by-S(13):.1f}" width="{S(52):.1f}" height="{S(15):.1f}" rx="{S(8):.1f}"/>'
        f'<circle cx="{cx-S(15):.1f}" cy="{by-S(13):.1f}" r="{S(12):.1f}"/>'
        f'<circle cx="{cx+S(2):.1f}" cy="{by-S(20):.1f}" r="{S(16):.1f}"/>'
        f'<circle cx="{cx+S(18):.1f}" cy="{by-S(12):.1f}" r="{S(11):.1f}"/>'
    )
    top_y = by - S(36)
    cls = f' class="{drift}"' if drift else ""
    return (
        f'<defs>'
        f'<clipPath id="{cid}">{shapes}</clipPath>'
        f'<linearGradient id="{gid}" x1="0" y1="{top_y:.1f}" x2="0" y2="{by:.1f}" gradientUnits="userSpaceOnUse">'
        f'<stop offset="0%" stop-color="{grad[0]}"/><stop offset="100%" stop-color="{grad[1]}"/>'
        f'</linearGradient></defs>'
        f'<g{cls} filter="url(#ds)">'
        f'<g clip-path="url(#{cid})">'
        f'<rect x="{cx-S(40):.1f}" y="{top_y:.1f}" width="{S(80):.1f}" height="{S(50):.1f}" fill="url(#{gid})"/>'
        f'<ellipse cx="{cx-S(2):.1f}" cy="{by-S(27):.1f}" rx="{S(13):.1f}" ry="{S(7):.1f}" fill="#FFFFFF" opacity="0.55"/>'
        f"</g></g>"
    )


def _drop(x, y, delay):
    d = f'M{x:.1f},{y:.1f} c 3,5 3,8 0,9 c -3,-1 -3,-4 0,-9 Z'
    return (
        f'<g class="rain" style="animation-delay:{delay:.2f}s" filter="url(#dsSoft)">'
        f'<path d="{d}" fill="url(#rainG)"/>'
        f'<circle cx="{x-1:.1f}" cy="{y+4.5:.1f}" r="0.9" fill="#FFFFFF" opacity="0.6"/>'
        f"</g>"
    )


def _flake(x, y, delay):
    return (
        f'<g class="snow" style="animation-delay:{delay:.2f}s" filter="url(#dsSoft)">'
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.8" fill="url(#snowG)" stroke="{SNOW_EDGE}" stroke-width="1"/>'
        f"</g>"
    )


def precipitation(cx, by, kind, intensity):
    count = {"light": 2, "normal": 3, "heavy": 4}[intensity]
    span = 30
    xs = [cx - span / 2 + span * (i / (count - 1) if count > 1 else 0.5) for i in range(count)]
    y0 = by + 6
    out = []
    for i, x in enumerate(xs):
        delay = i * (1.5 / max(count, 1))
        if kind == "rain":
            out.append(_drop(x, y0, delay))
        elif kind == "snow":
            out.append(_flake(x, y0 + 1, delay * 2))
        else:  # sleet -> alternate
            out.append(_drop(x, y0, delay) if i % 2 == 0 else _flake(x, y0 + 1, delay * 2))
    return "".join(out)


def lightning(cx, by):
    x, y = cx, by + 4
    d = f'M{x:.1f},{y:.1f} l -7,12 l 5,0 l -4,11 l 12,-15 l -5,0 l 6,-8 Z'
    return (
        f'<g class="bolt" filter="url(#dsSoft)">'
        f'<path d="{d}" fill="url(#boltG)"/></g>'
    )


def fog_lines(cy):
    rows = []
    for i, (w, off) in enumerate([(58, 0), (50, 6), (58, 12), (44, 18)]):
        y = cy + off
        x = 50 - w / 2
        rows.append(
            f'<line class="fog" style="animation-delay:{i*0.4:.1f}s" '
            f'x1="{x:.1f}" y1="{y:.1f}" x2="{x+w:.1f}" y2="{y:.1f}" '
            f'stroke="{FOG}" stroke-width="4.2" stroke-linecap="round"/>'
        )
    return "".join(rows)


def sky_body(tod, cx, cy, r):
    if tod == "night":
        return moon(cx, cy, r)
    if tod == "polartwilight":
        return sun(cx, cy, r, grad="twiG", ray=RAY_TWI)
    return sun(cx, cy, r)


# ---------------------------------------------------------------------------
# Composition (soft/version-1 layout)
# ---------------------------------------------------------------------------

def compose(base, tod, intensity, thunder):
    body = []
    if base == "clearsky":
        body.append(sky_body(tod, 50, 47, 17))

    elif base == "fair":
        body.append(sky_body(tod, 44, 42, 14))
        body.append(cloud(58, 74, s=0.62, drift="drift2"))

    elif base == "partlycloudy":
        body.append(sky_body(tod, 40, 40, 13))
        body.append(cloud(56, 70, s=0.82))

    elif base == "cloudy":
        body.append(cloud(46, 58, s=0.95, grad=CLOUD_GREY, drift="drift2"))
        body.append(cloud(54, 66, s=1.0, grad=CLOUD_LIGHT))

    elif base == "fog":
        body.append(cloud(50, 50, s=0.9, grad=CLOUD_GREY))
        body.append(fog_lines(58))

    elif base in ("rain", "sleet", "snow"):
        body.append(cloud(50, 52, s=0.98, grad=CLOUD_GREY))
        if thunder:
            body.append(lightning(50, 52))
        body.append(precipitation(50, 52, base, intensity))

    elif base in ("rainshowers", "sleetshowers", "snowshowers"):
        kind = base.replace("showers", "")
        body.append(sky_body(tod, 36, 38, 13))
        body.append(cloud(56, 56, s=0.86))
        if thunder:
            body.append(lightning(56, 56))
        body.append(precipitation(56, 56, kind, intensity))
    else:
        raise ValueError("unknown base: " + base)
    return "".join(body)


def parse(name):
    tod = "none"
    for suf in ("_day", "_night", "_polartwilight"):
        if name.endswith(suf):
            tod = suf[1:]
            name = name[: -len(suf)]
            break
    thunder = name.endswith("andthunder")
    if thunder:
        name = name[: -len("andthunder")]
    intensity = "normal"
    if name.startswith("light"):
        intensity, name = "light", name[len("light"):]
    elif name.startswith("heavy"):
        intensity, name = "heavy", name[len("heavy"):]
    return name, tod, intensity, thunder


def build_svg(symbol):
    global _uid
    _uid = 0
    base, tod, intensity, thunder = parse(symbol)
    inner = compose(base, tod, intensity, thunder)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" '
        f'role="img" aria-label="{symbol}">\n'
        f"<style>{STYLE}</style>\n<defs>{DEFS}</defs>\n"
        f"{inner}\n</svg>\n"
    )


def main():
    pngs = sorted(f for f in os.listdir(ICON_DIR) if f.endswith(".png"))
    for png in pngs:
        symbol = png[:-4]
        with open(os.path.join(ICON_DIR, symbol + ".svg"), "w") as fh:
            fh.write(build_svg(symbol))
    print(f"Generated {len(pngs)} SVG icons into {ICON_DIR}")


if __name__ == "__main__":
    main()
