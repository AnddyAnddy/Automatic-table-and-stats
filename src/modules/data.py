import json
import os
import re
from collections import Counter
from dataclasses import dataclass

from src.modules import aliases
from src.modules.json_encoder import EnhancedJSONEncoder
from src.modules.players import SERVER
from src.modules.utils import clean_rec


@dataclass
class EmbedResult:
    channel_id: int
    message_id: int


class Data:
    def __init__(self, data=None):
        self.errors = []
        if data is None:
            self._data = {"warnings": []}
        else:
            self._data = data

    @property
    def discord_infos(self):
        return self._data["discord_infos"]

    @property
    def full_path(self):
        return os.path.join(f"resources/results", f"{self._data['matchday']}/", f"{self._data['title']}.json")

    @property
    def warnings(self):
        return self._data["warnings"]

    @property
    def data(self):
        return self._data

    @property
    def title(self):
        return self._data["title"]

    def construct_report(self, halves):
        self._data.update(self._sum_merge(*halves))

    def warn(self, warning):
        self.warnings.append(warning)

    def update_stat(self, player: str, stat: int, original_stat_name: str):
        if stat < 0:
            raise ValueError(f"Error : {original_stat_name} can not be negative, given value: {stat}, player: {player}")
        try:
            stat_name = aliases.stat_match[original_stat_name]
        except KeyError:
            raise ValueError(f"Error : Could not understand what {original_stat_name} is, it must be among "
                             f"{tuple(aliases.stat_match.keys())}")

        if player in self._data["team1"]["time_played"]:
            team = "team1"
        elif player in self._data["team2"]["time_played"]:
            team = "team2"
        else:
            self.warn(f"{player} {stat} {stat_name} was added to the game in team 1 "
                      f"whereas {player} was not in at first.")
            team = "team1"

        self._data[team][stat_name][player] = stat

    def construct_match_data(self, text: str):
        infos = [line.lower() for line in text.splitlines() if line]

        self._get_rec(infos)
        self._get_matchday(infos)
        self._get_score(infos)
        self._get_discord_ids(infos)

    def edit_score(self, team1, team2, score_team1, score_team2):
        self._check_arg_in_team_scores(team1)
        self._check_arg_in_team_scores(team2)
        self._data["score"] = {team1: score_team1, team2: score_team2}
        self._data["title"] = f"{team1} {score_team1} - {score_team2} {team2}"
        self.save()

    def update_nick(self, nickname_in_match, real_nickname):
        if nickname_in_match in self._data["team1"]["time_played"]:
            team = "team1"
        elif nickname_in_match in self._data["team2"]["time_played"]:
            team = "team2"
        else:
            raise ValueError(f"Error : {nickname_in_match} is not in the game.")

        for stat_name, stats in self._data[team].items():
            if nickname_in_match in stats:
                if real_nickname not in stats:
                    stats[real_nickname] = 0
                stats[real_nickname] += stats[nickname_in_match]
                stats.pop(nickname_in_match)

    def save(self):
        os.makedirs(os.path.dirname(self.full_path), exist_ok=True)
        with open(self.full_path, "w+") as f:
            json.dump(self.data, f, indent=4, cls=EnhancedJSONEncoder)
        SERVER.update()

    def _get_matchday(self, infos: list[str]):
        try:
            matchday = [line for line in infos if "matchday" in line]
            self._data["matchday"] = int(re.findall(r".*(\d+).*", matchday[0])[0])
        except (IndexError, ValueError):
            self.errors.append("The match day is missing or incorrect, please follow the format: `matchday N`")

    def _get_score(self, infos: list[str]):
        with open("resources/teams/teams.json") as f:
            teams = json.load(f)
            all_teams = teams["div1"] + teams["div2"]
        try:
            score = [line for line in infos if any(team in line for team in all_teams)][0]
            score = re.split(r" +(\d+).*(\d+) +", score)
            args_score = score[0].strip(), int(score[1]), int(score[2]), score[3].strip()
            self._data["score"] = {args_score[0]: args_score[1], args_score[3]: args_score[2]}
            self._data["title"] = f"{args_score[0]} {args_score[1]} - {args_score[2]} {args_score[3]}"
            self._data["div"] = 1 if args_score[0] in teams["div1"] else 2
        except Exception:
            self.errors.append("Can not find 2 teams in your message, make sure they are in !teams")
            self._data["score"] = "Unknown"
            self._data["title"] = "Unknown"
            self._data["div"] = 0

    def _get_rec(self, infos: list[str]):
        recs = [clean_rec(line) for line in infos if "thehax" in line]
        if not recs:
            self.warn("Could not find the rec, is it hosted in thehax ?")
        self._data["recs"] = recs

    def _get_discord_ids(self, infos):
        discord_embed_results = [EmbedResult(*[int(e) for e in line.split("/")[-2:]])
                                 for line in infos if "discord.com" in line]
        if len(discord_embed_results) < 2:
            self.warn(
                f"Missing {2 - len(discord_embed_results)} result report from #report-official")
        self._data["discord_infos"] = discord_embed_results

    def _sum_merge(self, *halves):
        if len(halves) == 0:
            return {}
        elif len(halves) == 1:
            return halves[0]
        dict1, dict2 = halves
        res = {"team1": {}, "team2": {}}
        for team in res:
            for key in dict1[team]:
                res[team][key] = Counter(dict1[team][key]) + Counter(dict2[team][key])

        return res

    def _check_arg_in_team_scores(self, team):
        if team not in self._data["score"]:
            raise ValueError(f"Error : {team} is not a valid team for the match {self.title}")
