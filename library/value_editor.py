from abc import abstractmethod, ABC
from enum import Enum, EnumMeta
from pathlib import Path
from typing import Any, Callable, Optional

import easygui
import dearpygui.dearpygui as dpg
from music21.note import Pitch


class ValueEditor(ABC):

    @abstractmethod
    def __init__(self, **kwargs) -> None:
        self._stage: int = ...
        self._tag: int = ...

    @property
    def tag(self) -> int:
        return self._tag

    @property
    def callback(self) -> Optional[Callable]:
        return dpg.get_item_callback(self._tag)

    @callback.setter
    def callback(self, callback: Optional[Callable]) -> None:
        dpg.set_item_callback(self._tag, callback)

    @property
    def value(self) -> Optional[Any]:
        return dpg.get_value(self._tag)

    @value.setter
    def value(self, value: Optional[Any]):
        dpg.set_value(self._tag, value)

    def add(self, parent) -> None:
        dpg.push_container_stack(parent)
        dpg.unstage(self._stage)
        dpg.pop_container_stack()


class IntInput(ValueEditor):

    def __init__(self, **kwargs) -> None:
        with dpg.stage() as self._stage:
            self._tag = dpg.add_input_int(**kwargs)

    @property
    def value(self) -> int:
        return dpg.get_value(self._tag)

    @value.setter
    def value(self, value: int):
        dpg.set_value(self._tag, value)


class PositiveIntInput(ValueEditor):

    def __init__(self, **kwargs) -> None:
        kwargs["default_value"] = kwargs.get("default_value") or 0
        with dpg.stage() as self._stage:
            self._tag = dpg.add_input_int(**kwargs)

    @property
    def value(self) -> Optional[int]:
        return dpg.get_value(self._tag) or None

    @value.setter
    def value(self, value: Optional[int]):
        dpg.set_value(self._tag, value or 0)


class Combobox(ValueEditor):

    def __init__(self, items: list[Any], nullable: bool = False, **kwargs) -> None:

        if nullable and None not in items:
            items.insert(0, None)

        if kwargs.get("default_value") is None:
            if nullable:
                kwargs["default_value"] = self._value_to_str(None)
            else:
                kwargs["default_value"] = self._value_to_str(items[0])
        else:
            kwargs["default_value"] = self._value_to_str(kwargs["default_value"])

        kwargs["items"] = [self._value_to_str(i) for i in items]

        with dpg.stage() as self._stage:
            self._tag = dpg.add_combo(**kwargs)

    @property
    def value(self) -> Optional[Any]:
        return self._value_from_str(dpg.get_value(self._tag))

    @value.setter
    def value(self, value: Optional[Any]):
        dpg.set_value(self._tag, self._value_to_str(value))

    @staticmethod
    def _value_to_str(value: Optional[Any]) -> str:
        return str(value)

    @abstractmethod
    def _value_from_str(self, value_str: str) -> Optional[Any]:
        ...


class StrCombobox(Combobox):

    def _value_from_str(self, value_str: str) -> Optional[str]:
        if value_str == "None":
            return None
        return value_str


class FloatCombobox(Combobox):

    def _value_from_str(self, value_str: str) -> Optional[float]:
        if value_str == "None":
            return None
        return float(value_str)


class EnumCombobox(Combobox):

    def __init__(self, enum_cls: EnumMeta, **kwargs) -> None:
        self._enum_cls = enum_cls
        kwargs.pop("items", None)
        items = list(enum_cls)
        super(EnumCombobox, self).__init__(items, **kwargs)

    def _value_to_str(self, value: Optional[Enum]) -> str:
        if value is None:
            return "None"
        return value.value

    def _value_from_str(self, value_str: str) -> Optional[Enum]:
        if value_str == "None":
            return None
        enum_name = value_str.rpartition(".")[-1]
        return self._enum_cls(enum_name)


