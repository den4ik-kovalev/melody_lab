from __future__ import annotations

import copy
import functools
import inspect
import itertools
import random
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

import more_itertools
from music21.duration import Duration
from music21.note import Pitch, Note, Rest

from database import db
from melody import Melody


# Тип данных, обозначающий метод сервиса
ServiceMethod = Callable


class MelodyService:
    """ Класс для создания и изменения мелодий """

    info: ServiceInfo = ...

    class MethodType(Enum):
        """ Типы методов сервиса """

        Initial = 'Initial'  # метод генерирует мелодию с нуля
        Changing = 'Changing'  # метод изменяет существующую мелодию
        Combining = 'Combining'  # метод комбинирует несколько мелодий в одну
        Separating = 'Separating'  # метод разделяет одну мелодию на несколько

    class DurationMode(Enum):
        """ Режимы длительности нот """

        Minimum = 'Minimum'  # максимально короткие ноты
        Maximum = 'Maximum'  # максимально длинные ноты
        Random = 'Random'  # ноты случайной длительности
        Fixed = 'Fixed'  # ноты фиксированной длительности

    class AmountMode(Enum):
        """ Режимы количества нот """

        Minimum = 'Minimum'  # минимальное количество нот
        Maximum = 'Maximum'  # максимальное количество нот
        Random = 'Random'  # случайное количество нот
        Fixed = 'Fixed'  # фиксированное количество нот

    @classmethod
    def FromMidi(cls,
                 path: Path
                 ) -> Melody:
        """
        Загрузить мелодию из midi-файла
        :param path: Путь к файлу
        """
        return Melody.from_midi(path)

    @classmethod
    def FromLibrary(cls,
                    melody_id: int
                    ) -> Melody:
        """
        Загрузить мелодию из библиотеки
        :param melody_id: Идентификатор мелодии
        """
        row = db.select_melody(melody_id)
        return row["obj"]

    @classmethod
    def GenerateMelody(cls,
                       pitches: list[Pitch],
                       length: int,  # todo можно сделать через AmountMode
                       duration: float = 4.0,
                       grid_size: float = 1.0,
                       duration_mode: DurationMode = DurationMode.Random,
                       note_duration: Optional[float] = None,
                       alternate: bool = False,
                       use_all: bool = False
                       ) -> Melody:
        """
        Сгенерировать случайную мелодию
        :param pitches: Набор нот
        :param length: Количество нот
        :param duration: Общая длительность (в четвертях)
        :param grid_size: Шаг сетки (в четвертях)
        :param duration_mode: Насколько тянуть ноты
        :param note_duration: Длина ноты при DurationMode.Fixed (в четвертях)
        :param alternate: Чередовать ноты
        :param use_all: Использовать все ноты из набора
        """

        ''' Проверка параметров '''

        # убрать дубликаты в питчах
        pitches = list(set(pitches))

        # количество нот - положительное
        if length <= 0:
            return Melody()

        # длительность - не меньше чем размер сетки
        elif duration < grid_size:
            raise Exception("Duration must be greater than grid_size")

        # длительность делится на размер сетки
        if int(duration / grid_size) != duration / grid_size:
            raise Exception("Duration is not evenly divisible by grid_size")

        # количество нот может поместиться в мелодию такой длительности
        if int(duration / grid_size) < length:
            raise Exception("Too many notes for given duration and grid_size")

        # если длительность нот - фиксированная
        if duration_mode == cls.DurationMode.Fixed:

            # задана длительность нот
            if not note_duration:
                raise Exception("Note length not set")

            # длительность и количество нот не конфликтуют с длительностью мелодии
            elif note_duration * length > duration:
                raise Exception("Too many notes for given durations")

            # длительность нот не меньше размера сетки
            elif note_duration < grid_size:
                raise Exception("Note duration must be greater than grid_size")

            # длительность нот делится на размер сетки
            elif int(note_duration / grid_size) != note_duration / grid_size:
                raise Exception("Note duration is not evenly divisible by grid_size")

        # для чередования нот нужно хотя бы 2 разных ноты
        if alternate and len(pitches) < 2:
            raise Exception("Too few pitches to alternate")

        # если нужно использовать все ноты, количество нот должно это позволять
        if use_all and len(pitches) > length:
            raise Exception("Too short length to use all notes")

        ''' Основной алгоритм '''
        ''' 1. Вычисление длительности нот и пауз '''

        # если требуется случайная или максимальная длительность нот
        if duration_mode in (cls.DurationMode.Random, cls.DurationMode.Maximum):

            # получить сетку
            grid_indices = list(range(int(duration / grid_size)))

            # случайно выбрать слот под начало каждой ноты и отсортировать выборку
            note_indices = random.sample(grid_indices, k=length)
            note_indices.sort()

            # добавить индекс последнего слота в конец, т.к. далее будет использоваться pairwise
            note_indices.append(len(grid_indices))

            # объекты мелодии для заполнения
            melody_objects = []

            # добавить паузу в начало если нулевой слот не занят нотой
            first_rest_duration = note_indices[0] * grid_size
            if first_rest_duration:
                melody_objects.append(Rest(duration=Duration(first_rest_duration)))

            # для каждой пары подряд идущих слотов
            for note_idx, next_note_idx in itertools.pairwise(note_indices):

                # между слотами нужно будет вставить ноту и возможно паузу

                # создаем ноту пока неизвестной высоты и длительности
                note = Note(duration=Duration(0))

                # количество слотов между началом двух соседних нот
                grid_between = next_note_idx - note_idx

                # если это соседние слоты
                if not grid_between:

                    # единственный слот между ними идет под ноту
                    note_grid = 1
                    rest_grid = 0

                # иначе если слотов между нотами больше одного
                else:

                    # все возможные длительности первой ноты
                    posible_note_grid = list(range(1, grid_between + 1))

                    # выбрать случайную или максимальную длительность ноты в зависимости от режима длительности
                    if duration_mode == cls.DurationMode.Random:
                        note_grid = random.choice(posible_note_grid)
                    else:
                        note_grid = max(posible_note_grid)

                    # оставшиеся слоты займет пауза
                    rest_grid = max(posible_note_grid) - note_grid

                # заполнить длительность ноты и добавить ее к объектам мелодии
                note.duration = Duration(note_grid * grid_size)
                melody_objects.append(note)

                # если есть место под паузу, добавить паузу
                if rest_grid:
                    rest_duration = Duration(rest_grid * grid_size)
                    melody_objects.append(Rest(duration=rest_duration))

            # получается мелодия с нотами корректной длительности
            melody = Melody(melody_objects)

        # иначе - минимальная или фиксированная длительность нот
        else:

            # минимальная длина ноты равна размеру сетки
            if duration_mode == cls.DurationMode.Minimum:
                note_duration = grid_size

            # минимальная длительность ноты - частный случай фиксированной длительности

            # создать нужное количество нот нужной длительности сразу в списке объектов
            melody_objects = [Note(duration=Duration(note_duration)) for _ in range(length)]

            # вычислить количество пауз если каждая пауза будет минимальной длительности
            n_rests = int(duration / grid_size) - int(length * note_duration / grid_size)

            # заполнить свободное место в списке объектов паузами минимальной длительности
            for _ in range(n_rests):
                melody_objects.append(Rest(duration=Duration(grid_size)))

            # перемешать ноты и паузы в списке, создать из них объект мелодии и объединить подряд идущие паузы
            random.shuffle(melody_objects)
            melody = Melody(melody_objects)
            melody.normalize()

        ''' 2. Вычисление высоты нот '''

        # формируется список питчей для нот - chosen_pitches

        # если не требуется чтобы подряд идущие питчи не повторялись
        if not alternate:

            # если не требуется использовать все питчи
            if not use_all:

                # случайно выбрать нужное количество питчей из параметра
                chosen_pitches = random.choices(pitches, k=length)

                # сделать возможные дубликаты уникальными объектами
                chosen_pitches = copy.deepcopy(chosen_pitches)

            # если требуется использовать все питчи
            else:

                # взять в выборку все питчи из параметра
                # и еще столько сколько не хватает до требуемого количества нот
                chosen_pitches = pitches + random.choices(pitches, k=(length - len(pitches)))

                # сделать возможные дубликаты уникальными объектами
                chosen_pitches = copy.deepcopy(chosen_pitches)

            # перемешать выбранные питчи в случайном порядке
            random.shuffle(chosen_pitches)

        # если требуется чтобы подряд идущие питчи не повторялись
        else:

            # если требуется использовать все питчи
            if use_all:

                # взять в выборку все питчи из параметра, скопировать, перемешать
                chosen_pitches = copy.deepcopy(pitches)
                random.shuffle(chosen_pitches)

            # если не требуется использовать все питчи
            else:

                # сделать исходную выборку пустой
                chosen_pitches = []

            # пока выборка не достигнет требуемого размера
            while len(chosen_pitches) < length:

                # выбрать для вставки случайный питч из параметра и скопировать
                pitch_to_insert = random.choice(pitches)
                pitch_to_insert = copy.copy(pitch_to_insert)

                # возможные индексы для вставки в выборку
                indices_to_insert = list(range(len(chosen_pitches) + 1))

                # перебирая индексы для вставки
                while indices_to_insert:

                    # случайно выбрать один индекс
                    idx_to_insert = random.choice(indices_to_insert)

                    # определить питч до него и после него
                    prev_pitch = chosen_pitches[idx_to_insert - 1] if idx_to_insert > 0 else None
                    next_pitch = chosen_pitches[idx_to_insert] if idx_to_insert < len(chosen_pitches) else None

                    # определить можно ли случайный питч вставить в случайный индекс чтобы питчи не шли подряд
                    can_insert_pitch = (prev_pitch != pitch_to_insert) and (next_pitch != pitch_to_insert)

                    # если можно, то вставить в выборку и перейти к выбору нового случайного питча
                    if can_insert_pitch:
                        chosen_pitches.insert(idx_to_insert, pitch_to_insert)
                        break

                    # иначе этот индекс не подходит, нужно перейти к выбору другого места для вставки
                    else:
                        indices_to_insert.remove(idx_to_insert)

        # назначить каждой ноте в мелодии питч из выборки
        for note, pitch in zip(melody.notes, chosen_pitches):
            note.pitch = pitch

        # мелодия готова
        return melody

    @classmethod
    def ChangePitch(cls,
                    melody: Melody,
                    amount_mode: AmountMode = AmountMode.Random,
                    amount: Optional[int] = None,
                    pitches: Optional[list[Pitch]] = None,
                    ) -> Melody:
        """
        Изменить высоту случайных нот в мелодии
        :param melody: Мелодия
        :param amount_mode: Режим количества нот
        :param amount: Количество нот для замены
        :param pitches: Возможные ноты после замены
        """

        ''' Подготовка параметров '''
        # метод не изменяет входные параметры
        melody = copy.deepcopy(melody)

        # если возможные новые ноты не заданы - новые ноты будут среди существующих
        pitches = pitches or [n.pitch for n in melody.notes]

        # удалить дубликаты из возможных новых нот
        pitches = list(set(pitches))

        # количество нот для замены зависит от режима
        if amount_mode == cls.AmountMode.Minimum:
            amount = 1
        elif amount_mode == cls.AmountMode.Random:
            amount = random.randint(1, melody.length)
        elif amount_mode == cls.AmountMode.Maximum:
            amount = melody.length

        ''' Проверка параметров '''

        # если режим количества нот - фиксированный
        if amount_mode == cls.AmountMode.Fixed:

            # требуется задать количество нот
            if not amount:
                raise Exception(f"Invalid amount: {amount}")

            # количество нот для замены должно быть не больше чем всего нот в мелодии
            elif amount > melody.length:
                raise Exception(f"Invalid amount: {amount} > {melody.length}")

        ''' Основной алгоритм '''

        # случайно выбрать из мелодии ноты для замены питча
        notes_to_change = random.choices(melody.notes, k=amount)

        # для каждой ноты
        for note in notes_to_change:
            # выбрать случайный питч из возможных и установить ноте
            random_pitch = random.choice(pitches)
            note.pitch = copy.copy(random_pitch)  # todo проверить что питч отличается

        # мелодия готова
        return melody

    @classmethod
    def SwapPitch(cls,
                  melody: Melody,
                  amount_mode: AmountMode = AmountMode.Minimum,
                  amount: Optional[int] = None) -> Melody:
        """
        Поменять высоту нот в мелодии в случайных парах
        :param melody: Мелодия
        :param amount_mode: Режим количества пар нот
        :param amount: Количество пар нот
        """

        ''' Подготовка параметров '''

        # метод не изменяет входные параметры
        melody = copy.deepcopy(melody)

        # минимальное, максимальное, случайное количество пар нот
        min_amount = 1
        max_amount = melody.length // 2
        random_amount = random.randint(min_amount, max_amount)

        # количество пар нот зависит от режима
        if amount_mode == cls.AmountMode.Minimum:
            amount = min_amount
        elif amount_mode == cls.AmountMode.Maximum:
            amount = max_amount
        elif amount_mode == cls.AmountMode.Random:
            amount = random_amount

        ''' Проверка параметров '''

        # если в мелодии нет даже 2 нот, поменяться им невозможно
        if melody.length < 2:
            raise Exception("melody.length < 2")

        # количество пар должно быть задано к этому шагу
        if not amount:
            raise Exception(f"Invalid amount: {amount}")

        ''' Основной алгоритм '''

        # выбрать и перемешать список нот под замену питча
        notes_to_change = random.sample(melody.notes, k=amount * 2)
        random.shuffle(notes_to_change)

        # заменять питч, итерируясь по 2 элемента
        for note_1, note_2 in more_itertools.batched(notes_to_change, 2):
            note_1.pitch, note_2.pitch = note_2.pitch, note_1.pitch

        # мелодия готова
        return melody

    @classmethod
    def ShiftPitch(cls,
                   melody: Melody,
                   amount_mode: AmountMode = AmountMode.Minimum,
                   amount: Optional[int] = None
                   ) -> Melody:
        """
        Циклично сместить высоту нот мелодии
        :param melody: Мелодия
        :param amount_mode: Режим количества шагов смещения
        :param amount: Количество шагов
        """

        ''' Подготовка параметров '''

        # метод не изменяет входные параметры
        melody = copy.deepcopy(melody)

        # минимальное, максимальное, случайное число шагов
        min_amount = 1
        max_amount = melody.length - 1
        random_amount = random.randint(min_amount, max_amount)

        # количество шагов зависит от режима
        if amount_mode == cls.AmountMode.Minimum:
            amount = min_amount
        elif amount_mode == cls.AmountMode.Maximum:
            amount = max_amount
        elif amount_mode == cls.AmountMode.Random:
            amount = random_amount

        ''' Проверка параметров '''

        # если в мелодии нет даже 2 нот, сдвигать там нечего
        if melody.length < 2:
            return melody

        # количество шагов должно быть задано к этому моменту
        if not amount:
            raise Exception(f"Invalid amount: {amount}")

        ''' Основной алгоритм '''

        # скопировать в отдельный список ноты мелодии и сдвинуть на нужный шаг
        shifted_notes = copy.deepcopy(melody.notes)
        shifted_notes = shifted_notes[amount:] + shifted_notes[:amount]

        # нотам в мелодии присвоить питч ноты из сдвинутого списка
        for note, shifted_note in zip(melody.notes, shifted_notes):
            note.pitch = shifted_note.pitch

        # мелодия готова
        return melody

    @classmethod
    def ShufflePitch(cls,
                     melody: Melody,
                     amount_mode: AmountMode = AmountMode.Maximum,
                     amount: Optional[int] = None
                     ) -> Melody:
        """
        Перемешать высоту случайной группы нот из мелодии
        :param melody: Мелодия
        :param amount_mode: Режим количества измененных нот
        :param amount: Количество измененных нот
        """

        ''' Подготовка параметров '''

        # метод не изменяет входные параметры
        melody = copy.deepcopy(melody)

        # минимальное, максимальное, случайное число измененных нот
        min_amount = 2
        max_amount = melody.length
        random_amount = random.randint(min_amount, max_amount)

        # количество измененных нот зависит от режима
        if amount_mode == cls.AmountMode.Minimum:
            amount = min_amount
        elif amount_mode == cls.AmountMode.Maximum:
            amount = max_amount
        elif amount_mode == cls.AmountMode.Random:
            amount = random_amount

        ''' Проверка параметров '''

        # если в мелодии нет даже 2 нот, перемешивать там нечего
        if melody.length < 2:
            return melody

        # количество измененных нот должно быть задано к этому шагу
        if not amount:
            raise Exception(f"Invalid amount: {amount}")

        # количество измененных нот не больше чем всего нот в мелодии
        if amount > melody.length:
            raise Exception(f"amount = {amount} > melody.length")

        ''' Основной алгоритм '''

        # индексы измененных нот
        note_indexes = random.sample(list(range(melody.length)), amount)

        # они же, перемешанные
        shuffled_indexes = copy.copy(note_indexes)
        random.shuffle(shuffled_indexes)

        # перемешанные питчи
        shuffled_pitches = [melody.notes[si].pitch for si in shuffled_indexes]
        shuffled_pitches = copy.deepcopy(shuffled_pitches)

        # для каждого индекса ноты и его пары
        for note_index, shuffled_pitch in zip(note_indexes, shuffled_pitches):
            # заменить питч ноты по индексу на вычисленный питч парной ноты
            melody.notes[note_index].pitch = shuffled_pitch

        # мелодия готова
        return melody

    @classmethod
    def RemapPitch(cls,
                   melody: Melody,
                   amount_mode: AmountMode = AmountMode.Maximum,
                   amount: Optional[int] = None
                   ) -> Melody:
        """
        Перемешать высоту случайной группы нот, оставляя одинаковые ноты одинаковыми
        :param melody: Мелодия
        :param amount_mode: Режим количества измененных нот
        :param amount: Количество измененных нот
        """

        ''' Подготовка параметров '''

        # метод не изменяет входные параметры
        melody = copy.deepcopy(melody)

        # минимальное, максимальное, случайное число измененных нот
        min_amount = 2
        max_amount = melody.length
        random_amount = random.randint(min_amount, max_amount)

        # количество измененных нот зависит от режима
        if amount_mode == cls.AmountMode.Minimum:
            amount = min_amount
        elif amount_mode == cls.AmountMode.Maximum:
            amount = max_amount
        elif amount_mode == cls.AmountMode.Random:
            amount = random_amount

        ''' Проверка параметров '''

        # если в мелодии нет даже 2 нот, перемешивать там нечего
        if melody.length < 2:
            return melody

        # количество измененных нот должно быть задано к этому шагу
        if not amount:
            raise Exception(f"Invalid amount: {amount}")

        # количество измененных нот не больше чем всего нот в мелодии
        if amount > melody.length:
            raise Exception(f"amount = {amount} > melody.length")

        ''' Основной алгоритм '''

        # ноты, у которых будет меняться питч
        notes_to_change = random.sample(melody.notes, k=amount)

        # маппинг питчей этих нот
        pitches = copy.deepcopy([n.pitch for n in notes_to_change])
        pitches = list(set(pitches))
        shuffled_pitches = copy.deepcopy(pitches)
        random.shuffle(shuffled_pitches)
        pitches_mapping = dict(zip(pitches, shuffled_pitches))

        # заменить питчи согласно маппингу
        for note in notes_to_change:
            note.pitch = pitches_mapping[note.pitch]

        # мелодия готова
        return melody

    @classmethod
    def RevertPitch(cls,
                    melody: Melody) -> Melody:
        """
        Поменять нотам высоту в обратном порядке
        :param melody: Мелодия
        """

        ''' Подготовка параметров '''

        # метод не изменяет входные параметры
        melody = copy.deepcopy(melody)

        ''' Проверка параметров '''

        # если в мелодии нет даже 2 нот, перемешивать там нечего
        if melody.length < 2:
            return melody

        ''' Основной алгоритм '''

        # копии нот в обратном порядке
        melody_notes = copy.deepcopy(melody.notes)
        reversed_notes = reversed(melody_notes)

        # заменить каждой ноте питч на питч ее пары с конца
        for note, reversed_note in zip(melody.notes, reversed_notes):
            note.pitch = reversed_note.pitch

        # мелодия готова
        return melody

    @classmethod
    def ChangeRhythm(cls,
                     melody: Melody,
                     duration: Optional[float] = None,
                     grid_size: Optional[float] = None,
                     duration_mode: DurationMode = DurationMode.Random,
                     note_duration: Optional[float] = None
                     ) -> Melody:
        """
        Поменять ритм мелодии
        :param melody: Мелодия
        :param duration: Длительность новой мелодии (в четвертях)
        :param grid_size: Размер сетки (в четвертях)
        :param duration_mode: Насколько тянуть ноты
        :param note_duration: Длина ноты при DurationMode.Fixed (в четвертях)
        """

        ''' Подготовка параметров '''

        # метод не изменяет входные параметры
        melody = copy.deepcopy(melody)

        # длительность и размер сетки по умолчанию не меняются
        duration = duration or melody.duration.quarterLength
        grid_size = grid_size or melody.grid_size

        ''' Проверка параметров '''

        # проверка отсутствует и предоставляется методу MakeMelody

        ''' Основной алгоритм '''

        # создать новую мелодию с заданными ритмическими параметрами на одной ноте
        another_melody = cls.GenerateMelody(
            pitches=[Pitch("C0")],
            length=melody.length,
            duration=duration,
            grid_size=grid_size,
            duration_mode=duration_mode,
            note_duration=note_duration
        )

        # заменить созданной мелодии питчи на оригинальные
        for idx, note in enumerate(another_melody.notes):
            note.pitch = melody.notes[idx].pitch

        # мелодия готова
        return another_melody

    @classmethod
    def ConcatMelodies(cls,
                       melody_1: Optional[Melody] = None,
                       melody_2: Optional[Melody] = None,
                       melody_3: Optional[Melody] = None,
                       melody_4: Optional[Melody] = None
                       ):
        """
        Последовательно соединить мелодии
        :param melody_1: Мелодия
        :param melody_2: Мелодия
        :param melody_3: Мелодия
        :param melody_4: Мелодия
        """

        melodies = [melody_1, melody_2, melody_3, melody_4]
        melodies = [m for m in melodies if m]
        if not melodies:
            return Melody()
        return functools.reduce(lambda x,y: x+y, melodies)

    @classmethod
    def SubstitutePitch(cls,
                        rhythm: Melody,
                        sequence: Melody,
                        crop_rhythm: bool = True,
                        ) -> Melody:
        """
        Ноты из первой мелодии заменить на ноты из второй, сохранив ритм
        :param rhythm: Первая мелодия
        :param sequence: Вторая мелодия
        :param crop_rhythm: Сократить первую мелодию до числа нот во второй
        """

        ''' Подготовка параметров '''

        # метод не изменяет входные параметры
        rhythm = copy.deepcopy(rhythm)
        sequence = copy.deepcopy(sequence)

        ''' Основной алгоритм '''

        # сократить число нот в первой мелодии, если необходимо
        if crop_rhythm and (rhythm.length > sequence.length):
            rhythm.crop_length(limit=sequence.length)

        # заменить в первой мелодии высоту нот
        for note_1, note_2 in zip(rhythm.notes, sequence.notes):
            note_1.pitch = note_2.pitch

        # мелодия готова
        return rhythm

    @classmethod
    def SubstituteRhythm(cls,
                         sequence: Melody,
                         rhythm: Melody
                         ) -> Melody:
        """
        Ритм из первой мелодии заменить на ритм из второй, сохранив ноты
        :param sequence: Первая мелодия
        :param rhythm: Вторая мелодия
        """

        ''' Подготовка параметров '''

        # метод не изменяет входные параметры
        rhythm = copy.deepcopy(rhythm)
        sequence = copy.deepcopy(sequence)

        ''' Основной алгоритм '''

        # этот метод - брат-близнец метода SubstitutePitch
        result = cls.SubstitutePitch(
            rhythm=rhythm,
            sequence=sequence,
            crop_rhythm=True
        )

        # мелодия готова
        return result


