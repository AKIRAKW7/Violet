from rangos import instalar as instalar_rangos
import os
from dotenv import load_dotenv

load_dotenv()

import random
import hashlib
import asyncio

import aiohttp
import discord
import yt_dlp

from discord import app_commands
from discord.ext import commands

import database

TOKEN = os.getenv("DISCORD_TOKEN")


intents = discord.Intents.default()
intents.members = True
intents.message_content = True


bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

arbol = bot.tree
GUILD_ID = 1544748291537899551
GUILD = discord.Object(id=GUILD_ID)

# =========================================================
# 🛡️ VIOLET SECURITY — ESTADO ANTI-SPAM
# =========================================================

violet_spam_tracker = {}
violet_spam_warned = set()



GIF_API = {
    "beso": "kiss",
    "abrazo": "hug",
    "pat": "pat",
    "slap": "slap",
    "cuddle": "cuddle",
    "highfive": "highfive",
    "poke": "poke",
    "mordisco": "bite",
    "bailar": "dance",
    "dormir": "sleep"
}


async def obtener_gif(accion):
    endpoint = GIF_API.get(accion)

    if endpoint is None:
        return None

    urls = [
        f"https://nekos.best/api/v2/{endpoint}",
        f"https://api.waifu.pics/sfw/{endpoint}"
    ]

    for url in urls:
        try:
            timeout = aiohttp.ClientTimeout(total=8)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:

                    if response.status != 200:
                        continue

                    data = await response.json()

                    if "results" in data and data["results"]:
                        resultados = data["results"]

                        gif = random.choice(resultados)

                        return gif.get("url")

                    if "url" in data:
                        return data.get("url")

        except Exception as error:
            print(f"? Error obteniendo GIF de {accion}: {error}")
            continue

    return None

async def responder(
    interaction,
    contenido=None,
    embed=None,
    ephemeral=False,
    view=None,
    embeds=None,
    file=None,
    files=None
):
    try:
        kwargs = {
            "content": contenido,
            "ephemeral": ephemeral
        }

        if view is not None:
            kwargs["view"] = view

        if embeds is not None:
            kwargs["embeds"] = embeds
        elif embed is not None:
            kwargs["embed"] = embed

        if files is not None:
            kwargs["files"] = files
        elif file is not None:
            kwargs["file"] = file

        if interaction.response.is_done():
            await interaction.followup.send(**kwargs)
        else:
            await interaction.response.send_message(**kwargs)

    except Exception as error:
        print(f"Error enviando respuesta: {error}")


# =========================================================
# VIOLET AUTÓNOMA - REINICIO AUTOMÁTICO
# =========================================================

VIOLET_AUTO_REINICIO = True


async def violet_iniciar_actividad_automatica():
    await bot.wait_until_ready()

    if not VIOLET_AUTO_REINICIO:
        return

    if getattr(bot, "_violet_actividades_task", None):
        return

    bot._violet_actividades_task = asyncio.create_task(
        violet_loop_actividades()
    )

    print(" Actividades autónomas de Violet activadas.")

# =========================================================
# VIOLET MARKET  MOTOR AUTOMÁTICO
# =========================================================

VIOLET_MARKET_INTERVALO = 5 * 60
VIOLET_MARKET_MIN = 10.0
VIOLET_MARKET_MAX = 1000000.0


async def violet_market_loop():

    await asyncio.sleep(15)

    while True:

        try:
            mercado = await database.get_violet_market()

            if mercado is None:
                await database.init_violet_market()
                mercado = await database.get_violet_market()

            precio_actual = float(mercado[0])

            # Variación aleatoria entre -5% y +5%
            variacion = random.uniform(-0.05, 0.05)

            nuevo_precio = precio_actual * (1 + variacion)

            # Evitar que la moneda llegue a 0 o crezca indefinidamente
            nuevo_precio = max(
                VIOLET_MARKET_MIN,
                min(VIOLET_MARKET_MAX, nuevo_precio)
            )

            cambio_real = (
                (nuevo_precio - precio_actual)
                / precio_actual
            ) * 100

            from datetime import datetime, UTC

            timestamp = datetime.now(UTC).isoformat()

            await database.update_violet_market(
                nuevo_precio,
                cambio_real,
                timestamp
            )

            print(
                f" VLC | "
                f"${precio_actual:,.2f}  "
                f"${nuevo_precio:,.2f} "
                f"({cambio_real:+.2f}%)"
            )

            # Actualizar automáticamente el canal Violet Market
            for guild in bot.guilds:
                await violet_market_publish(guild)

        except Exception as error:
            print(f" Error en Violet Market: {error}")

        await asyncio.sleep(VIOLET_MARKET_INTERVALO)


# =========================================================
#  VIOLET MARKET  RESUMENÚ DE INVERSIONES
# =========================================================

async def violet_market_investment_summary(precio_actual):
    try:
        inversiones = await database.get_all_violet_investments()

        if not inversiones:
            return (
                " **Inversiones activas:** `0`\n"
                "No hay inversiones activas en este momento."
            )

        total_capital = 0.0
        total_valor = 0.0
        ganancia_total = 0.0

        for inversion in inversiones:
            amount = float(inversion[3])
            buy_price = float(inversion[4])

            if buy_price <= 0:
                continue

            valor_actual = (
                amount * float(precio_actual) / buy_price
            )

            total_capital += amount
            total_valor += valor_actual
            ganancia_total += valor_actual - amount

        if total_capital > 0:
            rendimiento = (
                ganancia_total / total_capital
            ) * 100
        else:
            rendimiento = 0.0

        if ganancia_total > 0:
            estado = ""
            resultado = f"+{ganancia_total:,.2f} "
        elif ganancia_total < 0:
            estado = ""
            resultado = f"{ganancia_total:,.2f} "
        else:
            estado = ""
            resultado = "0.00 "

        return (
            f" **Inversiones activas:** `{len(inversiones)}`\n"
            f" **Capital invertido:** `{total_capital:,.2f} `\n"
            f" **Valor actual:** `{total_valor:,.2f} `\n"
            f"{estado} **Resultado:** `{resultado}`\n"
            f" **Rendimiento:** `{rendimiento:+.2f}%`"
        )

    except Exception as error:
        print(f" Error calculando inversiones: {error}")
        return "❌ No se pudo calcular el resumen de inversiones."

# =========================================================
#  VIOLET MARKET  CANAL AUTOMÁTICO
# =========================================================

VIOLET_MARKET_CHANNEL_NAME = "violet-market"

async def violet_market_channel(guild):

    try:
        canal = discord.utils.get(
            guild.text_channels,
            name=VIOLET_MARKET_CHANNEL_NAME
        )

        if canal is None:

            permisos = guild.me.guild_permissions

            print("===== PERMISOS VIOLET =====")
            print(f"Servidor: {guild.name}")
            print(f"Gestionar canales: {permisos.manage_channels}")
            print(f"Administrador: {permisos.administrator}")
            print(f"Ver canales: {permisos.view_channel}")
            print(f"Enviar mensajes: {permisos.send_messages}")
            print("============================")

            canal = await guild.create_text_channel(
                VIOLET_MARKET_CHANNEL_NAME,
                topic=" Mercado automático de Violet Coin (VLC)"
            )

            print(
                f" Canal Violet Market creado en {guild.name}"
            )

        return canal

    except Exception as error:
        print(
            f" Error creando canal Violet Market: {error}"
        )
        return None




async def violet_market_publish(guild):

    canal = await violet_market_channel(guild)

    if canal is None:
        return

    datos = await database.get_violet_market()

    if datos is None:
        return

    (
        precio,
        precio_anterior,
        maximo,
        minimo,
        total_invertido,
        ultima_actualizacion
    ) = datos

    precio = float(precio)
    precio_anterior = float(precio_anterior)

    if precio_anterior > 0:
        cambio = (
            (precio - precio_anterior)
            / precio_anterior
        ) * 100
    else:
        cambio = 0

    if cambio > 0:
        tendencia = ""
    elif cambio < 0:
        tendencia = ""
    else:
        tendencia = ""

    embed = discord.Embed(
        title=" Violet Market",
        description=(
            "Mercado automático de **Violet Coin (VLC)**\n\n"
            f"{tendencia} **Precio actual:** "
            f"`{precio:,.2f} VLC`\n"
            f" **Variación:** `{cambio:+.2f}%`"
        ),
        color=discord.Color.purple()
    )

    embed.add_field(
        name=" Máximo histórico",
        value=f"`{float(maximo):,.2f} VLC`",
        inline=True
    )

    embed.add_field(
        name=" Mínimo histórico",
        value=f"`{float(minimo):,.2f} VLC`",
        inline=True
    )

    embed.add_field(
        name=" Total invertido",
        value=f"`{float(total_invertido):,.2f} `",
        inline=False
    )

    resumen_inversiones = await violet_market_investment_summary(
        precio
    )

    embed.add_field(
        name=" Movimiento de inversiones",
        value=resumen_inversiones,
        inline=False
    )

    embed.add_field(
        name=" Invertir",
        value="Usa `/invertir <cantidad>` para invertir.",
        inline=False
    )

    embed.set_footer(
        text="Violet Market  Actualización automática"
    )

    registro = await database.get_violet_market_channel(
        guild.id
    )

    mensaje = None

    if registro:
        channel_id, message_id = registro

        if channel_id == canal.id and message_id:
            try:
                mensaje = await canal.fetch_message(
                    message_id
                )
            except discord.NotFound:
                mensaje = None
            except discord.Forbidden:
                print(
                    f" Sin permisos para acceder al mensaje "
                    f"de Violet Market en {guild.name}"
                )
                return

    try:
        if mensaje:
            await mensaje.edit(
                embed=embed,
                view=VioletMarketView()
            )

        else:
            mensaje = await canal.send(
                embed=embed,
                view=VioletMarketView()
            )

            await database.save_violet_market_channel(
                guild.id,
                canal.id,
                mensaje.id
            )

    except discord.Forbidden:
        print(
            f" Sin permisos para publicar Violet Market "
            f"en {guild.name}"
        )

    except Exception as error:
        print(
            f" Error actualizando Violet Market: {error}"
        )


@bot.event
async def on_ready():
    if not getattr(bot, '_rangos_cargados', False):
        bot._rangos_cargados = True
        await instalar_rangos(bot, arbol, database)

    await database.init_db()
    await database.init_violet_market()
    if not hasattr(bot, "_violet_market_view_loaded"):
        bot.add_view(VioletMarketView())
        bot._violet_market_view_loaded = True
        print(" Violet Market View cargada.")

    if not hasattr(bot, "_violet_market_task"):
        bot._violet_market_task = asyncio.create_task(
            violet_market_loop()
        )
        print(" Violet Market automático activado.")

    # Crear canal Violet Market automáticamente en cada servidor
    if not hasattr(bot, "_violet_market_channels_loaded"):
        for guild in bot.guilds:
            try:
                canal = await violet_market_channel(guild)

                if canal:
                    await violet_market_publish(guild)

            except Exception as error:
                print(
                    f" Error preparando Violet Market en "
                    f"{guild.name}: {error}"
                )

        bot._violet_market_channels_loaded = True
        print(" Canales Violet Market preparados.")
    try:
        await violet_iniciar_actividad_automatica()
    except Exception as error:
        print(f" Error iniciando Violet Autónoma: {error}")

    # Cargar Violet Daily Life una sola vez
    if not hasattr(bot, "_daily_loaded"):
        try:
            from daily.daily_life import setup
            await setup(bot)
            bot._daily_loaded = True
            print(" Violet Daily Life cargado")
        except Exception as error:
            print(f" Error cargando Daily Life: {error}")

    try:
        synced = await arbol.sync()

        print(" Slash commands:", [cmd.name for cmd in synced])
        print(f" Violet conectada como {bot.user}")
        print(f"Comandos sincronizados: {len(synced)}")

    except Exception as error:
        print(f"Error sincronizando comandos: {error}")


@bot.event
async def on_message(message):
    # VIOLET PESCA AUTOMATICA V2 - registrar actividad
    try:
        if (
            message.guild is not None
            and not message.author.bot
            and message.channel.name == VIOLET_PESCA_CANAL_NOMBRE
        ):
            violet_pesca_marcar_usuario(
                message.guild.id,
                message.author.id
            )
    except Exception as error:
        print(f"? Error registrando actividad de pesca: {error}")


    if message.author.bot:
        return

    if message.guild:

        # 🛡️ ANTI-SPAM
        try:
            ahora = asyncio.get_running_loop().time()
            clave = (message.guild.id, message.author.id)

            historial = violet_spam_tracker.setdefault(clave, [])
            historial.append(ahora)

            historial[:] = [
                tiempo for tiempo in historial
                if ahora - tiempo <= 5
            ]

            if len(historial) >= 6:

                if clave not in violet_spam_warned:
                    violet_spam_warned.add(clave)

                    try:
                        await message.delete()
                    except Exception:
                        pass

                    await database.add_security_log(
                        message.guild.id,
                        message.author.id,
                        "ANTI-SPAM",
                        "6 mensajes en 5 segundos"
                    )

                    await message.channel.send(
                        f"? {message.author.mention} "
                        "detuve el spam. Reduce la velocidad de tus mensajes.",
                        delete_after=5
                    )

                    return

                try:
                    await message.delete()
                except Exception:
                    pass

                return

            if len(historial) < 3:
                violet_spam_warned.discard(clave)

        except Exception as error:
            print(f" Error Anti-Spam: {error}")

        try:
            nuevo_xp, nuevo_nivel, viejo_nivel = (
                await database.add_xp(
                    message.author.id,
                    message.guild.id,
                    random.randint(5, 15)
                )
            )

            if nuevo_nivel > viejo_nivel:

                await message.channel.send(
                    f" {message.author.mention} "
                    f"subió al nivel **{nuevo_nivel}**."
                )

        except Exception as error:
            print(f"Error XP: {error}")

    await bot.process_commands(message)


@bot.event
async def on_guild_join(guild):
    # VIOLET PESCA AUTOMATICA V2 - crear canal al entrar
    try:
        await violet_obtener_canal_pesca(guild)
    except Exception as error:
        print(f"? Error creando canal de pesca al entrar: {error}")


    print(f" Violet entró al servidor: {guild.name}")

    me = guild.me

    if me is None:
        return

    canal = None

    for channel in guild.text_channels:
        if channel.permissions_for(me).send_messages:
            canal = channel
            break

    if canal is None:
        print(f"? Violet no tiene permiso para hablar en {guild.name}")
        return

    embed = discord.Embed(
        title=" 💜 Violet ha llegado!",
        description=(
            f"Bienvenidos. Soy **Violet**, tu compañera para este servidor.\n\n"
            f"Gracias por invitarme a **{guild.name}**.\n\n"
            "\n"
            "    **❓ ¿QUÉ PUEDO HACER?** \n"
            "\n\n"
            "🛡️ **Seguridad y Moderación**\n"
            "Protege y administra tu servidor.\n\n"
            " **Música**\n"
            "Reproduce másica y controla la reproducción.\n\n"
            " **Economía**\n"
            "Dinero, tienda, recompensas y perfiles.\n\n"
            " **Social**\n"
            "Interacciones, perfiles y estadísticas.\n\n"
            " **Mascotas**\n"
            "Adopta, cuida y juega con tus mascotas.\n\n"
            " **Juegos**\n"
            "Minijuegos y entretenimiento.\n\n"
            "? **Niveles y Rankings**\n"
            "Gana XP, sube de nivel y compite.\n\n"
            "\n"
            "    **PARA COMENZAR** \n"
            "\n\n"
            " Usa `/violet` para abrir mi **Panel Principal**.\n"
            " Usa `/ayuda` para ver todos mis comandos."
        ),
        color=discord.Color.from_rgb(138, 43, 226)
    )

    embed.set_footer(
        text="Violet  Tu compañera para Discord"
    )

    archivo = discord.File(
        "assets/violet_panel.png",
        filename="violet_panel.png"
    )

    embed.set_image(
        url="attachment://violet_panel.png"
    )
    try:
        await canal.send(
            embed=embed,
            view=WelcomeView(),
            file=archivo
        )

        print(
            f" Bienvenida enviada en #{canal.name} "
            f"del servidor {guild.name}"
        )

    except discord.Forbidden as error:
        print(
            f"? Discord rechazó la bienvenida en #{canal.name}: "
            f"{error}"
        )

        # Intentar un mensaje simple como respaldo
        try:
            await canal.send(
                f" 💜 ¡Hola! Soy **Violet** y acabo de llegar a **{guild.name}**.\n"
                "Usa `/violet` para abrir mi Panel Principal."
            )
            print(f" Mensaje de respaldo enviado en #{canal.name}")

        except discord.Forbidden:
            print(
                f" Violet tampoco puede enviar mensajes en #{canal.name}."
            )

    except Exception as error:
        print(f" Error enviando bienvenida: {error}")
# =========================================================
# PRUEBA MENSAJE DE BIENVENIDA
# =========================================================

@bot.command(name="testbienvenida")
@commands.has_permissions(administrator=True)
async def testbienvenida(ctx):

    embed = discord.Embed(
        title=" 💜 Violet ha llegado!",
        description=(
            f"Bienvenidos. Soy **Violet**, tu compañera para este servidor.\n\n"
            f"Gracias por invitarme a **{ctx.guild.name}**.\n\n"
            "\n"
            "    **❓ ¿QUÉ PUEDO HACER?** \n"
            "\n\n"
            "🛡️ **Seguridad y Moderación**\n"
            "Protege y administra tu servidor.\n\n"
            " **Música**\n"
            "Reproduce másica y controla la reproducción.\n\n"
            " **Economía**\n"
            "Dinero, tienda, recompensas y perfiles.\n\n"
            " **Social**\n"
            "Interacciones, perfiles y estadísticas.\n\n"
            " **Mascotas**\n"
            "Adopta, cuida y juega con tus mascotas.\n\n"
            " **Juegos**\n"
            "Minijuegos y entretenimiento.\n\n"
            "? **Niveles y Rankings**\n"
            "Gana XP, sube de nivel y compite.\n\n"
            "\n"
            "    **PARA COMENZAR** \n"
            "\n\n"
            " Usa `/violet` para abrir mi **Panel Principal**.\n"
            " Usa `/ayuda` para ver todos mis comandos."
        ),
        color=discord.Color.from_rgb(138, 43, 226)
    )

    embed.set_footer(
        text="Violet  Tu compañera para Discord"
    )

    archivo = discord.File(
        "assets/violet_panel.png",
        filename="violet_panel.png"
    )

    embed.set_image(
        url="attachment://violet_panel.png"
    )

    await ctx.send(
        embed=embed,
        view=WelcomeView(),
        file=archivo
    )

# =========================================================
# BOTN DEL MENSAJE DE BIENVENIDA
# =========================================================

class WelcomeView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=180)
    @discord.ui.button(
        label="Abrir Panel",
        emoji="💜",
        style=discord.ButtonStyle.primary
    )
    async def abrir_panel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.defer(ephemeral=True)

        archivo = discord.File(
            "assets/violet_panel.png",
            filename="violet_panel.png"
        )

        await interaction.followup.send(
            embed=violet_main_embed(),
            view=VioletMainView(),
            file=archivo,
            ephemeral=True
        )
# =========================================================
# COMANDO VIOLET
# =========================================================

@arbol.command(
    name="violet",
    description="Abre el panel principal de Violet"
)
async def violet(interaction: discord.Interaction):

    try:
        await interaction.response.defer()

        archivo = discord.File(
            "assets/violet_panel.png",
            filename="violet_panel.png"
        )

        await interaction.followup.send(
            embed=violet_main_embed(),
            view=VioletMainView(),
            file=archivo
        )

    except Exception as error:
        print(f" Error en /violet: {error}")


# =========================================================
# AYUDA
# =========================================================

@arbol.command(
    name="ayuda",
    description="Muestra todos los comandos de Violet"
)
async def ayuda(interaction: discord.Interaction):

    embed = discord.Embed(
        title=" Violet",
        description="Lista de comandos disponibles",
        color=discord.Color.purple()
    )
    embed = discord.Embed(
        title=" Violet",
        description="Lista de comandos disponibles",
        color=discord.Color.purple()
    )

    embed.add_field(
        name=" Social",
        value=(
            "`/beso`\n"
            "`/abrazo`\n"
            "`/pat`\n"
            "`/slap`\n"
            "`/cuddle`\n"
            "`/ship`\n"
            "`/reputacion`\n"
            "`/estadisticas_sociales`\n"
            "`/ranking_interacciones`"
        ),
        inline=False
    )

    embed.add_field(
        name=" Economía",
        value=(
            "`/saldo`\n"
            "`/diario`\n"
            "`/trabajar`\n"
            "`/pagar`\n"
            "`/inventario`\n"
            "`/tienda`\n"
            "`/comprar`"
        ),
        inline=False
    )

    embed.add_field(
        name=" Mascotas",
        value=(
            "`/adoptar`\n"
            "`/mascota`\n"
            "`/alimentar`\n"
            "`/jugar_mascota`\n"
            "`/dormir_mascota`"
        ),
        inline=False
    )

    embed.add_field(
        name=" Juegos",
        value=(
            "`/dado`\n"
            "`/moneda`\n"
            "`/ppt`\n"
            "`/8ball`"
        ),
        inline=False
    )

    embed.add_field(
        name=" Niveles",
        value=(
            "`/perfil`\n"
            "`/rank`"
        ),
        inline=False
    )

    embed.add_field(
        name="🛡️ Moderación",
        value=(
            "`/clear`\n"
            "`/kick`\n"
            "`/ban`\n"
            "`/timeout`\n"
            "`/warn`\n"
            "`/warnings`\n"
            "`/lock`\n"
            "`/unlock`"
        ),
        inline=False
    )

    await responder(
        interaction,
        embed=embed
    )


# =========================================================
# HOLA
# =========================================================

@arbol.command(
    name="hola",
    description="Saluda a Violet"
)
async def hola(interaction: discord.Interaction):

    await responder(
        interaction,
        f" Hola {interaction.user.mention}."
    )


# =========================================================
# REGLAS
# =========================================================

@arbol.command(
    name="reglas",
    description="Muestra las reglas básicas"
)
async def reglas(interaction: discord.Interaction):

    embed = discord.Embed(
        title=" Reglas",
        description=(
            "1. Respeta a los demás.\n"
            "2. No hagas spam.\n"
            "3. No publiques contenido ilegal.\n"
            "4. Respeta al equipo de moderación.\n"
            "5. Diviértete."
        ),
        color=discord.Color.purple()
    )

    await responder(
        interaction,
        embed=embed
    )


# =========================================================
# PERFIL
# =========================================================

