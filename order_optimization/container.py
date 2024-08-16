from typing import Dict, List

from pandas import DataFrame


class ModelContainer:
    def __init__(
        self,
        model: object ,
        set_progress: callable
    ):
        self.model = model
        self.set_progress = set_progress
    

    async def run (self) -> None:
        await self.model.run

    def get(self) -> object:
        return self.model.get(self.set_progress)

    @property
    def fitness_values(self) -> float:
        return self.model.fitness_values

    @property
    def output(self) -> List[Dict]:
        return self.model.output

    @property
    def PAPER_SIZE(self) -> int:
        return self.model.PAPER_SIZE

class OrderContainer:
    def __init__(
        self,
        provider: object
    ):
        self.provider = provider
    
    def get(self) -> DataFrame:
        return self.provider.get()