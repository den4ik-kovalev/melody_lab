from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Union

from melody import Melody
from service import ServiceMethod, MelodyService


@dataclass
class MelodyFormula:
    """ Формула для получения мелодии """

    method_name: str
    params: dict[str, Union[Any, MelodyFormula]] = field(default_factory=dict)
    on_success: Optional[Callable] = None
    on_error: Optional[Callable] = None
    on_clear: Optional[Callable] = None

    _value: Optional[Melody] = field(init=False)

    def __post_init__(self) -> None:
        self._value = None

    @classmethod
    def for_service_method(cls,
                           service_method: ServiceMethod,
                           on_success: Optional[Callable] = None,
                           on_error: Optional[Callable] = None,
                           on_clear: Optional[Callable] = None
                           ) -> MelodyFormula:

        method_info = MelodyService.info.method_info(service_method)
        return cls(
            method_name=method_info.name,
            params={p.name: None for p in method_info.params},
            on_success=on_success,
            on_error=on_error,
            on_clear=on_clear
        )

    @property
    def service_method(self) -> ServiceMethod:
        return getattr(MelodyService, self.method_name)

    @property
    def value(self) -> Melody:
        """ Вычисление мелодии-значения один раз """

        # если значение еще не вычислялось
        if not self._value:

            # получить значения всех формул в params
            kwargs = {
                k: v if not isinstance(v, MelodyFormula) else v.value
                for k, v in self.params.items()
            }

            # и получить результат метода
            try:
                self._value = self.service_method(**kwargs)

            except Exception as e:
                if self.on_error:
                    self.on_error()
                raise

            else:
                if self.on_success:
                    self.on_success()

        return self._value

    def clear_value(self):
        self._value = None
        if self.on_clear:
            self.on_clear()

    def update_params(self, params):
        self.params.update(params)
        self.clear_value()
