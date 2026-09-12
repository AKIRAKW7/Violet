import discord
from discord import app_commands
from discord.ext import commands


class AyudaViolet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="ayudaviolet",
        description="Muestra las categorías de Violet."
    )
    async def ayudaviolet(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="💜 Centro de ayuda de Violet",
            description="Selecciona mentalmente la categoría que necesites.",
            color=discord.Color.purple()
        )

        embed.add_field(
            name="🛡️ Moderación",
            value="/clear /kick /ban /timeout /warn",
            inline=False
        )

        embed.add_field(
            name="💰 Economía",
            value="/saldo /diario /trabajar /tienda /comprar",
            inline=False
        )

        embed.add_field(
            name="💜 Social",
            value="/beso /abrazo /pat /slap /cuddle",
            inline=False
        )

        embed.add_field(
            name="⭐ Niveles",
            value="/nivel /ranking",
            inline=False
        )

        embed.add_field(
            name="🐾 Mascotas",
            value="/mascota /alimentar /jugar_mascota",
            inline=False
        )

        embed.add_field(
            name="🎮 Juegos",
            value="/coinflip /dado /numero",
            inline=False
        )

        embed.add_field(
            name="🎫 Soporte",
            value="/ticket /cerrarticket",
            inline=False
        )

        embed.add_field(
            name="📖 Violet Daily Life",
            value="/daily /daily-stats",
            inline=False
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(AyudaViolet(bot))
