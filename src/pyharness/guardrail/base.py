from abc import ABC, abstractmethod
from pyharness.models import Action, GuardResult


class Guard(ABC):
    @abstractmethod
    def check(self, action: Action) -> GuardResult:
        ...