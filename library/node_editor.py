from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator, Optional

import dearpygui.dearpygui as dpg

from library.dpg_painter import DpgPainter
from library.value_editor import ValueEditor


class Node:

    @dataclass
    class Input:
        node: Node
        key: str
        tag: int

    @dataclass
    class Param:
        key: str
        editor: ValueEditor

        @property
        def value(self) -> Any:
            return self.editor.value

        @value.setter
        def value(self, val: Any) -> None:
            self.editor.value = val

    @dataclass
    class Output:
        node: Node
        tag: int

    @dataclass
    class Link:
        tag: int
        input: Node.Input
        output: Node.Output

    def __init__(self, label: str, inputs: list[str], outputs_count: int) -> None:

        self._links: list[Node.Link] = []
        self._params: list[Node.Param] = []
        self._widgets: list[int] = []

        with dpg.stage() as self._stage:

            self._label = label
            with dpg.node(label=label) as self._tag:

                self._inputs: list[Node.Input] = []
                for input_key in inputs:
                    with dpg.node_attribute(label=input_key, attribute_type=dpg.mvNode_Attr_Input) as attr:
                        dpg.add_text(input_key)
                        self._inputs.append(Node.Input(node=self, key=input_key, tag=attr))

                self._outputs: list[Node.Output] = []
                for _ in range(outputs_count):
                    attr = dpg.add_node_attribute(attribute_type=dpg.mvNode_Attr_Output)
                    self._outputs.append(Node.Output(node=self, tag=attr))

    def __hash__(self) -> int:
        return self._tag

    @property
    def tag(self) -> int:
        return self._tag

    @property
    def inputs(self) -> Iterator[Node.Input]:
        for i in self._inputs:
            yield i

    @property
    def params(self) -> Iterator[Node.Param]:
        for p in self._params:
            yield p

    @property
    def outputs(self) -> Iterator[Node.Output]:
        for o in self._outputs:
            yield o

    @property
    def links(self) -> Iterator[Node.Link]:
        for l in self._links:
            yield l

    @property
    def input_links(self) -> Iterator[Node.Link]:
        for l in self._links:
            if l.input in self._inputs:
                yield l

    @property
    def output_links(self) -> Iterator[Node.Link]:
        for l in self._links:
            if l.output in self._outputs:
                yield l

    @property
    def busy_inputs(self) -> Iterator[Node.Input]:
        for l in self.input_links:
            yield l.input

    @property
    def parents(self) -> Iterator[Node]:
        for l in self.input_links:
            yield l.output.node

    @property
    def children(self) -> Iterator[Node]:
        for l in self.output_links:
            yield l.input.node

    @property
    def ancestors(self) -> Iterator[Node]:
        for p in self.parents:
            yield p
            yield from p.ancestors

    @property
    def descendants(self) -> Iterator[Node]:
        for c in self.children:
            yield c
            yield from c.descendants

    @property
    def params_dict(self) -> dict[str, Any]:
        return {p.key: p.value for p in self.params}

    @params_dict.setter
    def params_dict(self, data: dict[str, Any]) -> None:
        for key, value in data.items():
            param = [p for p in self.params if p.key == key][0]
            param.value = value
        self._on_params_change()

    def add(self, parent: int) -> None:
        dpg.push_container_stack(parent)
        dpg.unstage(self._stage)
        dpg.pop_container_stack()

    def add_param(self, key: str, editor: ValueEditor) -> None:
        with dpg.node_attribute(parent=self._tag, attribute_type=dpg.mvNode_Attr_Static) as attr:
            editor.add(parent=attr)
            dpg.configure_item(editor.tag, label=key)
            editor.callback = self._on_params_change
            self._params.append(Node.Param(key=key, editor=editor))
            self._on_params_change()

    def add_widget(self, widget: int) -> None:
        with dpg.node_attribute(parent=self._tag, attribute_type=dpg.mvNode_Attr_Static) as attr:
            dpg.move_item(widget, parent=attr)
            self._widgets.append(widget)

    def add_input_link(self, link: Node.Link) -> None:
        if link.input not in self._inputs:
            raise ValueError("link.input not in self._inputs")
        if link.input in self.busy_inputs:
            raise ValueError("link.input in self.busy_inputs")
        self._links.append(link)
        self._on_input_connected(link.input)

    def remove_input_link(self, link: Node.Link) -> None:
        if link not in self.input_links:
            raise ValueError("link not in self.input_links")
        self._links.remove(link)
        self._on_input_disconnected(link.input)

    def add_output_link(self, link: Node.Link) -> None:
        if link.output not in self._outputs:
            raise ValueError("link.output not in self._outputs")
        self._links.append(link)

    def remove_output_link(self, link: Node.Link) -> None:
        if link not in self.output_links:
            raise ValueError("link not in self.output_links")
        self._links.remove(link)

    def parent_by_input(self, input: Node.Input) -> Optional[Node]:
        if input not in self._inputs:
            raise ValueError("input not in self._inputs")
        if input not in self.busy_inputs:
            return None
        link = [l for l in self.input_links if l.input is input][0]
        return link.output.node

    def copy(self) -> Node:
        """ Копия, которая используется при восстановлении состояния NodeEditor """
        # Внимание!
        # При таком копировании не сохраняются Node._params и Node._widgets
        # Чтобы класс копировался корректно, нужно переопределить этот метод
        # При этом значения Node._params выставятся корректно, т.к. они сохраняются отдельно от Node
        return Node(
            label=self._label,
            inputs=[i.key for i in self._inputs],
            outputs_count=len(self._outputs)
        )

    def paint(self, r: int, g: int, b: int) -> None:
        DpgPainter.paint_node(self._tag, r, g, b)

    def _on_params_change(self) -> None:
        for node in self.descendants:
            node._on_ancestor_change(self)

    def _on_input_connected(self, input: Node.Input) -> None:
        for node in self.descendants:
            node._on_ancestor_change(self)

    def _on_input_disconnected(self, input: Node.Input) -> None:
        for node in self.descendants:
            node._on_ancestor_change(self)

    def _on_ancestor_change(self, ancestor: Node) -> None:
        pass


