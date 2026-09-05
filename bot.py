import discord
from discord import app_commands

# =========================
# CONFIGURACIÓN DE VIOLET
# =========================

intents = discord.Intents.default()

bot = discord.Client(intents=intents)
arbol = app_commands.CommandTree(bot)


# =========================
# CUANDO VIOLET SE CONECTA
# =========================

@bot.event
async def on_ready():
    try:
        comandos = await arbol.sync()

        print("=" * 40)
        print(f"Violet conectada como: {bot.user}")
        print(f"ID de Violet: {bot.user.id}")
        print(f"Comandos globales sincronizados: {len(comandos)}")
        print("=" * 40)

    except Exception as error:
        print(f"Error al sincronizar comandos: {error}")


# =========================
# COMANDO /HOLA
# =========================

@arbol.command(
    name="hola",
    description="Violet te saluda"
)
async def hola(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"¡Hola, {interaction.user.mention}! 💜🐾"
    )


# =========================
# COMANDO /AYUDA
# =========================

@arbol.command(
    name="ayuda",
    description="Muestra todos los comandos de Violet"
)
async def ayuda(interaction: discord.Interaction):

    embed = discord.Embed(
        title="💜 Menú de Ayuda — Violet",
        description=(
            "¡Hola! Soy **Violet**, tu bot multifunción. 🐾\n\n"
            "Estos son los sistemas que iremos incorporando:"
        ),
        color=0x9B59B6
    )

    embed.add_field(
        name="🎮 Diversión",
        value="`/hola`\nPróximamente más comandos.",
        inline=False
    )

    embed.add_field(
        name="👤 Perfil",
        value="Sistema de perfiles, XP y niveles.\nPróximamente.",
        inline=False
    )

    embed.add_field(
        name="💰 Economía",
        value="Monedas, trabajos, tienda e inventario.\nPróximamente.",
        inline=False
    )

    embed.add_field(
        name="❤️ Social",
        value="Interacciones, parejas y sistema social.\nPróximamente.",
        inline=False
    )

    embed.add_field(
        name="🐾 Mascotas",
        value="Adopta y cuida tus propias mascotas.\nPróximamente.",
        inline=False
    )

    embed.add_field(
        name="🎲 Juegos",
        value="Dados, monedas, duelos y minijuegos.\nPróximamente.",
        inline=False
    )

    embed.add_field(
        name="🛡️ Moderación",
        value="Herramientas para administrar servidores.\nPróximamente.",
        inline=False
    )

    embed.set_footer(
        text="Violet • Bot multifunción"
    )

    await interaction.response.send_message(embed=embed)


# =========================
# INICIAR VIOLET
# =========================

# IMPORTANTE:
# Coloca aquí tu NUEVO token.
# No compartas este token con nadie.

bot.run("MTU0NTYyNTAyODcxNDk1ODk5MA.GGjPne.x9-krnR5fwAZ5TbJx7bV-sBOz55o4JC1WcTKFw")
