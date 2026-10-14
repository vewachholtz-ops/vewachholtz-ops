"""Contenido de la tarjeta (líneas de texto, colores) y versión monocroma del generador.

La tarjeta del README la genera tarjeta_color.py, que usa el contenido definido aquí.

Uso:  python tarjeta.py foto.jpg     (o cara.txt para usar un dibujo ya hecho)
Salida: dark_mode.svg y light_mode.svg en la misma carpeta.
Requiere: pip install pillow numpy scikit-image rembg onnxruntime  (rembg quita el fondo de la foto)
"""
import html
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
from skimage import exposure

# ---------- contenido ----------
USUARIO = "vicente@wachholtz"
LINEAS = [
    ("kv", "Carrera", "Ingeniería Civil Industrial"),
    ("kv", "Universidad", "Universidad de los Andes, Chile"),
    ("kv", "Foco", "Operaciones · Simulación · Cadena de suministro"),
    ("kv", "Idiomas", "Español · Inglés (B2) · Alemán (básico)"),
    ("", ),
    ("sec", "Herramientas"),
    ("kv", "Datos", "Python · SQL · pandas · DuckDB · Power BI · Excel"),
    ("kv", "Simulación", "SimPy · Arena · FlexSim"),
    ("kv", "Apps web", "React · TypeScript"),
    ("kv", "IA local", "Ollama · RAG con citas que se comprueban"),
    ("", ),
    ("sec", "Proyectos que puedes usar con tus datos"),
    ("kv", "Tolva", "¿Cuántos camiones necesita tu mina?"),
    ("kv", "Mostrador", "Tus ventas analizadas con SQL"),
    ("kv", "Tesela", "Pregúntale a tus documentos, con citas"),
    ("", ),
    ("sec", "Contacto"),
    ("kv", "LinkedIn", "linkedin.com/in/vicente-wachholtz"),
    ("kv", "Correo", "vewachholtz@gmail.com"),
]
NOTA = ""

# ---------- diseño ----------
ANCHO_SVG, ANCHO_CHARS = 985, 66        # columna de texto: 66 caracteres de 13 px
X_TEXTO, Y0, PASO = 432, 34, 20
# la cara usa la misma letra y los mismos renglones que el texto: una fila de dibujo por renglón
MODO = "tonos"                          # "tonos": escala de caracteres por oscuridad; "formas": elige el carácter de forma más parecida
RAMPA = " .,:;i1tfLCG08@"
SUBFILAS = 1                            # filas de dibujo por renglón de texto: 1 = misma letra y renglones que el texto
ARTE_FS = 13 / SUBFILAS * 1.3 if SUBFILAS > 1 else 13
ARTE_PASO, X_ARTE = PASO / SUBFILAS, 24
ARTE_COLS = int(360 / (.6 * ARTE_FS))   # el dibujo ocupa ~360 px de ancho
ENCUADRE = 1.2                          # ancho del recorte = 1,2 cabezas: zoom a la cara
GLIFO = (round(2 * .6 * ARTE_FS), round(2 * ARTE_PASO))   # celda de un carácter al comparar formas (al doble)
SUAVIZADO = .04 * GLIFO[1]
TINTA = .4
GAMMA = 0.7                             # <1 da algo de tinta a las zonas claras
BORDES = 0.3                            # 0 = solo tonos; 0,3–0,5 = estilo dibujo con contornos
CARACTERES = "".join(chr(c) for c in range(32, 127) if chr(c) not in "`")
FUENTES_MONO = ["C:/Windows/Fonts/consola.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf", "/System/Library/Fonts/Menlo.ttc"]
TEMAS = {
    "dark_mode": dict(bg="#161b22", fg="#c9d1d9", key="#ffa657", val="#a5d6ff", dots="#616e7f", sec="#7ee787"),
    "light_mode": dict(bg="#f6f8fa", fg="#24292f", key="#953800", val="#0a3069", dots="#a8b4c2", sec="#116329"),
}
FUENTE = "ConsolasFallback, Consolas, 'Courier New', monospace"


def quitar_fondo(img):
    try:
        from rembg import new_session, remove
        rgba = remove(img, session=new_session("isnet-general-use"))
        return rgba.convert("L"), np.array(rgba.split()[-1]) > 128
    except ImportError:
        print("rembg no está instalado: se usa la foto completa")
        return img.convert("L"), np.ones(img.size[::-1], bool)


