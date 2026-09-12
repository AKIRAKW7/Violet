import discord
from discord import app_commands
from discord.ext import commands
import json
import os

ARCHIVO = "bienvenida_violet.json"


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


class BienvenidaViolet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="bienvenida",
        description="Configura el canal de bienvenida."
    )
    @app_commands.describe(
        canal="Canal donde Violet enviará las bienvenidas."
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def bienvenida(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel
    ):
        datos = cargar()

        datos[str(interaction.guild.id)] = {
            "bienvenida": canal.id
        }

        guardar(datos)

        await interaction.response.send_message(
            f"✅ Las bienvenidas se enviarán en {canal.mention}."
        )

    @app_commands.command(
        name="despedida",
        description="Configura el canal de despedidas."
    )
    @app_commands.describe(
        canal="Canal donde Violet enviará las despedidas."
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def despedida(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel
    ):
        datos = cargar()

        servidor = datos.setdefault(
            str(interaction.guild.id),
            {}
        )

        servidor["despedida"] = canal.id

        guardar(datos)

        await interaction.response.send_message(
            f"✅ Las despedidas se enviarán en {canal.mention}."
        )


async def setup(bot):
    await bot.add_cog(BienvenidaViolet(bot))
