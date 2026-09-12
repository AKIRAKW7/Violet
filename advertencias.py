import discord
from discord import app_commands
from discord.ext import commands
import json
import os


ARCHIVO = "warnings.json"


def cargar_warnings():
    if not os.path.exists(ARCHIVO):
        return {}

    try:
        with open(ARCHIVO, "r", encoding="utf-8") as archivo:
            return json.load(archivo)
    except Exception:
        return {}


def guardar_warnings(datos):
    with open(ARCHIVO, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, ensure_ascii=False, indent=4)


class Advertencias(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="warn", description="Advierte a un miembro.")
    @app_commands.describe(
        miembro="Miembro que recibirá la advertencia.",
        razon="Razón de la advertencia."
    )
    @app_commands.default_permissions(moderate_members=True)
    async def warn(
        self,
        interaction: discord.Interaction,
        miembro: discord.Member,
        razon: str = "Sin especificar"
    ):
        datos = cargar_warnings()

        guild_id = str(interaction.guild.id)
        user_id = str(miembro.id)

        datos.setdefault(guild_id, {})
        datos[guild_id].setdefault(user_id, [])

        datos[guild_id][user_id].append({
            "razon": razon,
            "moderador": interaction.user.id
        })

        guardar_warnings(datos)

        cantidad = len(datos[guild_id][user_id])

        await interaction.response.send_message(
            f"⚠️ **{miembro}** recibió una advertencia.\n"
            f"**Razón:** {razon}\n"
            f"**Advertencias:** `{cantidad}`"
        )

    @app_commands.command(name="warnings", description="Consulta las advertencias de un miembro.")
    @app_commands.describe(miembro="Miembro que quieres consultar.")
    @app_commands.default_permissions(moderate_members=True)
    async def warnings(
        self,
        interaction: discord.Interaction,
        miembro: discord.Member
    ):
        datos = cargar_warnings()

        guild_id = str(interaction.guild.id)
        user_id = str(miembro.id)

        lista = datos.get(guild_id, {}).get(user_id, [])

        embed = discord.Embed(
            title=f"⚠️ Advertencias de {miembro.display_name}",
            color=discord.Color.orange()
        )

        if not lista:
            embed.description = "Este usuario no tiene advertencias."
        else:
            for numero, advertencia in enumerate(lista, 1):
                embed.add_field(
                    name=f"Advertencia #{numero}",
                    value=f"**Razón:** {advertencia['razon']}",
                    inline=False
                )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @app_commands.command(name="clearwarns", description="Elimina todas las advertencias de un miembro.")
    @app_commands.describe(miembro="Miembro al que se le eliminarán las advertencias.")
    @app_commands.default_permissions(moderate_members=True)
    async def clearwarns(
        self,
        interaction: discord.Interaction,
        miembro: discord.Member
    ):
        datos = cargar_warnings()

        guild_id = str(interaction.guild.id)
        user_id = str(miembro.id)

        if guild_id in datos and user_id in datos[guild_id]:
            del datos[guild_id][user_id]

        guardar_warnings(datos)

        await interaction.response.send_message(
            f"🧹 Se eliminaron todas las advertencias de **{miembro}**."
        )


async def setup(bot):
    await bot.add_cog(Advertencias(bot))
