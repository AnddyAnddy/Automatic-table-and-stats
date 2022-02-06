import re


class Game:
    stat_match = {
        "m": "time_played",
        "g": "scorers",
        "cs": "cs",
        "s": "saves",
        "a": "assisters",
        "og": "own goals"
    }

    reverse_stat_match = {
        "scorers": "g",
        "cs": "cs",
        "saves": "s",
        "assisters": "a",
        "own goals": "og"
    }

    @staticmethod
    def parse(text: str, switched_team=False):
        def find_players(txt: list[str]):
            res = []
            for e in txt:
                if e.startswith(">"):
                    res.append(e[4:].lower().split(":** "))
                elif e == "SEPARATOR":
                    res.append(e)
            return res

        t = text.splitlines()
        t = find_players(t)
        separator = t.index("SEPARATOR")

        team1 = {x for x, y in t[:separator]} if not switched_team else {x for x, y in t[separator + 1:]}
        t.pop(separator)
        # t = [s[4:].lower().split(":** ") for s in t if s.startswith(">")]
        for elem in t:
            if elem[0].startswith("[og] "):
                elem[0] = elem[0].replace("[og] ", "")
                elem[1] = elem[1].replace("g", "og")
        try:
            t = [(x, *y.split(" ")) for x, y in t]
        except ValueError:
            return
        d = {}
        for name, *stats in t:
            if name in d:
                d[name] += stats
            else:
                d[name] = stats
        if len(d) <= 7:
            return

        game = {"team1": {"time_played": {}, "scorers": {}, "assisters": {}, "cs": {}, "saves": {}, "own goals": {}},
                "team2": {"time_played": {}, "scorers": {}, "assisters": {}, "cs": {}, "saves": {}, "own goals": {}}}
        for name, stats in d.items():
            for stat in stats:
                if Game.is_time(stat):
                    number, stat_name = Game.calculate_seconds(stat), Game.stat_match["m"]
                else:
                    number_stat_name = re.findall(r"\d+|\w+", stat)

                    try:
                        number, stat_name = int(number_stat_name[0]), Game.stat_match[number_stat_name[1]]
                    except KeyError:
                        continue
                team = "team1" if name in team1 else "team2"
                game[team][stat_name][name] = number

        return game

    @staticmethod
    def calculate_seconds(time) -> int:
        if "m" in time:
            if 'sec' in time:
                time = time.replace("m", " * 60 + ").replace("sec", "")
            else:
                time = time.replace("m", " * 60")
        else:
            time = time.replace("sec", "")
        res = eval(time)
        return min(res, 420)

    @staticmethod
    def is_time(val):
        return "m" in val or "sec" in val

# if __name__ == '__main__':
#     sample_game = open("../../resources/raw/26-01-22-21h17-JSadvsTheGoal.hbr2.txt", encoding="utf-8").read()
#     # data = construct_match_data(sample_text)
#     data2 = Game.parse(sample_game)
#     # data2.update(data)
#     with open("../../test.json", "w+") as f:
#         json.dump(data2, f, indent=4, cls=EnhancedJSONEncoder)
