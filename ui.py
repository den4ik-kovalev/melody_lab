from __future__ import annotations

import traceback
from pathlib import Path
from typing import Any, Callable, Optional

import dearpygui.dearpygui as dpg
import easygui
from music21.scale import MajorScale

from database import db
from formula import MelodyFormula
from service import ServiceMethod, MelodyService
from library.dpg_painter import DpgPainter
from library.value_editor import (
    ValueEditor, PositiveIntInput, Checkbox, StrCombobox, FloatCombobox, EnumCombobox,
    FilepathInput, PitchSetInput, MelodyInput
)
from library.modals import ModalWindow, MessageBox, ModalInputText
from library.node_editor import Node, NodeEditor, NodeFreezer
from library.window import Window
from midi import MidiPlayer
from settings import settings


class ServiceNode(Node):

    @property
    def formula(self) -> MelodyFormula:
        return self._formula

    def __init__(self, method: ServiceMethod) -> None:

        self._formula = MelodyFormula.for_service_method(
            service_method=method,
            on_success=(lambda: self.paint(0, 255, 0)),
            on_error=(lambda: self.paint(255, 0, 0)),
            on_clear=(lambda: self.paint(0, 0, 0))
        )

        inputs: list[str] = []
        params: list[[str, ValueEditor]] = []

        method_info = MelodyService.info.method_info(method)
        for param_info in method_info.params:

            if "Melody" in param_info.annotation:
                inputs.append(param_info.name)
                continue

            default_value = param_info.default if param_info.has_default else None
            if param_info.annotation == "bool":
                editor = Checkbox(default_value=default_value)
            elif param_info.name == "path":
                editor = FilepathInput(width=100)
            elif param_info.name == "melody_id":
                editor = MelodyInput(width=100)
            elif param_info.name == "pitches":
                if not param_info.has_default:
                    default_value = MajorScale("C").pitches
                editor = PitchSetInput(default_value=default_value, width=100)
            elif param_info.name == "length":
                if not param_info.has_default:
                    default_value = 4
                editor = PositiveIntInput(default_value=default_value, width=100)
            elif param_info.name == "amount":
                editor = PositiveIntInput(default_value=default_value, width=100)
            elif param_info.name == "duration":
                editor = PositiveIntInput(default_value=default_value, width=100, step=4)
            elif param_info.name in ("grid_size", "note_duration"):
                editor = FloatCombobox(
                    [0.25, 0.5, 1.0, 2.0],
                    default_value=default_value,
                    width=100
                )
            elif param_info.name == "duration_mode":
                editor = EnumCombobox(
                    MelodyService.DurationMode,
                    default_value=default_value,
                    width=100
                )
            elif param_info.name == "amount_mode":
                editor = EnumCombobox(
                    MelodyService.AmountMode,
                    default_value=default_value,
                    width=100
                )
            else:
                raise NotImplementedError

            params.append((param_info.name, editor))

        with dpg.stage():
            btn_play = dpg.add_button(label="Play", width=100, height=30, callback=self._on_play)

        super(ServiceNode, self).__init__(
            label=method_info.name, inputs=inputs, outputs_count=1
        )
        for param in params:
            self.add_param(*param)
        self.add_widget(btn_play)

    def copy(self) -> ServiceNode:
        return ServiceNode(method=self._formula.service_method)

    def _on_play(self) -> None:
        midi_player = MidiPlayer(settings.midi_player_mode)
        try:
            melody = self._formula.value
        except Exception as e:
            print(traceback.format_exc())
            MessageBox(str(e)).add()
        else:
            midi_player.play_melody(melody)

    def _on_params_change(self) -> None:
        super(ServiceNode, self)._on_params_change()
        self._formula.update_params({p.key: p.value for p in self._params})

    def _on_input_connected(self, input: Node.Input) -> None:
        super(ServiceNode, self)._on_input_connected(input)
        self._formula.update_params({input.key: self.parent_by_input(input).formula})

    def _on_input_disconnected(self, input: Node.Input) -> None:
        super(ServiceNode, self)._on_input_disconnected(input)
        self._formula.update_params({input.key: None})

    def _on_ancestor_change(self, ancestor: Node) -> None:
        super(ServiceNode, self)._on_ancestor_change(ancestor)
        self._formula.clear_value()