class NodeEditor:

    def __init__(self):
        self._nodes: list[Node] = []
        with dpg.stage() as self._stage:
            self._tag = dpg.add_node_editor(
                callback=self._on_link,
                delink_callback=self._on_delink,
                minimap=True,
                minimap_location=1
            )

    @property
    def tag(self) -> int:
        return self._tag

    @property
    def nodes(self) -> Iterator[Node]:
        for n in self._nodes:
            yield n

    @property
    def node_inputs(self) -> Iterator[Node.Input]:
        for node in self._nodes:
            for input in node.inputs:
                yield input

    @property
    def node_outputs(self) -> Iterator[Node.Output]:
        for node in self._nodes:
            for output in node.outputs:
                yield output

    @property
    def node_links(self) -> Iterator[Node.Link]:
        for node in self._nodes:
            for link in node.input_links:
                yield link

    def add(self, parent: int) -> None:
        dpg.push_container_stack(parent)
        dpg.unstage(self._stage)
        dpg.pop_container_stack()

    def clear(self) -> None:
        for node in self._nodes:
            dpg.delete_item(node.tag)
        self._nodes.clear()

    def add_node(self, node: Node) -> None:

        node.add(parent=self._tag)

        if self._nodes:
            pos_x, pos_y = dpg.get_item_pos(self._nodes[-1].tag)
            size_x, size_y = dpg.get_item_rect_size(self._nodes[-1].tag)
            pos = [pos_x + size_x + 40, pos_y]
        else:
            pos = [20, 20]

        dpg.set_item_pos(node.tag, pos)
        self._nodes.append(node)

    def delete_selection(self) -> None:

        for link_tag in dpg.get_selected_links(self._tag):
            link = [nl for nl in self.node_links if nl.tag == link_tag][0]
            self.remove_link(link)

        for node_tag in dpg.get_selected_nodes(self._tag):
            node = [n for n in self._nodes if n.tag == node_tag][0]
            for link in node.links:
                if dpg.does_item_exist(link.tag):
                    self.remove_link(link)

            dpg.delete_item(node_tag)
            self._nodes.remove(node)

    def create_link(self, input: Node.Input, output: Node.Output) -> None:
        link_tag = dpg.add_node_link(output.tag, input.tag, parent=self._tag)
        link = Node.Link(tag=link_tag, input=input, output=output)
        input.node.add_input_link(link)
        output.node.add_output_link(link)

    def remove_link(self, link: Node.Link) -> None:
        link.input.node.remove_input_link(link)
        link.output.node.remove_output_link(link)
        dpg.delete_item(link.tag)

    def _on_link(self, sender, app_data) -> None:
        output_tag, input_tag = app_data
        node_input = [ni for ni in self.node_inputs if ni.tag == input_tag][0]
        node_output = [no for no in self.node_outputs if no.tag == output_tag][0]
        if node_input in node_input.node.busy_inputs:
            return
        self.create_link(node_input, node_output)

    def _on_delink(self, sender, app_data):
        link_tag = app_data
        link = [nl for nl in self.node_links if nl.tag == link_tag][0]
        self.remove_link(link)


class NodeFreezer:
    """ Методы для сохранения состояния NodeEditor """

    @dataclass
    class NodeState:
        obj: Node
        pos: list[int]
        params_dict: dict[str, Any]

    @dataclass
    class EditorState:
        nodes: list[NodeFreezer.NodeState]

    @staticmethod
    def get_editor_state(editor: NodeEditor) -> NodeFreezer.EditorState:
        return NodeFreezer.EditorState(
            nodes=[
                NodeFreezer.NodeState(
                    obj=node,
                    pos=dpg.get_item_pos(node.tag),
                    params_dict=node.params_dict
                )
                for node in editor.nodes
            ]
        )

    @staticmethod
    def restore_editor_state(editor: NodeEditor, state: NodeFreezer.EditorState) -> None:

        editor.clear()
        old_2_new = {}  # NodeState.obj будут отличаться по tag, поэтому сопоставляем их словарем

        # Восстанавливаем параметры и позиции узлов
        for node_state in state.nodes:
            old = node_state.obj
            new = old.copy()
            old_2_new[old] = new
            editor.add_node(new)
            dpg.set_item_pos(new.tag, node_state.pos)
            new.params_dict = node_state.params_dict

        # Восстанавливаем ссылки между узлами
        for old, new in old_2_new.items():

            for old_link in old.input_links:

                old_input = old_link.input
                new_input = [i for i in new.inputs if i.key == old_input.key][0]

                old_output = old_link.output
                old_parent = old_output.node
                old_output_idx = list(old_parent.outputs).index(old_output)
                new_parent = old_2_new[old_parent]
                new_output = list(new_parent.outputs)[old_output_idx]

                editor.create_link(new_input, new_output)
