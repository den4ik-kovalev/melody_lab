import dearpygui.dearpygui as dpg
from loguru import logger

import config
from library.folder import Folder
from ui import MelodyBuilderWindow, MelodyLibraryWindow, SettingsWindow


logger.add("error.log", format="{time} {level} {message}", level="ERROR")


@logger.catch
def main() -> None:

    Folder(config.temp_dir).clear()

    dpg.create_context()

    with dpg.viewport_menu_bar():
        with dpg.menu(label="Menu"):
            dpg.add_menu_item(label="Melody Builder", callback=lambda: MelodyBuilderWindow().add)
            dpg.add_menu_item(label="Melody Library", callback=lambda: MelodyLibraryWindow().add)
            dpg.add_separator()
            dpg.add_menu_item(label="Settings", callback=lambda: SettingsWindow().add)

    dpg.create_viewport(title="Melody Lab")
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.maximize_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == '__main__':
    main()
