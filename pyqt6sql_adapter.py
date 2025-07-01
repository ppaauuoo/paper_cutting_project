import os
import uuid
import sqlite3
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

class PyQt6SQLAdapter:
    def __init__(self, db_path: str = "pyqt6_orders.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        self.conn = sqlite3.connect(self.db_path)
        c = self.conn.cursor()
        
        # Check if 'moved_path' column exists and add it if not
        c.execute("PRAGMA table_info(csvfile)")
        columns = [col[1] for col in c.fetchall()]
        if 'moved_path' not in columns:
            c.execute("ALTER TABLE csvfile ADD COLUMN moved_path TEXT")
        
        c.execute('''
        CREATE TABLE IF NOT EXISTS csvfile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            moved_path TEXT -- Added this column
        )
        ''')
        
        c.execute('''
        CREATE TABLE IF NOT EXISTS orderlist (
            id TEXT PRIMARY KEY,
            file_id INTEGER,
            order_number INTEGER,
            due_date TEXT,
            front_sheet TEXT,
            c_wave TEXT,
            middle_sheet TEXT,
            b_wave TEXT,
            back_sheet TEXT,
            level INTEGER,
            width REAL,
            length REAL,
            left_edge_cut INTEGER,
            middle_edge_cut INTEGER,
            right_edge_cut INTEGER,
            component_type TEXT,
            quantity INTEGER,
            production_quantity INTEGER,
            edge_type TEXT,
            order_status TEXT,
            excess_percentage INTEGER,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY(file_id) REFERENCES csvfile(id) ON DELETE CASCADE
        )
        ''')
        
        c.execute('''
        CREATE TABLE IF NOT EXISTS planorder (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT,
            plan_quantity INTEGER DEFAULT 0,
            order_leftover INTEGER DEFAULT 0,
            out INTEGER DEFAULT 0,
            paper_roll INTEGER DEFAULT 0,
            blade_type TEXT DEFAULT 'blade_1',
            FOREIGN KEY(order_id) REFERENCES orderlist(id) ON DELETE CASCADE
        )
        ''')
        
        c.execute('''
        CREATE TABLE IF NOT EXISTS optimizationplan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT
        )
        ''')
        
        c.execute('''
        CREATE TABLE IF NOT EXISTS optimizationplan_blade1_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            optimizationplan_id INTEGER,
            planorder_id INTEGER,
            FOREIGN KEY(optimizationplan_id) REFERENCES optimizationplan(id) ON DELETE CASCADE,
            FOREIGN KEY(planorder_id) REFERENCES planorder(id) ON DELETE CASCADE
        )
        ''')
        
        c.execute('''
        CREATE TABLE IF NOT EXISTS optimizationplan_blade2_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            optimizationplan_id INTEGER,
            planorder_id INTEGER,
            FOREIGN KEY(optimizationplan_id) REFERENCES optimizationplan(id) ON DELETE CASCADE,
            FOREIGN KEY(planorder_id) REFERENCES planorder(id) ON DELETE CASCADE
        )
        ''')
        
        self.conn.commit()

    # ---- OrderListAdapter methods ----
    def get_order(self, order_id: str) -> Dict[str, Any]:
        c = self.conn.cursor()
        c.execute("SELECT * FROM orderlist WHERE id=?", (order_id,))
        columns = [col[0] for col in c.description]
        row = c.fetchone()
        return dict(zip(columns, row)) if row else {}

    def update_order_quantity(self, order_id: str, new_quantity: int) -> None:
        self.conn.execute(
            "UPDATE orderlist SET quantity=? WHERE id=?",
            (new_quantity, order_id)
        )
        self.conn.commit()

    def delete_all_orders(self) -> None:
        self.conn.execute("DELETE FROM orderlist")
        self.conn.commit()

    # ---- PlanOrderAdapter methods ----
    def create_plan_orders(self, blade1_params: Dict[str, Any], blade2_params_list: List[Dict[str, Any]]) -> None:
        # Note: This method as defined in the prompt does not return IDs.
        # The OptimizationService would typically call create_plan_order_instance directly
        # and collect IDs, then pass them to create_optimization_plan.
        # We implement it as provided, assuming the service handles ID collection.
        if blade1_params:
            self.create_plan_order_instance(**blade1_params)
        for params in blade2_params_list:
            self.create_plan_order_instance(**params)
        self.conn.commit()

    def create_plan_order_instance(self, **kwargs: Any) -> int:
        columns = []
        values = []
        for key, value in kwargs.items():
            columns.append(key)
            values.append(value)
        
        query = f"""
        INSERT INTO planorder ({','.join(columns)})
        VALUES ({','.join(['?']*len(values))})
        """
        cur = self.conn.cursor()
        cur.execute(query, values)
        return cur.lastrowid

    # ---- OptimizationPlanAdapter methods ----
    def create_optimization_plan(self, blade1_orders: List[Any], blade2_orders: List[Any]) -> int:
        created_at = datetime.now().isoformat()
        cur = self.conn.cursor()
        
        # Create plan
        cur.execute(
            "INSERT INTO optimizationplan (created_at) VALUES (?)",
            (created_at,)
        )
        plan_id = cur.lastrowid
        
        # Link blade1 orders
        for planorder_id in blade1_orders: # Assuming blade1_orders contains planorder IDs
            cur.execute(
                """INSERT INTO optimizationplan_blade1_orders 
                (optimizationplan_id, planorder_id) VALUES (?,?)""",
                (plan_id, planorder_id)
            )
        
        # Link blade2 orders
        for planorder_id in blade2_orders: # Assuming blade2_orders contains planorder IDs
            cur.execute(
                """INSERT INTO optimizationplan_blade2_orders 
                (optimizationplan_id, planorder_id) VALUES (?,?)""",
                (plan_id, planorder_id) # Corrected variable name from plan_order_id to planorder_id
            )
        
        self.conn.commit()
        return plan_id

    def delete_all_plans(self) -> None:
        self.conn.execute("DELETE FROM optimizationplan_blade1_orders")
        self.conn.execute("DELETE FROM optimizationplan_blade2_orders")
        self.conn.execute("DELETE FROM optimizationplan")
        self.conn.commit()

    # ---- UI data retrieval ----
    def get_saved_orders(self) -> List[Dict[str, Any]]:
        query = """
        SELECT 
            p.paper_roll, 
            op.id AS plan_id, -- Use optimizationplan.id as plan_id
            p.blade_type,
            ol.due_date,
            ol.order_number,
            ol.component_type,
            p.plan_quantity,
            p.order_leftover,
            ol.width,
            ol.length,
            ol.edge_type,
            p.out
        FROM planorder p
        JOIN orderlist ol ON p.order_id = ol.id
        LEFT JOIN optimizationplan_blade1_orders b1 ON p.id = b1.planorder_id
        LEFT JOIN optimizationplan_blade2_orders b2 ON p.id = b2.planorder_id
        LEFT JOIN optimizationplan op ON 
            op.id = b1.optimizationplan_id OR op.id = b2.optimizationplan_id
        ORDER BY op.id, p.blade_type, ol.due_date
        """
        cur = self.conn.cursor()
        cur.execute(query)
        columns = [col[0] for col in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

    def close(self):
        self.conn.close()

    def populate_test_data(self):
        """Add sample data for UI testing"""
        # Clear existing data to ensure fresh test data
        self.conn.execute("DELETE FROM optimizationplan_blade1_orders")
        self.conn.execute("DELETE FROM optimizationplan_blade2_orders")
        self.conn.execute("DELETE FROM optimizationplan")
        self.conn.execute("DELETE FROM planorder")
        self.conn.execute("DELETE FROM orderlist")
        self.conn.execute("DELETE FROM csvfile")
        self.conn.commit()

        # Add CSVFile
        self.conn.execute("""
        INSERT INTO csvfile (name, file_path, uploaded_at, moved_path)
        VALUES ('testfile.csv', '/data/test.csv', datetime('now'), NULL)
        """)
        csv_file_id = self.conn.execute("SELECT id FROM csvfile WHERE name='testfile.csv'").fetchone()[0]
        
        # Add OrderLists
        orders_data = [
            (str(uuid.uuid4()), csv_file_id, 1001, '2025-07-01', 'K180', 'C120', 'K180', 'B120', 'K180', 
             1, 45.5, 120.0, 0, 0, 0, 'Front', 100, 0, 'Straight', 'New', 5),
            (str(uuid.uuid4()), csv_file_id, 1002, '2025-07-02', 'K180', 'C120', 'K180', 'B120', 'K180', 
             1, 60.0, 150.0, 0, 0, 0, 'Back', 200, 0, 'Curved', 'New', 5),
            (str(uuid.uuid4()), csv_file_id, 1003, '2025-07-01', 'K180', 'C120', 'K180', 'B120', 'K180', 
             1, 30.0, 80.0, 0, 0, 0, 'Side', 75, 0, 'Straight', 'New', 5),
        ]
        self.conn.executemany("""
        INSERT INTO orderlist (id, file_id, order_number, due_date, front_sheet, c_wave, middle_sheet, b_wave, back_sheet, level, width, length, left_edge_cut, middle_edge_cut, right_edge_cut, component_type, quantity, production_quantity, edge_type, order_status, excess_percentage, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),datetime('now'))
        """, orders_data)
        
        # Add PlanOrders and link to OptimizationPlan
        cur = self.conn.cursor()

        # Create a sample OptimizationPlan
        created_at = datetime.now().isoformat()
        cur.execute("INSERT INTO optimizationplan (created_at) VALUES (?)", (created_at,))
        plan_id_1 = cur.lastrowid

        # PlanOrder for ORD001 (blade_1)
        cur.execute("""
        INSERT INTO planorder (order_id, blade_type, paper_roll, plan_quantity, order_leftover, out)
        VALUES (?, 'blade_1', 66, 100, 0, 2)
        """, (orders_data[0][0],))
        plan_order_id_1 = cur.lastrowid
        cur.execute("""
        INSERT INTO optimizationplan_blade1_orders (optimizationplan_id, planorder_id) VALUES (?,?)
        """, (plan_id_1, plan_order_id_1))

        # PlanOrder for ORD002 (blade_2)
        cur.execute("""
        INSERT INTO planorder (order_id, blade_type, paper_roll, plan_quantity, order_leftover, out)
        VALUES (?, 'blade_2', 70, 200, 0, 3)
        """, (orders_data[1][0],))
        plan_order_id_2 = cur.lastrowid
        cur.execute("""
        INSERT INTO optimizationplan_blade2_orders (optimizationplan_id, planorder_id) VALUES (?,?)
        """, (plan_id_1, plan_order_id_2))

        # PlanOrder for ORD003 (blade_2, part of same plan as ORD001)
        cur.execute("""
        INSERT INTO planorder (order_id, blade_type, paper_roll, plan_quantity, order_leftover, out)
        VALUES (?, 'blade_2', 66, 75, 0, 1)
        """, (orders_data[2][0],))
        plan_order_id_3 = cur.lastrowid
        cur.execute("""
        INSERT INTO optimizationplan_blade2_orders (optimizationplan_id, planorder_id) VALUES (?,?)
        """, (plan_id_1, plan_order_id_3))

        self.conn.commit()
        print("Test data populated successfully.")

# Example of how to populate data (can be run once)
if __name__ == '__main__':
    adapter = PyQt6SQLAdapter()
    adapter.populate_test_data()
    adapter.close()
