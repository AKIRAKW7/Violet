import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import random

ARCHIVO = "mascotas_avanzadas.json"


def cargar():
    if not os.path.exists(ARCHIVO):
        return {}
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def guardar(datos):
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=4)


class MascotasAvanzadas(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="mascota",
        description="Muestra información de tu mascota."
    )
    async def mascota(self, interaction: discord.Interaction):
        datos = cargar()
        servidor = datos.setdefault(str(interaction.guild.id), {})

        mascota = servidor.setdefault(
            str(interaction.user.id),
            {
                "nombre": "Violet",
                "nivel": 1,
                "felicidad": 100,
                "energia": 100,
                "experiencia": 0
            }
        )

        embed = discord.Embed(
            title=f"🐾 Mascota de {interaction.user.display_name}",
            color=discord.Color.purple()
        )

        embed.add_field(
            name="Nombre",
            value=mascota["nombre"]
        )
        embed.add_field(
            name="Nivel",
            value=str(mascota["nivel"])
        )
        embed.add_field(
            name="❤️ Felicidad",
            value=f"{mascota['felicidad']}/100"
        )
        embed.add_field(
            name="⚡ Energía",
            value=f"{mascota['energia']}/100"
        )
        embed.add_field(
            name="⭐ XP",
            value=str(mascota["experiencia"])
        )

        guardar(datos)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="alimentar",
        description="Alimenta a tu mascota."
    )
    async def alimentar(self, interaction: discord.Interaction):
        datos = cargar()
        servidor = datos.setdefault(str(interaction.guild.id), {})

        mascota = servidor.setdefault(
            str(interaction.user.id),
            {
                "nombre": "Violet",
                "nivel": 1,
                "felicidad": 100,
                "energia": 100,
                "experiencia": 0
            }
        )

        mascota["felicidad"] = min(100, mascota["felicidad"] + 10)
        mascota["experiencia"] += random.randint(5, 15)

        if mascota["experiencia"] >= 100:
            mascota["experiencia"] = 0
            mascota["nivel"] += 1
            mensaje = f" 🎉 ¡Subió al nivel {mascota['nivel']}!"
        else:
            mensaje = ""

        guardar(datos)

        await interaction.response.send_message(
            f"🍖 Alimentaste a **{mascota['nombre']}**.{mensaje}"
        )

    @app_commands.command(
        name="jugar_mascota",
        description="Juega con tu mascota."
    )
    async def jugar_mascota(self, interaction: discord.Interaction):
        datos = cargar()
        servidor = datos.setdefault(str(interaction.guild.id), {})

        mascota = servidor.setdefault(
            str(interaction.user.id),
            {
                "nombre": "Violet",
                "nivel": 1,
                "felicidad": 100,
                "energia": 100,
                "experiencia": 0
            }
        )

        if mascota["energia"] < 10:
            await interaction.response.send_message(
                "😴 Tu mascota necesita descansar."
            )
            return

        mascota["energia"] -= 10
        mascota["felicidad"] = min(100, mascota["felicidad"] + 15)
        mascota["experiencia"] += 10

        guardar(datos)

        await interaction.response.send_message(
            f"🎾 Jugaste con **{mascota['nombre']}**. "
            f"❤️ Felicidad: `{mascota['felicidad']}/100`"
        )


async def setup(bot):
    await bot.add_cog(MascotasAvanzadas(bot))
