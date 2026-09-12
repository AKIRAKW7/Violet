import discord
from discord import app_commands
from discord.ext import commands
import random
import json
import os

ARCHIVO = "social_avanzado.json"


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


ACCIONES = {
    "mimar": [
        "le da mimos a {objetivo}",
        "abraza suavemente a {objetivo}",
        "cuida con cariño a {objetivo}"
    ],
    "cosquillas": [
        "le hace cosquillas a {objetivo}",
        "ataca con cosquillas a {objetivo}",
        "no deja de hacerle cosquillas a {objetivo}"
    ],
    "mirar": [
        "mira fijamente a {objetivo}",
        "observa a {objetivo} en silencio",
        "se queda mirando a {objetivo}"
    ],
    "sonreir": [
        "le sonríe a {objetivo}",
        "sonríe junto a {objetivo}",
        "le dedica una sonrisa a {objetivo}"
    ]
}


class SocialAvanzado(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def accion(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        tipo: str
    ):
        if usuario.id == interaction.user.id:
            texto = "No puedes realizar esta interacción contigo mismo."
            await interaction.response.send_message(texto, ephemeral=True)
            return

        datos = cargar()

        servidor = datos.setdefault(
            str(interaction.guild.id),
            {}
        )

        usuario_data = servidor.setdefault(
            str(interaction.user.id),
            {}
        )

        usuario_data[tipo] = usuario_data.get(tipo, 0) + 1

        guardar(datos)

        frase = random.choice(ACCIONES[tipo]).format(
            objetivo=usuario.mention
        )

        await interaction.response.send_message(
            f"💜 {interaction.user.mention} {frase}."
        )

    @app_commands.command(
        name="mimar",
        description="Mima a otro usuario."
    )
    async def mimar(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member
    ):
        await self.accion(interaction, usuario, "mimar")

    @app_commands.command(
        name="cosquillas",
        description="Hazle cosquillas a otro usuario."
    )
    async def cosquillas(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member
    ):
        await self.accion(interaction, usuario, "cosquillas")

    @app_commands.command(
        name="mirar",
        description="Mira fijamente a otro usuario."
    )
    async def mirar(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member
    ):
        await self.accion(interaction, usuario, "mirar")

    @app_commands.command(
        name="sonreir",
        description="Sonríe a otro usuario."
    )
    async def sonreir(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member
    ):
        await self.accion(interaction, usuario, "sonreir")


async def setup(bot):
    await bot.add_cog(SocialAvanzado(bot))
