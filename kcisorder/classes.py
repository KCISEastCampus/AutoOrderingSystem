from typing import Optional

class Meal:
    def __init__(
        self,
        id: Optional[str],
        english_name: str,
        chinese_name: str,
        remaining: int,
        cafeteria: int,
        type_: str,
        description: str = "",
    ) -> None:
        self.id = id
        self.english_name = english_name
        self.chinese_name = chinese_name
        self.remaining = remaining
        self.cafeteria = cafeteria
        self.type_ = type_
        self.description = description

    def __str__(self) -> str:
        return f"{self.type_} {self.id or '?'} - {self.chinese_name}"

    def __repr__(self) -> str:
        return (
            f"Meal(type_={self.type_!r}, id={self.id!r}, chinese_name={self.chinese_name!r}, "
            f"english_name={self.english_name!r}, remaining={self.remaining}, cafeteria={self.cafeteria})"
        )

    def get_description(self) -> str:
        return f"{self}\n{self.description or '(no description)'}"


class LoginError(Exception):
    pass
