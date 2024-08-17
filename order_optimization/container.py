from abc import ABC, abstractmethod
from typing import Callable, Dict, List

from pandas import DataFrame


class ModelInterface(ABC):

    @abstractmethod
    def run(self, set_progress: Callable) -> None:
        pass

    @property
    @abstractmethod
    def output(self) -> DataFrame:
        pass

    @property
    @abstractmethod
    def fitness_values(self) -> float:
        pass

    @property
    @abstractmethod
    def PAPER_SIZE(self) -> float:
        pass

class ModelContainer:
    def __init__(
        self,
        model: ModelInterface ,
        set_progress: Callable
    ):
        self.model = model
        self.set_progress = set_progress
    
    def run (self) -> None:
        self.model.run(self.set_progress)
    @property
    def fitness_values(self) -> float:
        return self.model.fitness_values

    @property
    def output(self) -> DataFrame:
        return self.model.output

    @property
    def PAPER_SIZE(self) -> float:
        return self.model.PAPER_SIZE



class ProviderInterface(ABC):
    @abstractmethod
    def get(self) -> DataFrame:
        pass


class OrderContainer:
    def __init__(
        self,
        provider: ProviderInterface
    ):
        self.provider = provider
    
    def get(self) -> DataFrame:
        return self.provider.get()