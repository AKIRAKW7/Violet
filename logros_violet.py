import discord
from discord import app_commands
from discord.ext import commands
import json
import os

ARCHIVO = "logros_violet.json"

LOGROS = {
    "primer_mensaje": ("💬", "Primer mensaje", "Escribe tu primer mensaje."),
    "nivel_5": ("⭐", "Nivel 5", "Alcanza el nivel 5."),
    "nivel_10": ("🌟", "Nivel 10", "Alcanza el nivel 10."),
    "social_10": ("💜", "Social", "Realiza 10 interacciones sociales."),
    "rico": ("💰", "Pequeño magnate", "Alcanza 10.000 monedas."),
}


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


class LogrosViolet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="logros",
        description="Muestra tus logros."
    )
    async def logros(self, interaction: discord.Interaction):
        datos = cargar()

        servidor = datos.setdefault(
            str(interaction.guild.id),
            {}
        )

        usuario = servidor.setdefault(
            str(interaction.user.id),
            []
        )

        lineas = []

        for clave, (emoji, nombre, descripcion) in LOGROS.items():
            if clave in usuario:
                lineas.append(
                    f"{emoji} **{nombre}** — {descripcion}"
                )
            else:
                lineas.append(
                    f"🔒 **{nombre}** — Bloqueado"
                )

        guardar(datos)

        embed = discord.Embed(
            title=f"🏆 Logros de {interaction.user.display_name}",
            description="\n".join(lineas),
            color=discord.Color.purple()
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="logro",
        description="Desbloquea un logro manualmente para pruebas."
    )
    @app_commands.describe(
        logro="Nombre interno del logro."
    )
    async def logro(
        self,
        interaction: discord.Interaction,
        logro: str
    ):
        if logro not in LOGROS:
            await interaction.response.send_message(
                "❌ Ese logro no existe.",
                ephemeral=True
            )
            return

        datos = cargar()

        servidor = datos.setdefault(
            str(interaction.guild.id),
            {}
        )

        usuario = servidor.setdefault(
            str(interaction.user.id),
            []
        )

        if logro not in usuario:
            usuario.append(logro)

        guardar(datos)

        emoji, nombre, descripcion = LOGROS[logro]

        await interaction.response.send_message(
            f"{emoji} **Logro desbloqueado:** {nombre}"
        )


async def setup(bot):
    await bot.add_cog(LogrosViolet(bot))
