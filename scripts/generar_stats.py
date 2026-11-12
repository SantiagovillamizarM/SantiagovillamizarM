"""Genera las tarjetas de estadisticas (negro / oro / blanco) en assets/.

Usa la API REST de GitHub. Si existe la variable GITHUB_TOKEN la usa para
tener mas limite de peticiones; sin ella tambien funciona.
"""

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

USUARIO = os.environ.get("GH_USER", "SantiagovillamizarM")
TOKEN = os.environ.get("GITHUB_TOKEN")
SALIDA = Path(__file__).resolve().parent.parent / "assets"

GOLD = "#D4AF37"
FONT = "'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif"


def api(ruta):
    req = urllib.request.Request(f"https://api.github.com{ruta}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "readme-stats-generator")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def total_busqueda(tipo, q):
    try:
        return api(f"/search/{tipo}?q={urllib.parse.quote(q)}&per_page=1")["total_count"]
    except Exception:
        return 0


def obtener_datos():
    usuario = api(f"/users/{USUARIO}")
    repos, pagina = [], 1
    while True:
        lote = api(f"/users/{USUARIO}/repos?per_page=100&page={pagina}&type=owner")
        repos += lote
        if len(lote) < 100:
            break
        pagina += 1
    propios = [r for r in repos if not r["fork"]]

    lenguajes = {}
    for r in propios:
        for nombre, bytes_ in api(f"/repos/{USUARIO}/{r['name']}/languages").items():
            lenguajes[nombre] = lenguajes.get(nombre, 0) + bytes_

    return {
        "repos": len(propios),
        "estrellas": sum(r["stargazers_count"] for r in propios),
        "seguidores": usuario["followers"],
        "commits": total_busqueda("commits", f"author:{USUARIO}"),
        "prs": total_busqueda("issues", f"author:{USUARIO} type:pr"),
        "lenguajes": lenguajes,
    }


def marco(ancho, alto, titulo, cuerpo):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho} {alto}" width="{ancho}" height="{alto}" role="img" aria-label="{escape(titulo)}">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{GOLD}"/><stop offset="100%" stop-color="{GOLD}" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <style>
    text {{ font-family: {FONT}; }}
    .in {{ opacity: 0; animation: in .8s ease-out forwards; }}
    @keyframes in {{ from {{ opacity: 0; transform: translateX(-8px); }} to {{ opacity: 1; transform: none; }} }}
    .bar {{ transform-box: fill-box; transform-origin: left; transform: scaleX(0); animation: grow 1.2s ease-out forwards; }}
    @keyframes grow {{ to {{ transform: scaleX(1); }} }}
  </style>
  <rect x="1" y="1" width="{ancho - 2}" height="{alto - 2}" rx="12" fill="#0D0D0D" stroke="{GOLD}" stroke-opacity=".7"/>
  <text x="26" y="40" fill="{GOLD}" font-size="15" font-weight="600" letter-spacing="4">{escape(titulo)}</text>
  <rect x="26" y="52" width="{ancho - 52}" height="1" fill="url(#g)"/>
{cuerpo}
</svg>
"""


def tarjeta_stats(d):
    filas = [
        ("Repositorios públicos", d["repos"]),
        ("Commits", d["commits"]),
        ("Lenguajes utilizados", len(d["lenguajes"])),
        ("Seguidores", d["seguidores"]),
    ]
    if d["estrellas"]:
        filas.append(("Estrellas", d["estrellas"]))
    if d["prs"]:
        filas.append(("Pull requests", d["prs"]))
    filas = filas[:5]
    cuerpo = ""
    for i, (etiqueta, valor) in enumerate(filas):
        y = 86 + i * 27
        cuerpo += (
            f'  <g class="in" style="animation-delay:{i * 0.12:.2f}s">\n'
            f'    <g transform="translate(32 {y - 5}) rotate(45)"><rect x="-3.5" y="-3.5" width="7" height="7" fill="{GOLD}"/></g>\n'
            f'    <text x="48" y="{y}" fill="#E6E6E6" font-size="14">{escape(etiqueta)}</text>\n'
            f'    <text x="374" y="{y}" fill="#FFFFFF" font-size="15" font-weight="700" text-anchor="end">{valor}</text>\n'
            f"  </g>\n"
        )
    return marco(400, 210, "ESTADÍSTICAS", cuerpo)


def tarjeta_lenguajes(d):
    total = sum(d["lenguajes"].values()) or 1
    top = sorted(d["lenguajes"].items(), key=lambda x: -x[1])[:5]
    tonos = ["#F7DC8A", "#D4AF37", "#B8892B", "#8C6A1E", "#FFFFFF"]
    cuerpo = ""
    for i, (nombre, bytes_) in enumerate(top):
        pct = bytes_ / total * 100
        y = 84 + i * 26
        cuerpo += (
            f'  <g class="in" style="animation-delay:{i * 0.12:.2f}s">\n'
            f'    <text x="26" y="{y}" fill="#E6E6E6" font-size="13">{escape(nombre)}</text>\n'
            f'    <text x="374" y="{y}" fill="{GOLD}" font-size="13" font-weight="600" text-anchor="end">{pct:.1f}%</text>\n'
            f'    <rect x="130" y="{y - 9}" width="190" height="8" rx="4" fill="#FFFFFF" fill-opacity=".08"/>\n'
            f'    <rect class="bar" style="animation-delay:{i * 0.12:.2f}s" x="130" y="{y - 9}" width="{max(pct / 100 * 190, 4):.1f}" height="8" rx="4" fill="{tonos[i]}"/>\n'
            f"  </g>\n"
        )
    return marco(400, 210, "LENGUAJES MÁS USADOS", cuerpo)


def main():
    d = obtener_datos()
    SALIDA.mkdir(exist_ok=True)
    (SALIDA / "stats.svg").write_text(tarjeta_stats(d), encoding="utf-8")
    (SALIDA / "lenguajes.svg").write_text(tarjeta_lenguajes(d), encoding="utf-8")
    print({k: v for k, v in d.items() if k != "lenguajes"}, sorted(d["lenguajes"], key=lambda k: -d["lenguajes"][k])[:5])


if __name__ == "__main__":
    main()
