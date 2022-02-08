class Roles:
    _captains = [747552995126018139, 747553142752935986]
    _admins = [783900703462260736, 635822253803569155]

    @staticmethod
    def captains():
        return Roles._captains + Roles._admins

    @staticmethod
    def admins():
        return Roles._admins
