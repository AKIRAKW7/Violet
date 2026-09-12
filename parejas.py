import discord
from discord import app_commands
from discord.ext import commands
import random
import json
import os

ARCHIVO = "parejas.json"


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


class Parejas(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="compatibilidad",
        description="Calcula la compatibilidad entre dos usuarios."
    )
    async def compatibilidad(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member
    ):
        if usuario.id == interaction.user.id:
            porcentaje = 100
        else:
            base = f"{min(interaction.user.id, usuario.id)}:{max(interaction.user.id, usuario.id)}"
            random.seed(base)
            porcentaje = random.randint(0, 100)

        if porcentaje >= 90:
            mensaje = "Una conexión extraordinaria."
        elif porcentaje >= 70:
            mensaje = "Hay una química bastante fuerte."
        elif porcentaje >= 50:
            mensaje = "Podrían llevarse bastante bien."
        elif porcentaje >= 30:
            mensaje = "Hay potencial, pero Violet tendrá que investigar."
        else:
            mensaje = "La compatibilidad parece bastante complicada."

        embed = discord.Embed(
            title="💜 Compatibilidad Violet",
            description=(
                f"{interaction.user.mention} × {usuario.mention}\n\n"
                f"**Compatibilidad:** `{porcentaje}%`\n\n"
                f"{mensaje}"
            ),
            color=discord.Color.magenta()
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="pareja",
        description="Registra una pareja."
    )
    async def pareja(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member
    ):
        if usuario.id == interaction.user.id:
            await interaction.response.send_message(
                "No puedes registrarte como tu propia pareja.",
                ephemeral=True
            )
            return

        datos = cargar()
        servidor = datos.setdefault(
            str(interaction.guild.id),
            {}
        )

        servidor[str(interaction.user.id)] = usuario.id
        servidor[str(usuario.id)] = interaction.user.id

        guardar(datos)

        await interaction.response.send_message(
            f"💜 {interaction.user.mention} y {usuario.mention} "
            f"ahora aparecen como pareja."
        )

    @app_commands.command(
        name="mipareja",
        description="Muestra tu pareja registrada."
    )
    async def mipareja(self, interaction: discord.Interaction):
        datos = cargar()
        servidor = datos.get(str(interaction.guild.id), {})

        pareja_id = servidor.get(str(interaction.user.id))

        if not pareja_id:
            await interaction.response.send_message(
                "No tienes una pareja registrada."
            )
            return

        pareja = interaction.guild.get_member(int(pareja_id))

        if not pareja:
            await interaction.response.send_message(
                "Tu pareja registrada ya no está en el servidor."
            )
            return

        await interaction.response.send_message(
            f"💜 Tu pareja registrada es {pareja.mention}."
        )


async def setup(bot):
    await bot.add_cog(Parejas(bot))
