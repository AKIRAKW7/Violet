from pathlib import Path

lineas = Path("bot.py").read_text(encoding="utf-8").splitlines()

for numero, linea in enumerate(lineas, start=1):
    if 1861 <= numero <= 1877:
        print(numero, linea)
