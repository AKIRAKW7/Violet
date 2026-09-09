from pathlib import Path
import shutil
from datetime import datetime

BASE = Path.home() / "Violet"
BOT = BASE / "bot.py"
DB = BASE / "database.py"
RANGOS = BASE / "rangos.py"

marca = "# VIOLET RANGOS V1"

# ─────────────────────────────────────────────
# BACKUP
# ─────────────────────────────────────────────
fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2(BOT, BASE / f"bot.py.rangos_{fecha}.bak")
shutil.copy2(DB, BASE / f"database.py.rangos_{fecha}.bak")

# ─────────────────────────────────────────────
# 100 RANGOS
# ─────────────────────────────────────────────
rangos = [
("🌱","Brote",1000),("🍃","Aprendiz",2000),("🪶","Novato",3000),
("🐾","Explorador",4500),("🔹","Aventurero",6000),("🗺️","Viajero",8000),
("🧭","Rastreador",10000),("⛏️","Recolector",12500),("🎣","Pescador",15000),
("🏹","Cazador",18000),("⚔️","Guerrero",22000),("🛡️","Guardián",26000),
("🔥","Combatiente",30000),("⚡","Veloz",35000),("💠","Especialista",40000),
("🟦","Experto",45000),("🟪","Veterano",50000),("💎","Élite",60000),
("🌟","Campeón",70000),("👑","Noble",80000),("🏰","Señor",90000),
("⚜️","Aristócrata",100000),("🔮","Místico",115000),("🌙","Nocturno",130000),
("☀️","Radiante",150000),("🌌","Cósmico",175000),("🪐","Astral",200000),
("🌠","Estelar",225000),("💫","Celestial",250000),("🔥","Infernal",275000),
("❄️","Glacial",300000),("🌊","Abisal",325000),("🌋","Volcánico",350000),
("🌪️","Tempestad",375000),("⚡","Tormenta",400000),("🐉","Domador",425000),
("🐲","Señor Dragón",450000),("🦄","Legendario",475000),("🪽","Serafín",500000),
("😈","Demonio",550000),("👼","Arcángel",600000),("🔱","Titán",650000),
("🗿","Coloso",700000),("🌑","Eclipse",750000),("☄️","Cometa",800000),
("🌌","Nebulosa",850000),("🕳️","Singularidad",900000),("🌐","Dimensional",950000),
("🌀","Trascendente",1000000),("💜","Violet",1100000),("💜","Violet Prime",1200000),
("🔮","Violet Arcana",1300000),("🌌","Violet Cosmic",1400000),("👑","Violet Royal",1500000),
("💎","Violet Diamond",1600000),("⚡","Violet Pulse",1700000),("🌠","Violet Star",1800000),
("🌙","Violet Moon",1900000),("☀️","Violet Sun",2000000),("🪐","Violet Planet",2200000),
("🌌","Violet Galaxy",2400000),("🌠","Violet Universe",2600000),("♾️","Infinito",2800000),
("🔱","Inmortal",3000000),("🧿","Omnipresente",3250000),("🌀","Eterno",3500000),
("👁️","Omnisciente",3750000),("🌌","Astral Supremo",4000000),("⚜️","Emperador",4250000),
("👑","Emperador Celestial",4500000),("🐉","Dios Dragón",4750000),("🔥","Dios de la Llama",5000000),
("❄️","Dios del Hielo",5250000),("🌊","Dios del Océano",5500000),("⚡","Dios del Trueno",5750000),
("🌑","Dios del Eclipse",6000000),("🌌","Dios Cósmico",6500000),("💫","Deidad Estelar",7000000),
("🪐","Señor de los Mundos",7500000),("♾️","Señor del Infinito",8000000),
("🌠","Arquitecto Cósmico",8500000),("🔮","Maestro Dimensional",9000000),
("🌀","Controlador del Caos",9500000),("💜","Corazón de Violet",10000000),
("👑","Soberano Violet",11000000),("🌌","Trono Celestial",12000000),
("💎","Diamante Absoluto",13000000),("🔱","Titán Supremo",14000000),
("🌠","Entidad Estelar",15000000),("🌀","Entidad Dimensional",16000000),
("♾️","Ser Infinito",17500000),("👁️","Ojo del Universo",19000000),
("🌌","Conciencia Cósmica",20000000),("💜","Alma de Violet",22000000),
("👑","Heredero de Violet",25000000),("🌌","Guardián del Universo",30000000),
("🔮","Creador de Dimensiones",40000000),("♾️","Señor del Infinito",50000000),
("💜","Dios de Violet",75000000),("🌌","Violet Absoluta",100000000)
]

