from __future__ import annotations

import copy
import functools
import itertools
from fractions import Fraction
from os import PathLike

from music21.note import Note, Rest
from music21.stream import Stream

from library.tools import Tools


class Melody(Stream):

    def __str__(self) -> str:
        return str(list(self))

    def __add__(self, other) -> Melody:
        other = copy.deepcopy(other)
        melody = copy.deepcopy(self)
        melody.append(list(other))
        return melody

    @property
    def length(self) -> int:
        """ Длина мелодии - количество нот в ней """
        return len(self.notes)

    @property
    def notes(self) -> list[Note]:
        """ Список нот мелодии """
        return list(super(Melody, self).notes)

    @property
    def grid_size(self) -> float:
        """ Размер сетки мелодии - НОК длительностей ее объектов """
        durations = [obj.duration.quarterLength for obj in self]
        durations = [Fraction(d) for d in durations]
        return float(functools.reduce(Tools.fraction_gcd, durations))

    @classmethod
    def from_midi(cls, path: PathLike) -> Melody:
        """ Загрузить мелодию из миди-файла """
        from music21 import converter
        part = converter.parse(path).parts[0]
        return cls([obj for measure in part for obj in measure.notesAndRests])

    def save_midi(self, path: PathLike):
        """ Записать мелодию в миди-файл """
        self.write("midi", path)

    def normalize(self) -> None:
        """ Нормализовать паузы - удалить нулевые и объединить подряд идущие """

        def drop_null_rests() -> None:
            """ Удалить паузы нулевой длительности """
            null_rests = [obj for obj in self if (isinstance(obj, Rest) and obj.duration.quarterLength == 0)]
            self.remove(null_rests)

        def join_consecutive_rests():
            """ Объединить подряд идущие паузы """
            for obj_1, obj_2 in itertools.pairwise(self):
                if isinstance(obj_1, Rest) and isinstance(obj_2, Rest):
                    obj_2.duration.quarterLength += obj_1.duration.quarterLength
                    obj_1.duration.quarterLength = 0

        # удалить нулевые паузы на случай если 1 такая в начале или в конце
        drop_null_rests()

        # объединить подряд идущие паузы между нотами
        join_consecutive_rests()

        # удалить нулевые паузы, появившиеся после предыдущего шага
        drop_null_rests()

    def crop_length(self, limit: int) -> None:
        """ Сократить мелодию до {limit} нот """

        # если лимит не положительный, просто убрать из мелодии все объекты
        if limit <= 0:
            self.remove(list(self))
            return

        # контейнер под новые объекты
        new_objects = []

        # количество добавленных нот
        notes_count = 0

        # заполнение new_objects
        for obj in self:

            # ноту добавлять, если не достигнут лимит по количеству нот
            if isinstance(obj, Note):

                # добавить ноту и завершить алгоритм после совпадения с лимитом
                new_objects.append(obj)
                notes_count += 1
                if notes_count == limit:
                    break

            # паузу всегда добавлять
            else:
                new_objects.append(obj)

        # обновить список объектов мелодии
        self.remove(list(self))
        self.append(new_objects)
