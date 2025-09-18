import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from datetime import datetime, timedelta
from utils.permissions import ensure_user_permissions, get_manageable_roles, PermissionCheckError
from database import Database

class ShuffleConfirmView(discord.ui.View):
    """View for shuffle confirmation with Yes/No buttons."""
    
    def __init__(self, cog, interaction: discord.Interaction, roles_to_shuffle: list):
        super().__init__(timeout=300.0)  # 5 minute timeout
        self.cog = cog
        self.original_interaction = interaction
        self.roles_to_shuffle = roles_to_shuffle
        self.confirmed = False

    @discord.ui.button(label="✅ Yes, Shuffle Roles", style=discord.ButtonStyle.green)
    async def confirm_shuffle(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle the confirmation button press."""
        if interaction.user.id != self.original_interaction.user.id:
            await interaction.response.send_message(
                "❌ Only the person who initiated the shuffle can confirm it.",
                ephemeral=True
            )
            return

        self.confirmed = True
        await interaction.response.edit_message(
            content="🎲 **Shuffling roles...** Please wait...",
            embed=None,
            view=None
        )
        
        # Perform the actual shuffle
        await self.cog.perform_shuffle(interaction, self.roles_to_shuffle)
        self.stop()

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.red)
    async def cancel_shuffle(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle the cancel button press."""
        if interaction.user.id != self.original_interaction.user.id:
            await interaction.response.send_message(
                "❌ Only the person who initiated the shuffle can cancel it.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="❌ Shuffle Cancelled",
            description="The role shuffle has been cancelled.",
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

    async def on_timeout(self):
        """Handle timeout - disable buttons and show timeout message."""
        if not self.confirmed:
            embed = discord.Embed(
                title="⏰ Shuffle Timed Out",
                description="The shuffle confirmation timed out after 5 minutes.",
                color=discord.Color.orange()
            )
            try:
                await self.original_interaction.edit_original_response(embed=embed, view=None)
            except discord.NotFound:
                pass  # Message was deleted

class ShuffleCommands(commands.Cog):
    def __init__(self, bot: commands.Bot, database: Database):
        self.bot = bot
        self.db = database

    @app_commands.command(name="shuffle", description="Randomly shuffle users between configured roles")
    async def shuffle_roles(self, interaction: discord.Interaction):
        """Main shuffle command that redistributes users among configured roles."""
        
        try:
            # Check user permissions
            await ensure_user_permissions(interaction, "shuffle")
            
            # Check cooldown
            cooldown_expires = await self.db.check_shuffle_cooldown(interaction.guild.id)
            if cooldown_expires:
                embed = discord.Embed(
                    title="⏰ Shuffle on Cooldown",
                    description=f"Please wait before shuffling again.",
                    color=discord.Color.orange()
                )
                embed.add_field(
                    name="Cooldown expires:",
                    value=f"<t:{int(cooldown_expires.timestamp())}:R>",
                    inline=False
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Get shuffleable roles from database
            roles_data = await self.db.get_shuffleable_roles(interaction.guild.id)
            
            if not roles_data:
                embed = discord.Embed(
                    title="❌ No Shuffleable Roles",
                    description="No roles have been configured for shuffling in this server.",
                    color=discord.Color.red()
                )
                embed.add_field(
                    name="How to add roles:",
                    value="Use `/config-roles add @role` to add roles to the shuffle pool.",
                    inline=False
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Get actual role objects and filter by what bot can manage
            roles_to_shuffle = []
            users_to_shuffle = []
            total_users = 0

            bot_member = interaction.guild.get_member(self.bot.user.id)
            
            for role_data in roles_data:
                role = interaction.guild.get_role(role_data['role_id'])
                if role and role in get_manageable_roles(bot_member, [role]):
                    if len(role.members) > 0:  # Only include roles with members
                        roles_to_shuffle.append(role)
                        users_to_shuffle.extend(role.members)
                        total_users += len(role.members)

            if not roles_to_shuffle:
                embed = discord.Embed(
                    title="❌ No Valid Roles",
                    description="No shuffleable roles found with members that I can manage.",
                    color=discord.Color.red()
                )
                embed.add_field(
                    name="Possible issues:",
                    value="• Roles are empty (no members)\n• Roles are above my highest role\n• I don't have Manage Roles permission",
                    inline=False
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if len(roles_to_shuffle) < 2:
                embed = discord.Embed(
                    title="❌ Need More Roles",
                    description="At least 2 roles with members are needed for shuffling.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Create confirmation embed
            embed = discord.Embed(
                title="🎲 Confirm Role Shuffle",
                description=f"Are you sure you want to shuffle roles for **{total_users}** users?",
                color=discord.Color.blue()
            )
            
            # Add role information
            role_info = []
            for role in roles_to_shuffle:
                role_info.append(f"• **{role.name}** ({len(role.members)} members)")
            
            embed.add_field(
                name="Roles to shuffle:",
                value="\n".join(role_info),
                inline=False
            )
            
            embed.add_field(
                name="What will happen:",
                value="• All users will have their current shuffle role removed\n• Each user will be randomly assigned one of the above roles\n• Users may get the same role they had before",
                inline=False
            )
            
            embed.set_footer(text="This action cannot be undone. You have 5 minutes to confirm.")

            # Create view with confirmation buttons
            view = ShuffleConfirmView(self, interaction, roles_to_shuffle)
            await interaction.response.send_message(embed=embed, view=view)

        except PermissionCheckError as e:
            await interaction.response.send_message(str(e), ephemeral=True)
        except Exception as e:
            print(f"Error in shuffle command: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while processing your request. Please try again.",
                ephemeral=True
            )

    async def perform_shuffle(self, interaction: discord.Interaction, roles_to_shuffle: list):
        """Perform the actual role shuffle."""
        try:
            # Collect all users from all roles
            all_users = []
            users_by_role = {}
            
            for role in roles_to_shuffle:
                users_by_role[role.id] = list(role.members)
                all_users.extend(role.members)
            
            # Remove duplicates (users with multiple shuffleable roles)
            unique_users = list(set(all_users))
            
            # Shuffle the users
            random.shuffle(unique_users)
            
            # Calculate how many users should get each role
            users_per_role = len(unique_users) // len(roles_to_shuffle)
            extra_users = len(unique_users) % len(roles_to_shuffle)
            
            # Distribute users to roles
            user_index = 0
            role_assignments = {}
            
            for i, role in enumerate(roles_to_shuffle):
                # Some roles get one extra user if there's a remainder
                role_user_count = users_per_role + (1 if i < extra_users else 0)
                role_assignments[role] = unique_users[user_index:user_index + role_user_count]
                user_index += role_user_count

            # Remove all users from their current shuffleable roles
            for user in unique_users:
                for role in roles_to_shuffle:
                    if role in user.roles:
                        try:
                            await user.remove_roles(role, reason="Role shuffle - removing old role")
                        except discord.HTTPException as e:
                            print(f"Failed to remove role {role.name} from {user.display_name}: {e}")

            # Add users to their new roles
            successful_assignments = 0
            failed_assignments = []
            
            for role, assigned_users in role_assignments.items():
                for user in assigned_users:
                    try:
                        await user.add_roles(role, reason="Role shuffle - assigning new role")
                        successful_assignments += 1
                    except discord.HTTPException as e:
                        print(f"Failed to add role {role.name} to {user.display_name}: {e}")
                        failed_assignments.append((user.display_name, role.name))

            # Set cooldown
            await self.db.set_shuffle_cooldown(interaction.guild.id, interaction.user.id)
            
            # Log the shuffle
            role_names = [role.name for role in roles_to_shuffle]
            await self.db.log_shuffle(
                interaction.guild.id,
                interaction.user.id,
                len(unique_users),
                role_names
            )

            # Create success embed
            embed = discord.Embed(
                title="✅ Roles Shuffled Successfully!",
                description=f"Successfully shuffled **{successful_assignments}** role assignments!",
                color=discord.Color.green()
            )
            
            # Show new role distribution
            distribution_info = []
            for role, assigned_users in role_assignments.items():
                distribution_info.append(f"• **{role.name}**: {len(assigned_users)} members")
            
            embed.add_field(
                name="New role distribution:",
                value="\n".join(distribution_info),
                inline=False
            )
            
            if failed_assignments:
                failed_text = "\n".join([f"• {user} → {role}" for user, role in failed_assignments[:5]])
                if len(failed_assignments) > 5:
                    failed_text += f"\n• ... and {len(failed_assignments) - 5} more"
                    
                embed.add_field(
                    name="⚠️ Some assignments failed:",
                    value=failed_text,
                    inline=False
                )
            
            embed.add_field(
                name="Cooldown:",
                value="Next shuffle available in 5 minutes",
                inline=False
            )
            
            embed.set_footer(text=f"Shuffle performed by {interaction.user.display_name}")

            await interaction.edit_original_response(embed=embed, view=None)

        except Exception as e:
            print(f"Error performing shuffle: {e}")
            error_embed = discord.Embed(
                title="❌ Shuffle Failed",
                description="An error occurred while shuffling roles. Some role changes may have been partially completed.",
                color=discord.Color.red()
            )
            await interaction.edit_original_response(embed=error_embed, view=None)

async def setup(bot: commands.Bot, database: Database):
    """Setup function to add this cog to the bot."""
    await bot.add_cog(ShuffleCommands(bot, database))