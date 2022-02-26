import glob
import json
import os.path
import typing

import discord
from discord import Embed
from discord.ext import commands

from src.modules.colors import Color
from src.modules.game import Game
from src.modules.players import SERVER, Leaderboard
from src.modules.table import Team
from src.modules.utils import TeamsList, create_menu, format_time, NormalLeaderboardList, MatchdayList, find_game, \
    TimeLeaderboardList, TableList, ratio


class Infos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._channels: dict[int, discord.abc.Messageable] = dict()

    @commands.command()
    async def teams(self, ctx, div: typing.Literal[1, 2] = 1):
        """Get the teams.

        Get teams from both div: !teams
        Get teams from div 1: !teams 1
        Get teams from div 2: !teams 2
        """
        with open("resources/teams/teams.json", "r") as f:
            data = json.load(f)
        if not div:
            data = data["div1"] + data["div2"]
        else:
            try:
                data = data[f"div{div}"]
            except KeyError:
                raise ValueError(f"Error : {div} is not a valid division, must be 1 or 2")
        data = sorted(data)
        await create_menu(TeamsList, ctx, data)

    @commands.command(aliases=["g", "game", "match"])
    async def get_game(self, ctx, matchday: int, *teams):
        """Get infos on a game.

        Get some infos about a game, write down the matchday and one of the two team of that game.
        Example:
            I want to see the stats of the matchday 1 between champions and ghouls
            I use: !game 1 ghouls
        """
        teams = " ".join(teams).lower().split(" + ")
        game = find_game(matchday, *teams)
        team_name = ("ONE", "TWO")
        embed = Embed(color=Color.DEFAULT, title=f"MD: {game['matchday']} {game['title'].upper()}")
        if "team1" in game:
            for i in (1, 2):
                team = "team" + str(i)
                players_time = ""
                players_stats = {}
                for key in game[team]:
                    for player, stat in game[team][key].items():
                        if player not in players_stats:
                            players_stats[player] = ""
                        if key == "time_played":
                            players_time += f"\n> **{player}**: {format_time(stat)}"
                        else:
                            players_stats[player] += f"{stat}{Game.reverse_stat_match[key]} "
                formatted_ps = self.format_player_stats(players_stats)
                embed.add_field(name=f":{team_name[i - 1].lower()}:        **TEAM {team_name[i - 1]}**",
                                inline=True,
                                value=f"{'―' * 11}\n\n" ":man_playing_handball: __**Players:**__\n" f"{players_time}"
                                      f"\n\n{'―' * 11}\n\n {formatted_ps}")

        if game["warnings"]:
            embed.set_footer(text=f"Warnings: {game['warnings']}")
        links = []
        if game["recs"]:
            links.append(*game["recs"])
        for discord_info in game["discord_infos"]:
            discord_links = f"https://discord.com/channels/635822055601864705/" \
                            f"{discord_info['channel_id']}/{discord_info['message_id']}"
            links.append(discord_links)
        await ctx.send('\n'.join(links), embed=embed)

    @commands.group(invoke_without_command=True, aliases=["lb"])
    async def leaderboard(self, ctx, key: typing.Literal["time", "goals", "assists", "saves", "cs", "og"],
                          div: typing.Literal[1, 2] = None):
        """See the leaderboard of a specific stat.

        Available stats: time, goals, assists, saves, cs, og
        """
        data = Leaderboard.sort_by(key, div)
        cls = TimeLeaderboardList if key == "time" else NormalLeaderboardList
        await create_menu(cls, ctx, data, key=key)

    @commands.command(aliases=["r", "rlb"])
    async def ratio_leaderboard(self, ctx, key: typing.Literal["time", "goals", "assists", "saves", "cs", "og"],
                                div: typing.Literal[1, 2] = 1, min_time=0):
        """See the ratio leaderboard of a specific stat.

        Available stats: time, goals, assists, saves, cs, og
        Div: 1 for div 1 and 2 for div 1
        Min time: the minimum time you want players to have played in order to appear in the leaderboard
        """

        data = [p for p in sorted(Leaderboard.sort_by(key, div),
                                  reverse=True,
                                  key=lambda x: x[1] / x[2] if x[2] != 0 else x[1])
                if p[2] // 60 >= min_time
                ]
        await create_menu(NormalLeaderboardList, ctx, data, key=key)

    @commands.command(aliases=["md"])
    async def matchday(self, ctx, matchday: int):
        """Get all results of a matchday."""
        path = os.path.join("resources/results/", str(matchday))
        filenames = [filename for filename in glob.glob(f"{path}/*")]
        data = []
        for filename in filenames:
            with open(filename, "r") as f:
                data.append(json.load(f)["score"])

        await create_menu(MatchdayList, ctx, data, matchday=matchday)

    @commands.command(aliases=["t"])
    async def table(self, ctx, div: typing.Literal[1, 2] = 1):
        """See the table of a specific division (1 or 2).

        Example:
            !table 1
                or
            !t 2
        """

        def sort_key(t: Team):
            return t.points, t.goals_diff, t.goals_for, t.goals_against, t.wins, t.name

        data = sorted(SERVER.table(div).teams.values(), key=lambda t: sort_key(t), reverse=True)
        await create_menu(TableList, ctx, data)

    def format_player_stats(self, players_stats):
        return f"📊  __**Player Pos:**__\n\n" + \
               "\n".join(f"> **{player}**: {stats}" for player, stats in players_stats.items()) + f"\n\n{'―' * 11}"

    @commands.command(aliases=["s", "stat", "info"])
    async def stats(self, ctx, *, name):
        """See the stats of a specific player."""
        with open("resources/players/players.json") as f:
            players = json.load(f)
        if name not in players:
            raise ValueError(f"Error : {name} is not in the players list.")
        player = players[name]
        desc = "```py\n"
        desc += f'{"name":<15} {name:<20} {"stat / mins %":<10}\n'
        seconds = player["time"]
        desc += f'{"time":<15} {format_time(seconds):<20}\n'
        for s in ('goals', 'assists', 'saves', 'cs', 'own goals'):
            val = player[s]
            r = ratio(val, seconds, s)
            desc += f'{s:<15} {val:<20} {r}\n'
        desc += "```"

        await ctx.send(embed=Embed(title=name, description=desc).set_footer(text=f"Division {player['div']}"))


def setup(bot):
    bot.add_cog(Infos(bot))
