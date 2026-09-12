import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import random

ARCHIVO = "tickets_violet.json"


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


class TicketsViolet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="ticket",
        description="Crea un ticket privado."
    )
    async def ticket(self, interaction: discord.Interaction):
        guild = interaction.guild

        existente = discord.utils.get(
            guild.text_channels,
            name=f"ticket-{interaction.user.id}"
        )

        if existente:
            await interaction.response.send_message(
                f"Ya tienes un ticket abierto: {existente.mention}",
                ephemeral=True
            )
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True
            )
        }

        canal = await guild.create_text_channel(
            f"ticket-{interaction.user.id}",
            overwrites=overwrites
        )

        datos = cargar()

        servidor = datos.setdefault(
            str(guild.id),
            {}
        )

        servidor[str(interaction.user.id)] = canal.id

        guardar(datos)

        await canal.send(
            f"🎫 Ticket creado para {interaction.user.mention}.\n"
            f"Explica aquí tu problema."
        )

        await interaction.response.send_message(
            f"🎫 Ticket creado: {canal.mention}",
            ephemeral=True
        )

    @app_commands.command(
        name="cerrarticket",
        description="Cierra el ticket actual."
    )
    async def cerrarticket(self, interaction: discord.Interaction):
        if not interaction.channel.name.startswith("ticket-"):
            await interaction.response.send_message(
                "Este comando solo puede utilizarse dentro de un ticket.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🔒 Cerrando ticket..."
        )

        await interaction.channel.delete(
            reason=f"Ticket cerrado por {interaction.user}"
        )


async def setup(bot):
    await bot.add_cog(TicketsViolet(bot))