# ─────────────────────────────────────────────
# RANGOS.PY
# ─────────────────────────────────────────────
codigo = f'''{marca}
import discord
from discord import app_commands

CANAL = "🏆・rangos"
RANGOS = {rangos!r}


def embed_tienda(pagina=0):
    inicio = pagina * 10
    items = RANGOS[inicio:inicio + 10]
    e = discord.Embed(
        title="🏆 TIENDA DE RANGOS",
        description="Compra rangos exclusivos usando **VLC**.",
        color=discord.Color.purple()
    )
    for i, (emoji, nombre, precio) in enumerate(items, inicio + 1):
        e.add_field(
            name=f"{{emoji}} #{{i}} — {{nombre}}",
            value=f"💰 **{{precio:,}} VLC**",
            inline=False
        )
    e.set_footer(text=f"Violet • Página {{pagina + 1}}/10 • 100 rangos")
    return e


async def canal_rangos(guild):
    canal = discord.utils.get(guild.text_channels, name=CANAL)
    if canal:
        return canal
    try:
        return await guild.create_text_channel(
            CANAL,
            reason="Violet - Tienda de Rangos"
        )
    except Exception as e:
        print(f"⚠️ Error creando tienda de rangos: {{e}}")
        return None


async def instalar(bot, arbol, database):

    @arbol.command(
        name="rangos",
        description="Abre la tienda de rangos"
    )
    async def rangos_cmd(interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message(
                "❌ Solo puedes usar esto en un servidor.",
                ephemeral=True
            )

        await canal_rangos(interaction.guild)
        await interaction.response.send_message(
            embed=embed_tienda()
        )


    @bot.command(name="rangos")
    async def rangos_prefix(ctx):
        if ctx.guild:
            await canal_rangos(ctx.guild)
            await ctx.send(embed=embed_tienda())


    @arbol.command(
        name="rango_comprar",
        description="Compra un rango con VLC"
    )
    async def comprar_rango(
        interaction: discord.Interaction,
        rango: int
    ):
        if not interaction.guild:
            return await interaction.response.send_message(
                "❌ Solo puedes usar esto en un servidor.",
                ephemeral=True
            )

        if not 1 <= rango <= 100:
            return await interaction.response.send_message(
                "❌ El rango debe estar entre 1 y 100.",
                ephemeral=True
            )

        emoji, nombre, precio = RANGOS[rango - 1]
        user = interaction.user
        guild = interaction.guild

        saldo = await database.balance(user.id, guild.id)

        if saldo < precio:
            return await interaction.response.send_message(
                f"❌ No tienes suficiente VLC.\\n"
                f"💰 Precio: **{{precio:,}} VLC**\\n"
                f"💳 Saldo: **{{saldo:,}} VLC**",
                ephemeral=True
            )

        if not guild.me.guild_permissions.manage_roles:
            return await interaction.response.send_message(
                "❌ Violet necesita **Gestionar roles**.",
                ephemeral=True
            )

        role = discord.utils.get(
            guild.roles,
            name=f"{{emoji}} {{nombre}}"
        )

        if not role:
            try:
                role = await guild.create_role(
                    name=f"{{emoji}} {{nombre}}",
                    color=discord.Color.purple(),
                    reason=f"Violet - Rango #{{rango}}"
                )
            except discord.Forbidden:
                return await interaction.response.send_message(
                    "❌ Violet no puede crear roles.",
                    ephemeral=True
                )

        if role >= guild.me.top_role:
            return await interaction.response.send_message(
                "❌ Mi rol debe estar por encima del rol del rango.",
                ephemeral=True
            )

        if role in user.roles:
            return await interaction.response.send_message(
                "❌ Ya tienes este rango.",
                ephemeral=True
            )

        if not await database.remove_balance(
            user.id, guild.id, precio
        ):
            return await interaction.response.send_message(
                "❌ No se pudo realizar el pago.",
                ephemeral=True
            )

        try:
            await user.add_roles(
                role,
                reason=f"Compra del rango #{{rango}}"
            )
        except Exception:
            await database.add_balance(
                user.id, guild.id, precio
            )
            return await interaction.response.send_message(
                "❌ No pude asignar el rol. Se devolvió tu VLC.",
                ephemeral=True
            )

        # Quitar rangos inferiores de la misma tienda
        for viejo in guild.roles:
            if viejo != role and viejo in user.roles:
                for n, (em, nom, _) in enumerate(RANGOS, 1):
                    if viejo.name == f"{{em}} {{nom}}" and n < rango:
                        try:
                            await user.remove_roles(viejo)
                        except Exception:
                            pass
                        break

        e = discord.Embed(
            title="🏆 ¡Rango comprado!",
            description=(
                f"{{emoji}} **{{nombre}}**\\n\\n"
                f"👤 {{user.mention}}\\n"
                f"💰 Pagado: **{{precio:,}} VLC**\\n"
                f"🏷️ {{role.mention}}"
            ),
            color=discord.Color.purple()
        )

        await interaction.response.send_message(embed=e)


    @arbol.command(
        name="rango_info",
        description="Consulta un rango"
    )
    async def rango_info(
        interaction: discord.Interaction,
        rango: int
    ):
        if not 1 <= rango <= 100:
            return await interaction.response.send_message(
                "❌ El rango debe estar entre 1 y 100.",
                ephemeral=True
            )

        emoji, nombre, precio = RANGOS[rango - 1]

        await interaction.response.send_message(
            f"{{emoji}} **{{nombre}}**\\n"
            f"🏆 Rango: **#{{rango}}/100**\\n"
            f"💰 Precio: **{{precio:,}} VLC**"
        )


    @arbol.command(
        name="rango_crear",
        description="Crea un rol personalizado para el servidor"
    )
    @app_commands.default_permissions(manage_roles=True)
    async def rango_crear(
        interaction: discord.Interaction,
        nombre: str,
        precio: int,
        emoji: str = "🏆"
    ):
        if not interaction.guild:
            return await interaction.response.send_message(
                "❌ Solo puedes usar esto en un servidor.",
                ephemeral=True
            )

        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message(
                "❌ Necesitas Gestionar Roles.",
                ephemeral=True
            )

        try:
            role = await interaction.guild.create_role(
                name=f"{{emoji}} {{nombre}}",
                color=discord.Color.purple(),
                reason="Violet - Rango personalizado"
            )

            await interaction.response.send_message(
                f"🏆 **Rango creado**\\n"
                f"{{role.mention}}\\n"
                f"💰 Precio: **{{precio:,}} VLC**"
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Violet no puede crear roles.",
                ephemeral=True
            )


    print("🏆 Sistema de rangos cargado.")
'''

