import dearpygui.dearpygui as dpg


class DpgPainter:

    @staticmethod
    def paint_node(tag: int, r: int, g: int, b: int):
        with dpg.theme() as theme:
            with dpg.theme_component(dpg.mvNode):
                dpg.add_theme_color(dpg.mvNodeCol_TitleBar, (r, g, b), category=dpg.mvThemeCat_Nodes)
        dpg.bind_item_theme(tag, theme)

    @staticmethod
    def paint_text(tag: int, r: int, g: int, b: int):
        with dpg.theme() as theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Text, (r, g, b), category=dpg.mvThemeCat_Core)
        dpg.bind_item_theme(tag, theme)
