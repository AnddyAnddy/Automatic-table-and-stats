from __future__ import annotations

import glob
import json
import os
from typing import TYPE_CHECKING, Iterable

import discord
from discord import Embed
from discord.ext import menus
from discord.ext.menus.views import ViewMenuPages

from src.modules.colors import Color
from src.modules.table import Team


class TeamsList(menus.ListPageSource):
    def __init__(self, data):
        super().__init__(data, per_page=15)

    async def format_page(self, menu: discord.ext.menus.Menu, entries):
        offset = menu.current_page * self.per_page
        return Embed(color=Color.DEFAULT,
                     description="\n```" + '\n'.join([f"{name:30} " for _, name in
                                                      enumerate(entries, start=offset)]) + "```") \
            .set_footer(text=f"[ {menu.current_page + 1} / {self.get_max_pages()} ]")


class MatchdayList(menus.ListPageSource):
    def __init__(self, data, matchday=None):
        super().__init__(data, per_page=7)
        self.matchday = matchday

    async def format_page(self, menu: discord.ext.menus.Menu, entries):
        offset = menu.current_page * self.per_page
        embed = Embed(color=Color.DEFAULT, title=f"Matchday n°{self.matchday}")
        for _, result in enumerate(entries, start=offset):
            keys = list(result.keys())
            embed.add_field(name=keys[0].upper().center(18), value=f"{'―' * 11}", inline=True)
            embed.add_field(name=f"{result[keys[0]]} - {result[keys[1]]}", value=f"{'―' * 11}", inline=True)
            embed.add_field(name=keys[1].upper().center(18), value=f"{'―' * 11}", inline=True)
        embed.set_footer(text=f"[ {menu.current_page + 1} / {self.get_max_pages()} ]")
        return embed


class NormalLeaderboardList(menus.ListPageSource):

    def __init__(self, data, key=None):
        super().__init__(data, per_page=20)
        self.key = key

    async def format_page(self, menu: discord.ext.menus.Menu, entries):
        def ratio(stat, time):
            if time == 0:
                rat = stat
            else:
                rat = stat / (time // 60)
            return f"{rat * 100:>10.2f}"

        offset = menu.current_page * self.per_page
        desc = '```\n'
        r = f"{self.key} / 14 mins %"
        desc += f'pos {"name":<20} {self.key:>10} {"time":>10} {r:>12}\n\n'
        return Embed(
            color=Color.DEFAULT,
            description=
            desc + '\n'.join([f"{add_zero(i + 1)}) {player:<20} {stat:>10} {format_time(time):>10} {ratio(stat, time)}"
                              for i, (player, stat, time) in
                              enumerate(entries, start=offset)])
            + "```"
        ) \
            .set_footer(text=f"[ {menu.current_page + 1} / {self.get_max_pages()} ]")


class TimeLeaderboardList(menus.ListPageSource):

    def __init__(self, data, key=None):
        super().__init__(data, per_page=20)
        self.key = key

    async def format_page(self, menu: discord.ext.menus.Menu, entries):
        offset = menu.current_page * self.per_page
        desc = '```\n'
        desc += f'pos {"name":<20} {"time":>10}\n\n'
        return Embed(
            color=Color.DEFAULT,
            description=
            desc + '\n'.join([f"{add_zero(i + 1)}) {player:<20} {format_time(time):>10}"
                              for i, (player, stat, time) in
                              enumerate(entries, start=offset)])
            + "```"
        ) \
            .set_footer(text=f"[ {menu.current_page + 1} / {self.get_max_pages()} ]")


class TableList(menus.ListPageSource):

    def __init__(self, data):
        super().__init__(data, per_page=20)

    async def format_page(self, menu: discord.ext.menus.Menu, entries: Iterable[Team]):
        offset = menu.current_page * self.per_page
        desc = '```\n'
        desc += f'{"pos":4} {"team":^20} {"GP":>3} {"W":>3} ' \
                f'{"D":>3} {"L":>3} {"GF":>3} {"GA":>3} {"GD":>3} {"PTS":>3}\n\n'
        return Embed(
            color=Color.DEFAULT,
            description=
            desc + '\n'.join([f"{add_zero(i + 1)}) {team.name:^20} {team.games_played:>3} {team.wins:>3} "
                              f"{team.draws:>3} {team.losses:>3} {team.goals_for:>3}"
                              f" {team.goals_against:>3} {team.goals_diff:>3} {team.points:>3}"
                              for i, team in enumerate(entries, start=offset)])
            + "```"
        ) \
            .set_footer(text=f"[ {menu.current_page + 1} / {self.get_max_pages()} ]")


async def create_menu(cls, ctx, data, **kwargs):
    pages = ViewMenuPages(source=cls(data, **kwargs), clear_reactions_after=True, timeout=None)
    await pages.start(ctx)


def format_time(seconds):
    m, s = divmod(seconds, 60)
    if s == 0:
        return f"{m}m"
    return f"{m}m{s}sec"


def add_zero(number) -> str:
    return f"0{number}" if number < 10 else str(number)


def find_game(matchday: int, *teams):
    path = os.path.join("resources/results/", str(matchday))
    filenames = [filename for filename in glob.glob(f"{path}/*")]
    try:
        results = [filename for filename in filenames if any(team in filename for team in teams)]
        if len(results) > 1:
            raise ValueError(f"Error : Found more than one match with matchday: {matchday} and team(s) {teams}")
        return json.load(open(results[0]))
    except ValueError:
        raise
    except Exception:
        raise ValueError(f"Error : Could not find a match with matchday: {matchday} and team(s) {teams}")


def game_exists(matchday, *teams):
    path = os.path.join("resources/results/", str(matchday))
    filenames = [filename for filename in glob.glob(f"{path}/*")]
    results = [filename for filename in filenames if any(team in filename for team in teams)]
    return len(results) == 1


def delete_game(matchday: int, *teams):
    path = os.path.join("resources/results/", str(matchday))
    filenames = [filename for filename in glob.glob(f"{path}/*")]
    try:
        results = [filename for filename in filenames if any(team in filename for team in teams)]
        if len(results) > 1:
            raise ValueError(f"Error : Found more than one match with matchday: {matchday} and team(s) {teams}")
        os.remove(results[0])
        return results[0]
    except ValueError:
        raise
    except Exception:
        raise ValueError(f"Error : Could not find a match with matchday: {matchday} and team(s) {teams}")


def all_tuple_to_int(values):
    return tuple(int(v) for v in values)


def clean_rec(elem):
    split_pattern = "https://"
    return split_pattern + elem.split(split_pattern)[-1].strip()