def dibujar_glifos():
    """Dibuja cada carácter en una celda del mismo tamaño que en la tarjeta (al doble) y devuelve su tinta."""
    ruta = next(f for f in FUENTES_MONO if Path(f).exists())
    fuente = ImageFont.truetype(ruta, round(2 * ARTE_FS))
    cw, ch = GLIFO
    glifos = []
    for c in CARACTERES:
        im = Image.new("L", (cw, ch), 0)
        # línea base como en el SVG: renglones de 20 px con la letra centrada
        ImageDraw.Draw(im).text((0, ch * .7), c, font=fuente, fill=255, anchor="ls")
        glifos.append(np.array(im.filter(ImageFilter.GaussianBlur(SUAVIZADO)), float).ravel() / 255)
    return CARACTERES, np.array(glifos)


def por_tonos(gris, mascara, filas, oscuro):
    """Cada celda recibe un carácter según su tono. Fondo claro: lo oscuro de la foto va denso.
    Fondo oscuro: los caracteres son claros, así que lo claro de la foto va denso (si no, queda como negativo)."""
    gris = gris.filter(ImageFilter.UnsharpMask(4, 200, 2))
    gris = Image.fromarray((exposure.equalize_adapthist(np.array(gris) / 255, clip_limit=.02) * 255).astype("uint8"))
    g = np.array(gris.resize((ARTE_COLS, filas), Image.LANCZOS), float) / 255
    mk = np.array(mascara.convert("L").resize((ARTE_COLS, filas), Image.BILINEAR)) > 100
    g = np.clip(np.interp(g, np.percentile(g[mk], [3, 97]), [0, 1]), 0, 1)
    idx = np.clip(((g if oscuro else 1 - g) * (len(RAMPA) - 2)).astype(int) + 1, 1, len(RAMPA) - 1)
    return ["".join(RAMPA[i] if mk[f, c] else " " for c, i in enumerate(fila)) for f, fila in enumerate(idx)]


