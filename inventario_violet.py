import discord
from discord import app_commands
from discord.ext import commands
import json
import os

ARCHIVO = "inventario_violet.json"


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


class InventarioViolet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="inventario",
        description="Muestra tu inventario."
    )
    async def inventario(self, interaction: discord.Interaction):
        datos = cargar()
        servidor = datos.setdefault(str(interaction.guild.id), {})
        items = servidor.get(str(interaction.user.id), {})

        if not items:
            texto = "Tu inventario está vacío."
        else:
            texto = "\n".join(
                f"• **{nombre}** × `{cantidad}`"
                for nombre, cantidad in items.items()
                if cantidad > 0
            )

        embed = discord.Embed(
            title=f"🎒 Inventario de {interaction.user.display_name}",
            description=texto,
            color=discord.Color.purple()
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="objeto",
        description="Añade un objeto a tu inventario."
    )
    @app_commands.describe(
        nombre="Nombre del objeto."
    )
    async def objeto(
        self,
        interaction: discord.Interaction,
        nombre: str
    ):
        datos = cargar()
        servidor = datos.setdefault(str(interaction.guild.id), {})
        usuario = servidor.setdefault(str(interaction.user.id), {})

        nombre = nombre[:40]
        usuario[nombre] = usuario.get(nombre, 0) + 1

        guardar(datos)

        await interaction.response.send_message(
            f"🎒 Has obtenido **{nombre}**."
        )

    @app_commands.command(
        name="usarobjeto",
        description="Usa un objeto de tu inventario."
    )
    @app_commands.describe(
        nombre="Objeto que quieres utilizar."
    )
    async def usarobjeto(
        self,
        interaction: discord.Interaction,
        nombre: str
    ):
        datos = cargar()
        servidor = datos.setdefault(str(interaction.guild.id), {})
        usuario = servidor.setdefault(str(interaction.user.id), {})

        if usuario.get(nombre, 0) <= 0:
            await interaction.response.send_message(
                "❌ No tienes ese objeto.",
                ephemeral=True
            )
            return

        usuario[nombre] -= 1

        if usuario[nombre] <= 0:
            del usuario[nombre]

        guardar(datos)

        await interaction.response.send_message(
            f"✨ Has utilizado **{nombre}**."
        )


async def setup(bot):
    await bot.add_cog(InventarioViolet(bot))
