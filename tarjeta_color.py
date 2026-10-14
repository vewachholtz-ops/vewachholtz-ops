"""Tarjeta del perfil con la cara en ASCII a color, estilo fastfetch.

La cara usa la misma letra y los mismos renglones que el texto, pero es más alta que el bloque
de texto; el texto va centrado verticalmente a su lado. Cada carácter lleva el color de la foto.

Uso:    python tarjeta_color.py foto.jpg assets
        python tarjeta_color.py --solo-texto assets   (cambia el texto y deja la cara que ya está en el SVG)
Requiere: pip install pillow numpy scikit-image rembg onnxruntime
La foto no se sube al repo (.gitignore).
Salida: assets/dark_mode.svg (la tarjeta es oscura; el README la usa en los dos temas de GitHub)
"""
import colorsys
import html
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
from skimage import exposure

import tarjeta as base  # contenido (LINEAS, USUARIO, NOTA), colores del tema y quitar_fondo

FS, PASO, CW = 13, 17, 13 * .6         # letra de 13 px, renglones de 17 px (como una terminal)
ARTE_COLS, X_ARTE = 64, 28
X_TEXTO, ANCHO_CHARS = 28 + 64 * CW + 40, 66
ANCHO_SVG = int(X_TEXTO + ANCHO_CHARS * CW + 34)
ENCUADRE, PROPORCION = 1.35, 1.35       # ancho = 1,35 cabezas; alto = 1,35 × ancho (cabeza, cuello y algo de hombros)
# de menos a más tinta; en fondo oscuro lo claro de la foto va con los caracteres más densos
RAMPA = " .'`^\",:;Il!i~+_-?][}{1)(|/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
NEGRITA = .72                           # brillo desde el que el carácter va en negrita
COLOR_NATURAL = True                    # True: color real de la foto; False: color con más contraste


