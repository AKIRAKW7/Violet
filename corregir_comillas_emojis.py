from pathlib import Path

ruta = Path("bot.py")
texto = ruta.read_text(encoding="utf-8")

emojis = [
    "💋", "🫂", "🐾", "👋", "🤗", "🙌", "👉", "🦷",
    "💃", "😴", "💞", "💖", "💍", "🌹", "👑"
]

corregidos = 0

for emoji in emojis:
    antiguo = f'("{emoji}"",'
    nuevo = f'("{emoji}",'
    cantidad = texto.count(antiguo)

    if cantidad:
        texto = texto.replace(antiguo, nuevo)
        corregidos += cantidad

ruta.write_text(texto, encoding="utf-8")

print("COMILLAS_EMOJIS_CORREGIDAS:", corregidos)
