from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass
import random
import time
import polars as pl
from polars import DataFrame as plDataFrame

ROLL_PAPER = [66, 68, 70, 73, 74, 75, 79, 82, 85, 88, 91, 93, 95, 97]
UNIT_CONVERTER = 25.4  # MM _TO_INCH
DEADLINE_RANGE = 500
PLAN_RANGE = DEADLINE_RANGE // 5
COMMON_FILTER = [
    "front_sheet",
    "c_wave",
    "middle_sheet",
    "b_wave",
    "back_sheet",
    "edge_type",
    "width",
    "length",
    "left_edge_cut",
    "middle_edge_cut",
    "right_edge_cut",
    "component_type",
]
LEGACY_FILTER = [
    "front_sheet",
    "c_wave",
    "middle_sheet",
    "b_wave",
    "back_sheet",
]

@dataclass
class HD:
    """Heuristic-based order packing implementation using Polars for optimized performance."""
    orders: plDataFrame
    x: int = 10
    h_type: str = "ffa"
    start_date: Optional[pl.Expr] = None
    stop_date: Optional[pl.Expr] = None
    common: bool = False
    common_init_order: Optional[Dict[str, Any]] = None
    preview: bool = False
    is_build: bool = True

    def __post_init__(self):
        """Initialize and build if required."""
        if self.orders.is_empty():
            raise ValueError("Orders dataframe cannot be empty")
        if self.is_build:
            self.build()

    def build(self) -> None:
        """Main processing pipeline for order packing using lazy evaluation."""
        start_time = time.time()
        
        # Process data using Polars' lazy API for optimization
        data = (
            self.orders.lazy()
            .pipe(self._format_data)
            .pipe(self._date_range_limit)
        )
        
        filter_func = self._filter_common_order if self.common else self._legacy_filter_order
        post_data = filter_func(data.collect())
        
        temp_size = min(ROLL_PAPER)
        data_df = self._run_packing_algorithm(post_data, temp_size)
        
        heuristic_ids = data_df.get_column("id").unique()
        self.heuristic_data = post_data.filter(
            pl.col("id").is_in(heuristic_ids.implode())
        )
        
        if self.preview:
            print(f"Processing completed in {time.time() - start_time:.2f} seconds")

    @staticmethod
    def _format_data(data: pl.LazyFrame) -> pl.LazyFrame:
        """Clean and preprocess order data using Polars expressions."""
        return (
            data
            # First fill nulls to avoid issues with date parsing
            .with_columns(pl.all().fill_null(0))
            # Then parse dates with explicit alias
            .with_columns(
                pl.col("due_date")
                .str.to_datetime(format="%Y-%m-%d", strict=False)
                .alias("due_date")
            )
            .filter(
                (pl.col("length") > 0) &
                (pl.col("width") > 0) &
                (pl.col("quantity") > 500)
            )
            .unique()  # Ensure no duplicate rows
        )

    def _date_range_limit(self, data: pl.LazyFrame) -> pl.LazyFrame:
        """Filter data based on date range constraints using Polars."""
        if self.start_date and self.stop_date:
            data = data.filter(
                (pl.col("due_date") >= self.start_date) &
                (pl.col("due_date") <= self.stop_date)
            )
        
        # Evaluate count without collecting full data
        count = data.select(pl.len()).collect().item()
        if count < PLAN_RANGE:
            raise ValueError("Insufficient orders in date range")
        return data

    def _run_packing_algorithm(
        self,
        data: plDataFrame,
        bin_size: float
    ) -> plDataFrame:
        """Execute selected packing heuristic with Polars optimizations."""
        if self.h_type == "ff":
            return self._first_fit_packing(data, bin_size, self.x)
        elif self.h_type == "ffa":
            sorted_data = data.sort("width")
            return self._first_fit_packing(sorted_data, bin_size, self.x)
        else:
            raise ValueError(f"Unsupported heuristic type: {self.h_type}")

    def _first_fit_packing(
        self,
        data: plDataFrame,
        bin_size: float,
        num_bins: int
    ) -> plDataFrame:
        """Optimized first-fit bin packing using Polars."""
        bins = [[] for _ in range(num_bins)]
        width_col = data.get_column("width")
        id_col = data.get_column("id")
        
        for width, order_id in zip(width_col, id_col):
            bin_found = False
            for bin_list in bins:
                if self._bin_can_fit(bin_list, width, bin_size):
                    bin_list.append((width, order_id))
                    bin_found = True
                    break
            
            if not bin_found:
                bins.append([(width, order_id)])
        
        return self._format_bin_data(bins)

    @staticmethod
    def _bin_can_fit(
        bin_contents: list[Tuple[float, Any]],
        item_width: float,
        bin_size: float
    ) -> bool:
        """Check if bin can accommodate new item with type hints."""
        current_width = sum(w for w, _ in bin_contents)
        return (current_width + item_width) <= bin_size

    @staticmethod
    def _format_bin_data(bins: list[list[Tuple[float, Any]]]) -> plDataFrame:
        """Convert bin data to Polars DataFrame more efficiently."""
        all_items = []
        for bin_items in bins:
            all_items.extend(bin_items)
        return pl.DataFrame({
            "width": [w for w, _ in all_items],
            "id": [i for _, i in all_items]
        })

    def get(self) -> plDataFrame:
        """Retrieve processed heuristic data with proper typing."""
        return self.heuristic_data

    def _legacy_filter_order(
        self,
        data: plDataFrame,
        sample_size: int = 100
    ) -> plDataFrame:
        """Optimized legacy filter using Polars expressions."""
        sample = data.head(DEADLINE_RANGE)
        if sample.height == 0:
            return data
        
        best_plan = None
        best_len = 0
        indices = random.sample(range(sample.height), min(sample_size, sample.height))
        
        for idx in indices:
            init_order = sample.row(idx, named=True)
            mask = pl.all_horizontal(
                [pl.col(col) == init_order[col] for col in LEGACY_FILTER if col in init_order]
            )
            plan = sample.filter(mask).group_by("width").head(2)
            
            current_len = plan.height
            if current_len > best_len:
                best_plan = plan
                best_len = current_len
                if best_len >= PLAN_RANGE:
                    break
        
        return best_plan if best_plan is not None else sample

    def _filter_common_order(
        self,
        data: plDataFrame,
        sample_size: int = 100
    ) -> plDataFrame:
        """Optimized common filter using Polars expressions."""
        if not self.common_init_order:
            raise ValueError("Common init order required for common filtering")
        
        # Prepare initial filter
        init_order = {
            **self.common_init_order,
            "length": self.common_init_order.get("cut_len", 0)
        }
        
        # Apply initial filter
        base_filters = LEGACY_FILTER + ["length"]
        mask = pl.all_horizontal(
            [pl.col(col) == init_order[col]
             for col in base_filters
             if col in init_order and col in data.columns]
        )
        filtered = data.filter(mask)
        
        if filtered.height == 0:
            raise ValueError("No matching orders for common criteria")
        
        best_plan = None
        best_len = 0
        indices = random.sample(range(filtered.height), min(sample_size, filtered.height))
        
        for idx in indices:
            order = filtered.row(idx, named=True)
            mask = pl.all_horizontal(
                [pl.col(col) == order[col]
                 for col in COMMON_FILTER
                 if col in order and col in data.columns]
            )
            orders = data.filter(mask).group_by("width").head(2)
            
            current_len = orders.height
            if current_len > best_len:
                best_plan = orders
                best_len = current_len
                if best_len >= PLAN_RANGE:
                    break
        
        return best_plan if best_plan is not None else filtered

