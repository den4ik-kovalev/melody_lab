import time
from abc import ABC, abstractmethod
from typing import Any, Callable

import dearpygui.dearpygui as dpg


class ModalWindow(ABC):

    @abstractmethod
    def __init__(self) -> None:
        self._stage = ...

    def add(self):
        dpg.unstage(self._stage)


class MessageBox(ModalWindow):

    def __init__(self, msg: str, no_close: bool = False) -> None:
        self._no_close = no_close
        with dpg.stage() as self._stage:
            with dpg.window(modal=True, no_close=no_close) as self._tag:
                dpg.add_text(msg)

    def add(self):
        super(MessageBox, self).add()
        if self._no_close:
            time.sleep(2)
            dpg.delete_item(self._tag)


class ModalInputText(ModalWindow):

    def __init__(self,
                 hint: str,
                 callback: Callable[[str], Any]
                 ) -> None:

        self._callback = callback
        with dpg.stage() as self._stage:
            with dpg.window(modal=True) as window:
                input_tag = dpg.add_input_text(
                    hint=hint,
                    width=200,
                    callback=self._on_input,
                    on_enter=True,
                    user_data=window
                )
                dpg.focus_item(input_tag)

    def _on_input(self, sender, app_data, window: int) -> None:
        dpg.delete_item(window)
        time.sleep(0.5)
        self._callback(app_data)
