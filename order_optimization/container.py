from abc import ABC, abstractmethod
from pandas import DataFrame
from typing import Callable


class ModelInterface(ABC):
    total: float
    fitness: float

    @property
    @abstractmethod
    def run(self) -> Callable:
        pass

    @property
    @abstractmethod
    def output(self) -> DataFrame:
        pass

    @property
    @abstractmethod
    def PAPER_SIZE(self) -> float:
        pass


class ModelContainer:
    def __init__(
        self,
        model: ModelInterface,
    ):
        self.model = model
        self.total = model.total
        self.fitness = model.fitness

    def run(self) -> None:
        self.model.run()

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
    def __init__(self, provider: ProviderInterface):
        self.provider = provider

    def get(self) -> DataFrame:
        return self.provider.get()