class ResultNode(Node):

    @property
    def parent(self) -> Optional[ServiceNode]:
        return self.parent_by_input(self._inputs[0])

    def __init__(self) -> None:

        with dpg.stage():
            btn_play = dpg.add_button(label="Play", width=100, height=30, callback=self._on_play)
            btn_save = dpg.add_button(label="Save", width=100, height=30, callback=self._on_save)
            btn_download = dpg.add_button(label="Download", width=100, height=30, callback=self._on_download)

        super(ResultNode, self).__init__(
            label="Melody", inputs=[""], outputs_count=0
        )
        self.add_widget(btn_play)
        self.add_widget(btn_save)
        self.add_widget(btn_download)

    def copy(self) -> ResultNode:
        return ResultNode()

    def _on_play(self) -> None:

        if not self.parent:
            return

        midi_player = MidiPlayer(settings.midi_player_mode)

        try:
            melody = self.parent.formula.value
        except Exception as e:
            print(traceback.format_exc())
            MessageBox(str(e)).add()
        else:
            midi_player.play_melody(melody)

    def _on_save(self) -> None:

        def input_callback(name: str) -> None:
            if not name:
                return
            melody = self.parent.formula.value
            db.insert_melody(name, melody)
            MessageBox(f"Melody saved: {name}", no_close=True).add()

        if not self.parent:
            return
        try:
            _ = self.parent.formula.value
        except Exception as e:
            MessageBox(str(e)).add()
        else:
            ModalInputText(hint="Enter melody name", callback=input_callback).add()

    def _on_download(self):
        if not self.parent:
            return
        try:
            melody = self.parent.formula.value
        except Exception as e:
            MessageBox(str(e)).add()
        else:
            default = (Path.home() / "untitled.mid").resolve()
            path = easygui.filesavebox(
                default=str(default),
                filetypes=["*.mid"]
            )
            if path:
                melody.save_midi(path)


class MelodyBuilderWindow(Window):

    def __init__(self) -> None:

        with dpg.stage() as self._stage:

            self._tag = dpg.add_window(
                label="Melody Builder",
                width=dpg.get_viewport_client_width(),
                height=dpg.get_viewport_client_height() - 20,
                no_move=True,
                on_close=self._on_close
            )

            self._node_editor = NodeEditor()
            self._node_editor.add(parent=self._tag)

            with dpg.handler_registry():
                self._delete_kph = dpg.add_key_press_handler(
                    key=dpg.mvKey_Delete,
                    callback=self._node_editor.delete_selection
                )

            with dpg.menu_bar(parent=self._tag):
                with dpg.menu(label="Edit"):
                    dpg.add_menu_item(
                        label="Clear editor",
                        callback=self._node_editor.clear
                    )
                with dpg.menu(label="Nodes"):
                    for method_type in MelodyService.MethodType:
                        methods_info = MelodyService.info.method_type_info(method_type)
                        with dpg.menu(label=method_type.value):
                            for method_info in methods_info:
                                dpg.add_menu_item(
                                    label=method_info.name,
                                    callback=self._on_add_service_node,
                                    user_data=method_info.func
                                )
                    with dpg.menu(label="Resulting"):
                        dpg.add_menu_item(
                            label="Melody",
                            callback=self._on_add_result_node
                        )
                with dpg.menu(label="Presets") as self._presets_menu:
                    dpg.add_menu_item(
                        label="Save preset",
                        callback=self._on_save_preset
                    )
                    # dpg.add_separator()  # todo random preset
                    # dpg.add_menu_item(
                    #     label="Random Preset",
                    #     callback = self._on_random_preset
                    # )

                    rows = db.select_presets_info()
                    if rows:
                        dpg.add_separator()

                    for row in rows:
                        with dpg.menu(label=row["name"]):
                            dpg.add_menu_item(
                                label="Load",
                                callback=self._on_load_preset,
                                user_data=row["rowid"]
                            )
                            dpg.add_menu_item(
                                label="Delete",
                                callback=self._on_delete_preset,
                                user_data=row["rowid"]
                            )
                with dpg.menu(label="Docs"):
                    dpg.add_menu_item(
                        label="Methods",
                        callback=self._on_show_docs
                    )

    def _on_close(self) -> None:
        dpg.delete_item(self._delete_kph)

    def _on_add_service_node(self, sender, app_data, method: ServiceMethod) -> None:
        self._node_editor.add_node(ServiceNode(method))

    def _on_add_result_node(self) -> None:
        self._node_editor.add_node(ResultNode())

    def _on_save_preset(self) -> None:

        def input_callback(name: str) -> None:
            if not name:
                return
            state = NodeFreezer.get_editor_state(self._node_editor)
            rowid = db.insert_preset(name, state=state)
            MessageBox(f"Preset saved: {name}", no_close=True).add()

            with dpg.menu(parent=self._presets_menu, label=name):
                dpg.add_menu_item(
                    label="Load",
                    callback=self._on_load_preset,
                    user_data=rowid
                )
                dpg.add_menu_item(
                    label="Delete",
                    callback=self._on_delete_preset,
                    user_data=rowid
                )

        ModalInputText(hint="Enter preset name", callback=input_callback).add()

    def _on_random_preset(self) -> None:
        pass

    def _on_load_preset(self, sender, app_data, rowid: int) -> None:
        preset = db.select_preset(rowid)
        state = preset["state"]
        NodeFreezer.restore_editor_state(self._node_editor, state)

    def _on_delete_preset(self, sender, app_data, rowid: int) -> None:
        db.delete_preset(rowid)
        dpg.delete_item(dpg.get_item_parent(sender))
        MessageBox("Preset deleted", no_close=True).add()

    def _on_show_docs(self) -> None:
        with dpg.window(modal=True, width=800, height=600):
            for method_type in MelodyService.MethodType:
                with dpg.collapsing_header(label=method_type.value, default_open=True):
                    for method_info in MelodyService.info.method_type_info(method_type):
                        with dpg.collapsing_header(
                            label=method_info.name, indent=20, bullet=True
                        ):
                            dpg.add_text(method_info.description)
                            dpg.add_separator()
                            for param_info in method_info.params:
                                dpg.add_text(f"{param_info.name} - {param_info.description}")