class Checkbox(ValueEditor):

    def __init__(self, **kwargs) -> None:
        kwargs["default_value"] = kwargs.get("default_value") or False
        with dpg.stage() as self._stage:
            self._tag = dpg.add_checkbox(**kwargs)

    @property
    def value(self) -> bool:
        return dpg.get_value(self._tag)

    @value.setter
    def value(self, val: Optional[bool]):
        dpg.set_value(self._tag, val)


class FilepathInput(ValueEditor):

    def __init__(self, filetypes: Optional[list[str]] = None, **kwargs) -> None:
        self._filetypes = filetypes
        self._path: Optional[Path] = kwargs.get("default_value")
        kwargs["default_value"] = self._path.name if self._path else ""
        kwargs["enabled"] = False
        kwargs["hint"] = "Choose file"
        with dpg.stage() as self._stage:
            self._tag = dpg.add_input_text(**kwargs)
            with dpg.item_handler_registry() as handler_reg:
                dpg.add_item_clicked_handler(
                    button=dpg.mvMouseButton_Left,
                    callback=self._on_click
                )
                dpg.bind_item_handler_registry(self._tag, handler_reg)

    @property
    def value(self) -> Optional[Path]:
        return self._path

    @value.setter
    def value(self, val: Optional[Path] = None):
        self._path = val
        strval = self._path.name if self._path else ""
        dpg.set_value(self._tag, strval)
        self.callback()

    def _on_click(self, sender, app_data):
        path = easygui.fileopenbox(
            default=str(self._path or (Path.home() / "*")),
            filetypes=self._filetypes
        )
        if path:
            self._path = Path(path)
            dpg.set_value(self._tag, self._path.name)
            self.callback()


class PitchSetInput(ValueEditor):

    def __init__(self, **kwargs) -> None:
        kwargs["default_value"] = self._value_to_str(kwargs.get("default_value"))
        with dpg.stage() as self._stage:
            self._tag = dpg.add_input_text(**kwargs)

    @property
    def value(self) -> Optional[list[Pitch]]:
        try:
            return self._value_from_str(dpg.get_value(self._tag))
        except Exception:
            return None

    @value.setter
    def value(self, value: Optional[list[Pitch]] = None):
        dpg.set_value(self._tag, self._value_to_str(value))

    @staticmethod
    def _value_to_str(value: Optional[list[Pitch]]) -> str:
        if value is None:
            return ""
        return ",".join([str(p) for p in value])

    @staticmethod
    def _value_from_str(value_str: str) -> Optional[list[Pitch]]:
        if value_str == "":
            return None
        parts = value_str.split(",")
        return [Pitch(p.strip()) for p in parts]


class MelodyInput(ValueEditor):

    def __init__(self, **kwargs) -> None:
        self._rowid: Optional[int] = None
        kwargs["default_value"] = ""
        kwargs["enabled"] = False
        kwargs["hint"] = "Choose melody"
        with dpg.stage() as self._stage:
            self._tag = dpg.add_input_text(**kwargs)
            with dpg.item_handler_registry() as handler_reg:
                dpg.add_item_clicked_handler(
                    button=dpg.mvMouseButton_Left,
                    callback=self._on_click
                )
                dpg.bind_item_handler_registry(self._tag, handler_reg)

    @property
    def value(self) -> Optional[int]:
        return self._rowid

    @value.setter
    def value(self, value: Optional[int] = None) -> None:
        from database import db

        self._rowid = value
        if value:
            value_str = db.select_melody(value)["name"]
        else:
            value_str = ""

        dpg.set_value(self._tag, value_str)
        self.callback()

    def _on_click(self, sender, app_data) -> None:
        from database import db
        from ui import MelodyLibraryWindow

        def on_select(rowid: int) -> None:
            if rowid:
                self._rowid = rowid
                name = db.select_melody(rowid)["name"]
                dpg.set_value(self._tag, name)
                self.callback()

        MelodyLibraryWindow.select_melody(callback=on_select)
