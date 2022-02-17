import glob
import json
import os
import re

import discord
from discord import Embed
from discord.ext import commands

from src.modules.colors import Color
from src.modules.data import Data
from src.modules.players import SERVER
from src.modules.roles import Roles
from src.modules.utils import find_game, delete_game, create_menu, MatchdayList


class Admin(commands.Cog):
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

    @commands.command()
    @commands.has_any_role(*Roles.admins())
    async def delete(self, ctx, matchday: int, one_team):
        """Delete a game report."""
        deleted_game = delete_game(matchday, one_team)
        await ctx.send(embed=Embed(color=Color.DEFAULT, description=f"{deleted_game} was deleted from the db"))
        SERVER.update()

    @commands.group(invoke_without_command=True)
    @commands.has_any_role(*Roles.admins())
    async def edit(self, ctx, subcommand):
        """Edit a report.

        Usage: edit <subcommand>
        Use help edit <subcommand> for more clarifications."""
        await ctx.send(embed=Embed(color=Color.DEFAULT,
                                   title="Use !help edit",
                                   description="Usage: edit <subcommand>"
                                               "Use help edit <subcommand> for more clarifications."))

    @edit.command(aliases=["recs"])
    @commands.has_any_role(*Roles.admins())
    async def rec(self, ctx, matchday: int, one_team, *recs):
        """Edit the recs of a game.

        Example:
            I want to edit recs of the game Balls be snakin vs Swifties, which is the matchday 5.
            I use: edit rec 5 snakin thehax_link1 thehax_link2

        Warning: This will override the previous recs"""
        data = Data(data=find_game(matchday, one_team))
        warnings = [""]
        if not recs:
            warning = "Missing recs in your message when you wanted to edit the game"
            data.warn(warning)
            warnings.append(warning)
        data.data["recs"] = list(recs)
        warning_msg = warnings[0] if warnings else ""
        recs_txt = " ".join(recs)
        await ctx.send(embed=Embed(
            color=Color.DEFAULT,
            description=f"Recs: {recs_txt} saved with {1 - len(warnings)} warning(s).\n{warning_msg}")
                       .set_footer(text=f"Match: {data.title}")
                       )
        data.save()

    @edit.command()
    @commands.has_any_role(*Roles.admins())
    async def score(self, ctx, matchday: int, team1: str, score_team1: int, score_team2: int, team2: str):
        """Edit the score of game.

        Example:
            I want to edit the score of the game Balls be snakin vs champions, which is the matchday 5.
            I use: edit score 5 "balls be snakin" 4 3 "champions"

        Note: Put teams in " " please.

        Warning: This will override the previous score"""
        team1, team2 = team1.lower(), team2.lower()
        data = Data(data=find_game(matchday, team1))
        data.edit_score(team1, team2, score_team1, score_team2)

        await ctx.send(embed=Embed(
            color=Color.DEFAULT,
            title=f"{data.title}: Score edited by {ctx.author.display_name}")
        )

    @edit.command(aliases=["stats"])
    @commands.has_any_role(*Roles.admins())
    async def stat(self, ctx, matchday: int, one_team, *, one_stat_per_line: str):
        """Edit the players stats of a game.

        Example:
            I want to edit some stats of the game Balls be snakin vs Swifties, which is the matchday 5.
            I use: edit stat 5 snakin
                worth 6 goals
                bla 17 saves
                anddy 2 own goals
                raiden 1 assists
                tha sup 1 cs

        Warning: This will override the previous stats
        Note: Please always put the "s" even if it's one or 0.
        Note: You can not edit time, only: goals assists saves cs and own goals"""
        stats = [re.split(r" *(.*) (\d+) (.*) *", stat) for stat in one_stat_per_line.splitlines()]
        stats = [(name.lower(), int(stat), stat_name.lower()) for _, name, stat, stat_name, _ in stats]
        data = Data(data=find_game(matchday, one_team))
        for player, stat, stat_name in stats:
            data.update_stat(player, stat, stat_name)
        desc = "\n".join([f"{player} {stat} {stat_name}" for player, stat, stat_name in stats])
        if data.warnings:
            desc += "\n\n - WARNING: " + "\n - WARNING: ".join(data.warnings) + "\n"

        await ctx.send(embed=Embed(
            color=Color.DEFAULT,
            title=f"{data.title}: Stats edited by {ctx.author.display_name}",
            description=desc)
        )
        data.save()

    @edit.command(aliases=["nick", "nicks"])
    @commands.has_any_role(*Roles.admins())
    async def nickname(self, ctx, matchday: int, one_team, *, nicknames_list: str):
        """Edit the nicknames of a game.

        Example:
            I want to edit some stats of the game Balls be snakin vs champions, which is the matchday 5.
            I use: edit nicks 5 snakin
                lonely bones = anddy
                thegoal = lancelot du lac

        Warning: This will override the previous nicks"""
        try:
            nicknames = [nick.split(" = ") for nick in nicknames_list.splitlines()]
            nicknames = [(nickname_in_match.lower(), real_nickname.lower())
                         for nickname_in_match, real_nickname in nicknames]
        except Exception:
            raise ValueError(f"Error : Could not understand {nicknames_list}")

        data = Data(data=find_game(matchday, one_team))
        for nickname_in_match, real_nickname in nicknames:
            data.update_nick(nickname_in_match, real_nickname)
        desc = "\n".join([f"{before} -> {after}" for before, after in nicknames])
        await ctx.send(embed=Embed(
            color=Color.DEFAULT,
            title=f"{data.title}: Nicknames edited by {ctx.author.display_name}",
            description=desc)
        )
        data.save()

    @commands.command(aliases=["malus"])
    @commands.has_any_role(*Roles.admins())
    async def add_malus(self, ctx, team):
        with open("resources/malus/malus.json") as malus_fp:
            teams = json.load(malus_fp)
            all_teams = teams["div1"].keys() + teams["div2"].keys()
        if team not in all_teams:
            raise ValueError(f"Error : {team} is not a team I can find.")
        div = "div1" if team in teams["div1"] else "div2"
        teams[div][team] += 1
        with open("resources/malus/malus.json", "w+") as malus_fp:
            json.dump(teams, malus_fp, indent=4)
        await ctx.send(embed=Embed(color=Color.DEFAULT, description=f"One malus was added to {team}"))

    @commands.command(aliases=["w"])
    async def warnings(self, ctx):
        """See all warnings.

        A warning is added whenever an information was missing in a report."""
        path = os.path.join("resources/results/")
        filenames = [filename for filename in glob.glob(f"{path}/*/*")]
        data = []
        for filename in filenames:
            with open(filename, "r") as f:
                d = json.load(f)
                if d["warnings"]:
                    data.append(d["score"])

        await create_menu(MatchdayList, ctx, data, matchday="[ALL]")
    #
    # @commands.command(enabled=False)
    # async def set_teams(self, ctx, *category_id: int):
    #     """Disabled, must be used at the beggining of the season"""
    #
    #     def predicate(channel: GuildChannel) -> bool:
    #         try:
    #             return channel.category.id in category_id
    #         except AttributeError:
    #             return False
    #
    #     data = sorted([channel.name for channel in ctx.guild.channels if predicate(channel)])
    #     with open("resources/teams/teams.json", "w+") as f:
    #         json.dump(data, f)


def setup(bot):
    bot.add_cog(Admin(bot))
