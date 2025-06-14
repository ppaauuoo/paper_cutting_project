from ortools.linear_solver import pywraplp
from rules import Logic
import pandas as pd

def solve_cutting_stock_lp(orders: pd.DataFrame, paper_size: float, blade: int = None, common: bool = False):
    solver = pywraplp.Solver.CreateSolver('SCIP')
    
    # Decision variables with blade consideration
    x = {i: solver.IntVar(0, int(orders.loc[i, 'quantity']), f'x_{i}') for i in orders.index}
    # Initialize all business rules
    logic = Logic(orders, None, common, paper_size, blade)
    
    # Total width calculation
    total_width = solver.Sum(x[i] * orders.loc[i, 'width'] for i in x)
    trim = paper_size - total_width
    
    # Main objective: Minimize trim deviation from ideal 2
    # Replace the current objective with:
    abs_diff = solver.NumVar(0, solver.infinity(), 'abs_diff')
    solver.Add(abs_diff >= trim - 2)
    solver.Add(abs_diff >= -(trim - 2))
    solver.Minimize(abs_diff)

    # 1. Paper type compatibility
    first_idx = logic.get_first_solution([1]*len(orders))  # Simulate GA solution
    edge_types = orders['edge_type'].tolist()
    init_type = 1 if edge_types[first_idx] in ['X', 'Y'] else 2
    
    for i in orders.index:
        if (init_type == 1 and edge_types[i] not in ['X', 'Y']) or \
           (init_type == 2 and edge_types[i] == 'X'):
            solver.Add(x[i] == 0)

    # 2. Order quantity constraints
    min_qty = orders.loc[first_idx, 'quantity']
    for i in orders.index:
        solver.Add(x[i] * orders.loc[i, 'quantity'] >= min_qty)

    # 3. Paper length constraints
    solver.Add(solver.Sum(x[i] for i in x) <= 5)

    # 4. Trim constraints (1-3 units)
    solver.Add(trim >= 1)
    solver.Add(trim <= 3)

    # 5. Common order parity
    # Replace the current common order parity constraint with:
    if common:
        total_sum = solver.Sum(x[i] for i in x)
        parity_var = solver.BoolVar('parity_var')
        solver.Add(total_sum - 2 * solver.Sum(solver.IntVar(0, solver.infinity(), f'pair_{i}') for i in range(len(x))) == parity_var)
        solver.Add(parity_var == 0)

    # 6. X-Y sequence validation
    # Replace the X-Y sequence validation block with:
    if any(et in ['X', 'Y'] for et in edge_types):
        for i in orders.index[1:]:
            prev_type = edge_types[i-1]
            curr_type = edge_types[i]
            if prev_type == 'X' and curr_type != 'Y':
                solver.Add(x[i-1] == 0, name=f'seq_constraint_X_{i}')
            elif prev_type == 'Y' and curr_type == 'X':
                solver.Add(x[i-1] == 0, name=f'seq_constraint_Y_{i}')

    # 7. Blade configuration
    if blade is not None:
        solver.Add(solver.Sum(x[i] for i in x) <= blade * 2)

    # Solve and format output
    status = solver.Solve()
    solution = {i: x[i].solution_value() for i in x}
    
    # Apply blade logic to output
    result_df = pd.DataFrame({
        'order_id': orders['id'],
        'out': [solution[i] for i in orders.index],
        'blade': blade if blade else orders.index + 1
    })
    
    return {
        'status': status,
        'trim': trim.solution_value(),
        'solution': result_df,
        'total_used': total_width.solution_value(),
        'paper_size': paper_size
    }


if __name__ == "__main__":
    # Sample test data matching GA implementation
    # sample_orders = pd.DataFrame({
    #     'id': [1, 2, 3, 4],
    #     'order_number': ['A100', 'A101', 'B200', 'C300'],
    #     'quantity': [50, 60, 75, 40],
    #     'width': [10.5, 12.0, 9.8, 11.2],
    #     'edge_type': ['X', 'Y', 'N', 'W'],
    #     'length': [100, 120, 90, 110],
    #     'component_type': ['front', 'back', 'middle', 'special'],
    #     'due_date': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04'],
    #     'front_sheet': [1, 0, 0, 1],
    #     'c_wave': [0, 1, 1, 0],
    #     'middle_sheet': [0, 0, 1, 0],
    #     'b_wave': [0, 1, 0, 1],
    #     'back_sheet': [0, 1, 1, 0],
    #     'level': [2, 2, 3, 1],
    #     'left_edge_cut': [0, 0, 1, 0],
    #     'middle_edge_cut': [1, 1, 0, 1],
    #     'right_edge_cut': [0, 0, 1, 1]
    # })
    
    sample_orders = pd.read_csv('../data/cleaned_plan2024.csv').head(100)

    # Run LP solver
    result = solve_cutting_stock_lp(
        orders=sample_orders,
        paper_size=66,
        blade=2,
        common=True
    )

    # Display results
    if result['status'] == pywraplp.Solver.OPTIMAL:
        print("\nLP Test Results:")
        print(f"Optimal trim: {result['trim']:.2f}")
        print(f"Total used width: {result['total_used']:.2f}/{result['paper_size']}")
        print("Solution:\n", result['solution'])
    else:
        print("No optimal solution found")
