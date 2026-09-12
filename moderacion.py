import discord
from discord import app_commands
from discord.ext import commands


class Moderacion(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="clear", description="Elimina mensajes del canal.")
    @app_commands.describe(cantidad="Cantidad de mensajes a eliminar.")
    @app_commands.default_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, cantidad: app_commands.Range[int, 1, 100]):
        if not interaction.channel or not hasattr(interaction.channel, "purge"):
            await interaction.response.send_message(
                "❌ Este comando no puede utilizarse aquí.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            mensajes = await interaction.channel.purge(limit=cantidad)
            await interaction.followup.send(
                f"🧹 Se eliminaron **{len(mensajes)} mensajes**.",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Violet no tiene permisos suficientes para eliminar mensajes.",
                ephemeral=True
            )
        except discord.HTTPException:
            await interaction.followup.send(
                "❌ Discord rechazó la operación.",
                ephemeral=True
            )

    @app_commands.command(name="kick", description="Expulsa a un miembro del servidor.")
    @app_commands.describe(miembro="Miembro que será expulsado.", razon="Razón de la expulsión.")
    @app_commands.default_permissions(kick_members=True)
    async def kick(
        self,
        interaction: discord.Interaction,
        miembro: discord.Member,
        razon: str = "Sin especificar"
    ):
        if miembro == interaction.user:
            await interaction.response.send_message(
                "❌ No puedes expulsarte a ti mismo.",
                ephemeral=True
            )
            return

        if miembro == self.bot.user:
            await interaction.response.send_message(
                "❌ No puedo expulsarme a mí misma.",
                ephemeral=True
            )
            return

        if miembro.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            await interaction.response.send_message(
                "❌ No puedes expulsar a alguien con un rol igual o superior al tuyo.",
                ephemeral=True
            )
            return

        try:
            await miembro.kick(reason=razon)
            await interaction.response.send_message(
                f"👢 **{miembro}** fue expulsado.\n**Razón:** {razon}"
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Violet no tiene permisos suficientes.",
                ephemeral=True
            )

    @app_commands.command(name="ban", description="Banea a un miembro del servidor.")
    @app_commands.describe(miembro="Miembro que será baneado.", razon="Razón del baneo.")
    @app_commands.default_permissions(ban_members=True)
    async def ban(
        self,
        interaction: discord.Interaction,
        miembro: discord.Member,
        razon: str = "Sin especificar"
    ):
        if miembro == interaction.user:
            await interaction.response.send_message(
                "❌ No puedes banearte a ti mismo.",
                ephemeral=True
            )
            return

        if miembro == self.bot.user:
            await interaction.response.send_message(
                "❌ No puedo banearme a mí misma.",
                ephemeral=True
            )
            return

        if miembro.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            await interaction.response.send_message(
                "❌ No puedes banear a alguien con un rol igual o superior al tuyo.",
                ephemeral=True
            )
            return

        try:
            await miembro.ban(reason=razon, delete_message_days=0)

            await interaction.response.send_message(
                f"🔨 **{miembro}** fue baneado.\n**Razón:** {razon}"
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Violet no tiene permisos suficientes.",
                ephemeral=True
            )

    @app_commands.command(name="unban", description="Desbanea a un usuario.")
    @app_commands.describe(usuario_id="ID del usuario que será desbaneado.")
    @app_commands.default_permissions(ban_members=True)
    async def unban(
        self,
        interaction: discord.Interaction,
        usuario_id: str
    ):
        try:
            user = await self.bot.fetch_user(int(usuario_id))
            await interaction.guild.unban(user)

            await interaction.response.send_message(
                f"🔓 **{user}** fue desbaneado."
            )

        except ValueError:
            await interaction.response.send_message(
                "❌ La ID proporcionada no es válida.",
                ephemeral=True
            )

        except discord.NotFound:
            await interaction.response.send_message(
                "❌ Ese usuario no está baneado.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Violet no tiene permisos suficientes.",
                ephemeral=True
            )

    @app_commands.command(name="timeout", description="Silencia temporalmente a un miembro.")
    @app_commands.describe(
        miembro="Miembro que será silenciado.",
        minutos="Duración en minutos.",
        razon="Razón del timeout."
    )
    @app_commands.default_permissions(moderate_members=True)
    async def timeout(
        self,
        interaction: discord.Interaction,
        miembro: discord.Member,
        minutos: app_commands.Range[int, 1, 40320],
        razon: str = "Sin especificar"
    ):
        if miembro == interaction.user:
            await interaction.response.send_message(
                "❌ No puedes silenciarte a ti mismo.",
                ephemeral=True
            )
            return

        if miembro.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            await interaction.response.send_message(
                "❌ No puedes silenciar a alguien con un rol igual o superior al tuyo.",
                ephemeral=True
            )
            return

        try:
            duracion = discord.utils.utcnow() + discord.timedelta(minutes=minutos)
            await miembro.timeout(duracion, reason=razon)

            await interaction.response.send_message(
                f"🔇 **{miembro}** recibió un timeout de **{minutos} minutos**.\n"
                f"**Razón:** {razon}"
            )

        except AttributeError:
            duracion = discord.utils.utcnow() + __import__("datetime").timedelta(minutes=minutos)
            await miembro.timeout(duracion, reason=razon)

            await interaction.response.send_message(
                f"🔇 **{miembro}** recibió un timeout de **{minutos} minutos**.\n"
                f"**Razón:** {razon}"
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Violet no tiene permisos suficientes.",
                ephemeral=True
            )

    @app_commands.command(name="untimeout", description="Quita el timeout de un miembro.")
    @app_commands.describe(miembro="Miembro al que se quitará el timeout.")
    @app_commands.default_permissions(moderate_members=True)
    async def untimeout(
        self,
        interaction: discord.Interaction,
        miembro: discord.Member
    ):
        try:
            await miembro.timeout(None)

            await interaction.response.send_message(
                f"🔊 Se quitó el timeout a **{miembro}**."
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Violet no tiene permisos suficientes.",
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(Moderacion(bot))
