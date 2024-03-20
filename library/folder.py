import shutil
from contextlib import contextmanager
from pathlib import Path


class Folder:

    def __init__(self, path: Path):
        self.path = path

    @property
    def name(self):
        return self.path.name

    def clear(self):
        for child in self.path.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()

    def subdirs(self) -> list[Path]:
        return [x for x in self.path.iterdir() if x.is_dir()]

    def files(self) -> list[Path]:
        return [x for x in self.path.iterdir() if x.is_file()]

    def contains_filename(self, filename: str) -> bool:
        for filepath in self.files():
            if filepath.name == filename:
                return True
        return False

    @contextmanager
    def clear_after(self):
        try:
            yield
        finally:
            self.clear()

    def find_by_suffix(self, suffix: str) -> list[Path]:
        return [
            child for child in self.path.iterdir()
            if child.suffix == suffix
        ]

    def find_by_name(self, name: str) -> list[Path]:
        return [
            child for child in self.path.iterdir()
            if child.name == name
        ]
