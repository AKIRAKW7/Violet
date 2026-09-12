from pathlib import Path

texto = Path("bot.py").read_text(encoding="utf-8")
lineas = texto.splitlines()

print("EMOJIS_VACIOS_RESTANTES:")

encontrados = 0

for numero, linea in enumerate(lineas, start=1):
    if (
        'emoji=""' in linea
        or "(''" in linea
        or '("",' in linea
        or '"emoji": ""' in linea
    ):
        print(numero, repr(linea))
        encontrados += 1

if encontrados == 0:
    print("NINGUNO")