def foto_a_ascii(ruta, oscuro, filas):
    img = ImageOps.exif_transpose(Image.open(ruta)).convert("RGB")
    if MODO == "formas" and img.width < 1200:   # fotos chicas: se agrandan para comparar formas
        f = -(-1200 // img.width)
        img = img.resize((img.width * f, img.height * f), Image.LANCZOS)
    gris, mascara = quitar_fondo(img)
    ys, xs = np.where(mascara)
    # recorte: de la cabeza a los hombros, con un poco de margen
    y0 = ys.min()
    # ancho de la cabeza: silueta entre el 20 % y el 40 % de la altura bajo el pelo
    tramo = range(y0 + int(.20 * (img.height - y0)), y0 + int(.40 * (img.height - y0)))
    anchos = [(np.where(mascara[r])[0].min(), np.where(mascara[r])[0].max()) for r in tramo if mascara[r].any()]
    hx0, hx1 = np.median([a for a, _ in anchos]), np.median([b for _, b in anchos])
    cx, ancho = (hx0 + hx1) / 2, (hx1 - hx0) * ENCUADRE
    caja = (int(max(0, cx - ancho / 2)), int(y0),
            int(min(img.width, cx + ancho / 2)), int(min(img.height, y0 + ancho * filas * ARTE_PASO / (ARTE_COLS * .6 * ARTE_FS))))
    gris, mascara = gris.crop(caja), Image.fromarray(mascara).crop(caja)
    if MODO == "tonos":
        return por_tonos(gris, mascara, filas, oscuro)
    # contraste local suave: más fuerte mete ruido en el pelo y borra los ojos
    gris = Image.fromarray((exposure.equalize_adapthist(np.array(gris) / 255, clip_limit=.01) * 255).astype("uint8"))
    # cada celda de la foto se compara con el dibujo de cada carácter y se elige el de forma más parecida
    cw, ch = GLIFO
    g = np.array(gris.resize((ARTE_COLS * cw, filas * ch), Image.LANCZOS).filter(ImageFilter.GaussianBlur(SUAVIZADO)), float) / 255
    mk = np.array(mascara.convert("L").resize((ARTE_COLS, filas), Image.BILINEAR)) > 100
    mkp = np.array(mascara.convert("L").resize((ARTE_COLS * cw, filas * ch), Image.BILINEAR)) > 100
    g = np.clip(np.interp(g, np.percentile(g[mkp], [2, 98]), [0, 1]), 0, 1)
    # TINTA ajusta la cantidad de tinta a lo que cabe en un carácter
    # + BORDES: suma el contorno (mandíbula, nariz, ojos) para que se vea aunque esa zona esté muy iluminada
    gy, gx = np.gradient(g)
    borde = np.hypot(gx, gy)
    borde = np.clip(borde / (np.percentile(borde[mkp], 97) + 1e-6), 0, 1)
    tono = g if oscuro else 1 - g           # fondo oscuro: lo claro de la foto lleva tinta (caracteres claros)
    tinta = np.where(mkp, (tono ** GAMMA * (1 - BORDES) + borde * BORDES) * TINTA, 0)
    celdas = tinta.reshape(filas, ch, ARTE_COLS, cw).transpose(0, 2, 1, 3).reshape(filas * ARTE_COLS, ch * cw)
    chars, glifos = dibujar_glifos()
    dist = (celdas ** 2).sum(1)[:, None] - 2 * celdas @ glifos.T + (glifos ** 2).sum(1)[None, :]
    idx = dist.argmin(1).reshape(filas, ARTE_COLS)
    return ["".join(chars[i] if mk[f, c] else " " for c, i in enumerate(fila)) for f, fila in enumerate(idx)]


def linea_kv(k, v, t):
    puntos = "." * max(2, ANCHO_CHARS - len(k) - len(v) - 6)
    return (f'<tspan fill="{t["dots"]}">. </tspan><tspan fill="{t["key"]}">{html.escape(k)}</tspan>'
            f'<tspan fill="{t["dots"]}">: {puntos} </tspan><tspan fill="{t["val"]}">{html.escape(v)}</tspan>')


def svg(arte, t):
    texto = [f'<tspan fill="{t["key"]}">{USUARIO}</tspan><tspan fill="{t["dots"]}"> {"—" * (ANCHO_CHARS - len(USUARIO) - 1)}</tspan>']
    for l in LINEAS:
        if not l[0]:
            texto.append("")
        elif l[0] == "sec":
            texto.append(f'<tspan fill="{t["sec"]}">— {html.escape(l[1])} </tspan><tspan fill="{t["dots"]}">{"—" * (ANCHO_CHARS - len(l[1]) - 3)}</tspan>')
        else:
            texto.append(linea_kv(l[1], l[2], t))
    texto.append(f'<tspan fill="{t["dots"]}">{" " * (ANCHO_CHARS - len(NOTA))}{NOTA}</tspan>')
    alto = Y0 + (len(texto) - 1) * PASO + 24
    y_arte = Y0                              # misma línea base que el texto
    partes = [f'<svg xmlns="http://www.w3.org/2000/svg" font-family="{FUENTE}" width="{ANCHO_SVG}px" height="{alto}px" font-size="13px">',
              "<style>@font-face{src:local('Consolas'),local('Consolas Bold');font-family:'ConsolasFallback';font-display:swap;-webkit-size-adjust:109%;size-adjust:109%}text,tspan{white-space:pre}</style>",
              f'<rect width="{ANCHO_SVG}px" height="{alto}px" fill="{t["bg"]}" rx="15"/>',
              f'<text x="{X_ARTE}" y="{y_arte}" fill="{t["fg"]}" font-size="{ARTE_FS}px">']
    # el dibujo va del primer al último renglón del texto
    paso_arte = (len(texto) - 1) * PASO / max(1, len(arte) - 1)
    partes += [f'<tspan x="{X_ARTE}" y="{y_arte + i * paso_arte:.1f}">{html.escape(f)}</tspan>' for i, f in enumerate(arte)]
    partes.append(f'</text><text x="{X_TEXTO}" y="{Y0}" fill="{t["fg"]}">')
    partes += [f'<tspan x="{X_TEXTO}" y="{Y0 + i * PASO}">{l}</tspan>' for i, l in enumerate(texto)]
    partes.append("</text></svg>")
    return "".join(partes)


if __name__ == "__main__":
    foto = sys.argv[1] if len(sys.argv) > 1 else "foto.jpg"
    destino = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".")
    for nombre, t in TEMAS.items():
        if foto.endswith(".txt"):          # dibujo ya hecho (por ejemplo cara.txt): se usa tal cual
            # en fondo oscuro los caracteres son claros: se usa la versión en que lo denso es lo claro de la foto
            oscura = Path(foto).with_name(Path(foto).stem + "-oscura.txt")
            ruta = oscura if nombre == "dark_mode" and oscura.exists() else Path(foto)
            arte = ruta.read_text(encoding="utf-8").splitlines()
        else:
            arte = foto_a_ascii(foto, nombre == "dark_mode", SUBFILAS * (len(LINEAS) + 1) + 1)
        (destino / f"{nombre}.svg").write_text(svg(arte, t), encoding="utf-8")
        print("listo:", destino / f"{nombre}.svg")
