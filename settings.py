import config
from library.file import YAMLFile
from midi import MidiPlayer


class AppSettings(YAMLFile):

    def __init__(self):
        super(AppSettings, self).__init__(path=(config.app_dir / "settings.yml"), auto_create=False)
        if not self.exists():
            self.write({"midi_player_mode": "PYGAME"})

    @property
    def midi_player_mode(self) -> MidiPlayer.Mode:
        value = self.read()["midi_player_mode"]
        if value == "OS":
            return MidiPlayer.Mode.OS
        else:
            return MidiPlayer.Mode.PYGAME


settings = AppSettings()
