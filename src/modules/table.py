import glob
import json

import jsonpickle


class Team:
    def __init__(self, name: str = "", games_played: int = 0, wins: int = 0, draws: int = 0,
                 losses: int = 0, goals_for: int = 0, goals_against: int = 0, malus: int = 0):
        self.name = name
        self.games_played = games_played
        self.wins = wins
        self.draws = draws
        self.losses = losses
        self.goals_for = goals_for
        self.goals_against = goals_against
        self.malus = malus

    @property
    def points(self):
        return 3 * self.wins + self.draws - self.malus

    @property
    def goals_diff(self):
        return self.goals_for - self.goals_against

    def update(self, score_self, score_opponent):
        self.games_played += 1
        self.goals_for += score_self
        self.goals_against += score_opponent
        if score_self > score_opponent:
            self.wins += 1
        elif score_self == score_opponent:
            self.draws += 1
        else:
            self.losses += 1

    def to_json(self):
        res = self.__dict__
        res["points"] = self.points
        res["goals_diff"] = self.goals_diff
        return res


class Table:
    def __init__(self, div):
        self.teams: dict[str, Team] = dict()
        self.div = div

    def update(self):
        path = f"resources/tables/div{self.div}.json"
        json.dump({}, open(path, "w+"))
        for filename in glob.glob("resources/results/*/*.json"):
            with open(filename, "r") as f:
                game: dict = json.load(f)
                if game["div"] != self.div:
                    continue
                score = game["score"]
                for team, nb_goals in score.items():
                    if team not in self.teams:
                        self.teams[team] = Team(name=team)
                team1, team2 = score.keys()
                self.teams[team1].update(score[team1], score[team2])
                self.teams[team2].update(score[team2], score[team1])

        res = {team_name: team.to_json() for team_name, team in self.teams.items()}
        with open(path, "w+") as db:
            json.dump(res, db, indent=4)
