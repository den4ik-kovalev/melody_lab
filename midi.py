import os
from enum import Enum, auto
from pathlib import Path
from tempfile import NamedTemporaryFile

import pygame
from music21.stream import Stream, Part
from music21.instrument import BassDrum, Piano
from music21.note import Note, Duration

import config
from melody import Melody


class MidiPlayer:

    class Mode(Enum):
        OS = auto()
        PYGAME = auto()

    def __init__(self, mode: Mode = Mode.OS) -> None:
        self.mode = mode

    def play_melody(self, melody: Melody) -> None:

        stream = self._add_drums(melody)
        file = NamedTemporaryFile(dir=config.temp_dir, suffix=".mid", delete=False)
        filepath = Path(file.name)
        file.close()
        stream.write("mid", filepath)

        if self.mode == self.Mode.OS:
            os.startfile(filepath)
        else:
            self._play_midi_pygame(filepath)

    @staticmethod
    def _add_drums(melody: Melody) -> Stream:

        notes_1 = [Note(duration=Duration(1)) for _ in range(int(melody.duration.quarterLength))]
        part_1 = Part([BassDrum()])
        part_1.append(notes_1)

        notes_2 = list(melody)
        part_2 = Part([Piano()])
        part_2.append(notes_2)

        stream = Stream()
        stream.insert(0, part_1)
        stream.insert(0, part_2)
        return stream

    @staticmethod
    def _play_midi_pygame(midi_path: Path) -> None:
        pygame.mixer.init(buffer=1024)
        pygame.mixer.music.set_volume(0.8)
        try:
            clock = pygame.time.Clock()
            pygame.mixer.music.load(midi_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():  # check if playback has finished
                clock.tick()
        except KeyboardInterrupt:
            pygame.mixer.music.fadeout(1000)
            pygame.mixer.music.stop()
            raise SystemExit