def main():
    """Main function to test the HD module with data/cleaned_plan2024.csv"""
    import os
    from datetime import datetime
    
    # Load test data
    test_file = os.path.join("../data", "cleaned_plan2024.csv")
    if not os.path.exists(test_file):
        raise FileNotFoundError(f"Test data file not found: {test_file}")
    
    # Read data with Polars
    df = pl.read_csv(test_file)
    
    # Test parameters
    test_params = {
        "orders": df,
        "x": 10,
        "h_type": "ffa",
        "start_date": datetime(2024, 1, 1),
        "stop_date": datetime(2024, 12, 31),
        "preview": True
    }
    
    print("\nRunning HD module with cleaned_plan2024.csv...")
    print(f"\nTest Data: {df.height} orders")
   
    # Test legacy filter
    print("\nTesting legacy filter:")
    hd_legacy = HD(**test_params, common=False)
    result_legacy = hd_legacy.get()
    print(f"Legacy filter result: {result_legacy.height} orders")
    
    # Test common filter with sample init order
    if "width" in df.columns and "length" in df.columns:
        print("\nTesting common filter:")
        sample_order = df.row(0, named=True)
        hd_common = HD(
            **test_params,
            common=True,
            common_init_order={
                "cut_len": sample_order["length"],
                "width": sample_order["width"]
            }
        )
        result_common = hd_common.get()
        print(f"Common filter result: {result_common.height} orders")
    
    # Show sample results
    print("\nSample results from legacy filter:")
    print(result_legacy.head(3))
    print("\nSample results from common filter:")
    print(result_common.head(3))
   
    print("\nProcessing completed successfully")


if __name__ == "__main__":
    main()
