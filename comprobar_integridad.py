from pathlib import Path

texto = Path("bot.py").read_text(encoding="utf-8")

print("CARACTERES_DANADOS:", texto.count("\uFFFD"))
print("TOTAL_LINEAS:", len(texto.splitlines()))

if "\uFFFD" not in texto:
    print("CODIFICACION_OK")