def foto_a_color(ruta):
    img = ImageOps.exif_transpose(Image.open(ruta)).convert("RGB")
    if img.width < 1200:
        f = -(-1200 // img.width)
        img = img.resize((img.width * f, img.height * f), Image.LANCZOS)
    _, mascara = base.quitar_fondo(img)
    ys, _ = np.where(mascara)
    y0 = ys.min()
    tramo = range(y0 + int(.20 * (img.height - y0)), y0 + int(.40 * (img.height - y0)))
    anchos = [(np.where(mascara[r])[0].min(), np.where(mascara[r])[0].max()) for r in tramo if mascara[r].any()]
    hx0, hx1 = np.median([a for a, _ in anchos]), np.median([b for _, b in anchos])
    cx, ancho = (hx0 + hx1) / 2, (hx1 - hx0) * ENCUADRE
    caja = (int(max(0, cx - ancho / 2)), int(y0), int(min(img.width, cx + ancho / 2)), int(min(img.height, y0 + ancho * PROPORCION)))
    rgb, mk = img.crop(caja), Image.fromarray(mascara).crop(caja)
    filas = round(ARTE_COLS * rgb.height / rgb.width * CW / PASO)
    c = np.array(rgb.resize((ARTE_COLS, filas), Image.LANCZOS), float) / 255
    mk = np.array(mk.convert("L").resize((ARTE_COLS, filas), Image.BILINEAR)) > 110
    # brillo con contraste local suave, estirado dentro de la silueta
    lum = c @ [.299, .587, .114]
    lum = exposure.equalize_adapthist(lum, clip_limit=.012)
    lum = np.clip(np.interp(lum, np.percentile(lum[mk], [2, 99]), [0, 1]), 0, 1)
    filas_out = []
    for f in range(filas):
        fila = []
        for k in range(ARTE_COLS):
            if not mk[f, k]:
                fila.append((" ", None, False))
                continue
            L = lum[f, k]
            ch = RAMPA[max(1, min(len(RAMPA) - 1, int(L * (len(RAMPA) - 1))))]
            h, s, _ = colorsys.rgb_to_hsv(*c[f, k])
            if COLOR_NATURAL:                     # color real de la foto, aclarado para fondo oscuro
                v = min(1, .15 + 1.1 * colorsys.rgb_to_hsv(*c[f, k])[2] ** .8) * (.35 + .65 * L)
            else:
                v = .10 + .90 * L ** 1.3          # lo oscuro queda casi apagado, lo claro brillante
            r, g, b = colorsys.hsv_to_rgb(h, min(1, s * 1.3), v)
            col = "#%02x%02x%02x" % tuple(int(round(x * 255 / 12) * 12) for x in (r, g, b))  # pocos colores = SVG liviano
            fila.append((ch, col, L >= NEGRITA))
        filas_out.append(fila)
    return filas_out


def linea_arte(fila):
    out, previo = [], None
    for ch, col, neg in fila:
        clave = (col, neg)
        if ch == " " or col is None:
            clave = None
        if out and clave == previo:
            out[-1][1] += ch
        else:
            out.append([clave, ch])
            previo = clave
    partes = []
    for clave, txt in out:
        txt = html.escape(txt)
        if clave is None:
            partes.append(txt)
        else:
            col, neg = clave
            partes.append(f'<tspan fill="{col}"{" font-weight=\"bold\"" if neg else ""}>{txt}</tspan>')
    return "".join(partes)


def texto_tarjeta(t):
    base.ANCHO_CHARS = ANCHO_CHARS
    lineas = [f'<tspan fill="{t["key"]}">{base.USUARIO}</tspan><tspan fill="{t["dots"]}"> {"—" * (ANCHO_CHARS - len(base.USUARIO) - 1)}</tspan>']
    for l in base.LINEAS:
        if not l[0]:
            lineas.append("")
        elif l[0] == "sec":
            lineas.append(f'<tspan fill="{t["sec"]}">— {html.escape(l[1])} </tspan><tspan fill="{t["dots"]}">{"—" * (ANCHO_CHARS - len(l[1]) - 3)}</tspan>')
        else:
            lineas.append(base.linea_kv(l[1], l[2], t))
    lineas.append(f'<tspan fill="{t["dots"]}">{" " * (ANCHO_CHARS - len(base.NOTA))}{base.NOTA}</tspan>')
    return lineas


def svg(arte, t):
    return armar([linea_arte(f) for f in arte], t)


def armar(arte, t):
    """El SVG con las filas de la cara ya convertidas a tspans y el texto de la tarjeta."""
    texto = texto_tarjeta(t)
    filas = max(len(arte), len(texto))
    y0 = 40
    alto = int(y0 + (filas - 1) * PASO + 30)
    inicio_texto = (filas - len(texto)) // 2      # texto centrado, en la misma grilla de renglones que la cara
    inicio_arte = (filas - len(arte)) // 2
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" font-family="{base.FUENTE}" width="{ANCHO_SVG}px" height="{alto}px" font-size="{FS}px">',
         "<style>@font-face{src:local('Consolas'),local('Consolas Bold');font-family:'ConsolasFallback';font-display:swap;-webkit-size-adjust:109%;size-adjust:109%}text,tspan{white-space:pre}</style>",
         f'<rect width="{ANCHO_SVG}px" height="{alto}px" fill="{t["bg"]}" rx="15"/>',
         f'<text x="{X_ARTE}" y="{y0}">']
    p += [f'<tspan x="{X_ARTE}" y="{y0 + (inicio_arte + i) * PASO}">{f}</tspan>' for i, f in enumerate(arte)]
    p.append(f'</text><text x="{X_TEXTO:.0f}" y="{y0}" fill="{t["fg"]}">')
    p += [f'<tspan x="{X_TEXTO:.0f}" y="{y0 + (inicio_texto + i) * PASO}">{l}</tspan>' for i, l in enumerate(texto)]
    p.append("</text></svg>")
    return "".join(p)


def cara_del_svg(ruta):
    """Las filas de la cara de un SVG ya generado, para rehacer solo el texto sin la foto."""
    s = Path(ruta).read_text(encoding="utf-8")
    inicio = s.index(f'<text x="{X_ARTE}" y=')
    bloque = s[s.index(">", inicio) + 1 : s.index("</text>", inicio)]
    filas = bloque.split(f'<tspan x="{X_ARTE}" y="')[1:]
    return [f[f.index('">') + 2 : -len("</tspan>")] for f in filas]


if __name__ == "__main__":
    if sys.argv[1:2] == ["--solo-texto"]:
        destino = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".")
        ruta = destino / "dark_mode.svg"
        ruta.write_text(armar(cara_del_svg(ruta), base.TEMAS["dark_mode"]), encoding="utf-8")
        print("listo:", ruta)
        sys.exit()
    foto = sys.argv[1] if len(sys.argv) > 1 else "foto.jpg"
    destino = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".")
    (destino / "dark_mode.svg").write_text(svg(foto_a_color(foto), base.TEMAS["dark_mode"]), encoding="utf-8")
    print("listo:", destino / "dark_mode.svg")