class MelodyLibraryWindow(Window):

    white_rgb = (255, 255, 255)
    red_rgb = (255, 0, 0)
    blue_rgb = (102, 204, 255)
    yellow_rgb = (255, 255, 153)

    @classmethod
    def select_melody(cls, callback: Callable[[int], Any]) -> None:
        window = cls(selection_mode=True)
        window.add()
        window.on_close = (lambda: callback(window.selected))
        window.center()

    @property
    def selected(self) -> Optional[int]:
        return self._selected

    def __init__(self, selection_mode=False) -> None:
        self.on_close: Optional[Callable] = None
        self._rows: dict[int, dict] = {}
        self._selected: Optional[int] = None

        with dpg.stage() as self._stage:

            with dpg.window(
                label="Melody Library",
                width=400,
                height=400,
                modal=selection_mode,
                on_close=self._on_close
            ) as self._tag:

                self._input_tag = dpg.add_input_text(
                    label="Search",
                    width=300,
                    callback=self._on_search,
                    on_enter=True,
                    hint="N:SomeName; D:4; M:1",
                )
                dpg.add_separator()

                with dpg.table(
                    parent=self._tag,
                    header_row=True,
                    policy=dpg.mvTable_SizingStretchProp,
                    row_background=True,
                    borders_innerH=True,
                    borders_innerV=True,
                    context_menu_in_body=True,
                    sortable=True,
                    callback=self._on_sort
                ) as table_tag:
                    dpg.add_table_column(user_data="name", label="Name", width_stretch=True)
                    dpg.add_table_column(user_data="length", label="Length")
                    dpg.add_table_column(user_data="duration", label="Duration")
                    dpg.add_table_column(user_data="grid_size", label="Grid")
                    dpg.add_table_column(user_data="favorite", label="Mark")
                for record in db.select_melodies_info():
                    with dpg.table_row(parent=table_tag) as row_tag:
                        with dpg.menu(label=record["name"]):
                            dpg.add_text(record["name"])
                            dpg.add_separator()
                            dpg.add_menu_item(
                                label="Play",
                                callback=self._on_play,
                                user_data=record["rowid"]
                            )
                            if not selection_mode:
                                dpg.add_menu_item(
                                    label="Download",
                                    callback=self._on_download,
                                    user_data=record["rowid"]
                                )
                                dpg.add_menu_item(
                                    label="Mark",
                                    callback=self._on_mark,
                                    user_data=row_tag
                                )
                                dpg.add_separator()
                                delete_mi_tag = dpg.add_menu_item(
                                    label="Delete",
                                    callback=self._on_delete,
                                    user_data=row_tag
                                )
                                DpgPainter.paint_text(delete_mi_tag, *self.red_rgb)
                            else:
                                dpg.add_separator()
                                select_mi_tag = dpg.add_menu_item(
                                    label="Select",
                                    callback=self._on_select,
                                    user_data=record["rowid"]
                                )
                                DpgPainter.paint_text(select_mi_tag, *self.blue_rgb)
                        dpg.add_text(str(record["length"]))
                        dpg.add_text(str(record["duration"]))
                        dpg.add_text(str(record["grid_size"]))
                        dpg.add_text("+" if record["favorite"] else "")

                        row_children = dpg.get_item_children(row_tag, 1)
                        for child in row_children:
                            rgb = self.yellow_rgb if record["favorite"] else self.white_rgb
                            DpgPainter.paint_text(child, *rgb)

                    self._rows[row_tag] = record

    def _on_close(self) -> None:
        if self.on_close:
            self.on_close()

    def _on_play(self, sender, app_data, rowid: int) -> None:
        record = db.select_melody(rowid)
        melody = record["obj"]
        midi_player = MidiPlayer(settings.midi_player_mode)
        midi_player.play_melody(melody)

    def _on_download(self, sender, app_data, rowid: int) -> None:
        record = db.select_melody(rowid)
        melody = record["obj"]
        default_path = (Path.home() / f"{record['name']}.mid").resolve()
        path = easygui.filesavebox(
            default=str(default_path),
            filetypes=["*.mid"]
        )
        if path:
            melody.save_midi(path)

    def _on_mark(self, sender, app_data, row_tag: int) -> None:
        record = self._rows[row_tag]
        db.switch_melody_favorite(record["rowid"])

        fav = not record["favorite"]
        record["favorite"] = fav

        row_children = dpg.get_item_children(row_tag, 1)
        dpg.set_value(row_children[-1], "+" if fav else "")
        for child in row_children:
            rgb = self.yellow_rgb if fav else self.white_rgb
            DpgPainter.paint_text(child, *rgb)

    def _on_delete(self, sender, app_data, row_tag: int) -> None:
        record = self._rows[row_tag]
        db.delete_melody(record["rowid"])
        dpg.delete_item(row_tag)
        self._rows.pop(row_tag)

    def _on_select(self, sender, app_data, rowid: int) -> None:
        self._selected = rowid
        dpg.delete_item(self._tag)
        self._on_close()

    def _on_sort(self, sender, app_data) -> None:
        if app_data is None:
            return

        column_tag, direction = app_data[0]
        record_field = dpg.get_item_configuration(column_tag)["user_data"]
        reverse = direction < 0

        order = list(self._rows.keys())
        order.sort(key=lambda x: self._rows[x][record_field], reverse=reverse)
        dpg.reorder_items(sender, 1, order)

    def _on_search(self) -> None:
        query = dpg.get_value(self._input_tag)
        show = list(self._rows.keys())
        if query:
            try:
                for part in query.split(";"):
                    part = part.strip()
                    key, value = part.split(":")
                    key = key.lower()
                    if key in ("n", "name"):
                        show = [r for r in show if value.lower() in self._rows[r]["name"].lower()]
                    elif key in ("l", "length"):
                        show = [r for r in show if int(value) == self._rows[r]["length"]]
                    elif key in ("d", "duration"):
                        show = [r for r in show if float(value) == self._rows[r]["duration"]]
                    elif key in ("g", "grid"):
                        show = [r for r in show if float(value) == self._rows[r]["grid_size"]]
                    elif key in ("m", "mark"):
                        value = {"0": 0, "1": 1, "-": 0, "+": 1}.get(value)
                        show = [r for r in show if value == self._rows[r]["favorite"]]
            except Exception:
                show = list(self._rows.keys())

        for row in self._rows.keys():
            dpg.configure_item(row, show=(row in show))


class SettingsWindow(ModalWindow):

    def __init__(self) -> None:

        settings_dct = settings.read()

        with dpg.stage() as self._stage:
            with dpg.window(modal=True, width=200, on_close=self._on_close) as window:
                dpg.add_text("MIDI player mode")
                self._cmb_midi_player_mode = StrCombobox(
                    ["OS", "PYGAME"],
                    width=185,
                    default_value=settings_dct["midi_player_mode"]
                )
                self._cmb_midi_player_mode.add(window)

    def _on_close(self):
        settings_dct = {"midi_player_mode": self._cmb_midi_player_mode.value}
        settings.write(settings_dct)
