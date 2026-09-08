import asyncio
import random
import time

import discord
from discord import app_commands
from discord.ext import commands


# =========================================================
# VIOLET DAILY LIFE
# =========================================================

DAILY_STORIES = [
    {
        "text": "Violet encontró una pequeña cafetería mientras caminaba por la Ciudad Neón.",
        "question": "¿Qué debería hacer?",
        "options": [
            ("☕ Entrar", "entrar"),
            ("🔎 Investigar", "investigar"),
            ("💜 Invitar a alguien", "invitar"),
        ],
    },
    {
        "text": "Una misteriosa caja apareció frente a Violet. Tiene un pequeño corazón dibujado.",
        "question": "¿Qué debería hacer?",
        "options": [
            ("📦 Abrirla", "abrir"),
            ("🔍 Examinarla", "examinar"),
            ("🚶 Dejarla ahí", "dejar"),
        ],
    },
    {
        "text": "Violet recibió un mensaje anónimo que decía: «Te estoy esperando en el parque».",
        "question": "¿Qué debería hacer?",
        "options": [
            ("🌳 Ir al parque", "parque"),
            ("📱 Responder", "responder"),
            ("🕵️ Investigar", "investigar"),
        ],
    },
    {
        "text": "Durante la noche, Violet escuchó música proveniente de un edificio abandonado.",
        "question": "¿Qué debería hacer?",
        "options": [
            ("🎵 Seguir la música", "musica"),
            ("🚪 Entrar al edificio", "entrar"),
            ("🏠 Volver a casa", "casa"),
        ],
    },
]


REWARDS = {
    "coins": 25,
    "xp": 10,
    "bond": 5,
}


class DailyView(discord.ui.View):

    def __init__(self, story, timeout=86400):
        super().__init__(timeout=timeout)

        self.story = story
        self.votes = {
            option_id: set()
            for _, option_id in story["options"]
        }

        for label, option_id in story["options"]:
            self.add_item(DailyButton(label, option_id, self))

    async def vote(self, interaction: discord.Interaction, option_id: str):

        user_id = interaction.user.id

        # Comprobar si la persona ya votó
        for voters in self.votes.values():

            if user_id in voters:

                await interaction.response.send_message(
                    "🔒 Ya has votado en esta historia. "
                    "Tu decisión no puede cambiarse.",
                    ephemeral=True
                )

                return

        # Registrar el primer voto
        self.votes[option_id].add(user_id)

        # Recompensas por participar
        try:
            import database

            await database.add_balance(
                user_id,
                interaction.guild_id,
                REWARDS["coins"]
            )

            await database.add_xp(
                user_id,
                interaction.guild_id,
                REWARDS["xp"]
            )

            recompensa = (
                f"\n\n🎁 Recompensas:\n"
                f"🪙 +{REWARDS["coins"]} monedas\n"
                f"⭐ +{REWARDS["xp"]} XP"
            )

        except Exception as error:
            print(f"❌ Error dando recompensa Daily Life: {error}")
            recompensa = ""

        await interaction.response.send_message(
            f"💜 Tu decisión fue registrada: "
            f"**{self.get_label(option_id)}**"
            f"{recompensa}",
            ephemeral=True
        )

        await self.update_message(interaction.message)

    def get_label(self, option_id):

        for label, current_id in self.story["options"]:
            if current_id == option_id:
                return label

        return option_id

    def total_votes(self):
        return sum(len(voters) for voters in self.votes.values())

    def winner(self):

        if self.total_votes() == 0:
            return None

        return max(
            self.votes,
            key=lambda option_id: len(self.votes[option_id])
        )

    async def update_message(self, message):

        embed = create_daily_embed(
            self.story,
            self.votes,
            finished=False
        )

        await message.edit(
            embed=embed,
            view=self
        )

    async def on_timeout(self):

        winner = self.winner()

        embed = create_daily_embed(
            self.story,
            self.votes,
            finished=True,
            winner=winner
        )

        for item in self.children:
            item.disabled = True

        # El mensaje se actualiza mediante la tarea de seguimiento.


class DailyButton(discord.ui.Button):

    def __init__(self, label, option_id, view):

        super().__init__(
            label=label,
            style=discord.ButtonStyle.primary
        )

        self.option_id = option_id
        self.daily_view = view

    async def callback(self, interaction: discord.Interaction):

        await self.daily_view.vote(
            interaction,
            self.option_id
        )


