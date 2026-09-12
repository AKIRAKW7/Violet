import discord
from discord import app_commands
from discord.ext import commands


class Configuracion(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="config",
        description="Panel principal de configuración de Violet."
    )
    @app_commands.default_permissions(manage_guild=True)
    async def config(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title="⚙️ Configuración de Violet",
            description=(
                "Panel de configuración del servidor.\n\n"
                "Selecciona una categoría para configurar Violet."
            ),
            color=discord.Color.purple()
        )

        embed.add_field(
            name="🛡️ Moderación",
            value="Configuración de seguridad y moderación.",
            inline=False
        )

        embed.add_field(
            name="⭐ Niveles",
            value="XP, niveles y recompensas.",
            inline=False
        )

        embed.add_field(
            name="💰 Economía",
            value="Economía, banco y recompensas.",
            inline=False
        )

        embed.add_field(
            name="💜 Social",
            value="Interacciones y sistemas sociales.",
            inline=False
        )

        embed.add_field(
            name="👋 Bienvenida",
            value="Mensajes de entrada y salida.",
            inline=False
        )

        embed.set_footer(
            text="Violet • Configuración del servidor"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Configuracion(bot))
