import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import random

ARCHIVO = "niveles.json"


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


def xp_necesaria(nivel):
    return 100 + ((nivel - 1) * 50)


def obtener_usuario(guild_id, user_id):
    datos = cargar()
    g = datos.setdefault(str(guild_id), {})
    u = g.setdefault(
        str(user_id),
        {
            "xp": 0,
            "nivel": 1,
            "mensajes": 0
        }
    )
    guardar(datos)
    return datos, u


class Niveles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldown = {}

    async def procesar_xp(self, message):
        if not message.guild or message.author.bot:
            return

        clave = (message.guild.id, message.author.id)

        ahora = discord.utils.utcnow().timestamp()

        if clave in self.cooldown and ahora - self.cooldown[clave] < 45:
            return

        self.cooldown[clave] = ahora

        datos, usuario = obtener_usuario(
            message.guild.id,
            message.author.id
        )

        usuario["mensajes"] += 1
        usuario["xp"] += random.randint(8, 15)

        nivel_anterior = usuario["nivel"]

        while usuario["xp"] >= xp_necesaria(usuario["nivel"]):
            usuario["xp"] -= xp_necesaria(usuario["nivel"])
            usuario["nivel"] += 1

        guardar(datos)

        if usuario["nivel"] > nivel_anterior:
            await message.channel.send(
                f"✨ {message.author.mention} subió al **nivel {usuario['nivel']}**."
            )

    @app_commands.command(
        name="nivel",
        description="Muestra tu nivel y experiencia."
    )
    @app_commands.describe(usuario="Usuario que quieres consultar.")
    async def nivel(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member | None = None
    ):
        usuario = usuario or interaction.user

        datos, u = obtener_usuario(
            interaction.guild.id,
            usuario.id
        )

        siguiente = xp_necesaria(u["nivel"])

        embed = discord.Embed(
            title=f"⭐ Nivel de {usuario.display_name}",
            color=discord.Color.purple()
        )

        embed.add_field(
            name="Nivel",
            value=f"`{u['nivel']}`",
            inline=True
        )

        embed.add_field(
            name="XP",
            value=f"`{u['xp']} / {siguiente}`",
            inline=True
        )

        embed.add_field(
            name="Mensajes",
            value=f"`{u['mensajes']}`",
            inline=True
        )

        if usuario.avatar:
            embed.set_thumbnail(url=usuario.avatar.url)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="ranking",
        description="Muestra el ranking de niveles del servidor."
    )
    async def ranking(self, interaction: discord.Interaction):
        datos = cargar()
        servidores = datos.get(str(interaction.guild.id), {})

        ranking = []

        for user_id, valores in servidores.items():
            ranking.append(
                (
                    int(valores.get("nivel", 1)),
                    int(valores.get("xp", 0)),
                    user_id
                )
            )

        ranking.sort(reverse=True)

        lineas = []

        for posicion, (nivel, xp, user_id) in enumerate(ranking[:10], 1):
            miembro = interaction.guild.get_member(int(user_id))

            if miembro:
                nombre = miembro.display_name
            else:
                nombre = f"Usuario {user_id}"

            lineas.append(
                f"**{posicion}.** {nombre} — Nivel `{nivel}` • `{xp}` XP"
            )

        if not lineas:
            lineas.append("Todavía no hay usuarios registrados.")

        embed = discord.Embed(
            title="🏆 Ranking de niveles",
            description="\n".join(lineas),
            color=discord.Color.gold()
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    cog = Niveles(bot)
    await bot.add_cog(cog)

    if not hasattr(bot, "_violet_niveles_cog"):
        bot._violet_niveles_cog = cog

        original = bot.get_listener("on_message")

        if original is None:
            async def listener(message):
                await cog.procesar_xp(message)

            bot.add_listener(listener, "on_message")
