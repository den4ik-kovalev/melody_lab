from abc import ABC, abstractmethod

import dearpygui.dearpygui as dpg


class Window(ABC):

    @abstractmethod
    def __init__(self) -> None:
        with dpg.stage() as self._stage:
            self._tag: int = ...

    @property
    def tag(self) -> int:
        return self._tag

    def add(self) -> None:
        dpg.unstage(self._stage)

    def center(self) -> None:
        dpg.set_item_pos(
            self._tag,
            [
                int((dpg.get_viewport_width() / 2 - dpg.get_item_width(self._tag) / 2)),
                int((dpg.get_viewport_height() / 2 - dpg.get_item_height(self._tag) / 2))
            ]
        )
