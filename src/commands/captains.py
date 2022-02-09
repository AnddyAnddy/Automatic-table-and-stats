import json
import os

import discord
from discord import Embed
from discord.ext import commands

from src.modules.colors import Color
from src.modules.data import Data
from src.modules.game import Game
from src.modules.json_encoder import EnhancedJSONEncoder


class Captain(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._channels: dict[int, discord.abc.Messageable] = dict()

    async def get_channel(self, channel_id: int) -> discord.abc.Messageable:
        if self._channels:
            return self._channels[channel_id]

        self._channels: dict[int, discord.abc.Messageable] = {
            726932351241814117: await self.bot.fetch_channel(726932351241814117),  # offi
            726932424172371968: await self.bot.fetch_channel(726932424172371968)  # fs
        }
        return self._channels[channel_id]

    async def save_raw_report(self, channel_id: int, message_id: int):
        channel = await self.get_channel(channel_id)
        message = await channel.fetch_message(message_id)
        try:
            embed = message.embeds[0]
        except IndexError:
            raise ValueError("Error : The message is not a valid report message")
        filename = embed.footer.text.replace("/", "").replace("Recording: ", "")
        full_path = os.path.join("resources/raw/", filename + ".txt")
        d_embed = embed.to_dict()
        game = d_embed["fields"][0]["value"] + "\nSEPARATOR\n" + d_embed["fields"][1]["value"]

        with open(full_path, "w+", encoding="utf-8") as raw:
            raw.write(game)

        return game

    @commands.command(aliases=["c", "cp"])
    # @commands.has_any_role(*Roles.captains())
    async def create_report(self, ctx, *, txt):
        """Create a game report.

        The format is almost the same than we usual do, direct example taken from the pre ssn final:
        !create_report
            matchday 1
            CHAMPIONS 5-2 Cicada
            1st: https://discord.com/channels/635822055601864705/726932351241814117/939263386112389170
            2nd: https://discord.com/channels/635822055601864705/726932351241814117/939265603766747207
            CS: /

            rec: https://thehax.pl/forum/powtorki.php?nagranie=25a41e6a0080cde55861a5a82085a916

        Things that changed:
            You MUST write !create_report or !c, it's a command.
            You MUST write the corresponding matchday
            You don't need to write down CS, it's written in the discord links
        Apart that, you must respect the minimal format:

            !create_report
            matchday N
            Team1 <score_team_1> <score_team_2> Team2
            discord link to the first half
            discord link to the second half
            thehax link(s) to the rec(s)
        """
        data = Data()
        data.construct_match_data(txt)
        # data = construct_match_data(txt)
        halves = []
        for i, info in enumerate(data.discord_infos):
            text_game = await self.save_raw_report(info.channel_id, info.message_id)
            halves.append(Game.parse(text_game, i != 0))
        data.construct_report(halves)

        if not data.warnings:
            await ctx.message.add_reaction("✅")

        else:
            msg = "\n - WARNING: " + "\n - WARNING: ".join(data.warnings) + "\n"
            await ctx.message.add_reaction("🇼")
            await ctx.send(embed=Embed(
                color=Color.DEFAULT,
                description="Error : "
                            f"{ctx.author.mention} your report has some warnings, "
                            f"it is saved but with those issues:\n{msg}\n"
            ))
        data.save()


def setup(bot):
    bot.add_cog(Captain(bot))
