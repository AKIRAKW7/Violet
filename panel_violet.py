import discord
from discord import app_commands
from discord.ext import commands


class PanelViolet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="panel",
        description="Abre el panel principal de Violet."
    )
    async def panel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="💜 Violet",
            description=(
                "**Tu compañera multifunción para Discord.**\n\n"
                "🛡️ Moderación\n"
                "💰 Economía\n"
                "💜 Social\n"
                "⭐ Niveles\n"
                "🐾 Mascotas\n"
                "🎮 Juegos\n"
                "🎵 Música\n"
                "🏆 Logros\n"
                "📖 Daily Life\n"
                "📈 Violet Market"
            ),
            color=discord.Color.purple()
        )

        embed.add_field(
            name="Comandos",
            value="Usa `/ayuda` para explorar las funciones."
        )

        if self.bot.user and self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(PanelViolet(bot))