@arbol.command(
    name="perfil",
    description="Muestra tu perfil premium de Violet"
)
async def perfil(
    interaction: discord.Interaction,
    usuario: discord.Member = None
):

    usuario = usuario or interaction.user

    data = await database.get_user(
        usuario.id,
        interaction.guild.id
    )

    monedas = data[2]
    xp = data[3]
    nivel = data[4]
    reputacion = data[5]

    xp_actual = xp % 100
    xp_faltante = 100 - xp_actual

    bloques = min(xp_actual // 10, 10)
    barra = "" * bloques + "" * (10 - bloques)

    embed = discord.Embed(
        title=f" {usuario.display_name}",
        description=(
            f"**Perfil Premium de Violet**\n\n"
            f"\n"
            f"    **INFORMACIN** \n"
            f"\n\n"
            f" Usuario: {usuario.mention}\n"
            f" ID: `{usuario.id}`\n\n"
            f" **Violet Premium**\n"
            f" Perfil personalizado"
        ),
        color=discord.Color.purple()
    )

    embed.set_thumbnail(
        url=usuario.display_avatar.url
    )

    embed.add_field(
        name="📈 Nivel",
        value=f"**{nivel}**",
        inline=True
    )

    embed.add_field(
        name=" Economía",
        value=f"**{monedas:,}** monedas",
        inline=True
    )

    embed.add_field(
        name=" Reputación",
        value=f"**{reputacion}**",
        inline=True
    )

    embed.add_field(
        name=" Experiencia",
        value=(
            f"{barra}\n"
            f"**{xp_actual}/100 XP**\n"
            f"Faltan **{xp_faltante} XP**"
        ),
        inline=False
    )

    titulo_violet = obtener_titulo_violet(xp)

    embed.add_field(
        name="🏷️ Título",
        value=f"**{titulo_violet}**",
        inline=False
    )

    embed.add_field(
        name=" Estado",
        value=(
            " **Premium Violet**\n"
            " Perfil exclusivo\n"
            " Experiencia personalizada"
        ),
        inline=False
    )

    embed.set_image(
        url=usuario.display_avatar.with_size(512).url
    )

    embed.set_footer(
        text="Violet  Perfil Premium"
    )

    await responder(
        interaction,
        embed=embed
    )


# =========================================================
# RANK
# =========================================================

@arbol.command(
    name="rank",
    description="Muestra el ranking de niveles"
)
async def rank(interaction: discord.Interaction):

    async with __import__("aiosqlite").connect(
        database.DB_NAME
    ) as db:

        cursor = await db.execute("""
            SELECT user_id, level, xp
            FROM users
            WHERE guild_id = ?
            ORDER BY level DESC, xp DESC
            LIMIT 10
        """, (interaction.guild.id,))

        filas = await cursor.fetchall()

    if not filas:
        await responder(
            interaction,
            " Todavía no hay datos."
        )
        return

    texto = ""

    for posicion, fila in enumerate(
        filas,
        start=1
    ):
        miembro = interaction.guild.get_member(
            fila[0]
        )

        nombre = (
            miembro.display_name
            if miembro
            else f"Usuario {fila[0]}"
        )

        titulo = obtener_titulo_violet(fila[2])

        texto += (
            f"**{posicion}.** {nombre} "
            f" Nivel **{fila[1]}** "
            f"({fila[2]} XP) "
            f" ? {titulo}\n"
        )

    embed = discord.Embed(
        title=" Ranking",
        description=texto,
        color=discord.Color.gold()
    )

    await responder(
        interaction,
        embed=embed
    )


# =========================================================
# ECONOMÍA
# =========================================================

@arbol.command(
    name="saldo",
    description="Muestra tu saldo y dinero guardado en el banco"
)
async def saldo(interaction: discord.Interaction):

    user = await database.get_user(
        interaction.user.id,
        interaction.guild.id
    )

    saldo_disponible = user[2]

    saldo_banco = await database.get_bank_balance(
        interaction.user.id,
        interaction.guild.id
    )

    total = saldo_disponible + saldo_banco

    embed = discord.Embed(
        title=" Saldo de Violet",
        color=discord.Color.purple()
    )

    embed.add_field(
        name=" Disponible",
        value=f"**{saldo_disponible:,}** monedas",
        inline=True
    )

    embed.add_field(
        name=" Banco",
        value=f"**{saldo_banco:,}** monedas",
        inline=True
    )

    embed.add_field(
        name=" Total",
        value=f"**{total:,}** monedas",
        inline=False
    )

    await responder(
        interaction,
        embed=embed
    )


@arbol.command(
    name="diario",
    description="Reclama tu recompensa diaria"
)
async def diario(interaction: discord.Interaction):

    correcto, valor = await database.claim_daily(
        interaction.user.id,
        interaction.guild.id
    )

    if not correcto:

        horas = valor // 3600
        minutos = (valor % 3600) // 60

        await responder(
            interaction,
            f"❌ Ya reclamaste tu recompensa. "
            f"Espera **{horas}h {minutos}m**.",
            ephemeral=True
        )
        return

    await responder(
        interaction,
        f" Recibiste **{valor}** monedas."
    )


@arbol.command(
    name="trabajar",
    description="Trabaja para ganar monedas"
)
async def trabajar(interaction: discord.Interaction):

    correcto, valor = await database.work(
        interaction.user.id,
        interaction.guild.id
    )

    if not correcto:

        minutos = valor // 60

        await responder(
            interaction,
            f"? Debes esperar aproximadamente "
            f"**{minutos} minutos**.",
            ephemeral=True
        )
        return

    await responder(
        interaction,
        f" Trabajaste y ganaste **{valor}** monedas."
    )


@arbol.command(
    name="pagar",
    description="Paga monedas a otro usuario"
)
async def pagar(
    interaction: discord.Interaction,
    usuario: discord.Member,
    cantidad: app_commands.Range[int, 1, 1000000]
):

    if usuario.id == interaction.user.id:

        await responder(
            interaction,
            " No puedes pagarte a ti mismo.",
            ephemeral=True
        )
        return

    correcto = await database.remove_balance(
        interaction.user.id,
        interaction.guild.id,
        cantidad
    )

    if not correcto:

        await responder(
            interaction,
            " No tienes suficientes monedas.",
            ephemeral=True
        )
        return

    await database.add_balance(
        usuario.id,
        interaction.guild.id,
        cantidad
    )

    await responder(
        interaction,
        f" {interaction.user.mention} "
        f"le pagó **{cantidad}** monedas a "
        f"{usuario.mention}."
    )


@arbol.command(
    name="inventario",
    description="Muestra tu inventario"
)
async def inventario(interaction: discord.Interaction):

    items = await database.get_inventory(
        interaction.user.id,
        interaction.guild.id
    )

    if not items:

        await responder(
            interaction,
            " Tu inventario está vacío."
        )
        return

    texto = ""

    for item, cantidad in items:
        texto += f" **{item}** x{cantidad}\n"

    embed = discord.Embed(
        title=" Inventario",
        description=texto,
        color=discord.Color.purple()
    )

    await responder(
        interaction,
        embed=embed
    )


# =========================================================
# TIENDA DE MINERÍA Y PESCA
# =========================================================

TIENDA_MINERIA_PESCA = {
    1: [
        ('⛏️', 'Pico de Hierro', '10% más de probabilidad de recursos raros', 2500),
        ('⛏️', 'Pico de Oro', '20% más de probabilidad de recursos raros', 10000),
        ('💎', 'Pico de Diamante', '35% más de probabilidad de recursos raros', 50000),
        ('🛒', 'Caña Reforzada', '10% más de probabilidad de peces raros', 2500),
        ('🛒', 'Caña de Oro', '20% más de probabilidad de peces raros', 10000),
        ('🛒', 'Caña de Diamante', '35% más de probabilidad de peces raros', 50000),
        ('🛒', 'Cubeta de Pesca', '+5% recompensa de pesca', 5000),
        ('🛒', 'Guantes Mineros', '+5% recompensa de minería', 5000),
    ],
    2: [
        ('🛒', 'Detector de Minerales', 'Aumenta la aparición de minerales raros', 75000),
        ('🛒', 'Taladro Minero', 'Aumenta considerablemente los minerales valiosos', 150000),
        ('🛒', 'Núcleo Violeta', 'Potencia minerales legendarios y míticos', 350000),
        ('🛒', 'Radar de Peces', 'Aumenta la aparición de peces raros', 75000),
        ('🛒', 'Seuelo Abisal', 'Aumenta peces valiosos', 150000),
        ('🛒', 'Seuelo Violeta', 'Potencia peces legendarios y míticos', 350000),
        ('🛒', 'Amuleto de Suerte', 'Aumenta la suerte general', 50000),
        ('🛒', 'Amuleto pico', 'Aumenta la probabilidad de recompensas épicas', 125000),
        ('🛒', 'Amuleto Legendario', 'Aumenta la probabilidad de recompensas legendarias', 300000),
        ('🛒', 'Amuleto Mítico', 'Aumenta la probabilidad de recompensas míticas', 750000),
    ],
    3: [
        ('🛒', 'Suerte Minera', 'Mejora permanentemente la suerte durante minería', 100000),
        ('🛒', 'Suerte Pesquera', 'Mejora permanentemente la suerte durante pesca', 100000),
        ('🛒', 'Minería Rápida', 'Reduce el tiempo entre actividades mineras', 150000),
        ('🛒', 'Pesca Rápida', 'Reduce el tiempo entre actividades pesqueras', 150000),
        ('🛒', 'Fortuna Legendaria', 'Aumenta objetos legendarios', 300000),
        ('🛒', 'Bendición de Violet', 'Aumenta objetos míticos', 750000),
        ('✨', 'Multiplicador XP', 'Aumenta la XP obtenida', 500000),
        ('🛒', 'Fortuna Dorada', 'Aumenta las monedas obtenidas', 600000),
        ('🛒', 'Favor Real', 'Gran aumento de recompensas raras', 1000000),
        ('🛒', 'Favor Cósmico', 'Máxima mejora de suerte', 2500000),
    ],
    4: [
        ('🛒', 'Poción de XP', 'Otorga una bonificación temporal de XP', 15000),
        ('🛒', 'Poción de Suerte', 'Aumenta temporalmente la suerte', 20000),
        ('🛒', 'Poción de Fortuna', 'Aumenta temporalmente las monedas', 25000),
        ('🛒', 'Poción de Velocidad', 'Reduce temporalmente el cooldown', 30000),
        ('🛒', 'Carnada Premium', 'Mejora una expedición de pesca', 10000),
        ('🛒', 'Dinamita Minera', 'Mejora una expedición minera', 12000),
        ('🛒', 'Brújula Misteriosa', 'Aumenta la posibilidad de hallar objetos raros', 40000),
        ('🛒', 'Llave Abisal', 'Aumenta las recompensas de rareza alta', 75000),
        ('🛒', 'Caja de Pesca', 'Entrega una recompensa aleatoria', 25000),
        ('🛒', 'Caja Minera', 'Entrega una recompensa aleatoria', 25000),
    ],
    5: [
        ('🛒', 'Mochila Grande', 'Aumenta la capacidad del inventario', 100000),
        ('🛒', 'Kit Minero', 'Mejora permanentemente la minería', 175000),
        ('🛒', 'Kit Pesquero', 'Mejora permanentemente la pesca', 175000),
        ('🛒', 'Detector Supremo', 'Gran aumento de minerales raros', 500000),
        ('🛒', 'Radar Oceánico', 'Gran aumento de peces raros', 500000),
        ('🛒', 'Reliquia de Violet', 'Aumenta recompensas míticas', 1500000),
        ('🛒', 'Artefacto Cósmico', 'Bonificación máxima de exploración', 5000000),
        ('🛒', 'Corona del Explorador', 'Bonificación global de minería y pesca', 10000000),
    ],
}


def obtener_pagina_tienda_mineria_pesca(pagina: int):

    pagina = max(1, min(5, pagina))

    return TIENDA_MINERIA_PESCA[pagina]


def crear_embed_tienda_mineria_pesca(pagina: int):

    objetos = obtener_pagina_tienda_mineria_pesca(pagina)

    titulos = {
        1: "? Equipamiento",
        2: " Equipamiento avanzado",
        3: " Mejoras especiales",
        4: " Consumibles",
        5: " Reliquias y objetos premium"
    }

    texto = ""

    for emoji, nombre, efecto, precio in objetos:
        texto += (
            f"{emoji} **{nombre}**\n"
            f"    {efecto}\n"
            f"    `{precio:,}` monedas\n\n"
        )

    texto += (
        "\n"
        f" Página **{pagina}/5**\n"
        "Usa `/comprar objeto cantidad` para adquirir una mejora."
    )

    return discord.Embed(
        title=f" Tienda de Violet  {titulos[pagina]}",
        description=texto,
        color=discord.Color.purple()
    )


@arbol.command(
    name="banco",
    description="Consulta tu dinero disponible y tu dinero guardado en el banco"
)
async def banco(interaction: discord.Interaction):

    datos = await database.get_user(
        interaction.user.id,
        interaction.guild.id
    )

    saldo = datos[2]

    banco_saldo = await database.get_bank_balance(
        interaction.user.id,
        interaction.guild.id
    )

    total = saldo + banco_saldo

    embed = discord.Embed(
        title=" Banco de Violet",
        color=discord.Color.purple()
    )

    embed.add_field(
        name=" Dinero disponible",
        value=f"**{saldo:,}** monedas",
        inline=True
    )

    embed.add_field(
        name=" Dinero guardado",
        value=f"**{banco_saldo:,}** monedas",
        inline=True
    )

    embed.add_field(
        name=" Patrimonio total",
        value=f"**{total:,}** monedas",
        inline=False
    )

    embed.set_footer(
        text="Violet Bank  Tu dinero, bajo control"
    )

    await responder(
        interaction,
        embed=embed
    )


@arbol.command(
    name="depositar",
    description="Guarda dinero en el banco"
)
@app_commands.describe(
    cantidad="Cantidad de monedas que quieres guardar"
)
async def depositar(
    interaction: discord.Interaction,
    cantidad: app_commands.Range[int, 1, 1000000000]
):

    correcto = await database.deposit_bank(
        interaction.user.id,
        interaction.guild.id,
        cantidad
    )

    if not correcto:

        await responder(
            interaction,
            f" No tienes suficientes monedas disponibles para depositar **{cantidad:,}**.",
            ephemeral=True
        )
        return

    banco_saldo = await database.get_bank_balance(
        interaction.user.id,
        interaction.guild.id
    )

    await responder(
        interaction,
        f" Depositaste **{cantidad:,}** monedas.\n"
        f" Saldo bancario: **{banco_saldo:,}** monedas."
    )


@arbol.command(
    name="retirar",
    description="Retira dinero guardado en el banco"
)
@app_commands.describe(
    cantidad="Cantidad de monedas que quieres retirar"
)
async def retirar(
    interaction: discord.Interaction,
    cantidad: app_commands.Range[int, 1, 1000000000]
):

    correcto = await database.withdraw_bank(
        interaction.user.id,
        interaction.guild.id,
        cantidad
    )

    if not correcto:

        await responder(
            interaction,
            f" No tienes suficientes monedas en el banco para retirar **{cantidad:,}**.",
            ephemeral=True
        )
        return

    banco_saldo = await database.get_bank_balance(
        interaction.user.id,
        interaction.guild.id
    )

    await responder(
        interaction,
        f" Retiraste **{cantidad:,}** monedas.\n"
        f" Saldo bancario restante: **{banco_saldo:,}** monedas."
    )


@arbol.command(
    name="tienda",
    description="Muestra la tienda"
)
async def tienda(interaction: discord.Interaction):

    embed = crear_embed_tienda_mineria_pesca(1)

    await responder(
        interaction,
        embed=embed,
        view=TiendaMineriaPescaView(1)
    )


@arbol.command(
    name="comprar",
    description="Compra un objeto o mejora de la tienda"
)
@app_commands.describe(
    objeto="Objeto que quieres comprar",
    cantidad="Cantidad"
)
async def comprar(
    interaction: discord.Interaction,
    objeto: str,
    cantidad: app_commands.Range[int, 1, 100]
):

    precios = {
        "comida": 100,
        "regalo": 250,
        "gema": 500,
        "suerte": 1000,
        "pocion_xp": 2500,
        "caja_misteriosa": 5000,
        "gema_rara": 10000,
        "corona": 25000,
        "cristal": 50000,
        "orbe": 75000,
        "trofeo": 100000
    }

    # Todos los objetos nuevos de minería y pesca
    for pagina in TIENDA_MINERIA_PESCA.values():
        for emoji, nombre, efecto, precio in pagina:
            precios[nombre.lower()] = precio

    objeto = objeto.lower().strip()

    for pagina in TIENDA_MINERIA_PESCA.values():
        for emoji, nombre, efecto, precio in pagina:
            if objeto == nombre.lower():
                precios[objeto] = precio
                break

    if objeto not in precios:

        await responder(
            interaction,
            " Ese objeto no existe en la tienda.",
            ephemeral=True
        )
        return

    precio_total = precios[objeto] * cantidad

    correcto = await database.remove_balance(
        interaction.user.id,
        interaction.guild.id,
        precio_total
    )

    if not correcto:

        await responder(
            interaction,
            f" No tienes suficientes monedas.\n"
            f" Necesitas **{precio_total:,}** monedas.",
            ephemeral=True
        )
        return

    await database.add_item(
        interaction.user.id,
        interaction.guild.id,
        objeto,
        cantidad
    )

    await responder(
        interaction,
        f" Compraste **{cantidad}x {objeto}**\n"
        f" Precio: **{precio_total:,}** monedas."
    )


# =========================================================
# NIVELES DE RELACIN SOCIAL
# =========================================================
# PERFIL SOCIAL
# =========================================================

@arbol.command(
    name="perfil_social",
    description="Muestra tu relación y estadísticas con otro usuario"
)
async def perfil_social(
    interaction: discord.Interaction,
    usuario: discord.Member
):

    if interaction.guild is None:
        await responder(
            interaction,
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    if usuario.id == interaction.user.id:
        await responder(
            interaction,
            " Debes seleccionar a otra persona.",
            ephemeral=True
        )
        return

    try:
        total = await database.get_total_interactions(
            interaction.guild.id,
            interaction.user.id,
            usuario.id
        )

        interacciones = await database.get_interactions(
            interaction.guild.id,
            interaction.user.id,
            usuario.id
        )

    except Exception as error:
        print(f" Error obteniendo perfil social: {error}")

        await responder(
            interaction,
            " No pude obtener el perfil social.",
            ephemeral=True
        )
        return

    nivel, icono = nivel_relacion(total)
    progreso = progreso_relacion(total)

    nombres = {
        "beso": " Besos",
        "abrazo": " Abrazos",
        "pat": " Pats",
        "slap": " Slaps",
        "cuddle": " Cuddles",
        "highfive": " Highfives",
        "poke": " Pokes",
        "mordisco": " Mordiscos",
        "bailar": " Bailes",
        "dormir": " Siestas"
    }

    estadisticas = []

    for accion, cantidad in interacciones:
        if cantidad > 0:
            estadisticas.append(
                f"{nombres.get(accion, accion)}: **{cantidad}**"
            )

    if estadisticas:
        texto_estadisticas = "\n".join(estadisticas)
    else:
        texto_estadisticas = "Todavía no tienen interacciones."

    embed = discord.Embed(
        title=f" Perfil social",
        description=(
            f"**{interaction.user.display_name}**  "
            f"**{usuario.display_name}**\n\n"
            f"{icono} **Relación:** {nivel}\n"
            f" **Interacciones:** **{total}**\n"
            f"{progreso}\n\n"
            f"\n"
            f"    **ESTADÍSTICAS** \n"
            f"\n\n"
            f"{texto_estadisticas}"
        ),
        color=discord.Color.purple()
    )

    embed.set_thumbnail(url=usuario.display_avatar.url)

    embed.set_footer(
        text="Violet  Sistema social"
    )

    await responder(
        interaction,
        embed=embed
    )




def nivel_relacion(total):
    if total >= 250:
        return " Alma gemela", ""
    if total >= 100:
        return " Vínculo especial", ""
    if total >= 50:
        return " Mejores amigos", ""
    if total >= 25:
        return " Cercanos", ""
    if total >= 10:
        return " Amistad", ""
    return " Conocidos", ""


def progreso_relacion(total):
    niveles = [
        (0, 10, "Amistad"),
        (10, 25, "Cercanos"),
        (25, 50, "Mejores amigos"),
        (50, 100, "Vínculo especial"),
        (100, 250, "Alma gemela"),
        (250, None, "Máximo")
    ]

    for minimo, maximo, siguiente in niveles:
        if total >= minimo and (maximo is None or total < maximo):
            if maximo is None:
                return f" Nivel máximo alcanzado: **{total}** interacciones"

            faltan = maximo - total
            return f" Faltan **{faltan}** interacciones para **{siguiente}**"

    return ""


# =========================================================
# LOGROS SOCIALES
# =========================================================

LOGROS_SOCIALES = {
    "primer_beso": ("💋", "Primer beso", "Da tu primer beso."),
    "primer_abrazo": ("🫂", "Primer abrazo", "Da tu primer abrazo."),
    "primer_pat": ("🐾", "Primer pat", "Da tu primer pat."),
    "primer_slap": ("👋", "Primer slap", "Haz tu primer slap."),
    "primer_cuddle": ("🤗", "Primer cuddle", "Haz tu primer cuddle."),
    "primer_highfive": ("🙌", "Primer highfive", "Haz tu primer highfive."),
    "primer_poke": ("👉", "Primer poke", "Haz tu primer poke."),
    "primer_mordisco": ("🦷", "Primer mordisco", "Da tu primer mordisco."),
    "primer_bailar": ("💃", "Primer baile", "Baila por primera vez."),
    "primer_dormir": ("😴", "Primera siesta", "Duerme junto a alguien por primera vez."),
    "inseparables": ("💞", "Inseparables", "Alcanza 25 interacciones."),
    "pareja_perfecta": ("💖", "Pareja perfecta", "Alcanza 100 interacciones."),
    "alma_gemela": ("💍", "Alma gemela", "Alcanza 250 interacciones."),
    "amigo_animales": ("🐾", "Amigo de los animales", "Haz 50 pats."),
    "romantico": ("🌹", "Romántico", "Da 50 besos."),
    "abrazador": ("🫂", "Abrazador", "Da 100 abrazos."),
    "maestro_social": ("👑", "Maestro social", "Usa las 10 interacciones sociales.")
}


@arbol.command(
    name="logros_sociales",
    description="Muestra tus logros sociales"
)
async def logros_sociales(interaction: discord.Interaction):

    if interaction.guild is None:
        await responder(
            interaction,
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    try:
        desbloqueados = await database.get_logros_sociales(
            interaction.guild.id,
            interaction.user.id
        )
    except Exception as error:
        print(f" Error obteniendo logros: {error}")

        await responder(
            interaction,
            " No pude obtener tus logros.",
            ephemeral=True
        )
        return

    ids_desbloqueados = {
        logro[0]
        for logro in desbloqueados
    }

    texto = []

    for logro_id, datos in LOGROS_SOCIALES.items():

        emoji, nombre, descripcion = datos
        recompensa = " 50 monedas  ? 25 XP"

        if logro_id in ids_desbloqueados:
            texto.append(
                f"{emoji} **{nombre}**\n"
                f" {descripcion}\n"
                f"  {recompensa}"
            )
        else:
            texto.append(
                f" **{nombre}**\n"
                f" {descripcion}\n"
                f"  {recompensa}"
            )

    cantidad = len(ids_desbloqueados)
    total_logros = len(LOGROS_SOCIALES)

    embed = discord.Embed(
        title=" Logros sociales",
        description=(
            f"**{interaction.user.display_name}**\n\n"
            f" Desbloqueados: **{cantidad}/{total_logros}**\n\n"
            + "\n\n".join(texto)
        ),
        color=discord.Color.purple()
    )

    embed.set_thumbnail(
        url=interaction.user.display_avatar.url
    )

    embed.set_footer(
        text="Violet  Sistema de logros"
    )

    await responder(
        interaction,
        embed=embed
    )


@arbol.command(
    name="ranking_social",
    description="Muestra el ranking de interacciones sociales del servidor"
)
async def ranking_social(interaction: discord.Interaction):

    if interaction.guild is None:
        await responder(
            interaction,
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    try:
        ranking = await database.get_interaction_ranking(
            interaction.guild.id,
            limit=10
        )
    except Exception as error:
        print(f" Error obteniendo ranking social: {error}")
        await responder(
            interaction,
            " No pude obtener el ranking social.",
            ephemeral=True
        )
        return

    if not ranking:
        await responder(
            interaction,
            " Todavía no hay interacciones sociales en este servidor."
        )
        return

    posiciones = ["", "", ""]

    lineas = []

    for posicion, fila in enumerate(ranking, start=1):
        user_id = fila[0]
        cantidad = fila[1]

        miembro = interaction.guild.get_member(user_id)

        if miembro:
            nombre = miembro.display_name
            mencion = miembro.mention
        else:
            nombre = f"Usuario {user_id}"
            mencion = nombre

        icono = posiciones[posicion - 1] if posicion <= 3 else f"**{posicion}.**"

        lineas.append(
            f"{icono} {mencion}   **{cantidad}** interacciones"
        )

    embed = discord.Embed(
        title=" Ranking social",
        description="\n".join(lineas),
        color=discord.Color.purple()
    )

    embed.set_footer(
        text="Violet  Ranking de interacciones"
    )

    await responder(
        interaction,
        embed=embed
    )


# =========================================================

# =========================================================
# MINERÍA
# =========================================================

MINERALES = [
('🛒', 'Piedra', 'Común', 10, 5, 28),
('🛒', 'Carbón', 'Común', 20, 8, 18),
('🛒', 'Arcilla', 'Común', 25, 9, 12),
('🛒', 'Hierro', 'Común', 35, 11, 10),
('🛒', 'Cobre', 'Común', 45, 12, 8),
('🛒', 'Obsidiana', 'Poco común', 80, 18, 6),
('🪨', 'Estado', 'Poco común', 55, 14, 6),
('⚙️', 'Zinc', 'Poco común', 65, 15, 5),
('🛒', 'Níquel', 'Poco común', 75, 17, 5),
('🛒', 'Plomo', 'Poco común', 70, 16, 4),
('🛒', 'Plata', 'Raro', 120, 20, 3.5),
('🛒', 'Esmeralda', 'Raro', 180, 24, 2.8),
('🛒', 'Rubí', 'Raro', 220, 27, 2.5),
('🛒', 'Zafiro', 'Raro', 230, 28, 2.3),
('🛒', 'Ámbar', 'Raro', 200, 26, 2.2),
('🛒', 'Amatista', 'Raro', 210, 27, 2),
('🛒', 'Topacio', 'Raro', 240, 29, 1.8),
('🛒', 'Peridoto', 'Raro', 260, 30, 1.7),
('🛒', 'Aguamarina', 'Raro', 280, 31, 1.5),
('🛒', 'Citrino', 'Raro', 250, 30, 1.5),
('🛒', 'Oro', 'pico', 350, 35, 1.3),
('🛒', 'Diamante', 'pico', 500, 50, 1.0),
('🛒', 'nix', 'pico', 450, 45, 0.9),
('🛒', 'Cuarzo Blanco', 'pico', 380, 38, 0.9),
('🛒', 'Cuarzo Violeta', 'pico', 600, 55, 0.8),
('🛒', 'Basalto Antiguo', 'pico', 420, 42, 0.8),
('🛒', 'Piedra Lunar', 'pico', 700, 60, 0.7),
('☀️', 'Piedra Solar', 'pico', 750, 65, 0.65),
('🛒', 'Cristal Marino', 'pico', 650, 58, 0.6),
('❄️', 'Cristal Glacial', 'pico', 720, 62, 0.6),
('🛒', 'Cristal Ígneo', 'pico', 800, 68, 0.55),
('🛒', 'Cristal Eléctrico', 'pico', 850, 70, 0.5),
('🛒', 'Cristal Natural', 'pico', 620, 56, 0.55),
('🛒', 'Cristal Estelar', 'Legendario', 1000, 75, 0.45),
('🛒', 'Fragmento Estelar', 'Legendario', 1200, 82, 0.4),
('🛒', 'Mineral Lunar', 'Legendario', 1300, 85, 0.38),
('☀️', 'Mineral Solar', 'Legendario', 1400, 90, 0.35),
('🛒', 'Mineral Cósmico', 'Legendario', 1600, 95, 0.3),
('🛒', 'Mineral Dimensional', 'Legendario', 1800, 105, 0.28),
('🌌', 'Mineral del Vacío', 'Legendario', 1900, 110, 0.25),
('🛒', 'Fragmento Abisal', 'Legendario', 2100, 115, 0.23),
('🛒', 'Mineral Maldito', 'Legendario', 2200, 120, 0.2),
('🛒', 'Mineral Real', 'Legendario', 2500, 125, 0.18),
('🛒', 'Cristal Violeta', 'Mítico', 3000, 150, 0.12),
('🛒', 'Cristal Arcano', 'Mítico', 3500, 165, 0.11),
('🛒', 'Núcleo Cósmico', 'Mítico', 4500, 190, 0.09),
('🛒', 'Núcleo Dimensional', 'Mítico', 5000, 210, 0.08),
('🛒', 'Núcleo del Vacío', 'Mítico', 6000, 230, 0.07),
('🛒', 'Esencia Estelar', 'Mítico', 6500, 240, 0.06),
('🛒', 'Corazón de Cristal', 'Mítico', 7000, 250, 0.055),
('🛒', 'Fragmento Celestial', 'Mítico', 7500, 260, 0.05),
('🛒', 'Cristal Prisma', 'Mítico', 8000, 275, 0.045),
('🛒', 'Corazón de Violet', 'Mítico', 10000, 300, 0.035),
('🛒', 'Granito', 'Común', 84, 14, 5.0),
('🛒', 'Mármol', 'Común', 85, 14, 5.0),
('🛒', 'Pizarra', 'Común', 86, 15, 5.0),
('🛒', 'Caliza', 'Común', 87, 15, 5.0),
('🛒', 'Arenisca', 'Común', 88, 15, 5.0),
('🛒', 'Cuarzo', 'Común', 89, 15, 5.0),
('🔷', 'Cobalto', 'Poco común', 200, 27, 3.0),
('⚙️', 'Titanio', 'Poco común', 202, 27, 3.0),
('🔩', 'Cromo', 'Poco común', 204, 27, 3.0),
('🟣', 'Manganeso', 'Poco común', 206, 27, 3.0),
('⚙️', 'Molibdeno', 'Poco común', 208, 27, 3.0),
('🔋', 'Litio', 'Poco común', 210, 28, 3.0),
('🛒', 'Jade', 'Raro', 448, 46, 1.5),
('🛒', 'Granate', 'Raro', 451, 46, 1.5),
('🛒', 'Lapislázuli', 'Raro', 454, 47, 1.5),
('🛒', 'Fluorita', 'Raro', 457, 47, 1.5),
('🛒', 'Malaquita', 'Raro', 460, 47, 1.5),
('🛒', 'Turquesa', 'Raro', 463, 47, 1.5),
('🛒', 'Pirita', 'Raro', 466, 48, 1.5),
('🛒', 'Cornalina', 'Raro', 469, 48, 1.5),
('🛒', 'Alejandrita', 'pico', 970, 79, 0.7),
('🛒', 'Opalo', 'pico', 975, 80, 0.7),
('🛒', 'Tanzanita', 'pico', 980, 80, 0.7),
('🛒', 'Morganita', 'pico', 985, 80, 0.7),
('🛒', 'Piedra Dragón', 'pico', 990, 81, 0.7),
('🛒', 'Piedra Magmática', 'pico', 995, 81, 0.7),
('🧊', 'Hielo Mineral', 'pico', 1000, 81, 0.7),
('🛒', 'Mineral del Trueno', 'pico', 1005, 82, 0.7),
('🛒', 'Mineral del Bosque', 'pico', 1010, 82, 0.7),
('🛒', 'Mineral de Mareas', 'pico', 1015, 82, 0.7),
('🛒', 'Fragmento de Luna', 'Legendario', 2172, 184, 0.25),
('☀️', 'Fragmento Solar', 'Legendario', 2180, 185, 0.25),
('🛒', 'Metal Estelar', 'Legendario', 2188, 186, 0.25),
('🛒', 'Aleación Dimensional', 'Legendario', 2196, 187, 0.25),
('👁️', 'Ojo Mineral', 'Legendario', 2204, 188, 0.25),
('🛒', 'Esencia Oscura', 'Legendario', 2212, 189, 0.25),
('🛒', 'Oro Celestial', 'Legendario', 2220, 190, 0.25),
('🛒', 'Polvo Cósmico', 'Legendario', 2228, 191, 0.25),
('🛒', 'Cristal Astral', 'Mítico', 5380, 364, 0.08),
('🛒', 'Cristal del Oráculo', 'Mítico', 5395, 366, 0.08),
('🛒', 'Prisma Cósmico', 'Mítico', 5410, 368, 0.08),
('🛒', 'Esencia Dimensional', 'Mítico', 5425, 370, 0.08),
('🛒', 'Esencia del Vacío', 'Mítico', 5440, 372, 0.08),
('🛒', 'Polvo Celestial', 'Mítico', 5455, 374, 0.08),
('🛒', 'Fragmento Violeta', 'Mítico', 5470, 376, 0.08),
('🛒', 'Corona Mineral', 'Mítico', 5485, 378, 0.08),
('🛒', 'Singularidad Mineral', 'Mítico', 5500, 380, 0.08)
]


@arbol.command(
    name="minar",
    description="Extrae minerales y gana monedas y XP"
)
async def minar(interaction: discord.Interaction):

    if interaction.guild is None:
        await responder(
            interaction,
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    guild_id = interaction.guild.id
    user_id = interaction.user.id

    disponible, restante = comprobar_cooldown_actividad(
        guild_id,
        user_id,
        "mineria"
    )

    if not disponible:
        await responder(
            interaction,
            f"? Ya minaste recientemente. "
            f"Podrás volver a usar `/minar` en **{formato_cooldown(restante)}**.",
            ephemeral=True
        )
        return

    registrar_uso_actividad(
        guild_id,
        user_id,
        "mineria"
    )

    try:
        nivel, xp, pico = await database.get_mining_stats(
            guild_id,
            user_id
        )

        # El nivel del pico mejora ligeramente las posibilidades
        disponibles = MINERALES.copy()

        pesos = [mineral[5] for mineral in disponibles]

        # Bonus progresivo del pico
        if pico > 1:
            for i in range(len(pesos)):
                if i >= 4:
                    pesos[i] *= 1 + ((pico - 1) * 0.15)

        mineral = random.choices(
            disponibles,
            weights=pesos,
            k=1
        )[0]

        emoji, nombre, rareza, valor, xp_ganado, _ = mineral

        nuevo_descubrimiento = await database.add_collection_item(
            guild_id,
            user_id,
            "mineria",
            nombre
        )

        await database.add_mining_item(
            guild_id,
            user_id,
            nombre,
            1
        )

        # Progreso de misiones
        await database.add_mission_progress(
            guild_id,
            user_id,
            "minar_5",
            amount=1,
            required=5
        )

        if rareza in ("Raro", "pico", "Legendario", "Mítico"):
            await database.add_mission_progress(
                guild_id,
                user_id,
                "minar_raro",
                amount=1,
                required=1
            )

        if rareza == "Mítico":
            await database.add_mission_progress(
                guild_id,
                user_id,
                "mitico",
                amount=1,
                required=1
            )

        await database.add_balance(
            user_id,
            guild_id,
            valor
        )

        nivel_anterior = nivel

        nuevo_nivel, nuevo_xp, _ = await database.add_mining_xp(
            guild_id,
            user_id,
            xp_ganado
        )

        texto = (
            f"💎 {interaction.user.mention} golpeó la roca...\n\n"
            f" **⛏️ ¡Encontraste un mineral!**\n\n"
            f"{emoji} **{nombre}**\n"
            f"Rareza: **{rareza}**\n"
            f" Valor: **+{valor}** monedas\n"
            f"? XP minería: **+{xp_ganado}**\n\n"
            f"? Nivel de minería: **{nuevo_nivel}**\n"
            f" XP: **{nuevo_xp}**"
        )

        if nuevo_nivel > nivel_anterior:
            texto += (
                f"\n\n **⬆️ ¡SUBISTE DE NIVEL!**\n"
                f"? Minería nivel **{nuevo_nivel}**"
            )

        if nombre == "Diamante":
            texto += "\n\n **💎 ¡Encontraste un DIAMANTE!**"

        elif nombre == "Cristal Violeta":
            texto += (
                "\n\n **✨ ¡EVENTO ULTRA RARO!**\n"
                "Has encontrado un **Cristal Violeta**."
            )

        embed = discord.Embed(
            title="⛏️ Expedición minera",
            description=texto,
            color=discord.Color.purple()
        )

        embed.set_thumbnail(
            url=interaction.user.display_avatar.url
        )

        embed.set_footer(
            text=f"Violet  Pico nivel {pico}"
        )

        await responder(
            interaction,
            embed=embed
        )

    except Exception as error:
        print(f" Error en /minar: {error}")

        await responder(
            interaction,
            " Ocurrió un error durante la minería.",
            ephemeral=True
        )



# =========================================================
# PESCA
# =========================================================

PECES = [
('🛒', 'Sardina', 'Común', 15, 5, 24),
('🛒', 'Pez tropical', 'Común', 30, 8, 18),
('🛒', 'Camarón', 'Común', 35, 9, 10),
('🛒', 'Cangrejo', 'Común', 40, 10, 8),
('🛒', 'Pez globo', 'Común', 50, 12, 7),
('🛒', 'Calamar', 'Común', 60, 13, 7),
('🛒', 'Almeja', 'Común', 70, 14, 6),
('🛒', 'Langostino', 'Común', 80, 15, 5),
('🛒', 'Caballa', 'Común', 55, 11, 6),
('🛒', 'Anchoa', 'Común', 45, 10, 7),
('🛒', 'Merluza', 'Poco común', 90, 16, 5),
('🛒', 'Salmón', 'Poco común', 110, 18, 4.5),
('🛒', 'Trucha', 'Poco común', 120, 19, 4),
('🛒', 'Atún', 'Poco común', 150, 22, 3.5),
('🛒', 'Pulpo', 'Poco común', 170, 24, 3),
('🛒', 'Langosta', 'Poco común', 190, 25, 2.8),
('🛒', 'Pez espada', 'Raro', 250, 30, 2),
('🛒', 'Delfín', 'Raro', 280, 32, 1.8),
('🛒', 'Tortuga marina', 'Raro', 300, 34, 1.5),
('🛒', 'Pez payaso', 'Raro', 220, 28, 1.8),
('🛒', 'Pez Ángel', 'Raro', 260, 31, 1.6),
('🛒', 'Pez león', 'Raro', 290, 33, 1.4),
('🛒', 'Calamar gigante', 'pico', 450, 45, 0.9),
('🛒', 'Tiburón', 'pico', 500, 50, 0.8),
('🛒', 'Orca', 'pico', 600, 55, 0.7),
('🛒', 'Pez Dragón', 'pico', 700, 60, 0.6),
('🛒', 'Ballena', 'Legendario', 1000, 75, 0.45),
('🛒', 'Ballena Azul', 'Legendario', 1300, 85, 0.35),
('🛒', 'Serpiente Marina', 'Legendario', 1600, 95, 0.28),
('🛒', 'Leviatán', 'Mítico', 3000, 140, 0.12),
('🛒', 'Pez Violeta', 'Mítico', 4000, 170, 0.08),
('🛒', 'Pez Cósmico', 'Mítico', 5000, 200, 0.06),
('🛒', 'Pez Celestial', 'Mítico', 6500, 230, 0.045),
('🛒', 'Pez Real', 'Mítico', 7500, 250, 0.035),
('🛒', 'Sardina Dorada', 'Raro', 355, 35, 1.4),
('🛒', 'Caballa Azul', 'Raro', 358, 35, 1.4),
('🛒', 'Atún Dorado', 'pico', 785, 62, 0.7),
('🛒', 'Salmón Real', 'pico', 790, 62, 0.7),
('🛒', 'Trucha Arcoíris', 'pico', 795, 63, 0.7),
('🛒', 'Pez Cristal', 'pico', 800, 63, 0.7),
('🛒', 'Pez Linterna', 'pico', 805, 63, 0.7),
('🛒', 'Pez Abisal', 'Legendario', 1836, 142, 0.25),
('🛒', 'Pez Fantasma', 'Legendario', 1844, 143, 0.25),
('🛒', 'Pez Espectral', 'Legendario', 1852, 144, 0.25),
('🛒', 'Tiburón Martillo', 'Legendario', 1860, 145, 0.25),
('🛒', 'Tiburón Blanco', 'Legendario', 1868, 146, 0.25),
('🛒', 'Tiburón Abisal', 'Legendario', 1876, 147, 0.25),
('🛒', 'Ballena Fantasma', 'Legendario', 1884, 148, 0.25),
('🛒', 'Dragón Marino', 'Legendario', 1892, 149, 0.25),
('🛒', 'Dragón Abisal', 'Legendario', 1900, 150, 0.25),
('🛒', 'Kraken Joven', 'Legendario', 1908, 151, 0.25),
('🛒', 'Kraken', 'Mítico', 4780, 284, 0.08),
('🛒', 'Dragón Marino Celestial', 'Mítico', 4795, 286, 0.08),
('🛒', 'Ser Cósmico', 'Mítico', 4810, 288, 0.08),
('🛒', 'Pez Nebulosa', 'Mítico', 4825, 290, 0.08),
('🛒', 'Pez Galaxia', 'Mítico', 4840, 292, 0.08),
('🛒', 'Pez Estelar', 'Mítico', 4855, 294, 0.08),
('🛒', 'Pez Lunar', 'Mítico', 4870, 296, 0.08),
('☀️', 'Pez Solar', 'Mítico', 4885, 298, 0.08),
('🛒', 'Pez Prisma', 'Mítico', 4900, 300, 0.08),
('🛒', 'Pez Diamante', 'Mítico', 4915, 302, 0.08),
('🛒', 'Pez Amatista', 'Mítico', 4930, 304, 0.08),
('🛒', 'Pez Arcano', 'Mítico', 4945, 306, 0.08),
('🛒', 'Pez Emperador', 'Mítico', 4960, 308, 0.08),
('🛒', 'Carpa', 'Común', 95, 14, 5.0),
('🛒', 'Barbo', 'Común', 96, 14, 5.0),
('🛒', 'Sargo', 'Común', 97, 14, 5.0),
('🛒', 'Dorada', 'Común', 98, 14, 5.0),
('🛒', 'Bacalao', 'Común', 99, 14, 5.0),
('🛒', 'Lenguado', 'Común', 100, 15, 5.0),
('🛒', 'Jurel', 'Común', 101, 15, 5.0),
('🛒', 'Sierra', 'Común', 102, 15, 5.0),
('🛒', 'Cangrejo Azul', 'Poco común', 236, 27, 3.0),
('🛒', 'Cangrejo Rey', 'Raro', 472, 42, 1.4),
('🛒', 'Camarón Tigre', 'Poco común', 240, 27, 3.0),
('🛒', 'Bogavante', 'Raro', 478, 43, 1.4),
('🛒', 'Ostra', 'Poco común', 244, 27, 3.0),
('🛒', 'Ostra Perla', 'Raro', 484, 43, 1.4),
('🛒', 'Concha Abisal', 'pico', 995, 76, 0.7),
('🛒', 'Medusa', 'Poco común', 250, 28, 3.0),
('🛒', 'Medusa Gigante', 'Raro', 493, 44, 1.4),
('🛒', 'Medusa Cristal', 'pico', 1010, 77, 0.7),
('🛒', 'Pez Mariposa', 'Poco común', 256, 28, 3.0),
('🛒', 'Pez Mandarín', 'Raro', 502, 44, 1.4),
('🛒', 'Pez Arcoíris', 'pico', 1025, 78, 0.7),
('🛒', 'Pez Globo Dorado', 'Raro', 508, 45, 1.4),
('🛒', 'Pez Globo Violeta', 'pico', 1035, 79, 0.7),
('🛒', 'Pulpo Violeta', 'pico', 1040, 79, 0.7),
('🛒', 'Pulpo Cristal', 'Legendario', 2212, 189, 0.25),
('🛒', 'Calamar Violeta', 'pico', 1050, 80, 0.7),
('🛒', 'Delfín Dorado', 'pico', 1055, 80, 0.7),
('🛒', 'Delfín Celestial', 'Legendario', 2236, 192, 0.25),
('🛒', 'Tortuga Dorada', 'pico', 1065, 81, 0.7),
('🛒', 'Tortuga Celestial', 'Legendario', 2252, 194, 0.25),
('🛒', 'Cocodrilo Marino', 'Legendario', 2260, 195, 0.25),
('🛒', 'Serpiente Marina', 'Legendario', 2268, 196, 0.25),
('🛒', 'Cangrejo Fantasma', 'Legendario', 2276, 197, 0.25),
('🛒', 'Camarón Cósmico', 'Mítico', 5470, 376, 0.08),
('🛒', 'Pez Vacío', 'Mítico', 5485, 378, 0.08),
('🛒', 'Pez Dimensional', 'Mítico', 5500, 380, 0.08)
]


@arbol.command(
    name="pescar",
    description="Pesca peces y gana monedas y XP"
)
async def pescar(interaction: discord.Interaction):

    if interaction.guild is None:
        await responder(
            interaction,
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    guild_id = interaction.guild.id
    user_id = interaction.user.id

    disponible, restante = comprobar_cooldown_actividad(
        guild_id,
        user_id,
        "pesca"
    )

    if not disponible:
        await responder(
            interaction,
            f" Ya pescaste recientemente. "
            f"Podrás volver a usar `/pescar` en **{formato_cooldown(restante)}**.",
            ephemeral=True
        )
        return

    registrar_uso_actividad(
        guild_id,
        user_id,
        "pesca"
    )

    try:
        nivel, xp, cana = await database.get_fishing_stats(
            guild_id,
            user_id
        )

        disponibles = PECES.copy()
        pesos = [pez[5] for pez in disponibles]

        # Una caa mejor aumenta las posibilidades de peces raros
        if cana > 1:
            for i in range(len(pesos)):
                if i >= 4:
                    pesos[i] *= 1 + ((cana - 1) * 0.15)

        pez = random.choices(
            disponibles,
            weights=pesos,
            k=1
        )[0]

        emoji, nombre, rareza, valor, xp_ganado, _ = pez

        nuevo_descubrimiento = await database.add_collection_item(
            guild_id,
            user_id,
            "pesca",
            nombre
        )

        await database.add_fish(
            guild_id,
            user_id,
            nombre,
            1
        )

        # Progreso de misiones
        await database.add_mission_progress(
            guild_id,
            user_id,
            "pescar_5",
            amount=1,
            required=5
        )

        if rareza == "Legendario":
            await database.add_mission_progress(
                guild_id,
                user_id,
                "pescar_legendario",
                amount=1,
                required=1
            )

        if rareza == "Mítico":
            await database.add_mission_progress(
                guild_id,
                user_id,
                "mitico",
                amount=1,
                required=1
            )

        await database.add_balance(
            user_id,
            guild_id,
            valor
        )

        nivel_anterior = nivel

        nuevo_nivel, nuevo_xp, _ = await database.add_fishing_xp(
            guild_id,
            user_id,
            xp_ganado
        )

        texto = (
            f" {interaction.user.mention} lanzó el anzuelo...\n\n"
            f" **🎣 ¡TIRÓN!**\n\n"
            f"{emoji} **{nombre}**\n"
            f"Rareza: **{rareza}**\n"
            f" Valor: **+{valor}** monedas\n"
            f"? XP pesca: **+{xp_ganado}**\n\n"
            f" Nivel de pesca: **{nuevo_nivel}**\n"
            f" XP: **{nuevo_xp}**"
        )

        if nuevo_nivel > nivel_anterior:
            texto += (
                f"\n\n **⬆️ ¡SUBISTE DE NIVEL!**\n"
                f" Pesca nivel **{nuevo_nivel}**"
            )

        if nombre == "Ballena":
            texto += "\n\n **🐋 HAS PESCADO UNA BALLENA!**"

        elif nombre == "Pez Violeta":
            texto += (
                "\n\n **✨ ¡EVENTO ULTRA RARO!**\n"
                "Las aguas brillaron con energía de Violet."
            )

        embed = discord.Embed(
            title=" Expedición de pesca",
            description=texto,
            color=discord.Color.blue()
        )

        embed.set_thumbnail(
            url=interaction.user.display_avatar.url
        )

        embed.set_footer(
            text=f"Violet  Caña nivel {cana}"
        )

        await responder(
            interaction,
            embed=embed
        )

    except Exception as error:
        print(f" Error en /pescar: {error}")

        await responder(
            interaction,
            " Ocurrió un error durante la pesca.",
            ephemeral=True
        )



# =========================================================
# PERFILES DE MINERÍA Y PESCA
# =========================================================

@arbol.command(
    name="mina",
    description="Muestra tus estadísticas y minerales"
)
async def mina(interaction: discord.Interaction):

    if interaction.guild is None:
        await responder(
            interaction,
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    guild_id = interaction.guild.id
    user_id = interaction.user.id

    try:
        nivel, xp, pico = await database.get_mining_stats(
            guild_id,
            user_id
        )

        inventario = await database.get_mining_inventory(
            guild_id,
            user_id
        )

        if inventario:
            minerales = "\n".join(
                f" {item}: **{cantidad}**"
                for item, cantidad in inventario
            )
        else:
            minerales = "Todavía no tienes minerales."

        embed = discord.Embed(
            title="⛏️ Mina de Violet",
            description=(
                f" **{interaction.user.display_name}**\n\n"
                f"? Nivel de minería: **{nivel}**\n"
                f"? XP: **{xp} / {nivel * 100}**\n"
                f"? Nivel del pico: **{pico}**\n\n"
                f" **Colección de minerales**\n"
                f"{minerales}"
            ),
            color=discord.Color.purple()
        )

        embed.set_thumbnail(
            url=interaction.user.display_avatar.url
        )

        embed.set_footer(text="Violet  Sistema de minería")

        await responder(interaction, embed=embed)

    except Exception as error:
        print(f" Error en /mina: {error}")
        await responder(
            interaction,
            " No pude cargar tus estadísticas de minería.",
            ephemeral=True
        )


@arbol.command(
    name="pesca",
    description="Muestra tus estadísticas y peces"
)
async def pesca(interaction: discord.Interaction):

    if interaction.guild is None:
        await responder(
            interaction,
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    guild_id = interaction.guild.id
    user_id = interaction.user.id

    try:
        nivel, xp, cana = await database.get_fishing_stats(
            guild_id,
            user_id
        )

        inventario = await database.get_fish_inventory(
            guild_id,
            user_id
        )

        if inventario:
            peces = "\n".join(
                f" {item}: **{cantidad}**"
                for item, cantidad in inventario
            )
        else:
            peces = "Todavía no tienes peces."

        embed = discord.Embed(
            title=" Pesca de Violet",
            description=(
                f" **{interaction.user.display_name}**\n\n"
                f" Nivel de pesca: **{nivel}**\n"
                f"? XP: **{xp} / {nivel * 100}**\n"
                f" Nivel de la caa: **{cana}**\n\n"
                f" **Acuario**\n"
                f"{peces}"
            ),
            color=discord.Color.blue()
        )

        embed.set_thumbnail(
            url=interaction.user.display_avatar.url
        )

        embed.set_footer(text="Violet  Sistema de pesca")

        await responder(interaction, embed=embed)

    except Exception as error:
        print(f" Error en /pesca: {error}")
        await responder(
            interaction,
            " No pude cargar tus estadísticas de pesca.",
            ephemeral=True
        )



# =========================================================
# MEJORAS DE MINERÍA Y PESCA
# =========================================================

COSTOS_PICO = {
    1: 0,
    2: 500,
    3: 1500,
    4: 4000,
    5: 10000,
    6: 25000,
    7: 60000,
    8: 150000,
    9: 350000,
    10: 750000
}

COSTOS_CANA = {
    1: 0,
    2: 500,
    3: 1500,
    4: 4000,
    5: 10000,
    6: 25000,
    7: 60000,
    8: 150000,
    9: 350000,
    10: 750000
}


@arbol.command(
    name="pico",
    description="Muestra tu pico y nivel de minería"
)
async def pico(interaction: discord.Interaction):

    if interaction.guild is None:
        await responder(
            interaction,
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    nivel, xp, pico_nivel = await database.get_mining_stats(
        interaction.guild.id,
        interaction.user.id
    )

    if pico_nivel >= 10:
        mejora = " Pico máximo"
    else:
        costo = COSTOS_PICO[pico_nivel + 1]
        mejora = f" Próxima mejora: **{costo:,}** monedas"

    embed = discord.Embed(
        title="⛏️ Pico de Violet",
        description=(
            f" {interaction.user.mention}\n\n"
            f"? **Nivel del pico:** {pico_nivel}/10\n"
            f" **Nivel de minería:** {nivel}\n"
            f"? **XP:** {xp}/{nivel * 100}\n\n"
            f"{mejora}"
        ),
        color=discord.Color.purple()
    )

    await responder(interaction, embed=embed)


@arbol.command(
    name="mejorar_pico",
    description="Mejora tu pico usando monedas"
)
async def mejorar_pico(interaction: discord.Interaction):

    if interaction.guild is None:
        await responder(
            interaction,
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    guild_id = interaction.guild.id
    user_id = interaction.user.id

    nivel, xp, pico_nivel = await database.get_mining_stats(
        guild_id,
        user_id
    )

    if pico_nivel >= 10:
        await responder(
            interaction,
            " Tu pico ya está en el nivel máximo.",
            ephemeral=True
        )
        return

    costo = COSTOS_PICO[pico_nivel + 1]
    datos = await database.get_user(user_id, guild_id)
    monedas = datos[2]

    if monedas < costo:
        await responder(
            interaction,
            f" Necesitas **{costo:,}** monedas.\n"
            f" Tienes: **{monedas:,}**",
            ephemeral=True
        )
        return

    await database.remove_balance(
        user_id,
        guild_id,
        costo
    )

    nuevo_nivel = pico_nivel + 1

    await database.set_mining_tool_level(
        guild_id,
        user_id,
        nuevo_nivel
    )

    embed = discord.Embed(
        title="⛏️ ¡Pico mejorado!",
        description=(
            f" {interaction.user.mention}\n\n"
            f"? Pico: **Nivel {pico_nivel}  {nuevo_nivel}**\n"
            f" Coste: **{costo:,}** monedas\n\n"
            f" Ahora tienes mejores posibilidades de encontrar "
            f"minerales raros."
        ),
        color=discord.Color.purple()
    )

    await responder(interaction, embed=embed)


@arbol.command(
    name="caa",
    description="Muestra tu caa y nivel de pesca"
)
async def cana(interaction: discord.Interaction):

    if interaction.guild is None:
        await responder(
            interaction,
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    nivel, xp, cana_nivel = await database.get_fishing_stats(
        interaction.guild.id,
        interaction.user.id
    )

    if cana_nivel >= 10:
        mejora = " Caña máxima"
    else:
        costo = COSTOS_CANA[cana_nivel + 1]
        mejora = f" Próxima mejora: **{costo:,}** monedas"

    embed = discord.Embed(
        title=" Caña de Violet",
        description=(
            f" {interaction.user.mention}\n\n"
            f" **Nivel de la caa:** {cana_nivel}/10\n"
            f" **Nivel de pesca:** {nivel}\n"
            f"? **XP:** {xp}/{nivel * 100}\n\n"
            f"{mejora}"
        ),
        color=discord.Color.blue()
    )

    await responder(interaction, embed=embed)


@arbol.command(
    name="mejorar_caa",
    description="Mejora tu caa usando monedas"
)
async def mejorar_cana(interaction: discord.Interaction):

    if interaction.guild is None:
        await responder(
            interaction,
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    guild_id = interaction.guild.id
    user_id = interaction.user.id

    nivel, xp, cana_nivel = await database.get_fishing_stats(
        guild_id,
        user_id
    )

    if cana_nivel >= 10:
        await responder(
            interaction,
            " Tu caa ya está en el nivel máximo.",
            ephemeral=True
        )
        return

    costo = COSTOS_CANA[cana_nivel + 1]
    datos = await database.get_user(user_id, guild_id)
    monedas = datos[2]

    if monedas < costo:
        await responder(
            interaction,
            f" Necesitas **{costo:,}** monedas.\n"
            f" Tienes: **{monedas:,}**",
            ephemeral=True
        )
        return

    await database.remove_balance(
        user_id,
        guild_id,
        costo
    )

    nuevo_nivel = cana_nivel + 1

    await database.set_fishing_rod_level(
        guild_id,
        user_id,
        nuevo_nivel
    )

    embed = discord.Embed(
        title="🎣 ¡Caña mejorada!",
        description=(
            f" {interaction.user.mention}\n\n"
            f" Caña: **Nivel {cana_nivel}  {nuevo_nivel}**\n"
            f" Coste: **{costo:,}** monedas\n\n"
            f" Ahora tienes mejores posibilidades de encontrar "
            f"peces raros."
        ),
        color=discord.Color.blue()
    )

    await responder(interaction, embed=embed)



# =========================================================
# VENTA DE MINERALES Y PECES
# =========================================================

@arbol.command(
    name="minerales",
    description="Muestra tus minerales recolectados"
)
async def minerales(interaction: discord.Interaction):

    if interaction.guild is None:
        await responder(
            interaction,
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    inventario = await database.get_mining_inventory(
        interaction.guild.id,
        interaction.user.id
    )

    if not inventario:
        await responder(
            interaction,
            "❌ No tienes minerales para mostrar.",
            ephemeral=True
        )
        return

    lineas = [
        f" {item}: **{cantidad}**"
        for item, cantidad in inventario
    ]

    embed = discord.Embed(
        title=" Tus minerales",
        description="\n".join(lineas),
        color=discord.Color.purple()
    )

    await responder(interaction, embed=embed)


@arbol.command(
    name="peces",
    description="Muestra tus peces capturados"
)
async def peces(interaction: discord.Interaction):

    if interaction.guild is None:
        await responder(
            interaction,
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    inventario = await database.get_fish_inventory(
        interaction.guild.id,
        interaction.user.id
    )

    if not inventario:
        await responder(
            interaction,
            " No tienes peces para mostrar.",
            ephemeral=True
        )
        return

    lineas = [
        f" {item}: **{cantidad}**"
        for item, cantidad in inventario
    ]

    embed = discord.Embed(
        title=" Tu acuario",
        description="\n".join(lineas),
        color=discord.Color.blue()
    )

    await responder(interaction, embed=embed)


@arbol.command(
    name="vender_minerales",
    description="Vende todos tus minerales"
)
async def vender_minerales(interaction: discord.Interaction):

    if interaction.guild is None:
        await responder(
            interaction,
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    guild_id = interaction.guild.id
    user_id = interaction.user.id

    precios = {
        "Piedra": 10,
        "Carbón": 20,
        "Arcilla": 25,
        "Hierro": 40,
        "Cobre": 60,
        "Obsidiana": 90,
        "Plata": 120,
        "Esmeralda": 180,
        "Rubí": 220,
        "Oro": 250,
        "Zafiro": 350,
        "Ámbar": 400,
        "Diamante": 500,
        "Fragmento Abisal": 750,
        "Cristal Violeta": 850,
        "Núcleo Cósmico": 1500
    }

    inventario = await database.get_mining_inventory(
        guild_id,
        user_id
    )

    if not inventario:
        await responder(
            interaction,
            "❌ No tienes minerales para vender.",
            ephemeral=True
        )
        return

    total = 0
    vendidos = []

    for item, cantidad in inventario:
        precio = precios.get(item, 0)

        if precio <= 0:
            continue

        ganancia = precio * cantidad
        total += ganancia

        if await database.remove_mining_item(
            guild_id,
            user_id,
            item,
            cantidad
        ):
            vendidos.append(
                f" {item} {cantidad}   {ganancia:,}"
            )

    if total <= 0:
        await responder(
            interaction,
            " No se pudieron vender tus minerales.",
            ephemeral=True
        )
        return

    await database.add_balance(
        user_id,
        guild_id,
        total
    )

    embed = discord.Embed(
        title=" Venta de minerales",
        description=(
            "\n".join(vendidos)
            + f"\n\n **Ganancia total: {total:,} monedas**"
        ),
        color=discord.Color.gold()
    )

    await responder(interaction, embed=embed)


@arbol.command(
    name="vender_peces",
    description="Vende todos tus peces"
)
async def vender_peces(interaction: discord.Interaction):

    if interaction.guild is None:
        await responder(
            interaction,
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    guild_id = interaction.guild.id
    user_id = interaction.user.id

    precios = {
        "Sardina": 15,
        "Pez tropical": 30,
        "Camarón": 35,
        "Cangrejo": 40,
        "Pez globo": 50,
        "Calamar": 80,
        "Almeja": 90,
        "Langosta": 130,
        "Pulpo": 150,
        "Delfín": 220,
        "Tortuga marina": 250,
        "Tiburón": 300,
        "Pez Dragón": 500,
        "Ballena": 600,
        "Pez Violeta": 1000,
        "Leviatán": 2000
    }

    inventario = await database.get_fish_inventory(
        guild_id,
        user_id
    )

    if not inventario:
        await responder(
            interaction,
            " No tienes peces para vender.",
            ephemeral=True
        )
        return

    total = 0
    vendidos = []

    for item, cantidad in inventario:
        precio = precios.get(item, 0)

        if precio <= 0:
            continue

        ganancia = precio * cantidad
        total += ganancia

        if await database.remove_fish(
            guild_id,
            user_id,
            item,
            cantidad
        ):
            vendidos.append(
                f" {item} {cantidad}   {ganancia:,}"
            )

    if total <= 0:
        await responder(
            interaction,
            " No se pudieron vender tus peces.",
            ephemeral=True
        )
        return

    await database.add_balance(
        user_id,
        guild_id,
        total
    )

    embed = discord.Embed(
        title=" Venta de peces",
        description=(
            "\n".join(vendidos)
            + f"\n\n **Ganancia total: {total:,} monedas**"
        ),
        color=discord.Color.blue()
    )

    await responder(interaction, embed=embed)



# =========================================================
# COOLDOWNS - MINERÍA Y PESCA
# =========================================================

import time

COOLDOWN_MINERIA_PESCA = 15 * 60

cooldowns_mineria_pesca = {}


def comprobar_cooldown_actividad(guild_id, user_id, actividad):
    clave = (guild_id, user_id, actividad)
    ahora = time.time()

    ultimo_uso = cooldowns_mineria_pesca.get(clave)

    if ultimo_uso is None:
        return True, 0

    restante = COOLDOWN_MINERIA_PESCA - (ahora - ultimo_uso)

    if restante > 0:
        return False, int(restante)

    return True, 0


def registrar_uso_actividad(guild_id, user_id, actividad):
    clave = (guild_id, user_id, actividad)
    cooldowns_mineria_pesca[clave] = time.time()


def formato_cooldown(segundos):
    minutos = segundos // 60
    segundos_restantes = segundos % 60

    return f"{minutos}m {segundos_restantes}s"


# =========================================================
# EVENTOS RAROS Y COFRES
# =========================================================

@arbol.command(
    name="cofre_mineria",
    description="Busca un cofre oculto en la mina"
)
async def cofre_mineria(interaction: discord.Interaction):

    if interaction.guild is None:
        await responder(
            interaction,
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    guild_id = interaction.guild.id
    user_id = interaction.user.id

    try:
        nivel, xp, pico = await database.get_mining_stats(
            guild_id,
            user_id
        )

        suerte = random.random()

        if suerte < 0.02:
            recompensa = 5000
            rareza = " LEGENDARIO"
            mensaje = " 🎁 ¡El cofre contiene un Núcleo Legendario!"

        elif suerte < 0.08:
            recompensa = 1500
            rareza = " PICO"
            mensaje = " 💎 ¡Encontraste un cofre de diamantes!"

        elif suerte < 0.25:
            recompensa = 500
            rareza = " RARO"
            mensaje = " 🪙 ¡Encontraste un cofre lleno de monedas!"

        else:
            recompensa = 100
            rareza = " COMN"
            mensaje = " Encontraste algunas monedas."

        await database.add_balance(
            user_id,
            guild_id,
            recompensa
        )

        embed = discord.Embed(
            title=" Cofre encontrado",
            description=(
                f"? {interaction.user.mention} exploró las profundidades...\n\n"
                f"{mensaje}\n\n"
                f"Rareza: **{rareza}**\n"
                f" Recompensa: **+{recompensa:,} monedas**\n"
                f"? Pico nivel: **{pico}**"
            ),
            color=discord.Color.purple()
        )

        await responder(interaction, embed=embed)

    except Exception as error:
        print(f" Error en /cofre_mineria: {error}")
        await responder(
            interaction,
            " No pude abrir el cofre.",
            ephemeral=True
        )


@arbol.command(
    name="pesca_rara",
    description="Intenta encontrar una criatura marina especial"
)
async def pesca_rara(interaction: discord.Interaction):

    if interaction.guild is None:
        await responder(
            interaction,
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    guild_id = interaction.guild.id
    user_id = interaction.user.id

    try:
        nivel, xp, cana = await database.get_fishing_stats(
            guild_id,
            user_id
        )

        suerte = random.random()

        if suerte < 0.01:
            nombre = " Dragón Marino Violeta"
            rareza = " LEGENDARIA"
            recompensa = 5000
            xp_ganado = 100

        elif suerte < 0.05:
            nombre = " Criatura Nebulosa"
            rareza = " MÍTICA"
            recompensa = 2000
            xp_ganado = 70

        elif suerte < 0.15:
            nombre = " Sirena Perdida"
            rareza = " PICA"
            recompensa = 800
            xp_ganado = 45

        else:
            nombre = " Concha Misteriosa"
            rareza = "? RARA"
            recompensa = 150
            xp_ganado = 15

        await database.add_balance(
            user_id,
            guild_id,
            recompensa
        )

        nivel_anterior = nivel

        nuevo_nivel, nuevo_xp, _ = await database.add_fishing_xp(
            guild_id,
            user_id,
            xp_ganado
        )

        texto = (
            f" El agua comenzó a brillar...\n\n"
            f" **✨ ¡HAS ENCONTRADO ALGO ESPECIAL!**\n\n"
            f"{nombre}\n"
            f"Rareza: **{rareza}**\n"
            f" Valor: **+{recompensa:,}** monedas\n"
            f"? XP: **+{xp_ganado}**"
        )

        if nuevo_nivel > nivel_anterior:
            texto += (
                f"\n\n **⬆️ ¡SUBISTE DE NIVEL!**\n"
                f" Pesca nivel **{nuevo_nivel}**"
            )

        embed = discord.Embed(
            title=" Evento de pesca",
            description=texto,
            color=discord.Color.blue()
        )

        await responder(interaction, embed=embed)

    except Exception as error:
        print(f" Error en /pesca_rara: {error}")
        await responder(
            interaction,
            " Algo salió mal durante el evento.",
            ephemeral=True
        )



# =========================================================
# COLECCIN DE MINERÍA Y PESCA
# =========================================================

@arbol.command(
    name="coleccion",
    description="Muestra tu colección de minería y pesca"
)
async def coleccion(interaction: discord.Interaction):

    if interaction.guild is None:
        await responder(
            interaction,
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    guild_id = interaction.guild.id
    user_id = interaction.user.id

    try:
        minerales = await database.get_collection(
            guild_id,
            user_id,
            "mineria"
        )

        peces = await database.get_collection(
            guild_id,
            user_id,
            "pesca"
        )

        total_minerales = len(MINERALES)
        total_peces = len(PECES)

        encontrados_minerales = len(minerales)
        encontrados_peces = len(peces)

        porcentaje_mineria = (
            int((encontrados_minerales / total_minerales) * 100)
            if total_minerales else 0
        )

        porcentaje_pesca = (
            int((encontrados_peces / total_peces) * 100)
            if total_peces else 0
        )

        nombres_minerales = {item[1] for item in MINERALES}
        nombres_peces = {item[1] for item in PECES}

        descubiertos_minerales = {
            fila[0] for fila in minerales
        }

        descubiertos_peces = {
            fila[0] for fila in peces
        }

        lineas_mineria = []

        for mineral in MINERALES:
            emoji, nombre, rareza, valor, xp, peso = mineral

            if nombre in descubiertos_minerales:
                estado = ""
            else:
                estado = ""

            lineas_mineria.append(
                f"{estado} {emoji} **{nombre}**  {rareza}"
            )

        lineas_pesca = []

        for pez in PECES:
            emoji, nombre, rareza, valor, xp, peso = pez

            if nombre in descubiertos_peces:
                estado = ""
            else:
                estado = ""

            lineas_pesca.append(
                f"{estado} {emoji} **{nombre}**  {rareza}"
            )

        def barra(porcentaje):
            llenas = porcentaje // 10
            vacias = 10 - llenas
            return "" * llenas + "" * vacias

        embed = discord.Embed(
            title=" Colección de Violet",
            description=(
                f" **{interaction.user.display_name}**\n\n"
                "? **MINERÍA**\n"
                f"{barra(porcentaje_mineria)} "
                f"**{porcentaje_mineria}%**\n"
                f" **{encontrados_minerales}/{total_minerales}** descubiertos\n\n"
                + "\n".join(lineas_mineria)
                + "\n\n"
                " **PESCA**\n"
                f"{barra(porcentaje_pesca)} "
                f"**{porcentaje_pesca}%**\n"
                f" **{encontrados_peces}/{total_peces}** descubiertos\n\n"
                + "\n".join(lineas_pesca)
            ),
            color=discord.Color.purple()
        )

        embed.set_thumbnail(
            url=interaction.user.display_avatar.url
        )

        embed.set_footer(
            text="Violet  Sistema de colecciones"
        )

        await responder(
            interaction,
            embed=embed
        )

    except Exception as error:
        print(f" Error en /coleccion: {error}")

        await responder(
            interaction,
            " No pude cargar tu colección.",
            ephemeral=True
        )


# =========================================================
# MISIONES DE MINERÍA Y PESCA
# =========================================================

MISIONES_ACTIVIDADES = {
    "minar_5": {
        "nombre": "? Minero Novato",
        "descripcion": "Extrae 5 minerales.",
        "categoria": "mineria",
        "objetivo": 5,
        "recompensa": 250,
        "xp": 25
    },
    "minar_raro": {
        "nombre": " Cazador de Tesoros",
        "descripcion": "Encuentra un mineral raro o superior.",
        "categoria": "mineria",
        "objetivo": 1,
        "recompensa": 500,
        "xp": 50
    },
    "pescar_5": {
        "nombre": " Pescador Novato",
        "descripcion": "Pesca 5 peces.",
        "categoria": "pesca",
        "objetivo": 5,
        "recompensa": 250,
        "xp": 25
    },
    "pescar_legendario": {
        "nombre": " Gran Pescador",
        "descripcion": "Encuentra un pez legendario.",
        "categoria": "pesca",
        "objetivo": 1,
        "recompensa": 1000,
        "xp": 100
    },
    "mitico": {
        "nombre": " Coleccionista Violeta",
        "descripcion": "Descubre un objeto mítico.",
        "categoria": "especial",
        "objetivo": 1,
        "recompensa": 2500,
        "xp": 250
    }
}


@bot.tree.command(
    name="misiones",
    description="Consulta tus misiones de minería y pesca"
)
async def misiones(interaction: discord.Interaction):

    if interaction.guild is None:
        await responder(
            interaction,
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    guild_id = interaction.guild.id
    user_id = interaction.user.id

    try:
        datos = await database.get_missions(
            guild_id,
            user_id
        )

        progreso = {
            mission_id: (progress, completed)
            for mission_id, progress, completed in datos
        }

        embed = discord.Embed(
            title=" Misiones de Violet",
            description="Completa actividades para obtener monedas y XP.",
            color=discord.Color.purple()
        )

        for mission_id, mision in MISIONES_ACTIVIDADES.items():

            actual, completada = progreso.get(
                mission_id,
                (0, 0)
            )

            if completada:
                estado = " RECOMPENSA DISPONIBLE"
            else:
                estado = f" {actual}/{mision['objetivo']}"

            embed.add_field(
                name=mision["nombre"],
                value=(
                    f"{mision['descripcion']}\n"
                    f"{estado}\n"
                    f" {mision['recompensa']} monedas "
                    f" ? {mision['xp']} XP"
                ),
                inline=False
            )

        embed.set_footer(
            text="Violet  Misiones de Minería y Pesca"
        )

        await responder(
            interaction,
            embed=embed
        )

    except Exception as error:
        print(f" Error en /misiones: {error}")

        await responder(
            interaction,
            " No pude cargar tus misiones.",
            ephemeral=True
        )



# =========================================================
# RECLAMAR MISIONES
# =========================================================

@bot.tree.command(
    name="reclamar_mision",
    description="Reclama la recompensa de una misión completada"
)
@app_commands.describe(
    mision="ID de la misión que quieres reclamar"
)
async def reclamar_mision(
    interaction: discord.Interaction,
    mision: str
):

    if interaction.guild is None:
        await responder(
            interaction,
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    guild_id = interaction.guild.id
    user_id = interaction.user.id

    if mision not in MISIONES_ACTIVIDADES:
        await responder(
            interaction,
            " Esa misión no existe.\n"
            "Usa `/misiones` para consultar las misiones disponibles.",
            ephemeral=True
        )
        return

    datos = MISIONES_ACTIVIDADES[mision]

    try:
        resultado, estado = await database.claim_mission(
            guild_id,
            user_id,
            mision
        )

        if not resultado:
            if estado == "not_found":
                mensaje = (
                    " Todavía no tienes progreso registrado "
                    "en esa misión."
                )

            elif estado == "not_completed":
                mensaje = (
                    f" Aún no has completado **{datos['nombre']}**.\n"
                    f"Objetivo: **{datos['objetivo']}**."
                )

            elif estado == "already_claimed":
                mensaje = (
                    f"? Ya reclamaste la recompensa de "
                    f"**{datos['nombre']}**."
                )

            else:
                mensaje = " No se pudo reclamar la misión."

            await responder(
                interaction,
                mensaje,
                ephemeral=True
            )
            return

        await database.add_balance(
            user_id,
            guild_id,
            datos["recompensa"]
        )

        await database.add_xp(
            user_id,
            guild_id,
            datos["xp"]
        )

        embed = discord.Embed(
            title=" Misión completada",
            description=(
                f"Has reclamado la recompensa de "
                f"**{datos['nombre']}**."
            ),
            color=discord.Color.purple()
        )

        embed.add_field(
            name=" Recompensa",
            value=f"+{datos['recompensa']} monedas",
            inline=True
        )

        embed.add_field(
            name="✨ XP",
            value=f"+{datos['xp']} XP",
            inline=True
        )

        embed.set_footer(
            text="Violet  Misiones"
        )

        await responder(
            interaction,
            embed=embed
        )

    except Exception as error:
        print(f" Error en /reclamar_mision: {error}")

        await responder(
            interaction,
            " No pude reclamar la misión.",
            ephemeral=True
        )



# =========================================================
# VIOLET AUTÓNOMA - MINERÍA Y PESCA
# =========================================================

VIOLET_CANAL_NOMBRE = "?violet-mineria-pesca"
VIOLET_INTERVALO = 20


async def violet_crear_canal(guild):

    existente = discord.utils.get(
        guild.text_channels,
        name=VIOLET_CANAL_NOMBRE
    )

    if existente:
        return existente

    try:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=False
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                embed_links=True,
                attach_files=True,
                read_message_history=True
            )
        }

        canal = await guild.create_text_channel(
            VIOLET_CANAL_NOMBRE,
            overwrites=overwrites,
            reason="Canal de actividades automáticas de Violet"
        )

        return canal

    except Exception as error:
        print(
            f" No pude crear el canal autónomo en "
            f"{guild.name}: {error}"
        )
        return None


async def violet_obtener_mejoras_actividad(guild_id, user_id):

    inventario = await database.get_inventory(
        user_id,
        guild_id
    )

    mejoras = {}

    nombres_canonicos = {
        "pico de hierro": "Pico de Hierro",
        "pico de oro": "Pico de Oro",
        "pico de diamante": "Pico de Diamante",
        "caa reforzada": "Caña Reforzada",
        "caa de oro": "Caña de Oro",
        "caa de diamante": "Caña de Diamante",
        "detector de minerales": "Detector de Minerales",
        "taladro minero": "Taladro Minero",
        "núcleo violeta": "Núcleo Violeta",
        "radar de peces": "Radar de Peces",
        "seuelo abisal": "Seuelo Abisal",
        "seuelo violeta": "Seuelo Violeta",
        "suerte minera": "Suerte Minera",
        "suerte pesquera": "Suerte Pesquera",
        "minería rápida": "Minería Rápida",
        "pesca rápida": "Pesca Rápida",
        "fortuna legendaria": "Fortuna Legendaria",
        "bendición de violet": "Bendición de Violet"
    }

    for item, cantidad in inventario:

        if cantidad <= 0:
            continue

        nombre = str(item).strip().lower()
        nombre = nombres_canonicos.get(nombre, item)

        mejoras[nombre] = cantidad

    return mejoras


def violet_aplicar_mejoras_pesos(pesos, mejoras, tipo):

    pesos = list(pesos)

    if tipo == "mineria":

        if mejoras.get("Pico de Diamante", 0) > 0:
            multiplicador = 1.35
        elif mejoras.get("Pico de Oro", 0) > 0:
            multiplicador = 1.20
        elif mejoras.get("Pico de Hierro", 0) > 0:
            multiplicador = 1.10
        else:
            multiplicador = 1.0

        for i in range(len(pesos)):
            if i >= 4:
                pesos[i] *= multiplicador

        if mejoras.get("Detector de Minerales", 0) > 0:
            for i in range(len(pesos)):
                if i >= 4:
                    pesos[i] *= 1.20

        if mejoras.get("Taladro Minero", 0) > 0:
            for i in range(len(pesos)):
                if i >= 5:
                    pesos[i] *= 1.25

        if mejoras.get("Núcleo Violeta", 0) > 0:
            for i in range(len(pesos)):
                if i >= 6:
                    pesos[i] *= 1.40

        if mejoras.get("Suerte Minera", 0) > 0:
            for i in range(len(pesos)):
                if i >= 4:
                    pesos[i] *= 1.15

        if mejoras.get("Fortuna Legendaria", 0) > 0:
            for i in range(len(pesos)):
                if i >= 5:
                    pesos[i] *= 1.30

        if mejoras.get("Bendición de Violet", 0) > 0:
            for i in range(len(pesos)):
                if i >= 6:
                    pesos[i] *= 1.50

    else:

        if mejoras.get("Caña de Diamante", 0) > 0:
            multiplicador = 1.35
        elif mejoras.get("Caña de Oro", 0) > 0:
            multiplicador = 1.20
        elif mejoras.get("Caña Reforzada", 0) > 0:
            multiplicador = 1.10
        else:
            multiplicador = 1.0

        for i in range(len(pesos)):
            if i >= 4:
                pesos[i] *= multiplicador

        if mejoras.get("Radar de Peces", 0) > 0:
            for i in range(len(pesos)):
                if i >= 4:
                    pesos[i] *= 1.20

        if mejoras.get("Seuelo Abisal", 0) > 0:
            for i in range(len(pesos)):
                if i >= 5:
                    pesos[i] *= 1.25

        if mejoras.get("Seuelo Violeta", 0) > 0:
            for i in range(len(pesos)):
                if i >= 6:
                    pesos[i] *= 1.40

        if mejoras.get("Suerte Pesquera", 0) > 0:
            for i in range(len(pesos)):
                if i >= 4:
                    pesos[i] *= 1.15

        if mejoras.get("Fortuna Legendaria", 0) > 0:
            for i in range(len(pesos)):
                if i >= 5:
                    pesos[i] *= 1.30

        if mejoras.get("Bendición de Violet", 0) > 0:
            for i in range(len(pesos)):
                if i >= 6:
                    pesos[i] *= 1.50

    return pesos


async def violet_actividad_automatica(guild):

    if bot.user is None:
        return None

    canal = discord.utils.get(
        guild.text_channels,
        name=VIOLET_CANAL_NOMBRE
    )

    if canal is None:
        return None

    try:

        actividad = random.choice([
            "mineria",
            "pesca"
        ])

        if actividad == "mineria":

            nivel, xp, pico = await database.get_mining_stats(
                guild.id,
                bot.user.id
            )

            pesos = [mineral[5] for mineral in MINERALES]

            if pico > 1:
                for i in range(len(pesos)):
                    if i >= 4:
                        pesos[i] *= 1 + ((pico - 1) * 0.15)

            mejoras = await violet_obtener_mejoras_actividad(
                guild.id,
                bot.user.id
            )

            pesos = violet_aplicar_mejoras_pesos(
                pesos,
                mejoras,
                "mineria"
            )

            mineral = random.choices(
                MINERALES,
                weights=pesos,
                k=1
            )[0]

            emoji, nombre, rareza, valor, xp_ganado, _ = mineral

            await database.add_mining_item(
                guild.id,
                bot.user.id,
                nombre,
                1
            )

            await database.add_mining_xp(
                guild.id,
                bot.user.id,
                xp_ganado
            )

            await database.add_collection_item(
                guild.id,
                bot.user.id,
                "mineria",
                nombre
            )

            embed = discord.Embed(
                title="? Violet está minando",
                description=(
                    f"Violet encontró {emoji} **{nombre}**.\n\n"
                    f" Rareza: **{rareza}**\n"
                    f" Valor: **{valor} monedas**\n"
                    f"? XP obtenida: **{xp_ganado}**"
                ),
                color=discord.Color.purple()
            )

        else:

            nivel, xp, caa = await database.get_fishing_stats(
                guild.id,
                bot.user.id
            )

            pesos = [pez[5] for pez in PECES]

            if caa > 1:
                for i in range(len(pesos)):
                    if i >= 4:
                        pesos[i] *= 1 + ((caa - 1) * 0.15)

            mejoras = await violet_obtener_mejoras_actividad(
                guild.id,
                bot.user.id
            )

            pesos = violet_aplicar_mejoras_pesos(
                pesos,
                mejoras,
                "pesca"
            )

            pez = random.choices(
                PECES,
                weights=pesos,
                k=1
            )[0]

            emoji, nombre, rareza, valor, xp_ganado, _ = pez

            await database.add_fish(
                guild.id,
                bot.user.id,
                nombre,
                1
            )

            await database.add_fishing_xp(
                guild.id,
                bot.user.id,
                xp_ganado
            )

            await database.add_collection_item(
                guild.id,
                bot.user.id,
                "pesca",
                nombre
            )

            embed = discord.Embed(
                title=" Violet está pescando",
                description=(
                    f"Violet atrapó {emoji} **{nombre}**.\n\n"
                    f" Rareza: **{rareza}**\n"
                    f" Valor: **{valor} monedas**\n"
                    f"? XP obtenida: **{xp_ganado}**"
                ),
                color=discord.Color.purple()
            )

        embed.set_footer(
            text="Violet  Actividad autónoma"
        )

        await canal.send(embed=embed)

    except Exception as error:
        print(
            f" Error en actividad autónoma de Violet "
            f"({guild.name}): {error}"
        )



# =========================================================

# =========================================================
# VIOLET PESCA AUTOMATICA V2
# Interacción automática con usuarios activos
# =========================================================

VIOLET_PESCA_AUTOMATICA_V2 = True
VIOLET_PESCA_CANAL_NOMBRE = "violet-pesca"
VIOLET_PESCA_ACTIVIDAD_SEGUNDOS = 30 * 60
VIOLET_PESCA_INTERVALO = 5 * 60

# guild_id -> {user_id: ultimo_timestamp}
violet_pesca_usuarios_activos = {}

# Evita iniciar dos loops
violet_pesca_task_v2 = None


async def violet_obtener_canal_pesca(guild):
    """
    Busca el canal de pesca automática.
    Si no existe, Violet lo crea automáticamente.
    """

    try:
        canal = discord.utils.get(
            guild.text_channels,
            name=VIOLET_PESCA_CANAL_NOMBRE
        )

        if canal:
            return canal

        canal = await guild.create_text_channel(
            VIOLET_PESCA_CANAL_NOMBRE,
            reason="Violet - creación automática del canal de pesca"
        )

        print(
            f" Canal de pesca creado automáticamente en "
            f"{guild.name}: #{canal.name}"
        )

        try:
            embed = discord.Embed(
                title=" Bienvenido al canal de pesca de Violet",
                description=(
                    "Aquí Violet organizará expediciones de pesca automáticas.\n\n"
                    " **❓ ¿Cómo participa la comunidad?**\n"
                    " Escribe en este canal para que Violet sepa que estás activo.\n"
                    " Violet podrá llamarte durante una expedición.\n"
                    " Pulsa los botones de los eventos para intentar conseguir peces.\n"
                    " Los peces obtenidos se guardan en tu inventario.\n"
                    " También puedes recibir **VLC** y XP.\n\n"
                    "? Discord no permite saber literalmente quién está "
                    "mirando un canal, por lo que Violet utiliza la actividad "
                    "reciente como indicador de presencia."
                ),
                color=discord.Color.purple()
            )

            embed.set_footer(text="Violet  Pesca automática")

            await canal.send(embed=embed)

        except Exception as error:
            print(f"? No pude publicar bienvenida de pesca: {error}")

        return canal

    except discord.Forbidden:
        print(
            f" Violet no tiene permisos para crear el canal de pesca "
            f"en {guild.name}"
        )
        return None

    except Exception as error:
        print(f" Error creando canal de pesca: {error}")
        return None


def violet_pesca_marcar_usuario(guild_id, user_id):
    ahora = time.time()

    usuarios = violet_pesca_usuarios_activos.setdefault(
        guild_id,
        {}
    )

    usuarios[user_id] = ahora


def violet_pesca_obtener_usuarios_activos(guild):
    ahora = time.time()

    usuarios = violet_pesca_usuarios_activos.get(
        guild.id,
        {}
    )

    activos = []

    for user_id, ultimo in list(usuarios.items()):

        if ahora - ultimo > VIOLET_PESCA_ACTIVIDAD_SEGUNDOS:
            del usuarios[user_id]
            continue

        miembro = guild.get_member(user_id)

        if miembro is None:
            continue

        if miembro.bot:
            continue

        activos.append(miembro)

    return activos


async def violet_pesca_recompensar(interaction, pez):
    """
    Entrega el pez y recompensa al usuario.
    """

    try:
        emoji, nombre, rareza, valor, xp_ganado, peso = pez

        guild_id = interaction.guild.id
        user_id = interaction.user.id

        # Guardar en colección
        try:
            await database.add_collection_item(
                user_id,
                guild_id,
                "pesca",
                nombre
            )
        except Exception as error:
            print(f"? Error colección pesca automática: {error}")

        # Guardar pez
        try:
            await database.add_fish(
                user_id,
                guild_id,
                nombre,
                1
            )
        except Exception as error:
            print(f"? Error inventario pesca automática: {error}")

        # Recompensa VLC
        recompensa = max(1, int(valor))

        try:
            await database.add_balance(
                user_id,
                guild_id,
                recompensa
            )
        except Exception as error:
            print(f"? Error recompensa VLC pesca automática: {error}")

        # XP de pesca si existe la función
        try:
            funcion_xp = getattr(
                database,
                "add_fishing_xp",
                None
            )

            if funcion_xp:
                await funcion_xp(
                    user_id,
                    guild_id,
                    xp_ganado
                )
        except Exception as error:
            print(f"? No se pudo añadir XP de pesca automática: {error}")

        return emoji, nombre, rareza, recompensa, xp_ganado

    except Exception as error:
        print(f" Error en recompensa de pesca automática: {error}")
        return None


class VioletPescaAutomaticaView(discord.ui.View):

    def __init__(self, target_id, pez, timeout=90):
        super().__init__(timeout=timeout)

        self.target_id = target_id
        self.pez = pez
        self.participado = False

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

    @discord.ui.button(
        label=" Pescar",
        style=discord.ButtonStyle.primary,
        custom_id="violet_pesca_automatica_pescar"
    )
    async def pescar_boton(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.user.id != self.target_id:
            await interaction.response.send_message(
                " Violet está interactuando con otra persona en esta expedición.",
                ephemeral=True
            )
            return

        if self.participado:
            await interaction.response.send_message(
                " Ya participaste en esta expedición.",
                ephemeral=True
            )
            return

        self.participado = True

        violet_pesca_marcar_usuario(
            interaction.guild.id,
            interaction.user.id
        )

        resultado = await violet_pesca_recompensar(
            interaction,
            self.pez
        )

        if resultado is None:
            await interaction.response.send_message(
                " No pude registrar tu captura.",
                ephemeral=True
            )
            return

        emoji, nombre, rareza, recompensa, xp_ganado = resultado

        for item in self.children:
            item.disabled = True

        embed = discord.Embed(
            title=" 🎣 ¡Captura realizada!",
            description=(
                f"{interaction.user.mention} consiguió:\n\n"
                f"{emoji} **{nombre}**\n"
                f" Rareza: **{rareza}**\n"
                f" Recompensa: **+{recompensa:,} VLC**\n"
                f"? XP: **+{xp_ganado}**"
            ),
            color=discord.Color.purple()
        )

        embed.set_footer(text="Violet  Pesca automática")

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )


async def violet_pesca_evento_automatico(guild):
    try:

        canal = await violet_obtener_canal_pesca(guild)

        if canal is None:
            return

        activos = violet_pesca_obtener_usuarios_activos(guild)

        if not activos:
            return

        usuario = random.choice(activos)

        # Usar la lista PECES existente
        if not globals().get("PECES"):
            print("? No existe la lista PECES.")
            return

        peces = PECES

        pesos = []

        for pez in peces:
            try:
                pesos.append(float(pez[5]))
            except Exception:
                pesos.append(1.0)

        pez = random.choices(
            peces,
            weights=pesos,
            k=1
        )[0]

        emoji, nombre, rareza, valor, xp_ganado, peso = pez

        # Registrar que Violet volvió a interactuar con el usuario
        violet_pesca_marcar_usuario(
            guild.id,
            usuario.id
        )

        embed = discord.Embed(
            title=" 💜 ¡Violet encontró algo!",
            description=(
                f"{usuario.mention}\n\n"
                "Violet lanzó la caa y algo mordió el anzuelo.\n\n"
                f" **Parece ser:** {emoji} **{nombre}**\n"
                f" Rareza: **{rareza}**\n\n"
                "🎣 Pulsa **Pescar** antes de que escape!"
            ),
            color=discord.Color.purple()
        )

        embed.set_footer(
            text="Violet  Expedición automática"
        )

        view = VioletPescaAutomaticaView(
            usuario.id,
            pez
        )

        await canal.send(
            content=(
                f" {usuario.mention}, "
                "💜 Violet quiere que participes!"
            ),
            embed=embed,
            view=view
        )

    except discord.Forbidden:
        print(
            f" Violet no puede enviar mensajes en "
            f"la pesca de {guild.name}"
        )

    except Exception as error:
        print(
            f" Error en evento de pesca automática "
            f"({guild.name}): {error}"
        )


async def violet_pesca_loop_v2():
    await asyncio.sleep(20)

    while True:

        try:

            for guild in list(bot.guilds):

                try:
                    await violet_obtener_canal_pesca(guild)

                    await violet_pesca_evento_automatico(
                        guild
                    )

                except Exception as error:
                    print(
                        f"? Error procesando pesca en "
                        f"{guild.name}: {error}"
                    )

        except Exception as error:
            print(
                f" Error general del loop de pesca automática: {error}"
            )

        await asyncio.sleep(
            VIOLET_PESCA_INTERVALO
        )


def violet_iniciar_pesca_automatica_v2():

    global violet_pesca_task_v2

    try:

        if (
            violet_pesca_task_v2 is None
            or violet_pesca_task_v2.done()
        ):

            violet_pesca_task_v2 = asyncio.create_task(
                violet_pesca_loop_v2()
            )

            print(
                " Violet Pesca Automática V2 iniciada."
            )

    except Exception as error:
        print(
            f" Error iniciando pesca automática V2: {error}"
        )


# =========================================================
# FIN VIOLET PESCA AUTOMATICA V2
# =========================================================


# VISTA PAGINADA DE TIENDA MINERÍA / PESCA
# =========================================================

class TiendaMineriaPescaView(discord.ui.View):

    def __init__(self, pagina=1):
        super().__init__(timeout=120)
        self.pagina = pagina

        self.anterior.disabled = pagina <= 1
        self.siguiente.disabled = pagina >= 3

    @discord.ui.button(
        label="Anterior",
        emoji="✨",
        style=discord.ButtonStyle.secondary
    )
    async def anterior(self, interaction, button):

        self.pagina -= 1

        embed = crear_embed_tienda_mineria_pesca(
            self.pagina
        )

        self.anterior.disabled = self.pagina <= 1
        self.siguiente.disabled = self.pagina >= 3

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )

    @discord.ui.button(
        label="Siguiente",
        emoji="✨",
        style=discord.ButtonStyle.primary
    )
    async def siguiente(self, interaction, button):

        self.pagina += 1

        embed = crear_embed_tienda_mineria_pesca(
            self.pagina
        )

        self.anterior.disabled = self.pagina <= 1
        self.siguiente.disabled = self.pagina >= 3

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )


# =========================================================
# GESTIN ECONMICA AUTÓNOMA DE VIOLET
# =========================================================

VIOLET_INVENTARIO_MAXIMO = 40
VIOLET_RESERVA_MONEDAS = 1000

VIOLET_RAREZAS_PROTEGIDAS = {
    "Raro",
    "pico",
    "Legendario",
    "Mítico"
}


async def violet_gestion_economica(guild):

    if bot.user is None:
        return

    user_id = bot.user.id
    guild_id = guild.id

    try:

        vendidos_mineria = []
        vendidos_pesca = []
        monedas_vendidas = 0

        # -------------------------------------------------
        # INVENTARIO DE MINERÍA
        # -------------------------------------------------

        inventario_mineria = await database.get_mining_inventory(
            guild_id,
            user_id
        )

        total_mineria = sum(
            cantidad
            for _, cantidad in inventario_mineria
        )

        if total_mineria >= VIOLET_INVENTARIO_MAXIMO:

            precios_mineria = {
                "Piedra": 10,
                "Carbón": 20,
                "Arcilla": 25,
                "Hierro": 40,
                "Cobre": 60,
                "Obsidiana": 90,
                "Plata": 120,
                "Esmeralda": 180,
                "Rubí": 220,
                "Oro": 250,
                "Zafiro": 350,
                "Ámbar": 400,
                "Diamante": 500,
                "Fragmento Abisal": 750,
                "Cristal Violeta": 850,
                "Núcleo Cósmico": 1500
            }

            rarezas_mineria = {
                "Piedra": "Común",
                "Carbón": "Común",
                "Arcilla": "Común",
                "Hierro": "Poco común",
                "Cobre": "Poco común",
                "Obsidiana": "Poco común",
                "Plata": "Raro",
                "Esmeralda": "Raro",
                "Rubí": "Raro",
                "Oro": "pico",
                "Zafiro": "pico",
                "Ámbar": "pico",
                "Diamante": "Legendario",
                "Fragmento Abisal": "Legendario",
                "Cristal Violeta": "Mítico",
                "Núcleo Cósmico": "Mítico"
            }

            for item, cantidad in inventario_mineria:

                rareza = rarezas_mineria.get(
                    item,
                    "Común"
                )

                if rareza in VIOLET_RAREZAS_PROTEGIDAS:
                    continue

                precio = precios_mineria.get(item, 0)

                if precio <= 0:
                    continue

                if await database.remove_mining_item(
                    guild_id,
                    user_id,
                    item,
                    cantidad
                ):
                    ganancia = precio * cantidad
                    monedas_vendidas += ganancia

                    vendidos_mineria.append(
                        f"? {item} x{cantidad}"
                    )

        # -------------------------------------------------
        # INVENTARIO DE PESCA
        # -------------------------------------------------

        inventario_pesca = await database.get_fish_inventory(
            guild_id,
            user_id
        )

        total_pesca = sum(
            cantidad
            for _, cantidad in inventario_pesca
        )

        if total_pesca >= VIOLET_INVENTARIO_MAXIMO:

            precios_pesca = {
                "Sardina": 15,
                "Pez tropical": 30,
                "Camarón": 35,
                "Cangrejo": 40,
                "Pez globo": 50,
                "Calamar": 80,
                "Almeja": 90,
                "Langosta": 130,
                "Pulpo": 150,
                "Delfín": 220,
                "Tortuga marina": 250,
                "Tiburón": 300,
                "Pez Dragón": 500,
                "Ballena": 600,
                "Pez Violeta": 1000,
                "Leviatán": 2000
            }

            rarezas_pesca = {
                "Sardina": "Común",
                "Pez tropical": "Común",
                "Camarón": "Común",
                "Cangrejo": "Común",
                "Pez globo": "Poco común",
                "Calamar": "Poco común",
                "Almeja": "Poco común",
                "Langosta": "Poco común",
                "Pulpo": "Raro",
                "Delfín": "Raro",
                "Tortuga marina": "Raro",
                "Tiburón": "pico",
                "Pez Dragón": "pico",
                "Ballena": "Legendario",
                "Pez Violeta": "Mítico",
                "Leviatán": "Mítico"
            }

            for item, cantidad in inventario_pesca:

                rareza = rarezas_pesca.get(
                    item,
                    "Común"
                )

                if rareza in VIOLET_RAREZAS_PROTEGIDAS:
                    continue

                precio = precios_pesca.get(item, 0)

                if precio <= 0:
                    continue

                if await database.remove_fish(
                    guild_id,
                    user_id,
                    item,
                    cantidad
                ):
                    ganancia = precio * cantidad
                    monedas_vendidas += ganancia

                    vendidos_pesca.append(
                        f" {item} x{cantidad}"
                    )

        # -------------------------------------------------
        # VENTA
        # -------------------------------------------------

        if monedas_vendidas > 0:

            await database.add_balance(
                user_id,
                guild_id,
                monedas_vendidas
            )

        # -------------------------------------------------
        # MEJORAS AUTOMÁTICAS
        # -------------------------------------------------

        datos = await database.get_user(
            user_id,
            guild_id
        )

        monedas = datos[2]

        nivel_mina, xp_mina, pico = (
            await database.get_mining_stats(
                guild_id,
                user_id
            )
        )

        nivel_pesca, xp_pesca, cana = (
            await database.get_fishing_stats(
                guild_id,
                user_id
            )
        )

        mejoras = []

        # Intentamos mejorar varias veces mientras
        # Violet conserve su reserva.
        while pico < 10:

            costo = COSTOS_PICO.get(
                pico + 1,
                0
            )

            if costo <= 0:
                break

            if monedas - costo < VIOLET_RESERVA_MONEDAS:
                break

            if not await database.remove_balance(
                user_id,
                guild_id,
                costo
            ):
                break

            pico += 1

            await database.set_mining_tool_level(
                guild_id,
                user_id,
                pico
            )

            monedas -= costo

            mejoras.append(
                f"? Pico nivel {pico}"
            )

        while cana < 10:

            costo = COSTOS_CANA.get(
                cana + 1,
                0
            )

            if costo <= 0:
                break

            if monedas - costo < VIOLET_RESERVA_MONEDAS:
                break

            if not await database.remove_balance(
                user_id,
                guild_id,
                costo
            ):
                break

            cana += 1

            await database.set_fishing_rod_level(
                guild_id,
                user_id,
                cana
            )

            monedas -= costo

            mejoras.append(
                f" Caña nivel {cana}"
            )

        # -------------------------------------------------
        # COMPRAS AUTOMÁTICAS DE VIOLET
        # -------------------------------------------------

        inventario_general = await database.get_inventory(
            user_id,
            guild_id
        )

        objetos_poseidos = {
            str(item).strip().lower()
            for item, cantidad in inventario_general
            if cantidad > 0
        }

        compras_prioritarias = [
            # Herramientas principales
            ("Pico de Diamante", 50000),
            ("Caña de Diamante", 50000),
            ("Pico de Oro", 10000),
            ("Caña de Oro", 10000),
            ("Pico de Hierro", 2500),
            ("Caña Reforzada", 2500),

            # Mejoras avanzadas
            ("Detector de Minerales", 75000),
            ("Radar de Peces", 75000),
            ("Taladro Minero", 150000),
            ("Seuelo Abisal", 150000),
            ("Núcleo Violeta", 350000),
            ("Seuelo Violeta", 350000),

            # Suerte
            ("Suerte Minera", 100000),
            ("Suerte Pesquera", 100000),

            # Velocidad
            ("Minería Rápida", 150000),
            ("Pesca Rápida", 150000),

            # Máximas
            ("Fortuna Legendaria", 300000),
            ("Bendición de Violet", 750000)
        ]

        for nombre_objeto, precio_objeto in compras_prioritarias:

            if nombre_objeto.lower() in objetos_poseidos:
                continue

            if monedas - precio_objeto < VIOLET_RESERVA_MONEDAS:
                continue

            comprado = await database.remove_balance(
                user_id,
                guild_id,
                precio_objeto
            )

            if not comprado:
                continue

            await database.add_item(
                user_id,
                guild_id,
                nombre_objeto,
                1
            )

            monedas -= precio_objeto

            mejoras.append(
                f" Compró **{nombre_objeto}** "
                f"por **{precio_objeto:,}** monedas"
            )

            # Solo una compra por ciclo.
            break

        # -------------------------------------------------
        # BANCO AUTOMÁTICO
        # -------------------------------------------------

        VIOLET_RESERVA_BANCO = 5000

        if monedas > VIOLET_RESERVA_BANCO:

            excedente = monedas - VIOLET_RESERVA_BANCO
            deposito = excedente // 2

            if deposito > 0:

                if await database.deposit_bank(
                    user_id,
                    guild_id,
                    deposito
                ):
                    monedas -= deposito

                    mejoras.append(
                        f" Depositó **{deposito:,} monedas** "
                        f"en el banco"
                    )

        # -------------------------------------------------
        # AVISO EN EL CANAL
        # -------------------------------------------------

        if vendidos_mineria or vendidos_pesca or mejoras:

            canal = discord.utils.get(
                guild.text_channels,
                name=VIOLET_CANAL_NOMBRE
            )

            if canal:

                partes = []

                if vendidos_mineria:
                    partes.append(
                        "? **Minerales vendidos:**\n"
                        + "\n".join(vendidos_mineria)
                    )

                if vendidos_pesca:
                    partes.append(
                        " **Peces vendidos:**\n"
                        + "\n".join(vendidos_pesca)
                    )

                if monedas_vendidas:
                    partes.append(
                        f" **Ganancia por ventas:** "
                        f"{monedas_vendidas:,} monedas"
                    )

                if mejoras:
                    partes.append(
                        "? **Mejoras automáticas:**\n"
                        + "\n".join(mejoras)
                    )

                embed = discord.Embed(
                    title=" Violet gestionó su economía",
                    description="\n\n".join(partes),
                    color=discord.Color.purple()
                )

                embed.set_footer(
                    text="Violet  Gestión económica autónoma"
                )

                await canal.send(embed=embed)

    except Exception as error:

        print(
            f" Error en gestión económica autónoma "
            f"({guild.name}): {error}"
        )


async def violet_loop_actividades():

    await bot.wait_until_ready()

    while not bot.is_closed():

        try:
            intervalo_actual = VIOLET_INTERVALO

            for guild in bot.guilds:

                canal = discord.utils.get(
                    guild.text_channels,
                    name=VIOLET_CANAL_NOMBRE
                )

                if canal:

                    actividad = await violet_actividad_automatica(
                        guild
                    )

                    await violet_gestion_economica(
                        guild
                    )

                    # ---------------------------------------------
                    # MEJORAS DE VELOCIDAD
                    # ---------------------------------------------

                    if bot.user is not None:

                        try:
                            mejoras = await violet_obtener_mejoras_actividad(
                                guild.id,
                                bot.user.id
                            )

                            mineria_rapida = (
                                mejoras.get("Minería Rápida", 0) > 0
                            )

                            pesca_rapida = (
                                mejoras.get("Pesca Rápida", 0) > 0
                            )

                            if mineria_rapida and pesca_rapida:
                                intervalo_actual = min(
                                    intervalo_actual,
                                    5
                                )

                            elif actividad == "mineria" and mineria_rapida:
                                intervalo_actual = min(
                                    intervalo_actual,
                                    10
                                )

                            elif actividad == "pesca" and pesca_rapida:
                                intervalo_actual = min(
                                    intervalo_actual,
                                    10
                                )

                        except Exception as error:
                            print(
                                f" Error calculando velocidad de Violet "
                                f"({guild.name}): {error}"
                            )

        except Exception as error:
            print(
                f" Error en loop autónomo de Violet: {error}"
            )

        await asyncio.sleep(intervalo_actual)


@bot.tree.command(
    name="violet-actividades",
    description="Crea el canal donde Violet minará y pescará automáticamente"
)
async def violet_actividades(
    interaction: discord.Interaction
):

    if interaction.guild is None:
        await responder(
            interaction,
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    try:

        canal = await violet_crear_canal(
            interaction.guild
        )

        if canal is None:
            await interaction.followup.send(
                " No pude crear el canal. "
                "Comprueba que Violet tenga permiso para gestionar canales.",
                ephemeral=True
            )
            return

        if not hasattr(bot, "_violet_actividades_iniciadas"):
            bot._violet_actividades_iniciadas = True

            bot._violet_actividades_task = asyncio.create_task(
                violet_loop_actividades()
            )

        embed = discord.Embed(
            title=" Violet Autónoma activada",
            description=(
                f"Violet comenzará a realizar actividades automáticamente "
                f"en {canal.mention}.\n\n"
                "? Minería automática\n"
                " Pesca automática\n"
                " Objetos raros y míticos\n"
                "? XP y niveles propios\n"
                " Economía propia de Violet\n"
                " Colección propia"
            ),
            color=discord.Color.purple()
        )

        embed.set_footer(
            text="Violet  Actividad autónoma cada 20 segundos"
        )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True
        )

    except Exception as error:

        print(
            f" Error en /violet-actividades: {error}"
        )

        await interaction.followup.send(
            " No pude activar las actividades autónomas.",
            ephemeral=True
        )


# =========================================================
# ESTADÍSTICAS DE VIOLET AUTÓNOMA
# =========================================================

@bot.tree.command(
    name="violet-estado",
    description="Muestra el estado de las actividades autónomas de Violet"
)
async def violet_estado(interaction: discord.Interaction):

    if interaction.guild is None:
        await responder(
            interaction,
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    try:
        canal = discord.utils.get(
            interaction.guild.text_channels,
            name=VIOLET_CANAL_NOMBRE
        )

        nivel_m, xp_m, pico = await database.get_mining_stats(
            interaction.guild.id,
            bot.user.id
        )

        nivel_p, xp_p, cana = await database.get_fishing_stats(
            interaction.guild.id,
            bot.user.id
        )

        embed = discord.Embed(
            title=" Estado de Violet",
            description=(
                "Violet está desarrollando sus propias "
                "actividades de minería y pesca."
            ),
            color=discord.Color.purple()
        )

        embed.add_field(
            name="⛏️ Minería",
            value=(
                f"Nivel: **{nivel_m}**\n"
                f"XP: **{xp_m}**\n"
                f"Pico: **Nivel {pico}**"
            ),
            inline=True
        )

        embed.add_field(
            name=" Pesca",
            value=(
                f"Nivel: **{nivel_p}**\n"
                f"XP: **{xp_p}**\n"
                f"Caña: **Nivel {cana}**"
            ),
            inline=True
        )

        embed.add_field(
            name=" Canal autónomo",
            value=(
                canal.mention
                if canal
                else " No configurado"
            ),
            inline=False
        )

        embed.set_footer(
            text="Violet  Actividad autónoma"
        )

        await responder(
            interaction,
            embed=embed
        )

    except Exception as error:
        print(f" Error en /violet-estado: {error}")

        await responder(
            interaction,
            " No pude consultar el estado de Violet.",
            ephemeral=True
        )


@bot.tree.command(
    name="violet-inventario",
    description="Muestra el inventario autónomo de Violet"
)
async def violet_inventario(
    interaction: discord.Interaction
):

    if interaction.guild is None:
        await responder(
            interaction,
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    try:
        minerales = await database.get_mining_inventory(
            interaction.guild.id,
            bot.user.id
        )

        peces = await database.get_fish_inventory(
            interaction.guild.id,
            bot.user.id
        )

        texto_minerales = (
            "\n".join(
                f"? **{item}**  {cantidad}"
                for item, cantidad in minerales
            )
            if minerales
            else "Sin minerales."
        )

        texto_peces = (
            "\n".join(
                f" **{item}**  {cantidad}"
                for item, cantidad in peces
            )
            if peces
            else "Sin peces."
        )

        embed = discord.Embed(
            title=" Inventario de Violet",
            color=discord.Color.purple()
        )

        embed.add_field(
            name="💎 Minerales",
            value=texto_minerales[:1024],
            inline=False
        )

        embed.add_field(
            name=" Peces",
            value=texto_peces[:1024],
            inline=False
        )

        embed.set_footer(
            text="Violet  Inventario autónomo"
        )

        await responder(
            interaction,
            embed=embed
        )

    except Exception as error:
        print(f" Error en /violet-inventario: {error}")

        await responder(
            interaction,
            " No pude cargar el inventario de Violet.",
            ephemeral=True
        )


@bot.tree.command(
    name="violet-nivel",
    description="Muestra los niveles de minería y pesca de Violet"
)
async def violet_nivel(
    interaction: discord.Interaction
):

    if interaction.guild is None:
        await responder(
            interaction,
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    try:
        nivel_m, xp_m, pico = await database.get_mining_stats(
            interaction.guild.id,
            bot.user.id
        )

        nivel_p, xp_p, cana = await database.get_fishing_stats(
            interaction.guild.id,
            bot.user.id
        )

        embed = discord.Embed(
            title=" Niveles de Violet",
            color=discord.Color.purple()
        )

        embed.add_field(
            name="⛏️ Minería",
            value=(
                f"**Nivel {nivel_m}**\n"
                f"? XP: **{xp_m}**\n"
                f"? Pico: **{pico}**"
            ),
            inline=True
        )

        embed.add_field(
            name=" Pesca",
            value=(
                f"**Nivel {nivel_p}**\n"
                f"? XP: **{xp_p}**\n"
                f" Caña: **{cana}**"
            ),
            inline=True
        )

        await responder(
            interaction,
            embed=embed
        )

    except Exception as error:
        print(f" Error en /violet-nivel: {error}")

        await responder(
            interaction,
            " No pude consultar los niveles de Violet.",
            ephemeral=True
        )



# SISTEMA SOCIAL
# =========================================================

ACCIONES_SOCIALES = {
    "beso": ("besó", "", "Beso"),
    "abrazo": ("abrazó", "", "Abrazo"),
    "pat": ("acarició", "", "Pat"),
    "slap": ("le dio una bofetada a", "", "Slap"),
    "cuddle": ("se acurrucó con", "", "Cuddle"),
    "highfive": ("chocó los cinco con", "", "Highfive"),
    "poke": ("molestá con un poke a", "", "Poke"),
    "mordisco": ("le dio un mordisco a", "", "Mordisco"),
    "bailar": ("bailó con", "", "Bailar"),
    "dormir": ("se quedó dormido junto a", "", "Dormir")
}


async def interaccion_social(
    interaction,
    usuario,
    accion_db
):

    if interaction.guild is None:

        await responder(
            interaction,
            " Este comando solo funciona "
            "en servidores.",
            ephemeral=True
        )
        return

    if usuario.id == interaction.user.id:

        await responder(
            interaction,
            " No puedes hacer eso contigo mismo.",
            ephemeral=True
        )
        return

    accion, emoji, nombre = ACCIONES_SOCIALES[
        accion_db
    ]

    try:

        await database.add_interaction(
            interaction.guild.id,
            interaction.user.id,
            usuario.id,
            accion_db
        )

        contador = await database.get_interaction_count(
            interaction.guild.id,
            interaction.user.id,
            usuario.id,
            accion_db
        )

        total = await database.get_total_interactions(
            interaction.guild.id,
            interaction.user.id,
            usuario.id
        )

    except Exception as error:

        print(
            f"Error registrando interacción: {error}"
        )

        await responder(
            interaction,
            " No pude registrar la interacción.",
            ephemeral=True
        )
        return

    # =====================================================
    # COMPROBAR LOGROS SOCIALES
    # =====================================================

    logros_nuevos = []

    if contador >= 1:
        logro = f"primer_{accion_db}"
        if await database.desbloquear_logro(
            interaction.guild.id,
            interaction.user.id,
            logro
        ):
            logros_nuevos.append(
                f" Primer {nombre.lower()}"
            )

    if total >= 25:
        if await database.desbloquear_logro(
            interaction.guild.id,
            interaction.user.id,
            "inseparables"
        ):
            logros_nuevos.append(" Inseparables")

    if total >= 100:
        if await database.desbloquear_logro(
            interaction.guild.id,
            interaction.user.id,
            "pareja_perfecta"
        ):
            logros_nuevos.append(" Pareja perfecta")

    if total >= 250:
        if await database.desbloquear_logro(
            interaction.guild.id,
            interaction.user.id,
            "alma_gemela"
        ):
            logros_nuevos.append(" Alma gemela")

    if accion_db == "pat" and contador >= 50:
        if await database.desbloquear_logro(
            interaction.guild.id,
            interaction.user.id,
            "amigo_animales"
        ):
            logros_nuevos.append(" Amigo de los animales")

    if accion_db == "beso" and contador >= 50:
        if await database.desbloquear_logro(
            interaction.guild.id,
            interaction.user.id,
            "romantico"
        ):
            logros_nuevos.append(" Romántico")

    if accion_db == "abrazo" and contador >= 100:
        if await database.desbloquear_logro(
            interaction.guild.id,
            interaction.user.id,
            "abrazador"
        ):
            logros_nuevos.append(" Abrazador")

    interacciones_distintas = len(
        await database.get_interactions(
            interaction.guild.id,
            interaction.user.id,
            usuario.id
        )
    )

    if interacciones_distintas >= 10:
        if await database.desbloquear_logro(
            interaction.guild.id,
            interaction.user.id,
            "maestro_social"
        ):
            logros_nuevos.append(" Maestro social")

    gif = await obtener_gif(
        accion_db
    )

    embed = discord.Embed(
        title=f"{emoji} {nombre}",
        description=(
            f"{interaction.user.mention} "
            f"**{accion}** a {usuario.mention}.\n\n"
            f"{emoji} **{nombre}s entre ustedes:** "
            f"**{contador}**\n"
            f" **Interacciones totales entre ustedes:** "
            f"**{total}**"
        ),
        color=discord.Color.purple()
    )

    if gif:
        embed.set_image(
            url=gif
        )

    embed.set_footer(
        text="Violet  Sistema social"
    )

    if logros_nuevos:
        try:
            recompensa_coins = 50 * len(logros_nuevos)
            recompensa_xp = 25 * len(logros_nuevos)

            await database.add_balance(
                interaction.user.id,
                interaction.guild.id,
                recompensa_coins
            )

            await database.add_xp(
                interaction.user.id,
                interaction.guild.id,
                recompensa_xp
            )

            embed.add_field(
                name=" Recompensas",
                value=(
                    f" **+{recompensa_coins}** monedas\\n"
                    f"? **+{recompensa_xp} XP**"
                ),
                inline=False
            )

        except Exception as error:
            print(f" Error entregando recompensa: {error}")

    if logros_nuevos:
        embed.add_field(
            name=" 🏆 ¡Nuevo logro desbloqueado!",
            value="\n".join(
                f" **{logro}**"
                for logro in logros_nuevos
            ),
            inline=False
        )

    await responder(
        interaction,
        embed=embed
    )


@arbol.command(
    name="beso",
    description="Besa a alguien"
)
async def beso(
    interaction: discord.Interaction,
    usuario: discord.Member
):

    await interaccion_social(
        interaction,
        usuario,
        "beso"
    )


@arbol.command(
    name="abrazo",
    description="Abraza a alguien"
)
async def abrazo(
    interaction: discord.Interaction,
    usuario: discord.Member
):

    await interaccion_social(
        interaction,
        usuario,
        "abrazo"
    )


@arbol.command(
    name="pat",
    description="Acaricia a alguien"
)
async def pat(
    interaction: discord.Interaction,
    usuario: discord.Member
):

    await interaccion_social(
        interaction,
        usuario,
        "pat"
    )


@arbol.command(
    name="slap",
    description="Da una bofetada anime"
)
async def slap(
    interaction: discord.Interaction,
    usuario: discord.Member
):

    await interaccion_social(
        interaction,
        usuario,
        "slap"
    )


@arbol.command(
    name="cuddle",
    description="Acurrúcate con alguien"
)
async def cuddle(
    interaction: discord.Interaction,
    usuario: discord.Member
):

    await interaccion_social(
        interaction,
        usuario,
        "cuddle"
    )


@arbol.command(name="highfive", description="Choca los cinco con otro usuario")
async def highfive(interaction: discord.Interaction, usuario: discord.Member):
    await interaccion_social(interaction, usuario, "highfive")


@arbol.command(name="poke", description="Hazle un poke a otro usuario")
async def poke(interaction: discord.Interaction, usuario: discord.Member):
    await interaccion_social(interaction, usuario, "poke")


@arbol.command(name="mordisco", description="Dale un mordisco a otro usuario")
async def mordisco(interaction: discord.Interaction, usuario: discord.Member):
    await interaccion_social(interaction, usuario, "mordisco")


@arbol.command(name="bailar", description="Baila con otro usuario")
async def bailar(interaction: discord.Interaction, usuario: discord.Member):
    await interaccion_social(interaction, usuario, "bailar")


@arbol.command(name="dormir", description="Duerme junto a otro usuario")
async def dormir(interaction: discord.Interaction, usuario: discord.Member):
    await interaccion_social(interaction, usuario, "dormir")


# =========================================================
# ESTADÍSTICAS SOCIALES
# =========================================================

@arbol.command(
    name="estadisticas_sociales",
    description="Muestra tus interacciones con alguien"
)
async def estadisticas_sociales(
    interaction: discord.Interaction,
    usuario: discord.Member
):

    if usuario.id == interaction.user.id:

        await responder(
            interaction,
            " Elige a otra persona.",
            ephemeral=True
        )
        return

    datos = await database.get_interactions(
        interaction.guild.id,
        interaction.user.id,
        usuario.id
    )

    if not datos:

        await responder(
            interaction,
            f" Todavía no tienes interacciones "
            f"con {usuario.mention}."
        )
        return

    nombres = {
        "beso": " Besos",
        "abrazo": " Abrazos",
        "pat": " Pats",
        "slap": " Slaps",
        "cuddle": " Cuddles",
        "highfive": " Highfives",
        "poke": " Pokes",
        "mordisco": " Mordiscos",
        "bailar": " Bailes",
        "dormir": " Siestas"
    }

    texto = ""

    total = 0

    for accion, cantidad in datos:

        nombre = nombres.get(
            accion,
            accion
        )

        texto += (
            f"{nombre}: **{cantidad}**\n"
        )

        total += cantidad

    texto += (
        f"\n **Total:** **{total}**"
    )

    embed = discord.Embed(
        title=(
            f" {interaction.user.display_name} "
            f" {usuario.display_name}"
        ),
        description=texto,
        color=discord.Color.purple()
    )

    await responder(
        interaction,
        embed=embed
    )


@arbol.command(
    name="ranking_interacciones",
    description="Ranking de interacciones"
)
async def ranking_interacciones(
    interaction: discord.Interaction
):

    datos = await database.get_interaction_ranking(
        interaction.guild.id,
        10
    )

    if not datos:

        await responder(
            interaction,
            " Todavía no hay interacciones."
        )
        return

    texto = ""

    for posicion, (user_id, target_id, total) in enumerate(
        datos,
        start=1
    ):

        usuario = interaction.guild.get_member(
            user_id
        )

        objetivo = interaction.guild.get_member(
            target_id
        )

        nombre1 = (
            usuario.display_name
            if usuario
            else str(user_id)
        )

        nombre2 = (
            objetivo.display_name
            if objetivo
            else str(target_id)
        )

        texto += (
            f"**{posicion}.** "
            f"{nombre1}  {nombre2} "
            f" **{total}**\n"
        )

    embed = discord.Embed(
        title=" Ranking de interacciones",
        description=texto,
        color=discord.Color.gold()
    )

    await responder(
        interaction,
        embed=embed
    )


# =========================================================
# SHIP
# =========================================================


@arbol.command(
    name="ship",
    description="Calcula la compatibilidad"
)
async def ship(
    interaction: discord.Interaction,
    usuario: discord.Member
):

    if usuario.id == interaction.user.id:

        await responder(
            interaction,
            "💞 El ship necesita dos personas.",
            ephemeral=True
        )
        return

    ids = sorted([
        str(interaction.user.id),
        str(usuario.id)
    ])

    clave = ":".join(ids)

    numero = int(
        hashlib.sha256(
            clave.encode()
        ).hexdigest()[:8],
        16
    ) % 101

    if numero >= 80:
        estado = " 💜 ¡Gran compatibilidad!"

    elif numero >= 50:
        estado = " Hay química."

    elif numero >= 30:
        estado = " Podría funcionar."

    else:
        estado = " Mejor como amigos."

    await responder(
        interaction,
        (
            f" **Ship**\n\n"
            f"{interaction.user.mention} + "
            f"{usuario.mention}\n"
            f"💞 Compatibilidad: **{numero}%**\n"
            f"{estado}"
        )
    )


# =========================================================
# REPUTACIN
# =========================================================

@arbol.command(
    name="reputacion",
    description="Da reputación a alguien"
)
async def reputacion(
    interaction: discord.Interaction,
    usuario: discord.Member
):

    if usuario.id == interaction.user.id:

        await responder(
            interaction,
            " No puedes darte reputación.",
            ephemeral=True
        )
        return

    await database.add_reputation(
        usuario.id,
        interaction.guild.id,
        1
    )

    await responder(
        interaction,
        f" {interaction.user.mention} "
        f"le dio reputación a {usuario.mention}."
    )


# =========================================================
# MASCOTAS
# =========================================================

@arbol.command(
    name="adoptar",
    description="Adopta una mascota"
)
async def adoptar(
    interaction: discord.Interaction,
    nombre: str,
    especie: str
):

    correcto = await database.create_pet(
        interaction.user.id,
        interaction.guild.id,
        nombre,
        especie
    )

    if not correcto:

        await responder(
            interaction,
            " Ya tienes una mascota.",
            ephemeral=True
        )
        return

    await responder(
        interaction,
        f" Adoptaste a **{nombre}** "
        f"({especie})."
    )


@arbol.command(
    name="mascota",
    description="Muestra tu mascota"
)
async def mascota(
    interaction: discord.Interaction
):

    pet = await database.get_pet(
        interaction.user.id,
        interaction.guild.id
    )

    if pet is None:

        await responder(
            interaction,
            " No tienes mascota. Usa `/adoptar`."
        )
        return

    embed = discord.Embed(
        title=f" {pet[0]}",
        description=f"Especie: **{pet[1]}**",
        color=discord.Color.purple()
    )

    embed.add_field(
        name=" Hambre",
        value=f"{pet[2]}/100"
    )

    embed.add_field(
        name="😊 Felicidad",
        value=f"{pet[3]}/100"
    )

    embed.add_field(
        name=" Energía",
        value=f"{pet[4]}/100"
    )

    await responder(
        interaction,
        embed=embed
    )


@arbol.command(
    name="alimentar",
    description="Alimenta a tu mascota"
)
async def alimentar(
    interaction: discord.Interaction
):

    correcto = await database.update_pet(
        interaction.user.id,
        interaction.guild.id,
        hunger=20,
        happiness=5
    )

    if not correcto:

        await responder(
            interaction,
            " No tienes mascota.",
            ephemeral=True
        )
        return

    await responder(
        interaction,
        " Alimentaste a tu mascota."
    )


@arbol.command(
    name="jugar_mascota",
    description="Juega con tu mascota"
)
async def jugar_mascota(
    interaction: discord.Interaction
):

    correcto = await database.update_pet(
        interaction.user.id,
        interaction.guild.id,
        hunger=-5,
        happiness=20,
        energy=-15
    )

    if not correcto:

        await responder(
            interaction,
            " No tienes mascota.",
            ephemeral=True
        )
        return

    await responder(
        interaction,
        " Jugaste con tu mascota."
    )


@arbol.command(
    name="dormir_mascota",
    description="Haz dormir a tu mascota"
)
async def dormir_mascota(
    interaction: discord.Interaction
):

    correcto = await database.update_pet(
        interaction.user.id,
        interaction.guild.id,
        energy=30,
        hunger=-5
    )

    if not correcto:

        await responder(
            interaction,
            " No tienes mascota.",
            ephemeral=True
        )
        return

    await responder(
        interaction,
        " Tu mascota descansó."
    )


# =========================================================
# JUEGOS
# =========================================================

@arbol.command(
    name="dado",
    description="Lanza un dado"
)
async def dado(interaction: discord.Interaction):

    numero = random.randint(1, 6)

    await responder(
        interaction,
        f" Salió **{numero}**."
    )


@arbol.command(
    name="moneda",
    description="Lanza una moneda"
)
async def moneda(interaction: discord.Interaction):

    resultado = random.choice([
        "Cara",
        "Cruz"
    ])

    await responder(
        interaction,
        f" Salió **{resultado}**."
    )


@arbol.command(
    name="ppt",
    description="Juega piedra papel o tijera"
)
@app_commands.describe(
    eleccion="piedra, papel o tijera"
)
async def ppt(
    interaction: discord.Interaction,
    eleccion: str
):

    eleccion = eleccion.lower()

    opciones = [
        "piedra",
        "papel",
        "tijera"
    ]

    if eleccion not in opciones:

        await responder(
            interaction,
            " Usa: piedra, papel o tijera.",
            ephemeral=True
        )
        return

    bot_eleccion = random.choice(
        opciones
    )

    if eleccion == bot_eleccion:
        resultado = " Empate."

    elif (
        (eleccion == "piedra" and bot_eleccion == "tijera")
        or
        (eleccion == "papel" and bot_eleccion == "piedra")
        or
        (eleccion == "tijera" and bot_eleccion == "papel")
    ):
        resultado = " Ganaste."

    else:
        resultado = " Perdiste."

    await responder(
        interaction,
        (
            f" Tú: **{eleccion}**\n"
            f" Violet: **{bot_eleccion}**\n\n"
            f"{resultado}"
        )
    )


@arbol.command(
    name="8ball",
    description="Pregunta a la bola mágica"
)
async def ocho_ball(
    interaction: discord.Interaction,
    pregunta: str
):

    respuestas = [
        "Sí.",
        "No.",
        "Probablemente.",
        "Definitivamente.",
        "No lo creo.",
        "Puede ser.",
        "Pregunta más tarde.",
        "Las estrellas dicen que sí.",
        "Las estrellas dicen que no."
    ]

    await responder(
        interaction,
        (
            f" **Pregunta:** {pregunta}\n\n"
            f" **Respuesta:** "
            f"{random.choice(respuestas)}"
        )
    )


# =========================================================
# MODERACIN
# =========================================================
@arbol.command(
    name="clear",
    description="Elimina mensajes"
)
@app_commands.checks.has_permissions(
    manage_messages=True
)
async def clear(
    interaction: discord.Interaction,
    cantidad: app_commands.Range[int, 1, 100]
):

    await interaction.response.defer(
        ephemeral=True
    )

    eliminados = await interaction.channel.purge(
        limit=cantidad
    )

    await interaction.followup.send(
        f" Eliminó **{len(eliminados)}** mensajes.",
        ephemeral=True
    )


@arbol.command(
    name="kick",
    description="Expulsa a un usuario"
)
@app_commands.checks.has_permissions(
    kick_members=True
)
async def kick(
    interaction: discord.Interaction,
    usuario: discord.Member,
    razon: str = "Sin razón"
):

    await usuario.kick(
        reason=razon
    )

    await responder(
        interaction,
        f" {usuario.mention} fue expulsado.\n"
        f"Razón: {razon}"
    )


@arbol.command(
    name="ban",
    description="Banea a un usuario"
)
@app_commands.checks.has_permissions(
    ban_members=True
)
async def ban(
    interaction: discord.Interaction,
    usuario: discord.Member,
    razon: str = "Sin razón"
):

    await usuario.ban(
        reason=razon
    )

    await responder(
        interaction,
        f" {usuario.mention} fue baneado.\n"
        f"Razón: {razon}"
    )


@arbol.command(
    name="timeout",
    description="Silencia temporalmente"
)
@app_commands.checks.has_permissions(
    moderate_members=True
)
async def timeout(
    interaction: discord.Interaction,
    usuario: discord.Member,
    minutos: app_commands.Range[int, 1, 40320]
):

    duracion = __import__(
        "datetime"
    ).timedelta(
        minutes=minutos
    )

    await usuario.timeout(
        duracion
    )

    await responder(
        interaction,
        f" {usuario.mention} recibió "
        f"timeout durante **{minutos} minutos**."
    )


@arbol.command(
    name="warn",
    description="Advierte a un usuario"
)
@app_commands.checks.has_permissions(
    moderate_members=True
)
async def warn(
    interaction: discord.Interaction,
    usuario: discord.Member,
    razon: str = "Sin razón"
):

    await database.add_warning(
        usuario.id,
        interaction.guild.id,
        interaction.user.id,
        razon
    )

    await responder(
        interaction,
        f"? {usuario.mention} recibió una advertencia.\n"
        f"Razón: {razon}"
    )


@arbol.command(
    name="warnings",
    description="Muestra las advertencias"
)
@app_commands.checks.has_permissions(
    moderate_members=True
)
async def warnings(
    interaction: discord.Interaction,
    usuario: discord.Member
):

    datos = await database.get_warnings(
        usuario.id,
        interaction.guild.id
    )

    if not datos:

        await responder(
            interaction,
            " Este usuario no tiene advertencias."
        )
        return

    texto = ""

    for numero, dato in enumerate(
        datos,
        start=1
    ):
        texto += (
            f"**{numero}.** {dato[0]}\n"
        )

    embed = discord.Embed(
        title=f"? Advertencias de {usuario.display_name}",
        description=texto,
        color=discord.Color.orange()
    )

    await responder(
        interaction,
        embed=embed
    )


@arbol.command(
    name="lock",
    description="Bloquea el canal"
)
@app_commands.checks.has_permissions(
    manage_channels=True
)
async def lock(
    interaction: discord.Interaction
):

    overwrite = interaction.channel.overwrites_for(
        interaction.guild.default_role
    )

    overwrite.send_messages = False

    await interaction.channel.set_permissions(
        interaction.guild.default_role,
        overwrite=overwrite
    )

    await responder(
        interaction,
        " Canal bloqueado."
    )


@arbol.command(
    name="unlock",
    description="Desbloquea el canal"
)
@app_commands.checks.has_permissions(
    manage_channels=True
)
async def unlock(
    interaction: discord.Interaction
):

    overwrite = interaction.channel.overwrites_for(
        interaction.guild.default_role
    )

    overwrite.send_messages = True

    await interaction.channel.set_permissions(
        interaction.guild.default_role,
        overwrite=overwrite
    )

    await responder(
        interaction,
        " Canal desbloqueado."
    )


# =========================================================
# ERRORES
# =========================================================

@arbol.error
async def error_comandos(
    interaction,
    error
):

    if isinstance(
        error,
        app_commands.errors.MissingPermissions
    ):

        await responder(
            interaction,
            " No tienes permisos para usar este comando.",
            ephemeral=True
        )

        return

    if isinstance(
        error,
        app_commands.errors.CommandOnCooldown
    ):

        await responder(
            interaction,
            "? Este comando está en cooldown.",
            ephemeral=True
        )

        return

    print(
        f"Error de comando: {error}"
    )



# =========================================================
# COMANDOS CON !
# =========================================================

@bot.command(name="ayuda")
async def cmd_ayuda(ctx):
    await ctx.send(
        " **Violet - Comandos**\n\n"
        " Social\n"
        "`!beso @usuario`\n"
        "`!abrazo @usuario`\n"
        "`!pat @usuario`\n"
        "`!slap @usuario`\n"
        "`!cuddle @usuario`\n"
        "`!ship @usuario`\n"
        "`!reputacion @usuario`\n\n"
        " Economía\n"
        "`!saldo`\n"
        "`!diario`\n"
        "`!trabajar`\n"
        "`!pagar @usuario cantidad`\n\n"
        " Mascotas\n"
        "`!adoptar nombre especie`\n"
        "`!mascota`\n"
        "`!alimentar`\n"
        "`!jugar_mascota`\n"
        "`!dormir_mascota`\n\n"
        " Juegos\n"
        "`!dado`\n"
        "`!moneda`\n"
        "`!ppt`\n"
        "`!8ball`\n\n"
        " Niveles\n"
        "`!perfil`\n"
        "`!rank`"
    )


@bot.command(name="hola")
async def cmd_hola(ctx):
    await ctx.send(f" Hola {ctx.author.mention}.")


@bot.command(name="beso")
async def cmd_beso(ctx, miembro: discord.Member = None):
    if miembro is None:
        await ctx.send(" Debes mencionar a alguien. Ejemplo: `!beso @usuario`")
        return

    if miembro.id == ctx.author.id:
        await ctx.send(" No puedes darte un beso a ti mismo.")
        return

    await database.add_interaction(
        ctx.guild.id,
        ctx.author.id,
        miembro.id,
        "beso"
    )

    contador = await database.get_interaction_count(
        ctx.guild.id,
        ctx.author.id,
        miembro.id,
        "beso"
    )

    gif = await obtener_gif("beso")

    embed = discord.Embed(
        description=(
            f" {ctx.author.mention} le dio un beso a "
            f"{miembro.mention}.\n\n"
            f" Besos entre ambos: **{contador}**"
        ),
        color=discord.Color.purple()
    )

    if gif:
        embed.set_image(url=gif)

    await ctx.send(embed=embed)



# =========================================================
# COMANDOS SOCIALES CON !
# =========================================================

@bot.command(name="abrazo")
async def cmd_abrazo(ctx, miembro: discord.Member = None):

    if miembro is None:
        await ctx.send(" Debes mencionar a alguien. Ejemplo: `!abrazo @usuario`")
        return

    if miembro.id == ctx.author.id:
        await ctx.send(" No puedes abrazarte a ti mismo.")
        return

    await database.add_interaction(
        ctx.guild.id,
        ctx.author.id,
        miembro.id,
        "abrazo"
    )

    contador = await database.get_interaction_count(
        ctx.guild.id,
        ctx.author.id,
        miembro.id,
        "abrazo"
    )

    gif = await obtener_gif("abrazo")

    embed = discord.Embed(
        description=(
            f" {ctx.author.mention} abrazó a {miembro.mention}.\n\n"
            f" Abrazos entre ambos: **{contador}**"
        ),
        color=discord.Color.purple()
    )

    if gif:
        embed.set_image(url=gif)

    await ctx.send(embed=embed)


@bot.command(name="pat")
async def cmd_pat(ctx, miembro: discord.Member = None):

    if miembro is None:
        await ctx.send(" Debes mencionar a alguien. Ejemplo: `!pat @usuario`")
        return

    if miembro.id == ctx.author.id:
        await ctx.send(" No puedes acariciarte a ti mismo.")
        return

    await database.add_interaction(
        ctx.guild.id,
        ctx.author.id,
        miembro.id,
        "pat"
    )

    contador = await database.get_interaction_count(
        ctx.guild.id,
        ctx.author.id,
        miembro.id,
        "pat"
    )

    gif = await obtener_gif("pat")

    embed = discord.Embed(
        description=(
            f" {ctx.author.mention} acarició a {miembro.mention}.\n\n"
            f" Pat entre ambos: **{contador}**"
        ),
        color=discord.Color.purple()
    )

    if gif:
        embed.set_image(url=gif)

    await ctx.send(embed=embed)


@bot.command(name="slap")
async def cmd_slap(ctx, miembro: discord.Member = None):

    if miembro is None:
        await ctx.send(" Debes mencionar a alguien. Ejemplo: `!slap @usuario`")
        return

    if miembro.id == ctx.author.id:
        await ctx.send(" No puedes darte una bofetada a ti mismo.")
        return

    await database.add_interaction(
        ctx.guild.id,
        ctx.author.id,
        miembro.id,
        "slap"
    )

    contador = await database.get_interaction_count(
        ctx.guild.id,
        ctx.author.id,
        miembro.id,
        "slap"
    )

    gif = await obtener_gif("slap")

    embed = discord.Embed(
        description=(
            f" {ctx.author.mention} le dio una bofetada a {miembro.mention}.\n\n"
            f" Slaps entre ambos: **{contador}**"
        ),
        color=discord.Color.purple()
    )

    if gif:
        embed.set_image(url=gif)

    await ctx.send(embed=embed)


@bot.command(name="cuddle")
async def cmd_cuddle(ctx, miembro: discord.Member = None):

    if miembro is None:
        await ctx.send(" Debes mencionar a alguien. Ejemplo: `!cuddle @usuario`")
        return

    if miembro.id == ctx.author.id:
        await ctx.send(" No puedes acurrucarte contigo mismo.")
        return

    await database.add_interaction(
        ctx.guild.id,
        ctx.author.id,
        miembro.id,
        "cuddle"
    )

    contador = await database.get_interaction_count(
        ctx.guild.id,
        ctx.author.id,
        miembro.id,
        "cuddle"
    )

    gif = await obtener_gif("cuddle")

    embed = discord.Embed(
        description=(
            f" {ctx.author.mention} se acurrucó con {miembro.mention}.\n\n"
            f" Cuddles entre ambos: **{contador}**"
        ),
        color=discord.Color.purple()
    )

    if gif:
        embed.set_image(url=gif)

    await ctx.send(embed=embed)


@bot.command(name="ship")
async def cmd_ship(ctx, miembro: discord.Member = None):

    if miembro is None:
        await ctx.send(" Debes mencionar a alguien. Ejemplo: `!ship @usuario`")
        return

    if miembro.id == ctx.author.id:
        await ctx.send("💞 El ship necesita dos personas.")
        return

    ids = sorted([
        str(ctx.author.id),
        str(miembro.id)
    ])

    clave = ":".join(ids)

    numero = int(
        hashlib.sha256(
            clave.encode()
        ).hexdigest()[:8],
        16
    ) % 101

    if numero >= 80:
        estado = " 💜 ¡Gran compatibilidad!"
    elif numero >= 50:
        estado = " Hay química."
    elif numero >= 30:
        estado = " Podría funcionar."
    else:
        estado = " Mejor como amigos."

    await ctx.send(
        f" **Ship**\n\n"
        f"{ctx.author.mention} + {miembro.mention}\n"
        f"💞 Compatibilidad: **{numero}%**\n"
        f"{estado}"
    )


@bot.command(name="reputacion", aliases=["reputación"])
async def cmd_reputacion(ctx, miembro: discord.Member = None):

    if miembro is None:
        await ctx.send(" Debes mencionar a alguien. Ejemplo: `!reputacion @usuario`")
        return

    if miembro.id == ctx.author.id:
        await ctx.send(" No puedes darte reputación.")
        return

    await database.add_reputation(
        miembro.id,
        ctx.guild.id,
        1
    )

    await ctx.send(
        f"? {ctx.author.mention} le dio reputación a "
        f"{miembro.mention}."
    )


# =========================================================
# INICIO
# =========================================================


# ==============================
# PIEDRA, PAPEL O TIJERA
# ==============================

import random

PPT_DESAFIOS = {}


def ppt_gana(jugador, rival):
    return (
        (jugador == "piedra" and rival == "tijera")
        or
        (jugador == "papel" and rival == "piedra")
        or
        (jugador == "tijera" and rival == "papel")
    )


@bot.command(name="ppt")
async def cmd_ppt(ctx, *args):

    opciones = {
        "piedra": "✊",
        "papel": "✋",
        "tijera": "✂️"
    }

    # DESAFIAR A OTRO USUARIO
    if ctx.message.mentions:

        rival = ctx.message.mentions[0]

        if rival.bot:
            await ctx.send(" No puedes jugar contra un bot.")
            return

        if rival.id == ctx.author.id:
            await ctx.send(" No puedes jugar contra ti mismo.")
            return

        if rival.id in PPT_DESAFIOS:
            await ctx.send(
                f" {rival.mention} ya tiene un desafío pendiente."
            )
            return

        PPT_DESAFIOS[rival.id] = {
            "desafiador": ctx.author.id,
            "canal": ctx.channel.id
        }

        await ctx.send(
            f" **✊ ¡Desafío de Piedra, Papel o Tijera!**\n\n"
            f"{ctx.author.mention} desafió a {rival.mention}.\n\n"
            f"{rival.mention}, responde con:\n"
            f"`!ppt piedra` \n"
            f"`!ppt papel` \n"
            f"`!ppt tijera` ✂️"
        )

        return

    # MOSTRAR AYUDA
    if len(args) != 1:

        await ctx.send(
            " **Piedra, Papel o Tijera**\n\n"
            "**Contra Violet:**\n"
            "`!ppt piedra`\n"
            "`!ppt papel`\n"
            "`!ppt tijera`\n\n"
            "**Contra otro usuario:**\n"
            "`!ppt @usuario`"
        )

        return

    eleccion = args[0].lower()

    if eleccion not in opciones:

        await ctx.send(
            " Elección inválida.\n"
            "Usa `piedra`, `papel` o `tijera`."
        )

        return

    # RESPONDER DESAFÍO
    desafio = PPT_DESAFIOS.get(ctx.author.id)

    if desafio:

        if "desafiado" not in desafio:

            desafiador_id = desafio["desafiador"]

            if desafio["canal"] != ctx.channel.id:
                await ctx.send(
                    " El desafío pertenece a otro canal."
                )
                return

            PPT_DESAFIOS[desafiador_id] = {
                "desafiado": ctx.author.id,
                "eleccion_desafiado": eleccion,
                "canal": ctx.channel.id
            }

            del PPT_DESAFIOS[ctx.author.id]

            desafiador = ctx.guild.get_member(
                desafiador_id
            )

            if desafiador is None:
                await ctx.send(
                    " No encontró al usuario que te desafió."
                )
                return

            await ctx.send(
                f" {ctx.author.mention} ya eligió.\n"
                f"{desafiador.mention}, ahora elige:\n\n"
                f"`!ppt piedra` \n"
                f"`!ppt papel` \n"
                f"`!ppt tijera` ✂️"
            )

            return

        # TERMINAR PARTIDA
        eleccion_desafiado = desafio[
            "eleccion_desafiado"
        ]

        desafiado_id = desafio["desafiado"]

        del PPT_DESAFIOS[ctx.author.id]

        desafiado = ctx.guild.get_member(
            desafiado_id
        )

        if desafiado is None:
            await ctx.send(
                " El usuario ya no está en el servidor."
            )
            return

        if eleccion == eleccion_desafiado:
            resultado = " **🤝 ¡Empate!**"

        elif ppt_gana(
            eleccion,
            eleccion_desafiado
        ):
            resultado = (
                f" **🏆 ¡Ganó {ctx.author.mention}!**"
            )

        else:
            resultado = (
                f" **🏆 ¡Ganó {desafiado.mention}!**"
            )

        await ctx.send(
            f" **PIEDRA, PAPEL O TIJERA**\n\n"
            f"{ctx.author.mention}: "
            f"{opciones[eleccion]} **{eleccion}**\n"
            f"{desafiado.mention}: "
            f"{opciones[eleccion_desafiado]} "
            f"**{eleccion_desafiado}**\n\n"
            f"{resultado}"
        )

        return

    # JUGAR CONTRA VIOLET
    violet = random.choice(
        list(opciones.keys())
    )

    if eleccion == violet:
        resultado = " **🤝 ¡Empate!**"

    elif ppt_gana(eleccion, violet):
        resultado = " **🏆 ¡Ganaste contra Violet!**"

    else:
        resultado = " **💜 ¡Violet ganó esta ronda!**"

    await ctx.send(
        f" **PIEDRA, PAPEL O TIJERA**\n\n"
        f"{ctx.author.mention}: "
        f"{opciones[eleccion]} **{eleccion}**\n"
        f" Violet: "
        f"{opciones[violet]} **{violet}**\n\n"
        f"{resultado}"
    )


# ==============================
# ==============================
# COMANDOS PREFIX ADICIONALES
# ==============================

@bot.command(name="reglas")
async def prefix_reglas(ctx):
    await reglas(ctx)

@bot.command(name="perfil")
async def prefix_perfil(ctx, miembro: discord.Member = None):
    await perfil(ctx, miembro)

@bot.command(name="rank")
async def prefix_rank(ctx):
    await rank(ctx)

@bot.command(name="diario")
async def prefix_diario(ctx):
    correcto, valor = await database.claim_daily(
        ctx.author.id,
        ctx.guild.id
    )

    if not correcto:
        horas = valor // 3600
        minutos = (valor % 3600) // 60

        await ctx.send(
            f"❌ Ya reclamaste tu recompensa. "
            f"Espera **{horas}h {minutos}m**."
        )
        return

    await ctx.send(
        f" Recibiste **{valor}** monedas."
    )

@bot.command(name="trabajar")
async def prefix_trabajar(ctx):
    correcto, valor = await database.work(
        ctx.author.id,
        ctx.guild.id
    )

    if not correcto:
        minutos = valor // 60

        await ctx.send(
            f"? Debes esperar aproximadamente "
            f"**{minutos} minutos**."
        )
        return

    await ctx.send(
        f" Trabajaste y ganaste **{valor}** monedas."
    )

@bot.command(name="pagar")
async def prefix_pagar(
    ctx,
    miembro: discord.Member,
    cantidad: int
):
    if miembro.bot:
        await ctx.send(" No puedes pagarle a un bot.")
        return

    if miembro.id == ctx.author.id:
        await ctx.send(" No puedes pagarte a ti mismo.")
        return

    if cantidad <= 0:
        await ctx.send(" La cantidad debe ser mayor que 0.")
        return

    correcto = await database.remove_balance(
        ctx.author.id,
        ctx.guild.id,
        cantidad
    )

    if not correcto:
        await ctx.send(" No tienes suficientes monedas.")
        return

    await database.add_balance(
        miembro.id,
        ctx.guild.id,
        cantidad
    )

    await ctx.send(
        f" {ctx.author.mention} pagó "
        f"**{cantidad:,}** monedas a {miembro.mention}."
    )

@bot.command(name="inventario")
async def prefix_inventario(ctx):
    await inventario(ctx)

@bot.command(name="tienda")
async def prefix_tienda(ctx):
    embed = discord.Embed(
        title=" Tienda de Violet",
        description=(
            " `comida`  100 monedas\n"
            " `regalo`  250 monedas\n"
            " `gema`  500 monedas\n"
            " `suerte`  1.000 monedas\n"
            " `pocion_xp`  2.500 monedas\n"
            " `caja_misteriosa`  5.000 monedas\n"
            " `gema_rara`  10.000 monedas\n"
            " `corona`  25.000 monedas\n"
            " `cristal`  50.000 monedas\n"
            " `orbe`  75.000 monedas\n"
            " `trofeo`  100.000 monedas\n\n"
            "Usa `!comprar objeto cantidad` para comprar."
        ),
        color=discord.Color.from_rgb(138, 43, 226)
    )

    await ctx.send(embed=embed)

@bot.command(name="comprar")
async def prefix_comprar(ctx, *, item: str):

    partes = item.strip().lower().split()

    if not partes:
        await ctx.send(" Usa `!comprar objeto cantidad`.")
        return

    objeto = partes[0]

    try:
        cantidad = int(partes[1]) if len(partes) > 1 else 1
    except ValueError:
        await ctx.send(" La cantidad debe ser un número.")
        return

    if cantidad < 1 or cantidad > 100:
        await ctx.send(" La cantidad debe estar entre 1 y 100.")
        return

    precios = {
        "comida": 100,
        "regalo": 250,
        "gema": 500,
        "suerte": 1000,
        "pocion_xp": 2500,
        "caja_misteriosa": 5000,
        "gema_rara": 10000,
        "corona": 25000,
        "cristal": 50000,
        "orbe": 75000,
        "trofeo": 100000
    }

    if objeto not in precios:
        await ctx.send(
            f" El objeto `{objeto}` no existe en la tienda. "
            f"Usa `!tienda` para ver los objetos disponibles."
        )
        return

    precio_total = precios[objeto] * cantidad

    eliminado = await database.remove_balance(
        ctx.author.id,
        ctx.guild.id,
        precio_total
    )

    if not eliminado:
        saldo = await database.get_balance(
            ctx.author.id,
            ctx.guild.id
        )

        await ctx.send(
            f" No tienes suficientes monedas.\n"
            f" Necesitas **{precio_total:,}** monedas.\n"
            f" Tienes **{saldo:,}** monedas."
        )
        return

    await database.add_item(
        ctx.author.id,
        ctx.guild.id,
        objeto,
        cantidad
    )

    await ctx.send(
        f" Compra realizada.\n\n"
        f" **{cantidad}x {objeto}**\n"
        f" Pagaste **{precio_total:,} monedas**."
    )

@bot.command(name="estadisticas_sociales")
async def prefix_estadisticas_sociales(
    ctx,
    miembro: discord.Member = None
):
    miembro = miembro or ctx.author

    total = await database.get_total_interactions(
        ctx.guild.id,
        ctx.author.id,
        miembro.id
    )

    await ctx.send(
        f" **Estadísticas sociales**\n\n"
        f" {ctx.author.mention}\n"
        f" Con {miembro.mention}: **{total} interacciones**"
    )

@bot.command(name="ranking_interacciones")
async def prefix_ranking_interacciones(ctx):
    ranking = await database.get_interaction_ranking(
        ctx.guild.id
    )

    if not ranking:
        await ctx.send(
            " Todavía no hay interacciones registradas."
        )
        return

    texto = " **Ranking de interacciones**\n\n"

    for posicion, fila in enumerate(ranking[:10], 1):
        usuario_id, total = fila

        miembro = ctx.guild.get_member(usuario_id)

        nombre = (
            miembro.mention
            if miembro
            else f"<@{usuario_id}>"
        )

        texto += (
            f"**{posicion}.** {nombre}  "
            f"**{total}** interacciones\n"
        )

    await ctx.send(texto)

@bot.command(name="adoptar")
async def prefix_adoptar(ctx, *, nombre: str):
    await adoptar(ctx, nombre)

@bot.command(name="mascota")
async def prefix_mascota(ctx):
    await mascota(ctx)

@bot.command(name="alimentar")
async def prefix_alimentar(ctx):
    await alimentar(ctx)

@bot.command(name="jugar_mascota")
async def prefix_jugar_mascota(ctx):
    await jugar_mascota(ctx)

@bot.command(name="dormir_mascota")
async def prefix_dormir_mascota(ctx):
    await dormir_mascota(ctx)

@bot.command(name="dado")
async def prefix_dado(ctx):
    await dado(ctx)

@bot.command(name="moneda")
async def prefix_moneda(ctx):
    await moneda(ctx)

@bot.command(name="8ball")
async def prefix_8ball(ctx, *, pregunta: str = None):
    if not pregunta:
        await ctx.send(" Debes hacer una pregunta. Ejemplo: `!8ball ¿Voy a tener suerte hoy?`")
        return

    respuestas = [
        "Sí.",
        "No.",
        "Probablemente.",
        "Definitivamente.",
        "No lo creo.",
        "Puede ser.",
        "Pregunta más tarde."
    ]

    import random
    await ctx.send(f" {random.choice(respuestas)}")

@bot.command(name="clear")
async def prefix_clear(ctx, cantidad: int = 10):
    await clear(ctx, cantidad)

@bot.command(name="kick")
async def prefix_kick(
    ctx,
    miembro: discord.Member,
    *,
    razon: str = "Sin razón"
):
    await kick(ctx, miembro, razon)

@bot.command(name="ban")
async def prefix_ban(
    ctx,
    miembro: discord.Member,
    *,
    razon: str = "Sin razón"
):
    await ban(ctx, miembro, razon)

@bot.command(name="timeout")
async def prefix_timeout(
    ctx,
    miembro: discord.Member,
    minutos: int,
    *,
    razon: str = "Sin razón"
):
    await timeout(ctx, miembro, minutos, razon)

@bot.command(name="warn")
async def prefix_warn(
    ctx,
    miembro: discord.Member,
    *,
    razon: str = "Sin razón"
):
    await warn(ctx, miembro, razon)

@bot.command(name="warnings")
async def prefix_warnings(
    ctx,
    miembro: discord.Member = None
):
    await warnings(ctx, miembro)

@bot.command(name="lock")
async def prefix_lock(ctx):
    await lock(ctx)

@bot.command(name="unlock")
async def prefix_unlock(ctx):
    await unlock(ctx)


# ==============================
# INTERFAZ PRINCIPAL DE VIOLET
# ==============================

class VioletMainView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(
        label="Seguridad",
        emoji="✨",
        style=discord.ButtonStyle.danger,
        row=0
    )
    async def seguridad(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="🛡️ Seguridad",
                description=(
                    "**Moderación de Violet**\n\n"
                    " `clear`  Limpiar mensajes\n"
                    " `kick`  Expulsar usuario\n"
                    " `ban`  Banear usuario\n"
                    "?? `timeout`  Silenciar usuario\n"
                    "? `warn`  Advertencia\n"
                    " `warnings`  Ver advertencias\n"
                    " `lock`  Bloquear canal\n"
                    " `unlock`  Desbloquear canal"
                ),
                color=discord.Color.red()
            ),
            view=VioletSecurityMainView()
        )

    @discord.ui.button(
        label="Social",
        emoji="💜",
        style=discord.ButtonStyle.primary,
        row=0
    )
    async def social(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            embed=discord.Embed(
                title=" Social",
                description=(
                    "Interactúa con otros usuarios.\n\n"
                    " Beso\n"
                    " Abrazo\n"
                    " Pat\n"
                    " Slap\n"
                    " Cuddle\n"
                    " Ship\n"
                    " Estadísticas\n"
                    " Ranking"
                ),
                color=discord.Color.pink()
            ),
            view=VioletSocialView()
        )

    @discord.ui.button(
        label="Economía",
        emoji="💜",
        style=discord.ButtonStyle.success,
        row=0
    )
    async def economia(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            embed=discord.Embed(
                title=" Economía",
                description=(
                    "Sistema económico de Violet.\n\n"
                    " Saldo\n"
                    " Diario\n"
                    " Trabajar\n"
                    " Pagar\n"
                    " Tienda\n"
                    " Inventario"
                ),
                color=discord.Color.green()
            ),
            view=VioletEconomyView()
        )

    @discord.ui.button(
        label="Mascotas",
        emoji="💜",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def mascotas(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            embed=discord.Embed(
                title=" Mascotas",
                description=(
                    "Cuida a tu mascota.\n\n"
                    " Adoptar\n"
                    " Estado\n"
                    " Alimentar\n"
                    " Jugar\n"
                    " Dormir"
                ),
                color=discord.Color.orange()
            ),
            view=VioletPetView()
        )

    @discord.ui.button(
        label="Juegos",
        emoji="💜",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def juegos(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            embed=discord.Embed(
                title=" Juegos",
                description=(
                    "Juegos disponibles en Violet.\n\n"
                    " Dado\n"
                    " Moneda\n"
                    "✊ Piedra, Papel o Tijera\n"
                    " 8Ball"
                ),
                color=discord.Color.blurple()
            ),
            view=VioletGamesView()
        )

    @discord.ui.button(
        label="Niveles",
        emoji="✨",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def niveles(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="📈 Niveles",
                description=(
                    "Sistema de progresión.\n\n"
                    " Perfil\n"
                    " Ranking\n"
                    " XP\n"
                    " Reputación"
                ),
                color=discord.Color.gold()
            ),
            view=VioletLevelsView()
        )

    @discord.ui.button(
        label="Mercado",
        emoji="💜",
        style=discord.ButtonStyle.success,
        row=2
    )
    async def mercado(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        embed = discord.Embed(
            title=" Violet Market",
            description=(
                "Mercado virtual de **Violet Coin (VLC)**.\n\n"
                " **Mercado**  `/mercado`\n"
                " **Invertir**  `/invertir <cantidad>`\n\n"
                "Compra y gestiona tus inversiones "
                "según la evolución del mercado."
            ),
            color=discord.Color.green()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @discord.ui.button(
        label="Música",
        emoji="💜",
        style=discord.ButtonStyle.secondary,
        row=2
    )
    async def musica(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        embed = discord.Embed(
            title=" Violet Music",
            description=(
                "Sistema de másica de Violet.\n\n"
                "▶️ **Reproducir**  `/play`\n"
                "⏸️ **Pausa**  `/pause`\n"
                "▶️ **Continuar**  `/resume`\n"
                "⏭️ **Siguiente**  `/skip`\n"
                "⏹️ **Detener**  `/stop`\n"
                " **Cola**  `/queue`\n"
                " **Volumen**  `/volume`"
            ),
            color=discord.Color.purple()
        )

        await interaction.response.send_message(
            embed=embed,
            view=VioletMusicView(),
            ephemeral=True
        )

    @discord.ui.button(
        label="Cerrar",
        emoji="💜",
        style=discord.ButtonStyle.danger,
        row=2
    )
    async def cerrar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            content=" Panel de Violet cerrado.",
            embed=None,
            view=None
        )


# Cola de másica por servidor
music_queues = {}

YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "default_search": "ytsearch",
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


async def play_next(guild_id):
    cola = music_queues.get(guild_id, [])

    if not cola:
        return

    guild = bot.get_guild(guild_id)

    if guild is None:
        return

    voice_client = guild.voice_client

    if voice_client is None or not voice_client.is_connected():
        return

    siguiente = cola.pop(0)

    if not cola:
        music_queues.pop(guild_id, None)

    audio = discord.FFmpegPCMAudio(
        siguiente["url"],
        **FFMPEG_OPTIONS
    )

    def terminado(error):
        if error:
            print(f" Error reproduciendo audio: {error}")

        asyncio.run_coroutine_threadsafe(
            play_next(guild_id),
            bot.loop
        )

    voice_client.play(audio, after=terminado)

    print(f" Reproduciendo siguiente: {siguiente['title']}")


@bot.tree.command(name="play", description="Reproduce una canción o búsqueda.")
@app_commands.describe(cancion="Nombre de la canción o URL")
async def play(interaction: discord.Interaction, cancion: str):

    if not interaction.guild:
        await interaction.response.send_message(
            " Este comando solo puede usarse en un servidor.",
            ephemeral=True
        )
        return

    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message(
            " Debes estar conectado a un canal de voz.",
            ephemeral=True
        )
        return

    canal = interaction.user.voice.channel
    await interaction.response.defer()

    try:
        voice_client = interaction.guild.voice_client

        if voice_client is None:
            voice_client = await canal.connect()
        elif voice_client.channel != canal:
            await voice_client.move_to(canal)

        loop = asyncio.get_running_loop()

        def obtener_audio():
            with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
                info = ydl.extract_info(cancion, download=False)

                if "entries" in info:
                    info = info["entries"][0]

                return {
                    "url": info["url"],
                    "title": info.get("title", "Canción desconocida"),
                    "webpage_url": info.get("webpage_url", cancion)
                }

        datos = await loop.run_in_executor(None, obtener_audio)

        guild_id = interaction.guild.id

        if voice_client.is_playing() or voice_client.is_paused():

            if guild_id not in music_queues:
                music_queues[guild_id] = []

            music_queues[guild_id].append(datos)

            posicion = len(music_queues[guild_id])

            await interaction.followup.send(
                f" **{datos['title']}** aadida a la cola.\n"
                f" Posición: **{posicion}**"
            )
            return

        audio = discord.FFmpegPCMAudio(
            datos["url"],
            **FFMPEG_OPTIONS
        )

        def terminado(error):
            if error:
                print(f" Error reproduciendo audio: {error}")

            asyncio.run_coroutine_threadsafe(
                play_next(guild_id),
                bot.loop
            )

        voice_client.play(audio, after=terminado)

        await interaction.followup.send(
            embed=discord.Embed(
                title=" Reproduciendo",
                description=f"**{datos['title']}**",
                color=discord.Color.purple()
            )
        )

    except Exception as e:
        print(f" Error en /play: {e}")
        await interaction.followup.send(
            " No pude reproducir esa canción. Revisa la consola."
        )


@bot.tree.command(name="pause", description="Pausa la canción actual.")
async def pause(interaction: discord.Interaction):

    if not interaction.guild:
        await interaction.response.send_message(
            " Este comando solo puede usarse en un servidor.",
            ephemeral=True
        )
        return

    voice_client = interaction.guild.voice_client

    if voice_client is None or not voice_client.is_connected():
        await interaction.response.send_message(
            " Violet no está conectada a un canal de voz.",
            ephemeral=True
        )
        return

    if not voice_client.is_playing():
        await interaction.response.send_message(
            " No hay ninguna canción reproduciéndose.",
            ephemeral=True
        )
        return

    voice_client.pause()

    await interaction.response.send_message(
        "⏸️ Canción pausada."
    )


@bot.tree.command(name="resume", description="Continúa la canción pausada.")
async def resume(interaction: discord.Interaction):

    if not interaction.guild:
        await interaction.response.send_message(
            " Este comando solo puede usarse en un servidor.",
            ephemeral=True
        )
        return

    voice_client = interaction.guild.voice_client

    if voice_client is None or not voice_client.is_connected():
        await interaction.response.send_message(
            " Violet no está conectada a un canal de voz.",
            ephemeral=True
        )
        return

    if not voice_client.is_paused():
        await interaction.response.send_message(
            " No hay ninguna canción pausada.",
            ephemeral=True
        )
        return

    voice_client.resume()

    await interaction.response.send_message(
        "▶️ Canción reanudada."
    )


@bot.tree.command(name="stop", description="Detiene la másica y desconecta a Violet.")
async def stop(interaction: discord.Interaction):

    if not interaction.guild:
        await interaction.response.send_message(
            " Este comando solo puede usarse en un servidor.",
            ephemeral=True
        )
        return

    voice_client = interaction.guild.voice_client

    if voice_client is None:
        await interaction.response.send_message(
            " Violet no está conectada a un canal de voz.",
            ephemeral=True
        )
        return

    if voice_client.is_playing() or voice_client.is_paused():
        voice_client.stop()

    music_queues.pop(interaction.guild.id, None)

    await voice_client.disconnect()

    await interaction.response.send_message(
        "⏹️ Música detenida y Violet desconectada."
    )


@bot.tree.command(name="skip", description="Salta la canción actual.")
async def skip(interaction: discord.Interaction):

    if not interaction.guild:
        await interaction.response.send_message(
            " Este comando solo puede usarse en un servidor.",
            ephemeral=True
        )
        return

    voice_client = interaction.guild.voice_client

    if voice_client is None or not voice_client.is_connected():
        await interaction.response.send_message(
            " Violet no está conectada a un canal de voz.",
            ephemeral=True
        )
        return

    if not voice_client.is_playing() and not voice_client.is_paused():
        await interaction.response.send_message(
            " No hay ninguna canción reproduciéndose.",
            ephemeral=True
        )
        return

    voice_client.stop()

    await interaction.response.send_message(
        "⏭️ Canción saltada."
    )


@bot.tree.command(name="queue", description="Muestra la cola de másica.")
async def queue(interaction: discord.Interaction):

    if not interaction.guild:
        await interaction.response.send_message(
            " Este comando solo puede usarse en un servidor.",
            ephemeral=True
        )
        return

    cola = music_queues.get(interaction.guild.id, [])

    if not cola:
        await interaction.response.send_message(
            " La cola está vacía.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title=" Cola de Violet",
        color=discord.Color.purple()
    )

    texto = ""

    for i, cancion in enumerate(cola, start=1):
        texto += f"**{i}.** {cancion['title']}\\n"

    embed.description = texto

    await interaction.response.send_message(embed=embed)


class VioletMusicView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(label="Reproducir", emoji="✨", style=discord.ButtonStyle.success)
    async def reproducir(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            " Usa `/play <canción>` para reproducir másica.",
            ephemeral=True
        )

    @discord.ui.button(label="Pausa", emoji="⚙️", style=discord.ButtonStyle.secondary)
    async def pausa(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = interaction.guild.voice_client if interaction.guild else None

        if voice_client and voice_client.is_playing():
            voice_client.pause()
            await interaction.response.send_message(
                "?? Música pausada.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                " No hay una canción reproduciéndose.",
                ephemeral=True
            )

    @discord.ui.button(label="Continuar", emoji="✨", style=discord.ButtonStyle.secondary)
    async def continuar(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = interaction.guild.voice_client if interaction.guild else None

        if voice_client and voice_client.is_paused():
            voice_client.resume()
            await interaction.response.send_message(
                "? Música reanudada.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                " No hay una canción pausada.",
                ephemeral=True
            )

    @discord.ui.button(label="Siguiente", emoji="⚙️", style=discord.ButtonStyle.secondary)
    async def siguiente(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = interaction.guild.voice_client if interaction.guild else None

        if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
            voice_client.stop()
            await interaction.response.send_message(
                "⏭️ Canción saltada.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                " No hay ninguna canción reproduciéndose.",
                ephemeral=True
            )

    @discord.ui.button(label="Detener", emoji="⚙️", style=discord.ButtonStyle.danger)
    async def detener(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = interaction.guild.voice_client if interaction.guild else None

        if voice_client:
            if voice_client.is_playing() or voice_client.is_paused():
                voice_client.stop()

            music_queues.pop(interaction.guild.id, None)
            await voice_client.disconnect()

            await interaction.response.send_message(
                "?? Música detenida y cola eliminada.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                " Violet no está conectada a un canal de voz.",
                ephemeral=True
            )

    @discord.ui.button(label="Cola", emoji="📜", style=discord.ButtonStyle.primary, row=1)
    async def cola(self, interaction: discord.Interaction, button: discord.ui.Button):
        cola_actual = music_queues.get(interaction.guild.id, [])

        if not cola_actual:
            await interaction.response.send_message(
                " La cola está vacía.",
                ephemeral=True
            )
            return

        texto = "\n".join(
            f"**{i}.** {cancion['title']}"
            for i, cancion in enumerate(cola_actual, start=1)
        )

        embed = discord.Embed(
            title=" Cola de Violet",
            description=texto,
            color=discord.Color.purple()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @discord.ui.button(label="Volumen", emoji="🔊", style=discord.ButtonStyle.primary, row=1)
    async def volumen(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            " Usa `/volume <0-100>` para cambiar el volumen.",
            ephemeral=True
        )

    @discord.ui.button(label="Desconectar", emoji="⏹️", style=discord.ButtonStyle.danger, row=1)
    async def desconectar(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = interaction.guild.voice_client if interaction.guild else None

        if voice_client:
            music_queues.pop(interaction.guild.id, None)
            await voice_client.disconnect()

            await interaction.response.send_message(
                " Violet se desconectó y la cola fue eliminada.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                " Violet no está conectada a un canal de voz.",
                ephemeral=True
            )



class ClearModal(discord.ui.Modal, title=" Limpiar mensajes"):

    cantidad = discord.ui.TextInput(
        label="Cantidad de mensajes",
        placeholder="Escribe un número entre 1 y 100",
        required=True,
        min_length=1,
        max_length=3
    )

    async def on_submit(self, interaction: discord.Interaction):

        try:
            cantidad = int(self.cantidad.value)
        except ValueError:
            await interaction.response.send_message(
                " Debes introducir un número válido.",
                ephemeral=True
            )
            return

        if cantidad < 1 or cantidad > 100:
            await interaction.response.send_message(
                " La cantidad debe estar entre 1 y 100.",
                ephemeral=True
            )
            return

        miembro_violet = interaction.guild.get_member(bot.user.id)

        if miembro_violet is None:
            await interaction.response.send_message(
                " No pude identificar a Violet en este servidor.",
                ephemeral=True
            )
            return

        permisos = interaction.channel.permissions_for(miembro_violet)

        if not permisos.manage_messages:
            await interaction.response.send_message(
                " Violet no tiene permiso para eliminar mensajes en este canal.",
                ephemeral=True
            )
            return

        try:
            await interaction.response.defer(ephemeral=True)

            eliminados = await interaction.channel.purge(
                limit=cantidad
            )

            await interaction.followup.send(
                f" Eliminó **{len(eliminados)}** mensajes.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.followup.send(
                " Violet no tiene permisos suficientes para eliminar mensajes.",
                ephemeral=True
            )

        except discord.NotFound:
            print("? La interacción del modal ya no es válida.")

        except Exception as error:
            print(f" Error al limpiar mensajes: {error}")

            try:
                await interaction.followup.send(
                    " Ocurrió un error al limpiar los mensajes.",
                    ephemeral=True
                )
            except Exception:
                pass


class VioletSecurityView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(
        label="Limpiar",
        emoji="💜",
        style=discord.ButtonStyle.danger,
        row=0
    )
    async def limpiar(self, interaction, button):
        await interaction.response.send_modal(ClearModal())

    @discord.ui.button(
        label="Expulsar",
        emoji="💜",
        style=discord.ButtonStyle.danger,
        row=0
    )
    async def expulsar(self, interaction, button):
        await interaction.response.send_message(
            " Usa el comando `kick` para expulsar a un usuario.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Banear",
        emoji="💜",
        style=discord.ButtonStyle.danger,
        row=0
    )
    async def banear(self, interaction, button):
        await interaction.response.send_message(
            " Usa el comando `ban` para banear a un usuario.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Timeout",
        emoji="⚙️",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def timeout_button(self, interaction, button):
        await interaction.response.send_message(
            "?? Usa el comando `timeout` para silenciar temporalmente a un usuario.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Advertir",
        emoji="✨",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def advertir(self, interaction, button):
        await interaction.response.send_message(
            "? Usa el comando `warn` para advertir a un usuario.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Advertencias",
        emoji="💜",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def advertencias(self, interaction, button):
        await interaction.response.send_message(
            " Usa el comando `warnings` para consultar las advertencias.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Bloquear",
        emoji="💜",
        style=discord.ButtonStyle.secondary,
        row=2
    )
    async def bloquear(self, interaction, button):
        await interaction.response.send_message(
            " Usa el comando `lock` para bloquear el canal.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Desbloquear",
        emoji="💜",
        style=discord.ButtonStyle.success,
        row=2
    )
    async def desbloquear(self, interaction, button):
        await interaction.response.send_message(
            " Usa el comando `unlock` para desbloquear el canal.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Volver",
        emoji="✨",
        style=discord.ButtonStyle.secondary,
        row=3
    )
    async def volver(self, interaction, button):
        await interaction.response.edit_message(
            embed=violet_main_embed(),
            view=VioletMainView()
        )



class SocialTargetSelect(discord.ui.UserSelect):

    def __init__(self, action):
        self.action = action

        super().__init__(
            placeholder="Selecciona a quién quieres interactuar...",
            min_values=1,
            max_values=1,
            row=0
        )

    async def callback(self, interaction: discord.Interaction):

        usuario = self.values[0]

        if usuario.id == interaction.user.id:
            await interaction.response.send_message(
                " No puedes hacer eso contigo mismo.",
                ephemeral=True
            )
            return

        await interaccion_social(
            interaction,
            usuario,
            self.action
        )


class SocialActionView(discord.ui.View):

    def __init__(self, action):
        super().__init__(timeout=120)

        self.add_item(SocialTargetSelect(action))

    @discord.ui.button(
        label="? Volver",
        emoji="✨",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def volver(self, interaction, button):

        await interaction.response.edit_message(
            embed=violet_main_embed(),
            view=VioletMainView()
        )


class VioletSocialView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(
        label="Beso",
        emoji="💜",
        style=discord.ButtonStyle.primary,
        row=0
    )
    async def beso(self, interaction, button):

        await interaction.response.edit_message(
            embed=discord.Embed(
                title=" Beso",
                description="Selecciona a la persona a la que quieres darle un beso.",
                color=discord.Color.purple()
            ),
            view=SocialActionView("beso")
        )

    @discord.ui.button(
        label="Abrazo",
        emoji="💜",
        style=discord.ButtonStyle.primary,
        row=0
    )
    async def abrazo(self, interaction, button):

        await interaction.response.edit_message(
            embed=discord.Embed(
                title=" Abrazo",
                description="Selecciona a la persona a la que quieres abrazar.",
                color=discord.Color.purple()
            ),
            view=SocialActionView("abrazo")
        )

    @discord.ui.button(
        label="Pat",
        emoji="💜",
        style=discord.ButtonStyle.primary,
        row=0
    )
    async def pat(self, interaction, button):

        await interaction.response.edit_message(
            embed=discord.Embed(
                title=" Pat",
                description="Selecciona a la persona que quieres acariciar.",
                color=discord.Color.purple()
            ),
            view=SocialActionView("pat")
        )

    @discord.ui.button(
        label="Slap",
        emoji="💜",
        style=discord.ButtonStyle.primary,
        row=1
    )
    async def slap(self, interaction, button):

        await interaction.response.edit_message(
            embed=discord.Embed(
                title=" Slap",
                description="Selecciona a la persona a la que quieres darle una bofetada anime.",
                color=discord.Color.purple()
            ),
            view=SocialActionView("slap")
        )

    @discord.ui.button(
        label="Cuddle",
        emoji="💜",
        style=discord.ButtonStyle.primary,
        row=1
    )
    async def cuddle(self, interaction, button):

        await interaction.response.edit_message(
            embed=discord.Embed(
                title=" Cuddle",
                description="Selecciona a la persona con la que quieres acurrucarte.",
                color=discord.Color.purple()
            ),
            view=SocialActionView("cuddle")
        )

    @discord.ui.button(
        label="Ship",
        emoji="💜",
        style=discord.ButtonStyle.success,
        row=1
    )
    async def ship(self, interaction, button):

        await interaction.response.send_message(
            " Usa `/ship @usuario` para calcular la compatibilidad.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Reputación",
        emoji="✨",
        style=discord.ButtonStyle.success,
        row=2
    )
    async def reputacion(self, interaction, button):

        await interaction.response.send_message(
            "? Usa `/reputacion @usuario` para consultar la reputación.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Estadísticas",
        emoji="💜",
        style=discord.ButtonStyle.secondary,
        row=2
    )
    async def estadisticas(self, interaction, button):

        await interaction.response.send_message(
            " Usa `/estadisticas_sociales @usuario` para consultar las estadísticas.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Ranking",
        emoji="💜",
        style=discord.ButtonStyle.secondary,
        row=2
    )
    async def ranking(self, interaction, button):

        await interaction.response.send_message(
            " Usa `/ranking_interacciones` para ver el ranking.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Volver",
        emoji="✨",
        style=discord.ButtonStyle.secondary,
        row=3
    )
    async def volver(self, interaction, button):

        await interaction.response.edit_message(
            embed=violet_main_embed(),
            view=VioletMainView()
        )


class EconomyTargetSelect(discord.ui.UserSelect):

    def __init__(self):
        super().__init__(
            placeholder="Selecciona a quién quieres pagar...",
            min_values=1,
            max_values=1,
            row=0
        )

    async def callback(self, interaction: discord.Interaction):

        usuario = self.values[0]

        if usuario.id == interaction.user.id:
            await interaction.response.send_message(
                " No puedes pagarte a ti mismo.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f" Has seleccionado a {usuario.mention}.\n\n"
            "Para realizar el pago utiliza `/pagar`.",
            ephemeral=True
        )


class EconomyTargetView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(EconomyTargetSelect())

    @discord.ui.button(
        label="? Volver",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def volver(self, interaction, button):

        await interaction.response.edit_message(
            embed=violet_main_embed(),
            view=VioletMainView()
        )


class VioletEconomyView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(
        label="Saldo",
        emoji="💜",
        style=discord.ButtonStyle.success,
        row=0
    )
    async def saldo(self, interaction, button):

        usuario = await database.get_user(
            interaction.user.id,
            interaction.guild.id
        )

        embed = discord.Embed(
            title=" Saldo",
            description=(
                f" {interaction.user.mention}\n\n"
                f" **{usuario[2]:,} monedas**"
            ),
            color=discord.Color.purple()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @discord.ui.button(
        label="Diario",
        emoji="💜",
        style=discord.ButtonStyle.success,
        row=0
    )
    async def diario(self, interaction, button):

        correcto, valor = await database.claim_daily(
            interaction.user.id,
            interaction.guild.id
        )

        if not correcto:

            horas = valor // 3600
            minutos = (valor % 3600) // 60

            await interaction.response.send_message(
                f"❌ Ya reclamaste tu recompensa. "
                f"Espera **{horas}h {minutos}m**.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f" Recibiste **{valor} monedas**.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Trabajar",
        emoji="💜",
        style=discord.ButtonStyle.success,
        row=0
    )
    async def trabajar(self, interaction, button):

        correcto, valor = await database.work(
            interaction.user.id,
            interaction.guild.id
        )

        if not correcto:

            minutos = valor // 60

            await interaction.response.send_message(
                f"? Debes esperar aproximadamente "
                f"**{minutos} minutos**.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f" Trabajaste y ganaste **{valor} monedas**.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Pagar",
        emoji="💜",
        style=discord.ButtonStyle.primary,
        row=1
    )
    async def pagar(self, interaction, button):

        await interaction.response.edit_message(
            embed=discord.Embed(
                title=" Pagar",
                description=(
                    "Selecciona al usuario al que quieres pagar.\n\n"
                    "Después podrás utilizar `/pagar` con la cantidad."
                ),
                color=discord.Color.purple()
            ),
            view=EconomyTargetView()
        )

    @discord.ui.button(
        label="Tienda",
        emoji="💜",
        style=discord.ButtonStyle.primary,
        row=1
    )
    async def tienda(self, interaction, button):

        embed = discord.Embed(
            title=" Tienda de Violet",
            description=(
                " **comida**  100 monedas\n"
                " **regalo**  250 monedas\n"
                " **gema**  500 monedas\n\n"
                "Compra utilizando `/comprar`."
            ),
            color=discord.Color.purple()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @discord.ui.button(
        label="Inventario",
        emoji="💜",
        style=discord.ButtonStyle.primary,
        row=1
    )
    async def inventario(self, interaction, button):

        items = await database.get_inventory(
            interaction.user.id,
            interaction.guild.id
        )

        if not items:

            await interaction.response.send_message(
                " Tu inventario está vacío.",
                ephemeral=True
            )
            return

        texto = ""

        for item, cantidad in items:
            texto += f" **{item}** {cantidad}\n"

        embed = discord.Embed(
            title=" Inventario",
            description=texto,
            color=discord.Color.purple()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @discord.ui.button(
        label="? Volver",
        style=discord.ButtonStyle.secondary,
        row=2
    )
    async def volver(self, interaction, button):

        await interaction.response.edit_message(
            embed=violet_main_embed(),
            view=VioletMainView()
        )


class VioletPetView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(
        label="Adoptar",
        emoji="💜",
        style=discord.ButtonStyle.primary,
        row=0
    )
    async def adoptar(self, interaction: discord.Interaction, button):
        await interaction.response.send_message(
            " Para adoptar tu mascota usa `/adoptar`.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Estado",
        emoji="💜",
        style=discord.ButtonStyle.primary,
        row=0
    )
    async def estado(self, interaction: discord.Interaction, button):
        mascota = await database.get_pet(
            interaction.user.id,
            interaction.guild.id
        )

        if not mascota:
            await interaction.response.send_message(
                " Todavía no tienes una mascota. Usa `/adoptar` para conseguir una.",
                ephemeral=True
            )
            return

        nombre = mascota[2]
        especie = mascota[3]
        hambre = mascota[4]
        felicidad = mascota[5]
        energia = mascota[6]

        embed = discord.Embed(
            title=f" {nombre}",
            description=(
                f" Dueo: {interaction.user.mention}\n"
                f" Especie: **{especie}**\n\n"
                f" Hambre: **{hambre}/100**\n"
                f" Felicidad: **{felicidad}/100**\n"
                f" Energía: **{energia}/100**"
            ),
            color=discord.Color.purple()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @discord.ui.button(
        label="Alimentar",
        emoji="💜",
        style=discord.ButtonStyle.success,
        row=0
    )
    async def alimentar(self, interaction: discord.Interaction, button):
        await interaction.response.send_message(
            " Usa `/alimentar` para alimentar a tu mascota.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Jugar",
        emoji="💜",
        style=discord.ButtonStyle.success,
        row=1
    )
    async def jugar(self, interaction: discord.Interaction, button):
        await interaction.response.send_message(
            " Usa `/jugar_mascota` para jugar con tu mascota.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Dormir",
        emoji="💜",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def dormir(self, interaction: discord.Interaction, button):
        await interaction.response.send_message(
            " Usa `/dormir_mascota` para hacer dormir a tu mascota.",
            ephemeral=True
        )

    @discord.ui.button(
        label="? Volver",
        style=discord.ButtonStyle.secondary,
        row=2
    )
    async def volver(self, interaction: discord.Interaction, button):
        await interaction.response.edit_message(
            embed=violet_main_embed(),
            view=VioletMainView()
        )


class VioletGamesView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(
        label="Dado",
        emoji="💜",
        style=discord.ButtonStyle.primary,
        row=0
    )
    async def dado(self, interaction: discord.Interaction, button):
        import random

        resultado = random.randint(1, 6)

        embed = discord.Embed(
            title=" Dado",
            description=(
                f"{interaction.user.mention} lanzó el dado.\n\n"
                f" Resultado: **{resultado}**"
            ),
            color=discord.Color.purple()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @discord.ui.button(
        label="Moneda",
        emoji="💜",
        style=discord.ButtonStyle.primary,
        row=0
    )
    async def moneda(self, interaction: discord.Interaction, button):
        import random

        resultado = random.choice(["Cara", "Cruz"])

        embed = discord.Embed(
            title=" Moneda",
            description=(
                f"{interaction.user.mention} lanzó una moneda.\n\n"
                f" Resultado: **{resultado}**"
            ),
            color=discord.Color.purple()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @discord.ui.button(
        label="PPT",
        emoji="✨",
        style=discord.ButtonStyle.success,
        row=1
    )
    async def ppt(self, interaction: discord.Interaction, button):
        await interaction.response.send_message(
            "? Usa `/ppt` para jugar Piedra, Papel o Tijera.",
            ephemeral=True
        )

    @discord.ui.button(
        label="8 Ball",
        emoji="💜",
        style=discord.ButtonStyle.success,
        row=1
    )
    async def ocho_ball(self, interaction: discord.Interaction, button):
        await interaction.response.send_message(
            " Usa `/8ball` para hacerle una pregunta a Violet.",
            ephemeral=True
        )

    @discord.ui.button(
        label="? Volver",
        style=discord.ButtonStyle.secondary,
        row=2
    )
    async def volver(self, interaction: discord.Interaction, button):
        await interaction.response.edit_message(
            embed=violet_main_embed(),
            view=VioletMainView()
        )


class VioletLevelsView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(
        label="Perfil",
        emoji="💜",
        style=discord.ButtonStyle.primary,
        row=0
    )
    async def perfil(self, interaction: discord.Interaction, button):
        usuario = await database.get_user(
            interaction.user.id,
            interaction.guild.id
        )

        xp = usuario[3]
        nivel = usuario[4]
        reputacion = usuario[5]

        embed = discord.Embed(
            title=f" Perfil de {interaction.user.display_name}",
            description=(
                f" Usuario: {interaction.user.mention}\n\n"
                f"? Nivel: **{nivel}**\n"
                f" XP: **{xp}**\n"
                f" Reputación: **{reputacion}**\n"
                f" Monedas: **{usuario[2]:,}**"
            ),
            color=discord.Color.purple()
        )

        if interaction.user.display_avatar:
            embed.set_thumbnail(
                url=interaction.user.display_avatar.url
            )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @discord.ui.button(
        label="Ranking",
        emoji="💜",
        style=discord.ButtonStyle.primary,
        row=0
    )
    async def ranking(self, interaction: discord.Interaction, button):
        await interaction.response.send_message(
            " Usa `/rank` para consultar el ranking de niveles.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Reputación",
        emoji="💜",
        style=discord.ButtonStyle.success,
        row=1
    )
    async def reputacion(self, interaction: discord.Interaction, button):
        usuario = await database.get_user(
            interaction.user.id,
            interaction.guild.id
        )

        embed = discord.Embed(
            title=" Reputación",
            description=(
                f"{interaction.user.mention}\n\n"
                f"? Tu reputación actual es **{usuario[5]}**."
            ),
            color=discord.Color.purple()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @discord.ui.button(
        label="Progreso",
        emoji="💜",
        style=discord.ButtonStyle.success,
        row=1
    )
    async def progreso(self, interaction: discord.Interaction, button):
        usuario = await database.get_user(
            interaction.user.id,
            interaction.guild.id
        )

        xp = usuario[3]
        nivel = usuario[4]

        xp_actual = xp % 100
        xp_faltante = 100 - xp_actual

        barra_llena = xp_actual // 10
        barra_vacia = 10 - barra_llena

        barra = "" * barra_llena + "" * barra_vacia

        embed = discord.Embed(
            title=" Progreso",
            description=(
                f"? Nivel actual: **{nivel}**\n\n"
                f"{barra}\n"
                f" **{xp_actual}/100 XP**\n\n"
                f"Te faltan **{xp_faltante} XP** para el siguiente nivel."
            ),
            color=discord.Color.purple()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @discord.ui.button(
        label="? Volver",
        style=discord.ButtonStyle.secondary,
        row=2
    )
    async def volver(self, interaction: discord.Interaction, button):
        await interaction.response.edit_message(
            embed=violet_main_embed(),
            view=VioletMainView()
        )


def violet_main_embed():
    return discord.Embed(
        title=" V I O L E T",
        description=(
            "\n"
            "    **PANEL PRINCIPAL** \n"
            "\n\n"
            "Selecciona una categoría para continuar.\n\n"
            "🛡️ **SEGURIDAD**\n"
            "Protección y moderación del servidor.\n\n"
            " **SOCIAL**\n"
            "Interacciones, diversión y estadísticas.\n\n"
            " **ECONOMÍA**\n"
            "Dinero, tienda y recompensas.\n\n"
            " **MASCOTAS**\n"
            "Adopta y cuida tus mascotas.\n\n"
            " **JUEGOS**\n"
            "Juegos rápidos y entretenimiento.\n\n"
            "📈 **NIVELES**\n"
            "XP, niveles y rankings.\n\n"
            " **MSICA**\n"
            "Reproduce másica y controla la cola."
        ),
        color=discord.Color.from_rgb(138, 43, 226)
    )

# ==============================
# INICIO DEL BOT
# ==============================

@bot.tree.command(name="pala")
async def pala(interaction: discord.Interaction):
    """Elige aleatoriamente a un miembro del servidor."""

    if interaction.guild is None:
        await interaction.response.send_message(
            " Este comando solo puede usarse dentro de un servidor.",
            ephemeral=True
        )
        return

    try:
        # Solicitar a Discord que complete la caché de miembros
        if not interaction.guild.chunked:
            await interaction.guild.chunk(cache=True)

    except Exception as error:
        print(f" Error cargando miembros: {error}")

    miembros = [
        miembro
        for miembro in interaction.guild.members
        if not miembro.bot
    ]

    print(
        f" /pala -> servidor={interaction.guild.name!r}, "
        f"ID={interaction.guild.id}, "
        f"miembros_en_cache={len(interaction.guild.members)}, "
        f"miembros_validos={len(miembros)}"
    )

    if not miembros:
        await interaction.response.send_message(
            " No pude obtener los miembros del servidor. "
            "Comprueba que Server Members Intent está activado.",
            ephemeral=True
        )
        return

    elegido = random.choice(miembros)

    await interaction.response.send_message(
        f"? {elegido.mention} deberías ponerte a agarrar la pala"
    )




# =========================================================
# 🏷️ SISTEMA DE TÍTULOS DE VIOLET
# =========================================================

TITULOS_VIOLET = [
    (100, " Novato"),
    (500, "? Aventurero"),
    (1000, " Experto"),
    (2500, " lite"),
    (5000, " Leyenda de Violet"),
    (10000, " Maestro de Violet"),
]


def obtener_titulo_violet(xp: int) -> str:
    titulo = " Recién llegado"

    for xp_requerido, nombre in TITULOS_VIOLET:
        if xp >= xp_requerido:
            titulo = nombre
        else:
            break

    return titulo


# =========================================================
# 🏷️ MENÚ DE TÍTULOS
# =========================================================

@bot.tree.command(
    name="titulos",
    description="Muestra los títulos de Violet y tus progresos"
)
async def titulos(interaction: discord.Interaction):

    data = await database.get_user(
        interaction.user.id,
        interaction.guild.id
    )

    xp = data[3]
    actual = obtener_titulo_violet(xp)

    texto = ""

    for xp_requerido, nombre in TITULOS_VIOLET:
        if xp >= xp_requerido:
            estado = " Desbloqueado"
        else:
            faltan = xp_requerido - xp
            estado = f" Faltan {faltan} XP"

        texto += f"{nombre}  **{xp_requerido} XP** • {estado}\\n"

    embed = discord.Embed(
        title="🏆 Títulos de Violet",
        description=(
            f"Tu título actual: **{actual}**\\n"
            f"? XP actual: **{xp}**\\n\\n"
            f"{texto}"
        ),
        color=discord.Color.purple()
    )

    embed.set_footer(
        text="Sigue participando para desbloquear nuevos títulos."
    )

    await interaction.response.send_message(embed=embed)


# =========================================================
#  CASINO  SLOTS
# =========================================================

@bot.tree.command(
    name="slots",
    description="Juega a las tragamonedas usando las monedas de Violet"
)
@app_commands.describe(apuesta="Cantidad de monedas que quieres apostar")
async def slots(interaction: discord.Interaction, apuesta: int):

    if interaction.guild is None:
        await interaction.response.send_message(
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    if apuesta <= 0:
        await interaction.response.send_message(
            " La apuesta debe ser mayor que 0.",
            ephemeral=True
        )
        return

    if apuesta > 1_000_000:
        await interaction.response.send_message(
            " La apuesta máxima es de **1.000.000 **.",
            ephemeral=True
        )
        return

    user_id = interaction.user.id
    guild_id = interaction.guild.id

    disponible, restante = comprobar_cooldown_casino(
        guild_id,
        user_id
    )

    if not disponible:
        await interaction.response.send_message(
            f"? Debes esperar **{restante} segundos** antes de jugar nuevamente.",
            ephemeral=True
        )
        return

    registrar_cooldown_casino(guild_id, user_id)

    user = await database.get_user(user_id, guild_id)
    saldo = user[2]

    if saldo < apuesta:
        await interaction.response.send_message(
            f" No tienes suficientes monedas.\n"
            f" Saldo: **{saldo:,} **\n"
            f" Apuesta: **{apuesta:,} **",
            ephemeral=True
        )
        return

    await database.remove_balance(
        user_id,
        guild_id,
        apuesta
    )

    simbolos = [
        "",
        "",
        "",
        "",
        "",
        "",
        "7?"
    ]

    resultado = [
        random.choice(simbolos),
        random.choice(simbolos),
        random.choice(simbolos)
    ]

    premio = 0
    multiplicador = 0

    if resultado[0] == resultado[1] == resultado[2]:

        if resultado[0] == "7?":
            multiplicador = 10
        elif resultado[0] == "":
            multiplicador = 8
        elif resultado[0] == "":
            multiplicador = 6
        else:
            multiplicador = 5

        premio = apuesta * multiplicador

    elif (
        resultado[0] == resultado[1]
        or resultado[1] == resultado[2]
        or resultado[0] == resultado[2]
    ):
        multiplicador = 2
        premio = apuesta * 2

    if premio > 0:
        await database.add_balance(
            user_id,
            guild_id,
            premio
        )

        if multiplicador >= 5:
            titulo = " 🎰 ¡JACKPOT DE VIOLET!"
        else:
            titulo = " 🏆 ¡Ganaste!"

        descripcion = (
            f"**{resultado[0]}  {resultado[1]}  {resultado[2]}**\n\n"
            f" Premio: **+{premio:,} **\n"
            f" Multiplicador: **x{multiplicador}**"
        )

    else:
        titulo = " Sin premio"
        descripcion = (
            f"**{resultado[0]}  {resultado[1]}  {resultado[2]}**\n\n"
            f" Perdiste: **-{apuesta:,} **"
        )

    victoria = premio > 0
    ganancia_neta = premio - apuesta if victoria else 0

    await database.registrar_casino(
        guild_id,
        user_id,
        apuesta,
        ganancia_neta,
        victoria
    )

    nuevo_saldo = (await database.get_user(user_id, guild_id))[2]

    embed = discord.Embed(
        title=titulo,
        description=descripcion,
        color=discord.Color.purple()
    )

    embed.add_field(
        name=" Saldo actual",
        value=f"**{nuevo_saldo:,} **",
        inline=False
    )

    embed.set_footer(
        text="Violet Casino  Juega responsablemente"
    )

    await interaction.response.send_message(
        embed=embed
    )



# =========================================================
#  CASINO  DADOS
# =========================================================

@bot.tree.command(
    name="dados",
    description="Apuesta monedas y lanza dos dados contra Violet"
)
@app_commands.describe(apuesta="Cantidad de monedas que quieres apostar")
async def dados(interaction: discord.Interaction, apuesta: int):

    if interaction.guild is None:
        await interaction.response.send_message(
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    if apuesta <= 0:
        await interaction.response.send_message(
            " La apuesta debe ser mayor que 0.",
            ephemeral=True
        )
        return

    if apuesta > 1_000_000:
        await interaction.response.send_message(
            " La apuesta máxima es de **1.000.000 **.",
            ephemeral=True
        )
        return

    user_id = interaction.user.id
    guild_id = interaction.guild.id

    disponible, restante = comprobar_cooldown_casino(
        guild_id,
        user_id
    )

    if not disponible:
        await interaction.response.send_message(
            f"? Debes esperar **{restante} segundos** antes de jugar nuevamente.",
            ephemeral=True
        )
        return

    registrar_cooldown_casino(guild_id, user_id)

    user = await database.get_user(user_id, guild_id)
    saldo = user[2]

    if saldo < apuesta:
        await interaction.response.send_message(
            f" No tienes suficientes monedas.\n"
            f" Saldo: **{saldo:,} **",
            ephemeral=True
        )
        return

    await database.remove_balance(
        user_id,
        guild_id,
        apuesta
    )

    jugador = random.randint(1, 6) + random.randint(1, 6)
    violet = random.randint(1, 6) + random.randint(1, 6)

    if jugador > violet:
        premio = apuesta * 2

        await database.add_balance(
            user_id,
            guild_id,
            premio
        )

        resultado = (
            f" **🏆 ¡Ganaste!**\n"
            f" Premio: **+{premio:,} **"
        )

    elif jugador == violet:
        premio = apuesta

        await database.add_balance(
            user_id,
            guild_id,
            premio
        )

        resultado = (
            f" **Empate**\n"
            f" Recuperaste tu apuesta: **+{premio:,} **"
        )

    else:
        resultado = (
            f" **Violet ganó**\n"
            f"Perdiste: **-{apuesta:,} **"
        )

    # Registrar estadísticas del casino
    if "Ganaste" in resultado:
        await database.registrar_casino(
            guild_id,
            user_id,
            apuesta,
            apuesta,
            True
        )
    else:
        await database.registrar_casino(
            guild_id,
            user_id,
            apuesta,
            0,
            False
        )

    nuevo_saldo = (await database.get_user(user_id, guild_id))[2]

    embed = discord.Embed(
        title=" Casino de Violet",
        description=(
            f" **Tú:**  `{jugador}`\n"
            f" **Violet:**  `{violet}`\n\n"
            f"{resultado}"
        ),
        color=discord.Color.purple()
    )

    embed.add_field(
        name=" Saldo",
        value=f"**{nuevo_saldo:,} **",
        inline=False
    )

    embed.set_footer(
        text="Casino Violet  Dados"
    )

    await interaction.response.send_message(
        embed=embed
    )



# =========================================================
#  CASINO  BLACKJACK
# =========================================================

@bot.tree.command(
    name="blackjack",
    description="Juega blackjack contra Violet"
)
@app_commands.describe(apuesta="Cantidad de monedas que quieres apostar")
async def blackjack(interaction: discord.Interaction, apuesta: int):

    if interaction.guild is None:
        await interaction.response.send_message(
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    if apuesta <= 0:
        await interaction.response.send_message(
            " La apuesta debe ser mayor que 0.",
            ephemeral=True
        )
        return

    if apuesta > 1_000_000:
        await interaction.response.send_message(
            " La apuesta máxima es de **1.000.000 **.",
            ephemeral=True
        )
        return

    user_id = interaction.user.id
    guild_id = interaction.guild.id

    disponible, restante = comprobar_cooldown_casino(
        guild_id,
        user_id
    )

    if not disponible:
        await interaction.response.send_message(
            f"? Debes esperar **{restante} segundos** antes de jugar nuevamente.",
            ephemeral=True
        )
        return

    registrar_cooldown_casino(guild_id, user_id)

    user = await database.get_user(user_id, guild_id)
    saldo = user[2]

    if saldo < apuesta:
        await interaction.response.send_message(
            f" No tienes suficientes monedas.\n"
            f" Saldo: **{saldo:,} **",
            ephemeral=True
        )
        return

    await database.remove_balance(
        user_id,
        guild_id,
        apuesta
    )

    def valor_mano(mano):
        total = sum(mano)
        ases = mano.count(11)

        while total > 21 and ases:
            total -= 10
            ases -= 1

        return total

    cartas = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11]

    jugador = [
        random.choice(cartas),
        random.choice(cartas)
    ]

    violet = [
        random.choice(cartas),
        random.choice(cartas)
    ]

    while valor_mano(jugador) < 17:
        jugador.append(random.choice(cartas))

    while valor_mano(violet) < 17:
        violet.append(random.choice(cartas))

    total_jugador = valor_mano(jugador)
    total_violet = valor_mano(violet)

    if total_jugador > 21:
        resultado = " Te pasaste de 21. **Violet gana.**"
        premio = 0

    elif total_violet > 21:
        resultado = " Violet se pasó de 21. **🏆 ¡Ganaste!**"
        premio = apuesta * 2

    elif total_jugador > total_violet:
        resultado = " **🏆 ¡Ganaste el blackjack!**"
        premio = apuesta * 2

    elif total_jugador == total_violet:
        resultado = " **Empate.** Recuperas tu apuesta."
        premio = apuesta

    else:
        resultado = " **Violet gana la partida.**"
        premio = 0

    if premio:
        await database.add_balance(
            user_id,
            guild_id,
            premio
        )

    # Registrar estadísticas del casino
    victoria = premio > 0
    ganancia_neta = premio - apuesta if victoria else 0

    await database.registrar_casino(
        guild_id,
        user_id,
        apuesta,
        ganancia_neta,
        victoria
    )

    nuevo_saldo = (await database.get_user(user_id, guild_id))[2]

    def mostrar_mano(mano):
        return " ".join(f"`{c}`" for c in mano)

    embed = discord.Embed(
        title=" Blackjack de Violet",
        description=resultado,
        color=discord.Color.purple()
    )

    embed.add_field(
        name=f" {interaction.user.display_name}",
        value=f"{mostrar_mano(jugador)}\n**Total: {total_jugador}**",
        inline=True
    )

    embed.add_field(
        name=" Violet",
        value=f"{mostrar_mano(violet)}\n**Total: {total_violet}**",
        inline=True
    )

    embed.add_field(
        name=" Resultado",
        value=(
            f"Premio: **+{premio:,} **"
            if premio
            else f"Apuesta perdida: **-{apuesta:,} **"
        ),
        inline=False
    )

    embed.add_field(
        name=" Saldo actual",
        value=f"**{nuevo_saldo:,} **",
        inline=False
    )

    embed.set_footer(
        text="Violet Casino  Blackjack"
    )

    await interaction.response.send_message(embed=embed)



# =========================================================
#  CASINO  RULETA
# =========================================================

@bot.tree.command(
    name="ruleta",
    description="Apuesta a un número de la ruleta"
)
@app_commands.describe(
    apuesta="Cantidad de monedas que quieres apostar",
    numero="Número del 0 al 36"
)
async def ruleta(
    interaction: discord.Interaction,
    apuesta: int,
    numero: int
):

    if interaction.guild is None:
        await interaction.response.send_message(
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    if apuesta <= 0:
        await interaction.response.send_message(
            " La apuesta debe ser mayor que 0.",
            ephemeral=True
        )
        return

    if apuesta > 1_000_000:
        await interaction.response.send_message(
            " La apuesta máxima es de **1.000.000 **.",
            ephemeral=True
        )
        return

    if numero < 0 or numero > 36:
        await interaction.response.send_message(
            " El número debe estar entre **0 y 36**.",
            ephemeral=True
        )
        return

    user_id = interaction.user.id
    guild_id = interaction.guild.id

    disponible, restante = comprobar_cooldown_casino(
        guild_id,
        user_id
    )

    if not disponible:
        await interaction.response.send_message(
            f"? Debes esperar **{restante} segundos** antes de jugar nuevamente.",
            ephemeral=True
        )
        return

    registrar_cooldown_casino(guild_id, user_id)

    user = await database.get_user(user_id, guild_id)
    saldo = user[2]

    if saldo < apuesta:
        await interaction.response.send_message(
            f" No tienes suficientes monedas.\n"
            f" Saldo: **{saldo:,} **",
            ephemeral=True
        )
        return

    await database.remove_balance(
        user_id,
        guild_id,
        apuesta
    )

    resultado = random.randint(0, 36)

    if resultado == numero:
        premio = apuesta * 36

        await database.add_balance(
            user_id,
            guild_id,
            premio
        )

        mensaje = (
            " **🎰 ¡JACKPOT!**\n"
            f" Salió el **{resultado}** y acertaste.\n"
            f" Premio: **+{premio:,} **"
        )

    else:
        premio = 0

        mensaje = (
            f" Salió el **{resultado}**.\n"
            f" Tu número era el **{numero}**.\n"
            f" Perdiste **-{apuesta:,} **."
        )

    # Registrar estadísticas del casino
    victoria = premio > 0
    ganancia_neta = premio - apuesta if victoria else 0

    await database.registrar_casino(
        guild_id,
        user_id,
        apuesta,
        ganancia_neta,
        victoria
    )

    nuevo_saldo = (await database.get_user(user_id, guild_id))[2]

    embed = discord.Embed(
        title=" Ruleta de Violet",
        description=mensaje,
        color=discord.Color.purple()
    )

    embed.add_field(
        name=" Tu apuesta",
        value=f"**{numero}**",
        inline=True
    )

    embed.add_field(
        name=" Resultado",
        value=f"**{resultado}**",
        inline=True
    )

    embed.add_field(
        name=" Saldo",
        value=f"**{nuevo_saldo:,} **",
        inline=False
    )

    embed.set_footer(
        text="Violet Casino  Ruleta"
    )

    await interaction.response.send_message(
        embed=embed
    )



# =========================================================
#  CASINO  RANKING
# =========================================================

@bot.tree.command(
    name="ranking_casino",
    description="Muestra el ranking de ganancias del casino"
)
async def ranking_casino(interaction: discord.Interaction):

    if interaction.guild is None:
        await interaction.response.send_message(
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    guild_id = interaction.guild.id

    ranking = await database.get_casino_ranking(
        guild_id,
        10
    )

    embed = discord.Embed(
        title=" Ranking del Casino",
        description="Los jugadores con mayores ganancias de Violet Casino.",
        color=discord.Color.purple()
    )

    if not ranking:
        embed.description = (
            " **El ranking está vacío.**\n\n"
            "Juega usando `/slots`, `/dados`, "
            "`/blackjack` o `/ruleta`."
        )

    else:
        puestos = ["", "", ""]

        for posicion, datos in enumerate(ranking, start=1):

            user_id, partidas, victorias, derrotas, apostado, ganancias = datos

            miembro = interaction.guild.get_member(user_id)

            if miembro:
                nombre = miembro.display_name
            else:
                nombre = f"Usuario {user_id}"

            icono = (
                puestos[posicion - 1]
                if posicion <= 3
                else f"**{posicion}.**"
            )

            embed.add_field(
                name=f"{icono} {nombre}",
                value=(
                    f" Ganancias: **{ganancias:,} **\n"
                    f" Partidas: **{partidas}**\n"
                    f" Victorias: **{victorias}**\n"
                    f" Derrotas: **{derrotas}**"
                ),
                inline=False
            )

    embed.set_footer(
        text="Violet Casino  Ranking del servidor"
    )

    await interaction.response.send_message(
        embed=embed
    )


# =========================================================
#  COOLDOWN GLOBAL DEL CASINO
# =========================================================

CASINO_COOLDOWN = 10
casino_cooldowns = {}

def comprobar_cooldown_casino(guild_id, user_id):
    clave = (guild_id, user_id)
    ahora = time.time()

    ultimo = casino_cooldowns.get(clave)

    if ultimo is None:
        return True, 0

    restante = CASINO_COOLDOWN - (ahora - ultimo)

    if restante > 0:
        return False, int(restante)

    return True, 0


def registrar_cooldown_casino(guild_id, user_id):
    casino_cooldowns[(guild_id, user_id)] = time.time()


# =========================================================
#  PANEL PRINCIPAL DEL CASINO
# =========================================================

@bot.tree.command(
    name="casino",
    description="Abre el panel principal de Violet Casino"
)
async def casino(interaction: discord.Interaction):

    if interaction.guild is None:
        await interaction.response.send_message(
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title=" Violet Casino",
        description=(
            " **Bienvenido al casino de Violet.**\n\n"
            "Usa tus  monedas para jugar y conseguir grandes premios.\n\n"
            " **Juegos disponibles**\n"
            " `/slots`  Tragamonedas\n"
            " `/dados`  Duelo de dados\n"
            " `/blackjack`  Blackjack contra Violet\n"
            " `/ruleta`  Ruleta\n\n"
            " **Información**\n"
            " `/ranking_casino`  Ranking de ganancias\n"
            " `/estadisticas_casino`  Tus estadísticas"
        ),
        color=discord.Color.purple()
    )

    embed.add_field(
        name=" Economía",
        value="Las apuestas utilizan las monedas virtuales de Violet.",
        inline=False
    )

    embed.add_field(
        name="⏳ Cooldown",
        value="Cada jugador tiene **10 segundos** entre partidas.",
        inline=False
    )

    embed.set_footer(
        text="Violet Casino  Juega con responsabilidad"
    )

    await interaction.response.send_message(
        embed=embed
    )


# =========================================================
#  ESTADÍSTICAS DEL CASINO
# =========================================================

@bot.tree.command(
    name="estadisticas_casino",
    description="Muestra tus estadísticas del casino"
)
async def estadisticas_casino(interaction: discord.Interaction):

    if interaction.guild is None:
        await interaction.response.send_message(
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    guild_id = interaction.guild.id
    user_id = interaction.user.id

    stats = await database.get_casino_stats(
        guild_id,
        user_id
    )

    partidas, victorias, derrotas, apostado, ganancias = stats

    if partidas > 0:
        porcentaje = (victorias / partidas) * 100
    else:
        porcentaje = 0

    embed = discord.Embed(
        title=" Tus estadísticas del Casino",
        description=(
            f"Jugador: {interaction.user.mention}\n\n"
            f" Partidas: **{partidas}**\n"
            f" Victorias: **{victorias}**\n"
            f" Derrotas: **{derrotas}**\n"
            f" Porcentaje de victorias: **{porcentaje:.1f}%**"
        ),
        color=discord.Color.purple()
    )

    embed.add_field(
        name=" Economía",
        value=(
            f" Total apostado: **{apostado:,}**\n"
            f" Ganancias netas: **{ganancias:,}**"
        ),
        inline=False
    )

    embed.set_footer(
        text="Violet Casino  Estadísticas personales"
    )

    await interaction.response.send_message(
        embed=embed
    )



# =========================================================
#  INTERFAZ INTERACTIVA DEL CASINO
# =========================================================

class CasinoView(discord.ui.View):

    def __init__(self, owner_id):
        super().__init__(timeout=180)
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                " Este panel pertenece a otro jugador.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(
        label="Slots",
        emoji="💜",
        style=discord.ButtonStyle.primary,
        row=0
    )
    async def slots_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_message(
            " Para jugar Slots utiliza `/slots`.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Dados",
        emoji="💜",
        style=discord.ButtonStyle.primary,
        row=0
    )
    async def dados_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_message(
            " Para jugar Dados utiliza `/dados`.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Blackjack",
        emoji="💜",
        style=discord.ButtonStyle.primary,
        row=0
    )
    async def blackjack_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_message(
            " Para jugar Blackjack utiliza `/blackjack`.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Ruleta",
        emoji="💜",
        style=discord.ButtonStyle.primary,
        row=1
    )
    async def ruleta_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_message(
            " Para jugar Ruleta utiliza `/ruleta`.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Estadísticas",
        emoji="💜",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def stats_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        stats = await database.get_casino_stats(
            interaction.guild.id,
            interaction.user.id
        )

        partidas, victorias, derrotas, apostado, ganancias = stats

        porcentaje = (
            (victorias / partidas) * 100
            if partidas > 0 else 0
        )

        embed = discord.Embed(
            title=" Estadísticas de Casino",
            description=(
                f" Partidas: **{partidas}**\n"
                f" Victorias: **{victorias}**\n"
                f" Derrotas: **{derrotas}**\n"
                f" Victoria: **{porcentaje:.1f}%**\n\n"
                f" Apostado: **{apostado:,}**\n"
                f" Ganancias: **{ganancias:,}**"
            ),
            color=discord.Color.purple()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @discord.ui.button(
        label="Ranking",
        emoji="💜",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def ranking_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        ranking = await database.get_casino_ranking(
            interaction.guild.id,
            10
        )

        if not ranking:
            texto = " El ranking todavía está vacío."
        else:
            texto = ""

            for posicion, datos in enumerate(ranking, start=1):
                user_id, partidas, victorias, derrotas, apostado, ganancias = datos

                miembro = interaction.guild.get_member(user_id)
                nombre = (
                    miembro.display_name
                    if miembro else f"Usuario {user_id}"
                )

                texto += (
                    f"**{posicion}. {nombre}**  "
                    f" **{ganancias:,}** \n"
                )

        embed = discord.Embed(
            title=" Ranking del Casino",
            description=texto,
            color=discord.Color.purple()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @discord.ui.button(
        label="Saldo",
        emoji="💜",
        style=discord.ButtonStyle.success,
        row=2
    )
    async def saldo_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        user = await database.get_user(
            interaction.user.id,
            interaction.guild.id
        )

        saldo = user[2]

        embed = discord.Embed(
            title=" Tu saldo",
            description=f"Tienes **{saldo:,} **.",
            color=discord.Color.purple()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @discord.ui.button(
        label="Cerrar",
        emoji="💜",
        style=discord.ButtonStyle.danger,
        row=2
    )
    async def cerrar_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content=" **Violet Casino cerrado.**",
            embed=None,
            view=self
        )
        self.stop()

# =========================================================
#  VIOLET MARKET  INTERFAZ
# =========================================================

class VioletMarketModal(discord.ui.Modal, title=" Invertir en Violet Market"):

    cantidad = discord.ui.TextInput(
        label="Cantidad de monedas",
        placeholder="Ejemplo: 1000",
        required=True,
        min_length=1,
        max_length=15
    )

    async def on_submit(self, interaction: discord.Interaction):

        try:
            cantidad = int(self.cantidad.value)

        except ValueError:
            await interaction.response.send_message(
                " Debes introducir una cantidad válida.",
                ephemeral=True
            )
            return

        if cantidad <= 0:
            await interaction.response.send_message(
                " La cantidad debe ser mayor que 0.",
                ephemeral=True
            )
            return

        if interaction.guild is None:
            await interaction.response.send_message(
                " Este botón solo funciona en servidores.",
                ephemeral=True
            )
            return

        datos = await database.get_violet_market()

        if datos is None:
            await interaction.response.send_message(
                " El mercado todavía no está disponible.",
                ephemeral=True
            )
            return

        precio_actual = float(datos[0])

        usuario = await database.get_user(
            interaction.user.id,
            interaction.guild.id
        )

        if usuario is None:
            await interaction.response.send_message(
                " No tienes una cuenta económica creada.",
                ephemeral=True
            )
            return

        saldo = usuario[2]

        if saldo < cantidad:
            await interaction.response.send_message(
                f" No tienes suficientes monedas.\n\n"
                f" Saldo: **{saldo:,} **\n"
                f" Necesitas: **{cantidad:,} **",
                ephemeral=True
            )
            return

        await database.remove_balance(
            interaction.user.id,
            interaction.guild.id,
            cantidad
        )

        await database.create_violet_investment(
            interaction.user.id,
            interaction.guild.id,
            cantidad,
            precio_actual,
            __import__("datetime").datetime.now(
                __import__("datetime").UTC
            ).isoformat()
        )

        embed = discord.Embed(
            title=" Inversión realizada",
            description=(
                f"Has invertido **{cantidad:,} ** "
                "en Violet Market.\n\n"
                f" Precio VLC: **{precio_actual:,.2f}**\n"
                f" Capital invertido: **{cantidad:,} **\n\n"
                "Tu inversión cambiará de valor según el mercado."
            ),
            color=discord.Color.purple()
        )

        embed.set_footer(
            text="Violet Market  Inversión"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


class VioletMarketView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Invertir",
        emoji="💜",
        style=discord.ButtonStyle.success,
        custom_id="violet_market_invertir"
    )
    async def invertir_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_modal(
            VioletMarketModal()
        )

    @discord.ui.button(
        label="Mi inversión",
        emoji="💜",
        style=discord.ButtonStyle.primary,
        custom_id="violet_market_mi_inversion"
    )
    async def mi_inversion_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.guild is None:
            await interaction.response.send_message(
                " Este botón solo funciona en servidores.",
                ephemeral=True
            )
            return

        inversiones = await database.get_violet_investments(
            interaction.user.id,
            interaction.guild.id
        )

        if not inversiones:
            await interaction.response.send_message(
                " **Mi inversión**\n\n"
                "No tienes inversiones activas en Violet Market.",
                ephemeral=True
            )
            return

        datos = await database.get_violet_market()

        if datos is None:
            await interaction.response.send_message(
                " El mercado todavía no está disponible.",
                ephemeral=True
            )
            return

        precio_actual = float(datos[0])

        total_invertido = sum(
            float(inversion[1])
            for inversion in inversiones
        )

        valor_actual = 0

        for inversion in inversiones:
            amount = float(inversion[1])
            buy_price = float(inversion[2])

            if buy_price > 0:
                valor_actual += (
                    amount * precio_actual / buy_price
                )

        diferencia = valor_actual - total_invertido

        if diferencia > 0:
            tendencia = ""
        elif diferencia < 0:
            tendencia = ""
        else:
            tendencia = ""

        embed = discord.Embed(
            title=" Mi inversión",
            description=(
                f" **Inversionista:** {interaction.user.mention}\n\n"
                f" **Capital invertido:** "
                f"`{total_invertido:,.2f} `\n"
                f" **Valor actual:** "
                f"`{valor_actual:,.2f} `\n"
                f"{tendencia} **Resultado:** "
                f"`{diferencia:+,.2f} `"
            ),
            color=discord.Color.purple()
        )

        embed.add_field(
            name=" Precio VLC actual",
            value=f"`{precio_actual:,.2f}`",
            inline=True
        )

        embed.add_field(
            name=" Inversiones",
            value=f"`{len(inversiones)}`",
            inline=True
        )

        embed.set_footer(
            text="Violet Market  Mi inversión"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @discord.ui.button(
        label="Estadísticas",
        emoji="💜",
        style=discord.ButtonStyle.secondary,
        custom_id="violet_market_estadisticas"
    )
    async def estadisticas_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.guild is None:
            await interaction.response.send_message(
                " Este botón solo funciona en servidores.",
                ephemeral=True
            )
            return

        historial = await database.get_violet_investment_history(
            interaction.user.id,
            interaction.guild.id,
            100
        )

        if not historial:
            await interaction.response.send_message(
                " **Estadísticas del inversor**\n\n"
                "Todavía no tienes operaciones cerradas.",
                ephemeral=True
            )
            return

        total_operaciones = len(historial)
        ganancias = sum(
            float(registro[6])
            for registro in historial
            if float(registro[6]) > 0
        )
        perdidas = sum(
            float(registro[6])
            for registro in historial
            if float(registro[6]) < 0
        )

        resultado_total = ganancias + perdidas

        mejor = max(
            historial,
            key=lambda registro: float(registro[6])
        )

        peor = min(
            historial,
            key=lambda registro: float(registro[6])
        )

        rendimiento_promedio = sum(
            float(registro[7])
            for registro in historial
        ) / total_operaciones

        if resultado_total > 0:
            tendencia = ""
        elif resultado_total < 0:
            tendencia = ""
        else:
            tendencia = ""

        embed = discord.Embed(
            title=" Estadísticas del inversor",
            description=(
                f" **Inversor:** {interaction.user.mention}\n\n"
                f" **Operaciones cerradas:** "
                f"`{total_operaciones}`\n"
                f" **Ganancias:** "
                f"`+{ganancias:,.2f} `\n"
                f" **Pérdidas:** "
                f"`{perdidas:,.2f} `\n"
                f"{tendencia} **Resultado neto:** "
                f"`{resultado_total:+,.2f} `\n"
                f" **Rendimiento promedio:** "
                f"`{rendimiento_promedio:+.2f}%`"
            ),
            color=discord.Color.purple()
        )

        embed.add_field(
            name=" Mejor inversión",
            value=(
                f"#{mejor[1]}  "
                f"**{float(mejor[6]):+,.2f} **\n"
                f"Rendimiento: "
                f"**{float(mejor[7]):+.2f}%**"
            ),
            inline=True
        )

        embed.add_field(
            name=" Peor inversión",
            value=(
                f"#{peor[1]}  "
                f"**{float(peor[6]):+,.2f} **\n"
                f"Rendimiento: "
                f"**{float(peor[7]):+.2f}%**"
            ),
            inline=True
        )

        embed.set_footer(
            text="Violet Market  Estadísticas"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @discord.ui.button(
        label="Gráfico VLC",
        emoji="💜",
        style=discord.ButtonStyle.secondary,
        custom_id="violet_market_grafico"
    )
    async def grafico_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.guild is None:
            await interaction.response.send_message(
                " Este botón solo funciona en servidores.",
                ephemeral=True
            )
            return

        historial = await database.get_violet_market_history(20)

        if not historial:
            await interaction.response.send_message(
                " **Gráfico VLC**\n\n"
                "Todavía no hay datos suficientes del mercado.",
                ephemeral=True
            )
            return

        precios = [
            float(registro[0])
            for registro in historial
        ]

        precios.reverse()

        minimo = min(precios)
        maximo = max(precios)
        actual = precios[-1]
        inicial = precios[0]

        if inicial > 0:
            cambio_acumulado = (
                (actual - inicial) / inicial
            ) * 100
        else:
            cambio_acumulado = 0

        if cambio_acumulado > 0:
            tendencia = " Alcista"
        elif cambio_acumulado < 0:
            tendencia = " Bajista"
        else:
            tendencia = " Estable"

        niveles = ""
        barras = []

        if maximo == minimo:
            barras = [""] * len(precios)

        else:
            for precio in precios:

                nivel = int(
                    ((precio - minimo) /
                     (maximo - minimo)) * 7
                )

                nivel = max(0, min(7, nivel))

                barras.append(
                    niveles[nivel]
                )

        grafico = "".join(barras)

        embed = discord.Embed(
            title=" Evolución de VLC",
            description=(
                "ltimos movimientos registrados del mercado.\n\n"
                f"```{grafico}```\n"
                f" **Precio actual:** `{actual:,.2f}`\n"
                f" **Precio inicial:** `{inicial:,.2f}`\n"
                f" **Mínimo:** `{minimo:,.2f}`\n"
                f" **Máximo:** `{maximo:,.2f}`\n"
                f" **Tendencia:** **{tendencia}**\n"
                f" **Cambio acumulado:** "
                f"`{cambio_acumulado:+.2f}%`\n"
                f" **Registros:** `{len(precios)}`"
            ),
            color=discord.Color.purple()
        )

        embed.set_footer(
            text="Violet Market  Evolución VLC"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @discord.ui.button(
        label="Mercado",
        emoji="💜",
        style=discord.ButtonStyle.secondary,
        custom_id="violet_market_info"
    )
    async def mercado_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        datos = await database.get_violet_market()

        if datos is None:
            await interaction.response.send_message(
                " El mercado todavía no está disponible.",
                ephemeral=True
            )
            return

        (
            precio,
            precio_anterior,
            maximo,
            minimo,
            total_invertido,
            ultima_actualizacion
        ) = datos

        precio = float(precio)
        precio_anterior = float(precio_anterior)

        if precio_anterior > 0:
            cambio = (
                (precio - precio_anterior)
                / precio_anterior
            ) * 100
        else:
            cambio = 0

        if cambio > 0:
            tendencia = ""
        elif cambio < 0:
            tendencia = ""
        else:
            tendencia = ""

        embed = discord.Embed(
            title=" Violet Market",
            description=(
                "Mercado virtual de **Violet Coin (VLC)**\n\n"
                f"{tendencia} **Precio actual:** "
                f"`{precio:,.2f} VLC`\n"
                f" **Variación:** "
                f"`{cambio:+.2f}%`"
            ),
            color=discord.Color.purple()
        )

        embed.add_field(
            name=" Máximo histórico",
            value=f"`{float(maximo):,.2f} VLC`",
            inline=True
        )

        embed.add_field(
            name=" Mínimo histórico",
            value=f"`{float(minimo):,.2f} VLC`",
            inline=True
        )

        embed.add_field(
            name=" Total invertido",
            value=f"`{float(total_invertido):,.2f} `",
            inline=False
        )

        embed.set_footer(
            text="Violet Market  Información"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @discord.ui.button(
        label="Actualizar",
        emoji="💜",
        style=discord.ButtonStyle.secondary,
        custom_id="violet_market_actualizar"
    )
    async def actualizar_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.guild is None:
            await interaction.response.send_message(
                " Este botón solo funciona en servidores.",
                ephemeral=True
            )
            return

        await interaction.response.defer(
            ephemeral=True
        )

        await violet_market_publish(
            interaction.guild
        )

        await interaction.followup.send(
            " **Violet Market actualizado correctamente.**",
            ephemeral=True
        )


    @discord.ui.button(
        label="Historial",
        emoji="💜",
        style=discord.ButtonStyle.secondary,
        custom_id="violet_market_historial"
    )
    async def historial_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.guild is None:
            await interaction.response.send_message(
                " Este botón solo funciona en servidores.",
                ephemeral=True
            )
            return

        historial = await database.get_violet_investment_history(
            interaction.user.id,
            interaction.guild.id,
            10
        )

        if not historial:
            await interaction.response.send_message(
                " **Historial de inversiones**\n\n"
                "Todavía no tienes inversiones retiradas.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=" Historial de inversiones",
            description=(
                "Tus últimas operaciones cerradas "
                "en Violet Market."
            ),
            color=discord.Color.purple()
        )

        for registro in historial[:10]:

            (
                history_id,
                investment_id,
                amount,
                buy_price,
                sell_price,
                value,
                profit,
                return_percent,
                created_at,
                closed_at
            ) = registro

            if profit > 0:
                resultado = f" +{profit:,.2f} "
            elif profit < 0:
                resultado = f" {profit:,.2f} "
            else:
                resultado = " 0.00 "

            embed.add_field(
                name=f" Inversión #{investment_id}",
                value=(
                    f"Capital: `{amount:,.2f} `\n"
                    f"Compra: `{buy_price:,.2f}`  "
                    f"Venta: `{sell_price:,.2f}`\n"
                    f"Resultado: **{resultado}**\n"
                    f"Rendimiento: "
                    f"**{return_percent:+.2f}%**"
                ),
                inline=False
            )

        embed.set_footer(
            text="Violet Market  Historial"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @discord.ui.button(
        label="Retirar",
        emoji="💜",
        style=discord.ButtonStyle.danger,
        custom_id="violet_market_retirar"
    )
    async def retirar_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.guild is None:
            await interaction.response.send_message(
                " Este botón solo funciona en servidores.",
                ephemeral=True
            )
            return

        inversiones = await database.get_violet_investments(
            interaction.user.id,
            interaction.guild.id
        )

        if not inversiones:
            await interaction.response.send_message(
                " **Retirar inversión**\n\n"
                "No tienes inversiones activas para retirar.",
                ephemeral=True
            )
            return

        opciones = []

        for inversion in inversiones[:25]:
            investment_id = inversion[0]
            amount = float(inversion[1])
            buy_price = float(inversion[2])

            opciones.append(
                discord.SelectOption(
                    label=f"Inversión #{investment_id}",
                    description=f"Capital: {amount:,.2f} ",
                    value=str(investment_id),
                    emoji="💜"
                )
            )

        class RetirarInvestmentSelect(discord.ui.Select):

            def __init__(self):
                super().__init__(
                    placeholder="Selecciona la inversión que quieres retirar",
                    min_values=1,
                    max_values=1,
                    options=opciones
                )

            async def callback(
                self,
                select_interaction: discord.Interaction
            ):

                investment_id = int(self.values[0])

                inversion = await database.get_violet_investment(
                    investment_id,
                    select_interaction.user.id,
                    select_interaction.guild.id
                )

                if inversion is None:
                    await select_interaction.response.send_message(
                        " Esa inversión ya no existe.",
                        ephemeral=True
                    )
                    return

                datos = await database.get_violet_market()

                if datos is None:
                    await select_interaction.response.send_message(
                        " El mercado todavía no está disponible.",
                        ephemeral=True
                    )
                    return

                precio_actual = float(datos[0])

                amount = float(inversion[1])
                buy_price = float(inversion[2])

                if buy_price <= 0:
                    await select_interaction.response.send_message(
                        " No se puede calcular el valor de esta inversión.",
                        ephemeral=True
                    )
                    return

                valor_actual = (
                    amount * precio_actual / buy_price
                )

                ganancia = valor_actual - amount

                if amount > 0:
                    rendimiento = (
                        (ganancia / amount) * 100
                    )
                else:
                    rendimiento = 0

                from datetime import datetime, UTC

                await database.add_balance(
                    select_interaction.user.id,
                    select_interaction.guild.id,
                    valor_actual
                )

                await database.record_violet_investment_history(
                    investment_id,
                    select_interaction.user.id,
                    select_interaction.guild.id,
                    amount,
                    buy_price,
                    precio_actual,
                    valor_actual,
                    ganancia,
                    rendimiento,
                    inversion[3],
                    datetime.now(UTC).isoformat()
                )

                await database.delete_violet_investment(
                    investment_id,
                    select_interaction.user.id,
                    select_interaction.guild.id,
                    amount
                )

                if ganancia > 0:
                    resultado = f" Ganancia: **+{ganancia:,.2f} **"
                elif ganancia < 0:
                    resultado = f" Pérdida: **{ganancia:,.2f} **"
                else:
                    resultado = " Sin ganancias ni pérdidas."

                embed = discord.Embed(
                    title=" Inversión retirada",
                    description=(
                        f"Has retirado la inversión **#{investment_id}**.\n\n"
                        f" Capital original: **{amount:,.2f} **\n"
                        f" Valor actual: **{valor_actual:,.2f} **\n"
                        f"{resultado}\n\n"
                        "Las monedas fueron devueltas a tu saldo."
                    ),
                    color=discord.Color.purple()
                )

                embed.set_footer(
                    text="Violet Market  Retiro"
                )

                await select_interaction.response.edit_message(
                    embed=embed,
                    view=None
                )

        class RetirarInvestmentView(discord.ui.View):

            def __init__(self):
                super().__init__(timeout=60)
                self.add_item(RetirarInvestmentSelect())

        await interaction.response.send_message(
            " **Retirar inversión**\n\n"
            "Selecciona cuál de tus inversiones quieres retirar:",
            view=RetirarInvestmentView(),
            ephemeral=True
        )


# =========================================================
#  VIOLET MARKET  INVERTIR
# =========================================================
# =========================================================
#  VIOLET MARKET  INVERTIR
# =========================================================

@bot.tree.command(
    name="invertir",
    description="Invierte monedas en Violet Market"
)
@app_commands.describe(
    cantidad="Cantidad de monedas que quieres invertir"
)
async def invertir(
    interaction: discord.Interaction,
    cantidad: int
):

    if interaction.guild is None:
        await interaction.response.send_message(
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    if cantidad <= 0:
        await interaction.response.send_message(
            " La cantidad debe ser mayor que 0.",
            ephemeral=True
        )
        return

    datos = await database.get_violet_market()

    if datos is None:
        await interaction.response.send_message(
            " El mercado todavía no está disponible.",
            ephemeral=True
        )
        return

    precio_actual = float(datos[0])

    usuario = await database.get_user(
        interaction.user.id,
        interaction.guild.id
    )

    if usuario is None:
        await interaction.response.send_message(
            " No tienes una cuenta económica creada.",
            ephemeral=True
        )
        return

    saldo = usuario[2]

    if saldo < cantidad:
        await interaction.response.send_message(
            f" No tienes suficientes monedas.\n"
            f" Saldo: **{saldo:,} **\n"
            f" Necesitas: **{cantidad:,} **",
            ephemeral=True
        )
        return

    await database.remove_balance(
        interaction.user.id,
        interaction.guild.id,
        cantidad
    )

    await database.create_violet_investment(
        interaction.user.id,
        interaction.guild.id,
        cantidad,
        precio_actual,
        __import__("datetime").datetime.now(
            __import__("datetime").UTC
        ).isoformat()
    )

    embed = discord.Embed(
        title=" Inversión realizada",
        description=(
            f"Has invertido **{cantidad:,} ** en Violet Market.\n\n"
            f" Precio VLC: **{precio_actual:,.2f}**\n"
            f" Capital invertido: **{cantidad:,} **\n\n"
            "Tu inversión cambiará de valor según el mercado."
        ),
        color=discord.Color.purple()
    )

    embed.set_footer(
        text="Violet Market  Inversión"
    )

    await interaction.response.send_message(
        embed=embed
    )
# =========================================================
#  VIOLET MARKET  PANEL PRINCIPAL
# =========================================================

@bot.tree.command(
    name="mercado",
    description="Muestra el mercado de Violet Coin"
)
async def mercado(interaction: discord.Interaction):

    if interaction.guild is None:
        await interaction.response.send_message(
            " Este comando solo funciona en servidores.",
            ephemeral=True
        )
        return

    datos = await database.get_violet_market()

    if datos is None:
        await interaction.response.send_message(
            " El mercado todavía no está disponible.",
            ephemeral=True
        )
        return

    (
        precio,
        precio_anterior,
        maximo,
        minimo,
        total_invertido,
        ultima_actualizacion
    ) = datos

    if precio_anterior > 0:
        cambio = (
            (precio - precio_anterior)
            / precio_anterior
        ) * 100
    else:
        cambio = 0

    if cambio > 0:
        tendencia = ""
    elif cambio < 0:
        tendencia = ""
    else:
        tendencia = ""

    embed = discord.Embed(
        title=" Violet Market",
        description=(
            "Mercado virtual de **Violet Coin (VLC)**\n\n"
            f"{tendencia} **Precio actual:** `{precio:,.2f} VLC`\n"
            f" **Variación:** `{cambio:+.2f}%`"
        ),
        color=discord.Color.purple()
    )

    embed.add_field(
        name=" Máximo histórico",
        value=f"`{maximo:,.2f} VLC`",
        inline=True
    )

    embed.add_field(
        name=" Mínimo histórico",
        value=f"`{minimo:,.2f} VLC`",
        inline=True
    )

    embed.add_field(
        name=" Total invertido",
        value=f"`{total_invertido:,.2f} VLC`",
        inline=False
    )

    embed.add_field(
        name=" ❓ ¿Cómo funciona?",
        value=(
            "Invierte tus monedas en VLC y su valor cambiará "
            "automáticamente con el mercado.\n\n"
            " Si sube, puedes obtener ganancias.\n"
            " Si baja, puedes tener pérdidas."
        ),
        inline=False
    )

    embed.set_footer(
        text="Violet Market  Mercado virtual"
    )

    await interaction.response.send_message(
        embed=embed
    )


# =========================================================
# 🛡️ VIOLET SECURITY — COMANDO PRINCIPAL
# =========================================================


class VioletSecurityMainView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(label="Anti-Spam", emoji="✨", style=discord.ButtonStyle.primary, row=0)
    async def antispam(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "? **Anti-Spam**\n\nProtección contra mensajes repetitivos y flood.\n\nEstado: **ACTIVO**",
            ephemeral=True
        )

    @discord.ui.button(label="Anti-Raid", emoji="🛡️", style=discord.ButtonStyle.danger, row=0)
    async def antiraid(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            " **Anti-Raid**\n\nProtección contra entradas masivas de usuarios.\n\nEstado: **ACTIVO**",
            ephemeral=True
        )

    @discord.ui.button(label="Anti-Nuke", emoji="✨", style=discord.ButtonStyle.danger, row=0)
    async def antinuke(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "? **Anti-Nuke**\n\nProtección contra acciones destructivas del servidor.\n\nEstado: **ACTIVO**",
            ephemeral=True
        )

    @discord.ui.button(label="Enlaces", emoji="🔗", style=discord.ButtonStyle.secondary, row=1)
    async def enlaces(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            " **Protección de enlaces**\n\nSistema preparado para detectar enlaces sospechosos.",
            ephemeral=True
        )

    @discord.ui.button(label="Estadísticas", emoji="📊", style=discord.ButtonStyle.secondary, row=1)
    async def estadisticas(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            " **Estadísticas de seguridad**\n\n? Amenazas bloqueadas: 0\n Raids detectados: 0\n Enlaces bloqueados: 0\n? Alertas: 0",
            ephemeral=True
        )

    @discord.ui.button(label="Configuración", emoji="✨", style=discord.ButtonStyle.secondary, row=1)
    async def configuracion(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "? **Configuración de Violet Security**\n\nLos módulos de seguridad están preparados para configurarse desde este centro.",
            ephemeral=True
        )

    @discord.ui.button(label="Cuarentena", emoji="🚨", style=discord.ButtonStyle.secondary, row=2)
    async def cuarentena(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            " **Cuarentena**\n\nSistema de aislamiento de usuarios sospechosos.",
            ephemeral=True
        )

    @discord.ui.button(label="Registros", emoji="📋", style=discord.ButtonStyle.secondary, row=2)
    async def registros(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            " **Registros de seguridad**\n\nNo hay incidentes recientes registrados.",
            ephemeral=True
        )

    @discord.ui.button(label="Volver", emoji="✨", style=discord.ButtonStyle.secondary, row=3)
    async def volver(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            embed=violet_main_embed(),
            view=VioletMainView()
        )


@bot.tree.command(
    name="seguridad",
    description="Abre el Centro de Seguridad de Violet."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def seguridad(interaction: discord.Interaction):

    embed = discord.Embed(
        title="🛡️ VIOLET SECURITY",
        description=(
            "Centro de seguridad y protección de tu servidor.\n\n"
            "Selecciona una función para administrar la seguridad."
        ),
        color=discord.Color.purple()
    )

    embed.add_field(
        name="🛡️ Protección",
        value=(
            "Anti-Spam\n"
            "Anti-Raid\n"
            "Anti-Nuke\n"
            "Protección de enlaces"
        ),
        inline=False
    )

    embed.add_field(
        name=" Sistema",
        value="Estadísticas y registros de seguridad",
        inline=False
    )

    await interaction.response.send_message(
        embed=embed,
        view=VioletSecurityMainView(),
        ephemeral=True
    )


@seguridad.error
async def seguridad_error(
    interaction: discord.Interaction,
    error
):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message(
            " Necesitas el permiso **Gestionar servidor** para usar Violet Security.",
            ephemeral=True
        )
    else:
        print(f" Error /seguridad: {error}")


if __name__ == "__main__":
    if not TOKEN:
        print(" ERROR: No existe DISCORD_TOKEN.")
    else:
        print(" Iniciando Violet...")
        bot.run(TOKEN)


# VIOLET RANGOS - INICIALIZACIN
async def _violet_cargar_rangos():
    try:
        await instalar_rangos(bot, arbol, database)
    except Exception as e:
        print(f"? Error cargando rangos: {e}")






# ============================================================
# VIOLET CONFIGURACIÓN
# ============================================================

@arbol.command(
    name="config",
    description="Configura los sistemas de Violet en este servidor."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def config(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚙️ Configuración de Violet",
        description=(
            "Panel de configuración del servidor.\n\n"
            "??? **Moderación**\n"
            "? **Niveles y roles**\n"
            "💰 **Economía**\n"
            "💞 **Social**\n"
            "👋 **Bienvenida**\n"
            "🎫 **Soporte y tickets**"
        ),
        color=discord.Color.purple()
    )

    embed.set_footer(
        text="Violet . Configuración del servidor"
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


@config.error
async def config_error(
    interaction: discord.Interaction,
    error
):
    if isinstance(
        error,
        app_commands.errors.MissingPermissions
    ):
        mensaje = (
            "? Necesitas el permiso "
            "**Gestionar servidor** para usar este comando."
        )

        if interaction.response.is_done():
            await interaction.followup.send(
                mensaje,
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                mensaje,
                ephemeral=True
            )
        return

    if interaction.response.is_done():
        await interaction.followup.send(
            "? Ocurrió un error al abrir la configuración.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "? Ocurrió un error al abrir la configuración.",
            ephemeral=True
        )


# ============================================================
# VIOLET SOCIAL AVANZADO
# ============================================================

async def _social_avanzado(
    interaction: discord.Interaction,
    usuario: discord.Member,
    accion: str,
    emoji: str,
    texto: str
):
    if usuario.id == interaction.user.id:
        await interaction.response.send_message(
            f"{emoji} {interaction.user.mention} {texto} a s? mismo.",
            ephemeral=False
        )
        return

    await interaction.response.send_message(
        f"{emoji} {interaction.user.mention} **{texto}** a {usuario.mention}."
    )


@arbol.command(
    name="mimar",
    description="Mima a otro miembro del servidor."
)
@app_commands.describe(usuario="La persona que quieres mimar.")
async def mimar(
    interaction: discord.Interaction,
    usuario: discord.Member
):
    await _social_avanzado(
        interaction,
        usuario,
        "mimar",
        "??",
        "mima"
    )


@arbol.command(
    name="cosquillas",
    description="Hazle cosquillas a otro miembro."
)
@app_commands.describe(usuario="La persona a la que quieres hacer cosquillas.")
async def cosquillas(
    interaction: discord.Interaction,
    usuario: discord.Member
):
    await _social_avanzado(
        interaction,
        usuario,
        "cosquillas",
        "?",
        "hace cosquillas"
    )


@arbol.command(
    name="mirar",
    description="Mira cariñosamente a otro miembro."
)
@app_commands.describe(usuario="La persona que quieres mirar.")
async def mirar(
    interaction: discord.Interaction,
    usuario: discord.Member
):
    await _social_avanzado(
        interaction,
        usuario,
        "mirar",
        "??",
        "mira"
    )


@arbol.command(
    name="sonreir",
    description="Sonríele a otro miembro."
)
@app_commands.describe(usuario="La persona a la que quieres sonreír.")
async def sonreir(
    interaction: discord.Interaction,
    usuario: discord.Member
):
    await _social_avanzado(
        interaction,
        usuario,
        "sonreir",
        "??",
        "le sonríe"
    )


# ============================================================
# VIOLET PAREJAS
# ============================================================

@arbol.command(
    name="compatibilidad",
    description="Calcula la compatibilidad entre dos miembros."
)
@app_commands.describe(
    usuario="La persona con la que quieres comprobar la compatibilidad."
)
async def compatibilidad(
    interaction: discord.Interaction,
    usuario: discord.Member
):
    if usuario.id == interaction.user.id:
        porcentaje = 100
    else:
        base = "|".join(
            sorted([
                str(interaction.user.id),
                str(usuario.id)
            ])
        )
        numero = int(
            hashlib.sha256(base.encode()).hexdigest()[:8],
            16
        )
        porcentaje = numero % 101

    if porcentaje >= 90:
        estado = "💞 Compatibilidad legendaria"
    elif porcentaje >= 75:
        estado = "💞 Muy compatibles"
    elif porcentaje >= 50:
        estado = "💞 Buena conexión"
    elif porcentaje >= 25:
        estado = "💞 Compatibilidad moderada"
    else:
        estado = "💞 Necesitan conocerse mejor"

    embed = discord.Embed(
        title="💞 Compatibilidad Violet",
        description=(
            f"{interaction.user.mention} ? {usuario.mention}\n\n"
            f"**Compatibilidad: {porcentaje}%**\n"
            f"{estado}"
        ),
        color=discord.Color.pink()
    )

    await interaction.response.send_message(embed=embed)


@arbol.command(
    name="pareja",
    description="Declara o registra una pareja."
)
@app_commands.describe(
    usuario="La persona que quieres registrar como pareja."
)
async def pareja(
    interaction: discord.Interaction,
    usuario: discord.Member
):
    if usuario.id == interaction.user.id:
        await interaction.response.send_message(
            "? No puedes registrarte como tu propia pareja.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="💞 Nueva pareja",
        description=(
            f"?? {interaction.user.mention} y {usuario.mention} "
            "han sido registrados como pareja.\n\n"
            "Violet les desea mucha felicidad."
        ),
        color=discord.Color.purple()
    )

    await interaction.response.send_message(embed=embed)


@arbol.command(
    name="mipareja",
    description="Consulta tu pareja registrada."
)
async def mipareja(
    interaction: discord.Interaction
):
    embed = discord.Embed(
        title="💞 Mi pareja",
        description=(
            "Actualmente no tienes una pareja registrada.\n\n"
            "Usa `/pareja @usuario` para registrar una."
        ),
        color=discord.Color.purple()
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# ============================================================
# VIOLET BIENVENIDA Y DESPEDIDA
# ============================================================

@arbol.command(
    name="bienvenida",
    description="Configura el canal de bienvenida de Violet."
)
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(
    canal="Canal donde Violet enviar? las bienvenidas."
)
async def bienvenida(
    interaction: discord.Interaction,
    canal: discord.TextChannel
):
    embed = discord.Embed(
        title="👋 Bienvenida configurada",
        description=(
            f"Las nuevas personas serán recibidas en "
            f"{canal.mention}.\n\n"
            "?? Violet está lista para recibir a los nuevos miembros."
        ),
        color=discord.Color.purple()
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


@bienvenida.error
async def bienvenida_error(
    interaction: discord.Interaction,
    error
):
    if isinstance(
        error,
        app_commands.errors.MissingPermissions
    ):
        mensaje = (
            "? Necesitas el permiso "
            "**Gestionar servidor** para configurar la bienvenida."
        )
    else:
        mensaje = "? No se pudo configurar la bienvenida."

    if interaction.response.is_done():
        await interaction.followup.send(
            mensaje,
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            mensaje,
            ephemeral=True
        )


@arbol.command(
    name="despedida",
    description="Configura el canal de despedidas de Violet."
)
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(
    canal="Canal donde Violet enviar? las despedidas."
)
async def despedida(
    interaction: discord.Interaction,
    canal: discord.TextChannel
):
    embed = discord.Embed(
        title="👋 Despedida configurada",
        description=(
            f"Las salidas del servidor serán anunciadas en "
            f"{canal.mention}."
        ),
        color=discord.Color.purple()
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


@despedida.error
async def despedida_error(
    interaction: discord.Interaction,
    error
):
    if isinstance(
        error,
        app_commands.errors.MissingPermissions
    ):
        mensaje = (
            "? Necesitas el permiso "
            "**Gestionar servidor** para configurar la despedida."
        )
    else:
        mensaje = "? No se pudo configurar la despedida."

    if interaction.response.is_done():
        await interaction.followup.send(
            mensaje,
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            mensaje,
            ephemeral=True
        )


# ===== VIOLET FINAL SYSTEMS INTEGRATION =====
# Integración final de sistemas sin iniciar el bot.
# ============================================================

import time
from collections import defaultdict, deque

# ============================================================
# CONFIGURACIÓN INTERNA
# ============================================================

VIOLET_FINAL_VERSION = "1.0-FINAL"

_violet_spam_cache = defaultdict(lambda: deque(maxlen=8))
_violet_warn_cache = defaultdict(list)
_violet_pair_cache = {}
_violet_level_roles = {}
_violet_ticket_channels = {}
_violet_welcome_channels = {}
_violet_goodbye_channels = {}
_violet_achievements = defaultdict(set)
_violet_inventory_cache = defaultdict(dict)
_violet_pet_cache = {}
_violet_user_stats = defaultdict(
    lambda: {
        "messages": 0,
        "commands": 0,
        "interactions": 0,
        "wins": 0,
        "losses": 0,
    }
)

# ============================================================
# UTILIDADES
# ============================================================

def violet_get_member(guild, user_id):
    if guild is None:
        return None

    miembro = guild.get_member(user_id)

    if miembro is not None:
        return miembro

    return None


def violet_is_staff(member):
    if member is None:
        return False

    permisos = member.guild_permissions

    return (
        permisos.administrator
        or permisos.manage_guild
        or permisos.manage_messages
    )


async def violet_safe_send(interaction, content=None, embed=None, ephemeral=False):
    try:
        if interaction.response.is_done():
            return await interaction.followup.send(
                content=content,
                embed=embed,
                ephemeral=ephemeral
            )

        return await interaction.response.send_message(
            content=content,
            embed=embed,
            ephemeral=ephemeral
        )

    except discord.HTTPException:
        return None


# ============================================================
# ESTADÍSTICAS INTERNAS
# ============================================================

@bot.event
async def on_interaction(interaction):
    try:
        if interaction.type == discord.InteractionType.application_command:
            usuario = interaction.user

            datos = _violet_user_stats[usuario.id]
            datos["commands"] += 1

    except Exception:
        pass


# ============================================================
# SISTEMA DE LOGROS INTERNO
# ============================================================

VIOLET_ACHIEVEMENT_DATA = {
    "primer_mensaje": {
        "nombre": "Primer paso",
        "descripcion": "Envía tu primer mensaje con Violet activa.",
        "emoji": "🏆",
    },
    "primer_comando": {
        "nombre": "Explorador",
        "descripcion": "Utiliza tu primer comando de Violet.",
        "emoji": "🏆",
    },
    "social": {
        "nombre": "Corazón social",
        "descripcion": "Realiza una interacción social.",
        "emoji": "🏆",
    },
    "juego": {
        "nombre": "Jugador",
        "descripcion": "Participa en un juego.",
        "emoji": "🏆",
    },
    "economia": {
        "nombre": "Emprendedor",
        "descripcion": "Participa en la economía de Violet.",
        "emoji": "🏆",
    },
    "mascota": {
        "nombre": "Amigo animal",
        "descripcion": "Interactúa con una mascota.",
        "emoji": "🏆",
    },
}


def violet_unlock_achievement(user_id, achievement):
    if achievement not in VIOLET_ACHIEVEMENT_DATA:
        return False

    if achievement in _violet_achievements[user_id]:
        return False

    _violet_achievements[user_id].add(achievement)
    return True


# ============================================================
# SISTEMA DE INVENTARIO INTERNO
# ============================================================

def violet_add_item(user_id, item, cantidad=1):
    inventario = _violet_inventory_cache[user_id]

    inventario[item] = inventario.get(item, 0) + cantidad

    if inventario[item] <= 0:
        inventario.pop(item, None)


def violet_remove_item(user_id, item, cantidad=1):
    inventario = _violet_inventory_cache[user_id]

    actual = inventario.get(item, 0)

    if actual < cantidad:
        return False

    inventario[item] = actual - cantidad

    if inventario[item] <= 0:
        inventario.pop(item, None)

    return True


# ============================================================
# SISTEMA DE MASCOTAS
# ============================================================

def violet_create_pet(user_id, nombre="Violetita"):
    if user_id not in _violet_pet_cache:
        _violet_pet_cache[user_id] = {
            "nombre": nombre,
            "nivel": 1,
            "felicidad": 100,
            "energia": 100,
            "xp": 0,
        }

    return _violet_pet_cache[user_id]


def violet_pet_xp(user_id, cantidad):
    mascota = violet_create_pet(user_id)

    mascota["xp"] += cantidad

    while mascota["xp"] >= mascota["nivel"] * 100:
        mascota["xp"] -= mascota["nivel"] * 100
        mascota["nivel"] += 1

    return mascota


# ============================================================
# SISTEMA DE PAREJAS PERSISTENTE EN MEMORIA
# ============================================================

def violet_set_pair(user_a, user_b):
    _violet_pair_cache[user_a] = user_b
    _violet_pair_cache[user_b] = user_a


def violet_get_pair(user_id):
    return _violet_pair_cache.get(user_id)


# ============================================================
# SISTEMA DE ROLES POR NIVEL
# ÚNICO COMANDO NUEVO PARA RESPETAR EL LÍMITE DE DISCORD
# ============================================================

if not any(
    getattr(c, "name", None) == "rolnivel"
    for c in arbol.get_commands()
):

    @arbol.command(
        name="rolnivel",
        description="Configura los roles automáticos de nivel de Violet."
    )
    @app_commands.describe(
        accion="Acción que quieres realizar.",
        nivel="Nivel asociado al rol.",
        rol="Rol que Violet asignar?."
    )
    @app_commands.choices(
        accion=[
            app_commands.Choice(
                name="Configurar",
                value="configurar"
            ),
            app_commands.Choice(
                name="Listar",
                value="listar"
            ),
            app_commands.Choice(
                name="Eliminar",
                value="eliminar"
            ),
        ]
    )
    @app_commands.checks.has_permissions(manage_roles=True)
    async def rolnivel(
        interaction: discord.Interaction,
        accion: app_commands.Choice[str],
        nivel: int | None = None,
        rol: discord.Role | None = None
    ):

        accion_value = accion.value
        guild_id = interaction.guild.id

        if accion_value == "configurar":

            if nivel is None or rol is None:
                await interaction.response.send_message(
                    "? Para configurar debes indicar **nivel** y **rol**.",
                    ephemeral=True
                )
                return

            if rol >= interaction.guild.me.top_role:
                await interaction.response.send_message(
                    "? Violet no puede administrar ese rol porque está "
                    "por encima de su rol más alto.",
                    ephemeral=True
                )
                return

            if guild_id not in _violet_level_roles:
                _violet_level_roles[guild_id] = {}

            _violet_level_roles[guild_id][nivel] = rol.id

            await interaction.response.send_message(
                f"? El rol {rol.mention} quedó configurado para el "
                f"nivel **{nivel}**.",
                ephemeral=True
            )
            return

        if accion_value == "listar":

            configurados = _violet_level_roles.get(guild_id, {})

            if not configurados:
                await interaction.response.send_message(
                    "? No hay roles de nivel configurados.",
                    ephemeral=True
                )
                return

            lineas = []

            for nivel_config, rol_id in sorted(configurados.items()):
                rol_obj = interaction.guild.get_role(rol_id)

                if rol_obj:
                    lineas.append(
                        f"**Nivel {nivel_config}:** {rol_obj.mention}"
                    )

            embed = discord.Embed(
                title="? Roles de nivel",
                description="\n".join(lineas),
                color=discord.Color.purple()
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )
            return

        if accion_value == "eliminar":

            if nivel is None:
                await interaction.response.send_message(
                    "? Indica el nivel que quieres eliminar.",
                    ephemeral=True
                )
                return

            configurados = _violet_level_roles.get(guild_id, {})

            if nivel not in configurados:
                await interaction.response.send_message(
                    f"? No existe un rol configurado para el nivel {nivel}.",
                    ephemeral=True
                )
                return

            configurados.pop(nivel, None)

            await interaction.response.send_message(
                f"??? Se eliminó la configuración del nivel **{nivel}**.",
                ephemeral=True
            )


# ============================================================
# MEJORA DE PAREJAS
# ============================================================

def violet_register_pair(user_a, user_b):
    violet_set_pair(user_a, user_b)

    violet_unlock_achievement(user_a, "social")
    violet_unlock_achievement(user_b, "social")


# ============================================================
# SISTEMA DE TICKETS MEDIANTE BOTONES
# NO CREA OTRO SLASH COMMAND
# ============================================================

class VioletTicketView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Crear ticket",
        style=discord.ButtonStyle.primary,
        emoji="⚙️",
        custom_id="violet_ticket_create"
    )
    async def crear_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        guild = interaction.guild

        if guild is None:
            return

        existente = discord.utils.get(
            guild.text_channels,
            name=f"ticket-{interaction.user.id}"
        )

        if existente:
            await interaction.response.send_message(
                f"?? Ya tienes un ticket abierto: {existente.mention}",
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
        }

        if guild.me:
            overwrites[guild.me] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True
            )

        try:
            canal = await guild.create_text_channel(
                f"ticket-{interaction.user.id}",
                overwrites=overwrites,
                reason="Violet Ticket"
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "? Violet no tiene permisos para crear canales.",
                ephemeral=True
            )
            return

        _violet_ticket_channels[interaction.user.id] = canal.id

        embed = discord.Embed(
            title="🎫 Ticket creado",
            description=(
                f"{interaction.user.mention}, tu ticket está listo.\n\n"
                "Describe aqu? tu problema o solicitud."
            ),
            color=discord.Color.purple()
        )

        await canal.send(
            embed=embed,
            view=VioletCloseTicketView()
        )

        await interaction.response.send_message(
            f"?? Ticket creado: {canal.mention}",
            ephemeral=True
        )


class VioletCloseTicketView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Cerrar ticket",
        style=discord.ButtonStyle.danger,
        emoji="⚙️",
        custom_id="violet_ticket_close"
    )
    async def cerrar_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not violet_is_staff(interaction.user):
            if interaction.channel.name.startswith("ticket-"):
                try:
                    owner_id = int(
                        interaction.channel.name.replace(
                            "ticket-",
                            ""
                        )
                    )
                except ValueError:
                    owner_id = None

                if owner_id != interaction.user.id:
                    await interaction.response.send_message(
                        "? No tienes permiso para cerrar este ticket.",
                        ephemeral=True
                    )
                    return

        await interaction.response.send_message(
            "?? Cerrando ticket..."
        )

        await asyncio.sleep(1)

        try:
            await interaction.channel.delete(
                reason="Violet Ticket cerrado"
            )
        except discord.HTTPException:
            pass


# ============================================================
# PANEL DE SOPORTE INTERNO
# ============================================================

def violet_ticket_embed():
    return discord.Embed(
        title="🎫 Soporte de Violet",
        description=(
            "Necesitas ayuda?\n\n"
            "Pulsa **Crear ticket** para abrir un canal privado "
            "con tu solicitud."
        ),
        color=discord.Color.purple()
    )


# ============================================================
# PROTECCIÓN ANTI-SPAM
# ============================================================

@bot.listen("on_message")
async def violet_final_antispam(message):

    if message.author.bot:
        return

    if message.guild is None:
        return

    ahora = time.monotonic()

    cache = _violet_spam_cache[message.author.id]

    cache.append(ahora)

    recientes = [
        t for t in cache
        if ahora - t <= 5
    ]

    if len(recientes) < 7:
        return

    miembro = message.guild.get_member(message.author.id)

    if miembro is None:
        return

    if violet_is_staff(miembro):
        return

    try:
        await message.delete()
    except discord.HTTPException:
        pass

    _violet_spam_cache[message.author.id].clear()

    try:
        await message.channel.send(
            f"?? {message.author.mention}, reduce la velocidad de envío.",
            delete_after=5
        )
    except discord.HTTPException:
        pass


# ============================================================
# MENSAJES DE BIENVENIDA
# ============================================================

@bot.event
async def on_member_join(member):

    canal_id = _violet_welcome_channels.get(member.guild.id)

    canal = None

    if canal_id:
        canal = member.guild.get_channel(canal_id)

    if canal is None:
        for posible in member.guild.text_channels:
            permisos = posible.permissions_for(member.guild.me)

            if permisos.send_messages:
                canal = posible
                break

    if canal is None:
        return

    embed = discord.Embed(
        title="?? ?Violet ha llegado!",
        description=(
            f"Bienvenido/a {member.mention} a **{member.guild.name}**.\n\n"
            "Esperamos que disfrutes del servidor."
        ),
        color=discord.Color.purple()
    )

    embed.set_thumbnail(url=member.display_avatar.url)

    try:
        await canal.send(embed=embed)
    except discord.HTTPException:
        pass


# ============================================================
# MENSAJES DE DESPEDIDA
# ============================================================

@bot.event
async def on_member_remove(member):

    canal_id = _violet_goodbye_channels.get(member.guild.id)

    if not canal_id:
        return

    canal = member.guild.get_channel(canal_id)

    if canal is None:
        return

    embed = discord.Embed(
        title="👋 Hasta pronto",
        description=(
            f"**{member}** ha abandonado el servidor.\n\n"
            "Violet recordar? tu visita."
        ),
        color=discord.Color.purple()
    )

    try:
        await canal.send(embed=embed)
    except discord.HTTPException:
        pass


# ============================================================
# SISTEMA DE MENSAJES / XP / LOGROS
# ============================================================

@bot.listen("on_message")
async def violet_final_message_system(message):

    if message.author.bot:
        return

    if message.guild is None:
        return

    usuario_id = message.author.id

    datos = _violet_user_stats[usuario_id]

    datos["messages"] += 1

    violet_unlock_achievement(
        usuario_id,
        "primer_mensaje"
    )

    if datos["messages"] >= 10:
        violet_unlock_achievement(
            usuario_id,
            "social"
        )


# ============================================================
# CARGA DE VISTAS PERSISTENTES
# ============================================================

async def violet_final_prepare_views():

    if getattr(bot, "_violet_final_views_loaded", False):
        return

    try:
        bot.add_view(VioletTicketView())
        bot.add_view(VioletCloseTicketView())

        bot._violet_final_views_loaded = True

        print("?? Vistas de tickets cargadas.")

    except Exception as error:
        print(
            f"? Error cargando vistas finales: {error}"
        )


# ============================================================
# INTEGRACIÓN EN ON_READY
# ============================================================

_violet_original_on_ready = on_ready


@bot.event
async def on_ready():

    if not getattr(bot, "_violet_final_ready_done", False):

        bot._violet_final_ready_done = True

        try:
            await violet_final_prepare_views()
        except Exception as error:
            print(
                f"? Error preparando sistemas finales: {error}"
            )

        print(
            f"?? Sistemas finales Violet {VIOLET_FINAL_VERSION} preparados."
        )

    try:
        await _violet_original_on_ready()
    except Exception as error:
        print(
            f"? Error en el arranque original de Violet: {error}"
        )


# ============================================================
# ESTADO FINAL
# ============================================================

print(
    "?? Violet Final Systems Integration cargada."
)

# ===== FIN VIOLET FINAL SYSTEMS INTEGRATION =====
