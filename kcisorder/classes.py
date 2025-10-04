class Meal:
    def __init__(self, id: str, english_name: str, chinese_name: str, remaining: int, cafeteria: str, type_: str) -> None:
        self.id = id
        self.english_name = english_name
        self.chinese_name = chinese_name
        self.remaining = remaining
        self.cafeteria = cafeteria
        self.type_ = type_
        self.description = ""

    def __str__(self) -> str:
        return f"{self.type_} {self.id} - {self.chinese_name}"

    def __repr__(self):
        return f"Meal(type = {self.type_}, id = {self.id}, chinese_name = {self.chinese_name}, english_name = {self.english_name}, remaining = {self.remaining}, cafeteria = {self.cafeteria})"

    def get_description(self) -> str:
        return f"{self}\n{self.description}"
