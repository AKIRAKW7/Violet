import discord
from discord.ext import commands
import time


class ProteccionViolet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mensajes = {}
        self.alertas = {}

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild or message.author.bot:
            return

        ahora = time.monotonic()
        clave = (
            message.guild.id,
            message.author.id
        )

        historial = self.mensajes.setdefault(clave, [])

        historial.append(ahora)

        historial[:] = [
            t for t in historial
            if ahora - t <= 8
        ]

        if len(historial) >= 8:
            ultimo = self.alertas.get(clave, 0)

            if ahora - ultimo > 30:
                self.alertas[clave] = ahora

                try:
                    await message.channel.send(
                        f"🛡️ {message.author.mention}, "
                        f"reduce la velocidad de tus mensajes."
                    )
                except discord.Forbidden:
                    pass

                try:
                    await message.author.timeout(
                        discord.utils.utcnow() +
                        __import__("datetime").timedelta(seconds=30),
                        reason="Protección anti-spam de Violet"
                    )
                except (discord.Forbidden, discord.HTTPException):
                    pass


async def setup(bot):
    await bot.add_cog(ProteccionViolet(bot))
