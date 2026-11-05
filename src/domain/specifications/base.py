# src/domain/specifications/base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class Specification(ABC, Generic[T]):
    """
    Interfaz base para el patrón Specification con soporte para composición booleana
    (AND, OR, NOT).
    """

    @abstractmethod
    def is_satisfied_by(self, candidate: T) -> bool:
        """Evalúa si el candidato cumple con la regla de negocio."""
        raise NotImplementedError("Subclases deben implementar is_satisfied_by.")

    def and_(self, other: Specification[T]) -> Specification[T]:
        return AndSpecification(self, other)

    def or_(self, other: Specification[T]) -> Specification[T]:
        return OrSpecification(self, other)

    def not_(self) -> Specification[T]:
        return NotSpecification(self)


class AndSpecification(Specification[T]):
    """Especificación compuesta que exige que ambas especificaciones se cumplan."""

    def __init__(self, primera: Specification[T], segunda: Specification[T]) -> None:
        self._primera = primera
        self._segunda = segunda

    def is_satisfied_by(self, candidate: T) -> bool:
        return self._primera.is_satisfied_by(candidate) and self._segunda.is_satisfied_by(candidate)


class OrSpecification(Specification[T]):
    """Especificación compuesta que exige que al menos una especificación se cumpla."""

    def __init__(self, primera: Specification[T], segunda: Specification[T]) -> None:
        self._primera = primera
        self._segunda = segunda

    def is_satisfied_by(self, candidate: T) -> bool:
        return self._primera.is_satisfied_by(candidate) or self._segunda.is_satisfied_by(candidate)


class NotSpecification(Specification[T]):
    """Especificación compuesta que invierte el resultado de la especificación original."""

    def __init__(self, spec: Specification[T]) -> None:
        self._spec = spec

    def is_satisfied_by(self, candidate: T) -> bool:
        return not self._spec.is_satisfied_by(candidate)
