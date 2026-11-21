from functools import cache
from importlib.resources import files


@cache
def get_prompt(name: str) -> str:
    return files(__package__).joinpath(f"{name}.md").read_text(encoding="utf-8")


def get_prompt_version(name: str) -> str:
    first_line = get_prompt(name).splitlines()[0]
    return first_line.removeprefix("<!-- prompt: ").removesuffix(" -->").strip()