def create_daily_embed(
    story,
    votes,
    finished=False,
    winner=None
):

    description = (
        "╭─────────────── 🌙 ───────────────╮\n"
        "│        **VIOLET DAILY LIFE**        │\n"
        "╰────────────────────────────────────╯\n\n"
        f"📖 **DÍA {time.strftime('%j')}**\n\n"
        f"{story['text']}\n\n"
        f"❓ **{story['question']}**\n\n"
    )

    for label, option_id in story["options"]:

        cantidad = len(votes.get(option_id, set()))

        description += (
            f"{label} — **{cantidad} voto(s)**\n"
        )

    description += "\n"

    if finished and winner:

        winner_label = next(
            (
                label
                for label, option_id in story["options"]
                if option_id == winner
            ),
            winner
        )

        description += (
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🏆 **DECISIÓN GANADORA**\n\n"
            f"{winner_label}\n\n"
            "📖 La historia continuará mañana..."
        )

    else:

        description += (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⏳ La votación permanecerá abierta durante 24 horas.\n"
            "💜 ¡Tu decisión puede cambiar la historia!"
        )

    return discord.Embed(
        description=description,
        color=discord.Color.from_rgb(138, 43, 226)
    )


class DailyLife(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        self.active_daily = {}

        self.daily_task = asyncio.create_task(
            self.daily_loop()
        )

    def cog_unload(self):

        if self.daily_task:
            self.daily_task.cancel()

    @app_commands.command(
        name="daily",
        description="Muestra la situación diaria de Violet."
    )
    async def daily(self, interaction: discord.Interaction):

        guild_id = interaction.guild_id

        if guild_id is None:

            await interaction.response.send_message(
                "❌ Este comando solo puede utilizarse dentro de un servidor.",
                ephemeral=True
            )

            return

        if guild_id not in self.active_daily:

            story = random.choice(DAILY_STORIES)

            view = DailyView(story)

            self.active_daily[guild_id] = {
                "story": story,
                "view": view,
                "created": time.time(),
            }

        data = self.active_daily[guild_id]

        await interaction.response.send_message(
            embed=create_daily_embed(
                data["story"],
                data["view"].votes
            ),
            view=data["view"]
        )

    @app_commands.command(
        name="daily-config",
        description="Configura el canal donde se publicará Violet Daily Life."
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def daily_config(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel
    ):

        if not hasattr(self.bot, "_daily_channels"):
            self.bot._daily_channels = {}

        self.bot._daily_channels[interaction.guild_id] = canal.id

        await interaction.response.send_message(
            f"⚙️ Canal de Daily Life configurado en {canal.mention}.",
            ephemeral=True
        )

    @app_commands.command(
        name="daily-stats",
        description="Muestra las estadísticas de la historia diaria."
    )
    async def daily_stats(self, interaction: discord.Interaction):

        guild_id = interaction.guild_id

        if guild_id not in self.active_daily:

            await interaction.response.send_message(
                "📖 Todavía no existe una historia diaria activa.",
                ephemeral=True
            )

            return

        data = self.active_daily[guild_id]
        view = data["view"]

        total = view.total_votes()

        resultado = "Todavía no hay votos."

        if total:

            ganador = view.winner()

            resultado = (
                f"🏆 Decisión provisional: "
                f"**{view.get_label(ganador)}**"
            )

        embed = discord.Embed(
            title="📊 Violet Daily Life",
            description=(
                f"🗳️ Votos totales: **{total}**\n\n"
                f"{resultado}"
            ),
            color=discord.Color.purple()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    async def daily_loop(self):

        await self.bot.wait_until_ready()

        # Evita publicar varias veces el mismo día
        publicados = set()

        while not self.bot.is_closed():

            try:
                ahora = time.localtime()
                dia_actual = time.strftime("%Y-%m-%d", ahora)

                canales = getattr(self.bot, "_daily_channels", {})

                for guild_id, channel_id in list(canales.items()):

                    # Ya publicado hoy en este servidor
                    clave = (guild_id, dia_actual)

                    if clave in publicados:
                        continue

                    canal = self.bot.get_channel(channel_id)

                    if canal is None:
                        continue

                    story = random.choice(DAILY_STORIES)
                    view = DailyView(story)

                    self.active_daily[guild_id] = {
                        "story": story,
                        "view": view,
                        "created": time.time(),
                    }

                    await canal.send(
                        embed=create_daily_embed(
                            story,
                            view.votes
                        ),
                        view=view
                    )

                    publicados.add(clave)

                    print(
                        f"📖 Daily Life publicado en {guild_id}"
                    )

            except Exception as error:
                print(
                    f"❌ Error en Daily Life automático: {error}"
                )

            # Comprobar cada minuto
            await asyncio.sleep(60)


async def setup(bot):

    await bot.add_cog(
        DailyLife(bot)
    )
