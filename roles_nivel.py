import discord
from discord import app_commands
from discord.ext import commands
import json
import os

ARCHIVO = "roles_nivel.json"


def cargar():
    if not os.path.exists(ARCHIVO):
        return {}
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def guardar(datos):
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=4)


class RolesNivel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="rolnivel",
        description="Configura un rol automático para un nivel."
    )
    @app_commands.describe(
        nivel="Nivel que desbloqueará el rol.",
        rol="Rol que recibirá el usuario."
    )
    @app_commands.checks.has_permissions(manage_roles=True)
    async def rolnivel(
        self,
        interaction: discord.Interaction,
        nivel: app_commands.Range[int, 1, 1000],
        rol: discord.Role
    ):
        if rol >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                "No puedo administrar ese rol porque está por encima de mi rol.",
                ephemeral=True
            )
            return

        datos = cargar()
        servidor = datos.setdefault(str(interaction.guild.id), {})
        servidor[str(nivel)] = rol.id
        guardar(datos)

        await interaction.response.send_message(
            f"✅ El rol {rol.mention} se asignará automáticamente al alcanzar "
            f"el **nivel {nivel}**."
        )

    @app_commands.command(
        name="rolesnivel",
        description="Muestra los roles configurados por nivel."
    )
    async def rolesnivel(self, interaction: discord.Interaction):
        datos = cargar()
        servidor = datos.get(str(interaction.guild.id), {})

        if not servidor:
            await interaction.response.send_message(
                "No hay roles automáticos configurados."
            )
            return

        lineas = []

        for nivel, rol_id in sorted(
            servidor.items(),
            key=lambda x: int(x[0])
        ):
            rol = interaction.guild.get_role(int(rol_id))

            if rol:
                lineas.append(
                    f"**Nivel {nivel}:** {rol.mention}"
                )
            else:
                lineas.append(
                    f"**Nivel {nivel}:** rol eliminado"
                )

        embed = discord.Embed(
            title="⭐ Roles por nivel",
            description="\n".join(lineas),
            color=discord.Color.purple()
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="eliminarrolnivel",
        description="Elimina un rol automático de nivel."
    )
    @app_commands.describe(
        nivel="Nivel cuyo rol automático quieres eliminar."
    )
    @app_commands.checks.has_permissions(manage_roles=True)
    async def eliminarrolnivel(
        self,
        interaction: discord.Interaction,
        nivel: app_commands.Range[int, 1, 1000]
    ):
        datos = cargar()
        servidor = datos.get(str(interaction.guild.id), {})

        if str(nivel) not in servidor:
            await interaction.response.send_message(
                f"No existe un rol configurado para el nivel {nivel}.",
                ephemeral=True
            )
            return

        del servidor[str(nivel)]
        guardar(datos)

        await interaction.response.send_message(
            f"✅ Rol automático del nivel **{nivel}** eliminado."
        )


async def setup(bot):
    await bot.add_cog(RolesNivel(bot))
