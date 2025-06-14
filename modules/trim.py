MAX_TRIM = 3
MIN_TRIM = 1

class TrimCalculator:
    def __init__(self):
        self._penalty_value = 1000  # Default value, can be overridden

    def calculate_trim(self, paper_size: float, output: float) -> float:
        """Calculate trim amount (paper_size - output)"""
        return paper_size - output

    def apply_trim_penalty(self, trim: float) -> float:
        """Apply penalty based on trim value and return the penalty amount"""
        penalty = 0
        if trim <= MIN_TRIM:
            penalty += self._penalty_value * abs(trim)
        if trim >= MAX_TRIM:
            penalty += self._penalty_value * trim
        return penalty

    @property
    def penalty_value(self) -> int:
        return self._penalty_value

    @penalty_value.setter
    def penalty_value(self, value: int) -> None:
        self._penalty_value = value