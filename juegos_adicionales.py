import discord
from discord import app_commands
from discord.ext import commands
import random
import json
import os

class JuegosAdicionales(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="coinflip", description="Lanza una moneda.")
    async def coinflip(self, interaction: discord.Interaction):
        resultado = random.choice(["Cara", "Cruz"])
        await interaction.response.send_message(
            f"🪙 La moneda cayó en **{resultado}**."
        )

    @app_commands.command(name="dado", description="Lanza un dado.")
    @app_commands.describe(caras="Cantidad de caras del dado.")
    async def dado(
        self,
        interaction: discord.Interaction,
        caras: app_commands.Range[int, 2, 100]
    ):
        resultado = random.randint(1, caras)
        await interaction.response.send_message(
            f"🎲 Resultado: **{resultado}** / {caras}"
        )

    @app_commands.command(name="numero", description="Violet elige un número.")
    @app_commands.describe(minimo="Número mínimo.", maximo="Número máximo.")
    async def numero(
        self,
        interaction: discord.Interaction,
        minimo: int,
        maximo: int
    ):
        if minimo >= maximo:
            await interaction.response.send_message(
                "El mínimo debe ser menor que el máximo.",
                ephemeral=True
            )
            return

        resultado = random.randint(minimo, maximo)

        await interaction.response.send_message(
            f"🔮 Violet eligió **{resultado}**."
        )


async def setup(bot):
    await bot.add_cog(JuegosAdicionales(bot))
