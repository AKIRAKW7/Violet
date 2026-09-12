import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import random
import time

ARCHIVO = "economia_avanzada.json"


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


class EconomiaAvanzada(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def usuario(self, datos, guild_id, user_id):
        servidor = datos.setdefault(str(guild_id), {})
        return servidor.setdefault(
            str(user_id),
            {
                "saldo": 1000,
                "banco": 0,
                "racha": 0,
                "prestigio": 0
            }
        )

    @app_commands.command(
        name="patrimonio",
        description="Muestra tu patrimonio total."
    )
    async def patrimonio(self, interaction: discord.Interaction):
        datos = cargar()
        u = self.usuario(
            datos,
            interaction.guild.id,
            interaction.user.id
        )

        total = u["saldo"] + u["banco"]

        embed = discord.Embed(
            title="💰 Patrimonio",
            color=discord.Color.purple()
        )

        embed.add_field(name="💵 Efectivo", value=f"${u['saldo']:,}")
        embed.add_field(name="🏦 Banco", value=f"${u['banco']:,}")
        embed.add_field(name="💎 Patrimonio", value=f"${total:,}", inline=False)
        embed.add_field(name="🔥 Racha", value=str(u["racha"]))

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="prestigio",
        description="Muestra tu prestigio económico."
    )
    async def prestigio(self, interaction: discord.Interaction):
        datos = cargar()
        u = self.usuario(
            datos,
            interaction.guild.id,
            interaction.user.id
        )

        patrimonio = u["saldo"] + u["banco"]
        prestigio = patrimonio // 10000

        u["prestigio"] = prestigio
        guardar(datos)

        await interaction.response.send_message(
            f"👑 Tu prestigio económico es **{prestigio}**."
        )

    @app_commands.command(
        name="riesgo",
        description="Realiza una apuesta económica de alto riesgo."
    )
    @app_commands.describe(
        cantidad="Cantidad que quieres arriesgar."
    )
    async def riesgo(
        self,
        interaction: discord.Interaction,
        cantidad: app_commands.Range[int, 1, 1000000]
    ):
        datos = cargar()
        u = self.usuario(
            datos,
            interaction.guild.id,
            interaction.user.id
        )

        if u["saldo"] < cantidad:
            await interaction.response.send_message(
                "❌ No tienes suficiente dinero.",
                ephemeral=True
            )
            return

        if random.random() < 0.48:
            ganancia = cantidad * 2
            u["saldo"] += ganancia
            resultado = f"🎉 Ganaste **${ganancia:,}**."
        else:
            u["saldo"] -= cantidad
            resultado = f"💀 Perdiste **${cantidad:,}**."

        guardar(datos)

        await interaction.response.send_message(
            f"🎲 {interaction.user.mention} {resultado}"
        )


async def setup(bot):
    await bot.add_cog(EconomiaAvanzada(bot))
