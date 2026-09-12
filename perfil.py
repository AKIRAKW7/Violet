import discord
from discord import app_commands
from discord.ext import commands


class PerfilView(discord.ui.View):
    def __init__(self, usuario):
        super().__init__(timeout=180)
        self.usuario = usuario

    @discord.ui.button(label="Estadísticas", emoji="📊", style=discord.ButtonStyle.secondary)
    async def estadisticas(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title=f"📊 Estadísticas de {self.usuario.display_name}",
            description="Aquí aparecerán las estadísticas completas del usuario.",
            color=discord.Color.purple()
        )

        embed.add_field(name="⭐ Nivel", value="Próximamente", inline=True)
        embed.add_field(name="💰 Economía", value="Próximamente", inline=True)
        embed.add_field(name="💜 Social", value="Próximamente", inline=True)
        embed.add_field(name="🏆 Logros", value="Próximamente", inline=True)
        embed.add_field(name="🐾 Mascota", value="Próximamente", inline=True)
        embed.add_field(name="🎮 Juegos", value="Próximamente", inline=True)

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )

    @discord.ui.button(label="Volver", emoji="↩️", style=discord.ButtonStyle.primary)
    async def volver(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = crear_perfil(self.usuario)

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )


def crear_perfil(usuario):
    embed = discord.Embed(
        title=f"💜 Perfil de {usuario.display_name}",
        description=(
            f"Perfil de **{usuario.mention}**\n\n"
            "Tu identidad dentro de Violet."
        ),
        color=discord.Color.purple()
    )

    if usuario.avatar:
        embed.set_thumbnail(url=usuario.avatar.url)

    embed.add_field(
        name="⭐ Nivel",
        value="Próximamente",
        inline=True
    )

    embed.add_field(
        name="✨ Experiencia",
        value="Próximamente",
        inline=True
    )

    embed.add_field(
        name="💰 Dinero",
        value="Próximamente",
        inline=True
    )

    embed.add_field(
        name="💜 Interacciones",
        value="Próximamente",
        inline=True
    )

    embed.add_field(
        name="🏆 Logros",
        value="Próximamente",
        inline=True
    )

    embed.add_field(
        name="🐾 Mascota",
        value="Próximamente",
        inline=True
    )

    embed.set_footer(
        text="Violet • Tu compañera multifunción para Discord"
    )

    return embed


class Perfil(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="perfil",
        description="Muestra tu perfil completo de Violet."
    )
    @app_commands.describe(
        usuario="Usuario cuyo perfil quieres consultar."
    )
    async def perfil(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member | None = None
    ):
        usuario = usuario or interaction.user

        embed = crear_perfil(usuario)

        await interaction.response.send_message(
            embed=embed,
            view=PerfilView(usuario)
        )


async def setup(bot):
    await bot.add_cog(Perfil(bot))
