"""Generic Result type for functional error handling."""

from typing import Generic, TypeVar, Union

T = TypeVar("T")
E = TypeVar("E")


class Ok(Generic[T]):
    __slots__ = ("_value",)

    def __init__(self, value: T):
        self._value = value

    @property
    def value(self) -> T:
        return self._value

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False

    def unwrap(self) -> T:
        return self._value

    def unwrap_or(self, default: T) -> T:
        return self._value

    def __repr__(self) -> str:
        return f"Ok({self._value!r})"


class Err(Generic[E]):
    __slots__ = ("_error",)

    def __init__(self, error: E):
        self._error = error

    @property
    def error(self) -> E:
        return self._error

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True

    def unwrap(self) -> None:
        if isinstance(self._error, Exception):
            raise self._error
        raise RuntimeError(f"Unwrapped Err: {self._error}")

    def unwrap_or(self, default: T) -> T:
        return default

    def __repr__(self) -> str:
        return f"Err({self._error!r})"


Result = Union[Ok[T], Err[E]]