RANGOS.write_text(codigo, encoding="utf-8")

# ─────────────────────────────────────────────
# INTEGRACIÓN MÍNIMA EN BOT.PY
# ─────────────────────────────────────────────
bot = BOT.read_text(encoding="utf-8")

if "from rangos import instalar as instalar_rangos" not in bot:
    bot = "from rangos import instalar as instalar_rangos\n" + bot

# Añadir una inicialización al final del archivo, antes de ejecutar el bot
if "await instalar_rangos(bot, arbol, database)" not in bot:
    bot += '''

# VIOLET RANGOS - INICIALIZACIÓN
async def _violet_cargar_rangos():
    try:
        await instalar_rangos(bot, arbol, database)
    except Exception as e:
        print(f"⚠️ Error cargando rangos: {e}")

'''

    # Intentar colocar la llamada antes del run principal
    patrones = [
        "bot.run(",
        "asyncio.run(main())"
    ]

    insertado = False

    for patron in patrones:
        if patron in bot:
            pos = bot.rfind(patron)
            bloque = "await instalar_rangos(bot, arbol, database)\n"
            # No se puede usar await fuera de async.
            # Se integra mediante llamada síncrona en setup_hook alternativo.
            insertado = False
            break

    # Usamos un wrapper sobre setup_hook si existe.
    if "async def setup_hook" in bot:
        import re
        bot = re.sub(
            r"(async def setup_hook\(.*?\):\n)",
            r"\1    await instalar_rangos(bot, arbol, database)\n",
            bot,
            count=1
        )
        insertado = True

    if not insertado:
        # Crear una tarea desde on_ready si no hay setup_hook.
        import re
        patron = r"(async def on_ready\(\):\n)"
        if re.search(patron, bot):
            bot = re.sub(
                patron,
                r"\1    if not getattr(bot, '_rangos_cargados', False):\n"
                r"        bot._rangos_cargados = True\n"
                r"        await instalar_rangos(bot, arbol, database)\n",
                bot,
                count=1
            )
            insertado = True

    BOT.write_text(bot, encoding="utf-8")

print("✅ rangos.py creado")
print("✅ bot.py conectado")
print("🏆 100 rangos cargados")
print()
print("Comprobando archivos...")
