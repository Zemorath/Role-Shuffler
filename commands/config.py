import discord
from discord.ext import commands
from discord import app_commands
from utils.permissions import ensure_user_permissions, ensure_bot_can_manage_role, PermissionCheckError
from database import Database

class RoleConfigCommands(commands.Cog):
    def __init__(self, bot: commands.Bot, database: Database):
        self.bot = bot
        self.db = database

    @app_commands.command(name="config-roles", description="Manage shuffleable roles for this server")
    @app_commands.describe(
        action="Choose what to do with shuffleable roles",
        role="The role to add or remove (not needed for 'list')"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="add", value="add"),
        app_commands.Choice(name="remove", value="remove"),
        app_commands.Choice(name="list", value="list")
    ])
    async def config_roles(self, interaction: discord.Interaction, action: str, role: discord.Role = None):
        """Configure which roles can be shuffled in this server."""
        
        try:
            # Check user permissions for all actions
            await ensure_user_permissions(interaction, "manage_roles")
            
            if action == "add":
                await self._add_role(interaction, role)
            elif action == "remove":
                await self._remove_role(interaction, role)
            elif action == "list":
                await self._list_roles(interaction)
                
        except PermissionCheckError as e:
            await interaction.response.send_message(str(e), ephemeral=True)
        except Exception as e:
            print(f"Error in config_roles command: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while processing your request. Please try again.",
                ephemeral=True
            )

    async def _add_role(self, interaction: discord.Interaction, role: discord.Role):
        """Add a role to the shuffleable roles list."""
        if not role:
            await interaction.response.send_message(
                "❌ You must specify a role to add. Use `/config-roles add @role`",
                ephemeral=True
            )
            return

        # Check if bot can manage this role
        await ensure_bot_can_manage_role(interaction, role)

        # Ensure server is in database
        await self.db.add_server(interaction.guild.id, interaction.guild.name)

        # Add role to database
        success = await self.db.add_shuffleable_role(
            interaction.guild.id,
            role.id,
            role.name,
            interaction.user.id
        )

        if success:
            embed = discord.Embed(
                title="✅ Role Added",
                description=f"**{role.name}** has been added to the shuffleable roles list.",
                color=discord.Color.green()
            )
            embed.add_field(
                name="What this means:",
                value="Users with this role can now be included in role shuffles.",
                inline=False
            )
        else:
            embed = discord.Embed(
                title="⚠️ Role Already Added",
                description=f"**{role.name}** is already in the shuffleable roles list.",
                color=discord.Color.yellow()
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _remove_role(self, interaction: discord.Interaction, role: discord.Role):
        """Remove a role from the shuffleable roles list."""
        if not role:
            await interaction.response.send_message(
                "❌ You must specify a role to remove. Use `/config-roles remove @role`",
                ephemeral=True
            )
            return

        # Remove role from database
        success = await self.db.remove_shuffleable_role(interaction.guild.id, role.id)

        if success:
            embed = discord.Embed(
                title="✅ Role Removed",
                description=f"**{role.name}** has been removed from the shuffleable roles list.",
                color=discord.Color.green()
            )
            embed.add_field(
                name="What this means:",
                value="Users with this role will no longer be included in role shuffles.",
                inline=False
            )
        else:
            embed = discord.Embed(
                title="⚠️ Role Not Found",
                description=f"**{role.name}** was not in the shuffleable roles list.",
                color=discord.Color.yellow()
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _list_roles(self, interaction: discord.Interaction):
        """List all shuffleable roles for this server."""
        roles_data = await self.db.get_shuffleable_roles(interaction.guild.id)

        if not roles_data:
            embed = discord.Embed(
                title="📝 Shuffleable Roles",
                description="No shuffleable roles have been configured for this server.",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="How to add roles:",
                value="Use `/config-roles add @role` to add roles to the shuffle pool.",
                inline=False
            )
        else:
            embed = discord.Embed(
                title="📝 Shuffleable Roles",
                description=f"There are **{len(roles_data)}** roles configured for shuffling:",
                color=discord.Color.blue()
            )

            # Group roles into a formatted list
            role_list = []
            for role_data in roles_data:
                role = interaction.guild.get_role(role_data['role_id'])
                if role:  # Role still exists
                    member_count = len(role.members)
                    role_list.append(f"• **{role.name}** ({member_count} members)")
                else:  # Role was deleted
                    role_list.append(f"• ~~{role_data['role_name']}~~ (deleted)")

            # Split into chunks if too long
            role_text = "\n".join(role_list)
            if len(role_text) > 1000:
                # Split into multiple fields if too long
                chunks = [role_list[i:i+10] for i in range(0, len(role_list), 10)]
                for i, chunk in enumerate(chunks):
                    field_name = "Roles:" if i == 0 else f"Roles (continued {i+1}):"
                    embed.add_field(
                        name=field_name,
                        value="\n".join(chunk),
                        inline=False
                    )
            else:
                embed.add_field(
                    name="Roles:",
                    value=role_text,
                    inline=False
                )

            embed.add_field(
                name="Usage:",
                value="Use `/shuffle` to randomly redistribute these roles among users.",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot, database: Database):
    """Setup function to add this cog to the bot."""
    await bot.add_cog(RoleConfigCommands(bot, database))