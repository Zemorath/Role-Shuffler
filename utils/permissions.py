import discord
from typing import Union

def has_manage_roles_permission(user: Union[discord.Member, discord.User], guild: discord.Guild) -> bool:
    """
    Check if a user has permission to manage roles (configure shuffleable roles).
    
    Returns True if the user has any of:
    - Administrator permission
    - Manage Roles permission
    - Is the guild owner
    """
    if not isinstance(user, discord.Member):
        return False
    
    # Guild owner always has permission
    if user.id == guild.owner_id:
        return True
    
    # Check for administrator or manage roles permission
    return user.guild_permissions.administrator or user.guild_permissions.manage_roles

def has_shuffle_permission(user: Union[discord.Member, discord.User], guild: discord.Guild) -> bool:
    """
    Check if a user has permission to trigger role shuffles.
    
    For now, this uses the same permissions as manage_roles, but can be customized
    in the future if you want different permission levels.
    """
    return has_manage_roles_permission(user, guild)

def can_bot_manage_role(bot_member: discord.Member, role: discord.Role) -> bool:
    """
    Check if the bot can manage a specific role.
    
    The bot can manage a role if:
    - The bot has Manage Roles permission
    - The role is below the bot's highest role in the hierarchy
    - The role is not @everyone
    """
    if not bot_member.guild_permissions.manage_roles:
        return False
    
    # Can't manage @everyone role
    if role.is_default():
        return False
    
    # Check role hierarchy - bot's top role must be higher than the target role
    bot_top_role = bot_member.top_role
    return bot_top_role.position > role.position

def get_manageable_roles(bot_member: discord.Member, roles: list[discord.Role]) -> list[discord.Role]:
    """
    Filter a list of roles to only include ones the bot can manage.
    """
    return [role for role in roles if can_bot_manage_role(bot_member, role)]

def format_permission_error(user: discord.Member, required_permission: str) -> str:
    """
    Format a user-friendly permission error message.
    """
    return (
        f"❌ {user.mention}, you need **{required_permission}** permission to use this command.\n"
        f"Contact a server administrator if you believe this is an error."
    )

def format_bot_permission_error(role_name: str) -> str:
    """
    Format a user-friendly error message when the bot can't manage a role.
    """
    return (
        f"❌ I cannot manage the role **{role_name}**.\n"
        f"This might be because:\n"
        f"• The role is higher than my highest role\n"
        f"• I don't have the **Manage Roles** permission\n"
        f"• The role is a special role (like @everyone)\n\n"
        f"Please check my permissions and role hierarchy."
    )

class PermissionCheckError(Exception):
    """Custom exception for permission check failures."""
    pass

async def ensure_user_permissions(interaction: discord.Interaction, permission_type: str = "manage_roles"):
    """
    Ensure a user has the required permissions, raising an exception if they don't.
    
    Args:
        interaction: The Discord interaction
        permission_type: Either "manage_roles" or "shuffle"
    
    Raises:
        PermissionCheckError: If the user doesn't have the required permissions
    """
    if permission_type == "manage_roles":
        has_permission = has_manage_roles_permission(interaction.user, interaction.guild)
        perm_name = "Manage Roles or Administrator"
    elif permission_type == "shuffle":
        has_permission = has_shuffle_permission(interaction.user, interaction.guild)
        perm_name = "Manage Roles or Administrator"
    else:
        raise ValueError(f"Unknown permission type: {permission_type}")
    
    if not has_permission:
        raise PermissionCheckError(format_permission_error(interaction.user, perm_name))

async def ensure_bot_can_manage_role(interaction: discord.Interaction, role: discord.Role):
    """
    Ensure the bot can manage a specific role, raising an exception if it can't.
    
    Raises:
        PermissionCheckError: If the bot can't manage the role
    """
    bot_member = interaction.guild.get_member(interaction.client.user.id)
    
    if not can_bot_manage_role(bot_member, role):
        raise PermissionCheckError(format_bot_permission_error(role.name))