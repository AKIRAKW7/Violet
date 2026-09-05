import discord
from discord import app_commands

intents = discord.Intents.default()

bot = discord.Client(intents=intents)
arbol = app_commands.CommandTree(bot)


@bot.event
async def on_ready():
    await arbol.sync()
    print(f"Bot conectado como {bot.user}")


@arbol.command(name="hola", description="El bot te saluda")
async def hola(interaction: discord.Interaction):
    await interaction.response.send_message("¡Hola! 🐱")


bot.run(MTU0NTYyNTAyODcxNDk1ODk5MA.GOd6Zh.-hz9K6dZGFQLvoFgAbrRhTaDUIvk9xdvVhbd3Q)