@dataclass
class ServiceInfo:
    """ Информация о методах сервиса """

    @dataclass
    class MethodInfo:
        """ Информация об одном методе сервиса """

        @dataclass
        class ParamInfo:
            """ Информация об одном параметре метода """

            name: str  # название параметра
            description: str  # описание параметра
            optional: bool  # является опциональным параметром
            has_default: bool  # есть значение по умолчанию
            default: Any  # значение по умолчанию
            annotation: str  # type annotation параметра

        type: MelodyService.MethodType  # тип метода
        name: str  # название метода
        func: ServiceMethod  # объект метода
        description: str  # описание метода
        params: list[ParamInfo]  # параметры метода

    methods: list[MethodInfo]  # методы сервиса

    def __init__(self):

        # информация о методах для заполнения
        method_infos = []

        # для каждого метода сервиса и его типа из словаря
        for method, method_type in {
            MelodyService.FromLibrary: MelodyService.MethodType.Initial,
            MelodyService.FromMidi: MelodyService.MethodType.Initial,
            MelodyService.GenerateMelody: MelodyService.MethodType.Initial,
            MelodyService.ChangePitch: MelodyService.MethodType.Changing,
            MelodyService.SwapPitch: MelodyService.MethodType.Changing,
            MelodyService.ShiftPitch: MelodyService.MethodType.Changing,
            MelodyService.ShufflePitch: MelodyService.MethodType.Changing,
            MelodyService.RemapPitch: MelodyService.MethodType.Changing,
            MelodyService.RevertPitch: MelodyService.MethodType.Changing,
            MelodyService.ChangeRhythm: MelodyService.MethodType.Changing,
            MelodyService.ConcatMelodies: MelodyService.MethodType.Combining,
            MelodyService.SubstitutePitch: MelodyService.MethodType.Combining,
            MelodyService.SubstituteRhythm: MelodyService.MethodType.Combining
        }.items():

            # сигнатура функции
            method_signature = inspect.signature(method)

            # получить docstring по строкам
            docstrings = [s.strip() for s in method.__doc__.splitlines() if s.strip()]

            # первая строка - описание метода в целом
            main_doc = docstrings.pop(0)

            # информация о параметрах для заполнения
            param_infos = []

            # остальные строки - информация о параметрах
            # 1 строка содержит 1 параметр
            # для каждой строки из документации метода
            for docstring in docstrings:

                # убрать начало ":param"
                docstring = docstring.lstrip(":param")

                # получить название и описание параметра через двоеточие
                param_name, param_doc = docstring.split(":")
                param_name = param_name.strip()
                param_doc = param_doc.strip()

                # информация по параметру из сигнатуры
                param_signature = method_signature.parameters[param_name]

                # добавить информацию о параметре в список
                param_infos.append(
                    ServiceInfo.MethodInfo.ParamInfo(
                        name=param_name,
                        description=param_doc,
                        optional=("Optional" in param_signature.annotation),
                        has_default=param_signature.default is not param_signature.empty,
                        default=param_signature.default,
                        annotation=param_signature.annotation
                    )
                )

            # добавить информацию о методе в список
            method_infos.append(
                ServiceInfo.MethodInfo(
                    name=method.__name__,
                    type=method_type,
                    func=method,
                    description=main_doc,
                    params=param_infos
                )
            )

        # информация о сервисе готова
        self.methods = method_infos

    def method_info(self, method: ServiceMethod) -> Optional[ServiceInfo.MethodInfo]:
        return [m for m in self.methods if m.func == method][0]

    def method_type_info(self, method_type: MelodyService.MethodType) -> list[ServiceInfo.MethodInfo]:
        return [m for m in self.methods if m.type == method_type]


MelodyService.info = ServiceInfo()
