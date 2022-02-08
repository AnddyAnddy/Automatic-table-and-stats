# -*- coding: utf-8 -*-

import json
import os

import discord
from discord import Embed
from discord.abc import GuildChannel
from discord.ext import commands
from discord.ext.commands import Bot
from discord.ext.commands import has_permissions
from dotenv import load_dotenv

import config
from src.modules.players import SERVER
from src.modules.utils import TeamsList, create_menu

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.default()


def get_prefix(client, message):  # first we define get_prefix
    with open('prefixes.json', 'r') as f:  # we open and read the prefixes.json, assuming it's in the same file
        prefixes = json.load(f)  # load the json as prefixes

    try:
        id = str(message.guild.id)
    except Exception:
        id = 0
    return prefixes[id] if id in prefixes else "!"  # receive the prefix for the guild id given


BOT: Bot = commands.Bot(command_prefix=get_prefix, case_insensitive=True, intents=intents,
                        chunk_guilds_at_startup=False)


def load_extensions(reloading=False):
    if reloading:
        for extension in config.extensions:
            BOT.reload_extension(extension)
    else:
        for extension in config.extensions:
            BOT.load_extension(extension)


load_extensions()


@BOT.command(pass_context=True)
@has_permissions(administrator=True)
async def set_prefix(ctx, prefix="!"):
    """Set a new prefix for this bot.

    With no args, this resets the prefix to the default one."""
    with open('prefixes.json', 'r') as f:
        prefixes = json.load(f)

    prefixes[str(ctx.guild.id)] = prefix

    with open('prefixes.json', 'w') as f:
        json.dump(prefixes, f, indent=4)

    await ctx.send(f'Prefix changed to: {prefix}')


@BOT.command(hidden=True)
async def reload(ctx):
    if ctx.author.id != 339349743488729088:
        await ctx.message.delete()
    load_extensions(True)
    await ctx.send("Reloaded")


@BOT.event
async def on_ready():
    """On ready event."""
    print(f'{BOT.user} has connected\n')


@BOT.event
async def on_guild_remove(guild):  # when the bot is removed from the guild
    with open('prefixes.json', 'r') as f:  # read the file
        prefixes = json.load(f)

    try:
        prefixes.pop(str(guild.id))  # find the guild.id that bot was removed from
    except KeyError:
        pass

    with open('prefixes.json', 'w') as f:  # deletes the guild.id as well as its prefix
        json.dump(prefixes, f, indent=4)


def get_prefix2(id):
    """Return the prefix of this bot for a specific guild or ! as default"""
    with open('prefixes.json', 'r') as f:
        prefixes = json.load(f)

    return prefixes[id] if id in prefixes else "!"


@BOT.command(hidden=True, enabled=False)
async def get_teams(ctx, *category_id: int):
    def predicate(channel: GuildChannel) -> bool:
        try:
            return channel.category.id in category_id
        except AttributeError:
            return False

    data = sorted([channel.name for channel in ctx.guild.channels if predicate(channel)])
    await create_menu(TeamsList, ctx, data)
    with open("resources/teams/teams.json", "w+") as f:
        json.dump(data, f)


async def send_error(ctx, desc, read_help=True):
    try:
        helper = f"Read !help {ctx.invoked_with}" * read_help
        desc = desc[desc.find(":") + 1:]
        await ctx.send(embed=Embed(title="Error !", color=0x000000,
                                   description=f"{str(desc)}\n{helper}"))
    except Exception:
        pass


async def send_global_error(ctx, desc):
    try:
        desc = desc[desc.find(":") + 1:]
        await ctx.send(embed=Embed(title="Error !", color=0x000000,
                                   description=f"{str(desc)}"))
    except Exception:
        pass


@BOT.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.CommandNotFound):
        return await send_error(ctx, f"The command doesn't exist, check `!help` !", read_help=False)

    elif isinstance(error, commands.errors.MissingRequiredArgument):
        return await send_error(ctx, str(error))
    elif isinstance(error, commands.errors.CommandInvokeError):
        if isinstance(error.original, ValueError):
            if str(error.original).startswith("Error"):
                return await send_error(ctx, str(error.original))
            if str(error.original).startswith("Global"):
                return await send_global_error(ctx, str(error.original))
    elif isinstance(error, commands.errors.BadArgument):
        return await send_error(ctx, str(error))
    await ctx.send(str(error))
    raise error


if __name__ == '__main__':
    SERVER.update()
    # Updater().update_all()
    BOT.run(TOKEN)
