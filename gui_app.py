import os
import sys
import threading
import time
import traceback
import uuid
from typing import Any, Dict, List

import pandas as pd

# Add this before import statements
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime  # เพิ่ม import datetime สำหรับการบันทึกเวลา
from time import sleep  # เพิ่ม import sleep

UNIT_CONVERTER = 25.4

# เพิ่ม import ที่จำเป็นสำหรับ retry mechanism
# Add at top of gui_app.py
import humanize
import numpy as np
from PyQt6.QtCore import (
    QDate,
    QDateTime,
    QLocale,
    QObject,
    Qt,
    QThread,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QDialog,  # Changed from 'QDialg' to 'QDialog'
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressDialog,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Import ORD class
from modules.ordplan import ORD

# Import the new SQL adapter
from pyqt6sql_adapter import PyQt6SQLAdapter

# Try importing optimization service (as fallback if core not available)
try:
    # Use `core` instead of `modules.core`
    from core.container import ModelContainer, OrderContainer  # เพิ่ม OrderContainer
    from core.optimization_service import OptimizationService
    from modules.hd import HD  # เพิ่ม HD

    # Import actual adapters and settings
    from ordplan_project.settings import MAX_TRIM, MIN_TRIM, ROLL_PAPER
except ImportError as e:
    print(f'Import core failed: {str(e)}')
    OptimizationService = None
    ModelContainer = None
    OrderContainer = None # กำหนดค่าเป็น None
    HD = None # กำหนดค่าเป็น None
    # Print the full traceback for debugging
    traceback.print_exc()
    # Fallback for ROLL_PAPER if settings cannot be imported
    ROLL_PAPER = [66, 68, 70, 73, 74, 75, 79, 82, 85, 88, 91, 93, 95, 97]


# Mock optimization service if core not available
class MockOptimizationService:
    def run_optimization_pipeline(self, **kwargs):  # Changed to accept any keyword arguments
        """Accept required parameters (size, start_date, stop_date)"""
        # Simulate 3 seconds loading time
        time.sleep(3)
        # Simulate progress updates
        progress_callback = kwargs.get('progress_callback')
        if progress_callback:
            for i in range(1, 101):
                time.sleep(0.03) # Simulate work
                progress_callback(i)
        return {
            'roll': '66',
            'init_order_number': 28,  # sample data
            'total': 65.8,  # sample data
            'trim': 0.2     # sample data
        }

    # เพิ่มเมธอดนี้เพื่อจำลองการบันทึกผลลัพธ์
    def save_optimization_results(self, results):
        """Mock method to simulate saving optimization results."""
        print(f"Mock saving optimization results: {results}")
        # ในสถานการณ์จริง จะมีการบันทึกลงฐานข้อมูลหรือไฟล์

class MockModelContainer:
    fitness_values = 0
    total = 100
    PAPER_SIZE = 100
    output = "Mock Output"

# Removed PyQt Adapters as they are replaced by PyQt6SQLAdapter

# Worker signals for thread communication
class WorkerSignals(QObject):
    progress = pyqtSignal(int)
    finished = pyqtSignal(object)

# เพิ่มฟังก์ชัน monkey_patch_excepthook เพื่อจัดการข้อผิดพลาดที่ไม่ได้ดักจับ
def monkey_patch_excepthook():
    original_excepthook = sys.excepthook
    def custom_excepthook(etype, value, tb):
        traceback.print_exception(etype, value, tb)
        QApplication.restoreOverrideCursor()
        QApplication.processEvents()
        original_excepthook(etype, value, tb)
    sys.excepthook = custom_excepthook

# Add this class definition
class OptimizationWorker(QObject):
    finished = pyqtSignal(object)
    progress = pyqtSignal(float)

    def __init__(self, service, start_date, stop_date, roll_size):
        super().__init__()
        self.service = service
        self.start_date = start_date
        self.stop_date = stop_date
        self.roll_size = roll_size
        
        # ตัวแปรของ retry mechanism
        self.LENGTH = 100  # จำนวนครั้งที่ลอง
        self.MAX_RETRY_COUNT = round(self.LENGTH * 10 / 100)  # 10% ของ LENGTH
        self.e_count = 0
        self.total_success_rates = []
        
    def run(self):
        try:
            # Convert roll_size from string to float
            size_value = float(self.roll_size) if self.roll_size is not None else None
            
            final_results = {}
            
            # ---- ส่วนของ retry mechanism ----
            for i in range(self.LENGTH):
                try:
                    # รายงาน progress รวม (outer loop)
                    # Note: การ emit progress ที่นี่จะทำให้ progress bar กระโดดไปที่ค่าเริ่มต้นของแต่ละรอบ
                    # หากต้องการ progress ที่ราบรื่นกว่า ควรให้ progress_callback เป็นผู้จัดการ progress ทั้งหมด
                    total_progress_ratio = (i + 1) / self.LENGTH
                    self.progress.emit(total_progress_ratio * 100)

                    # รัน optimization
                    self.results = self.service.run_optimization_pipeline(
                        start_date=self.start_date,
                        stop_date=self.stop_date,
                        size=size_value,
                        progress_callback=self.progress_callback
                    )
                    
                    # บันทึกผลลัพธ์
                    self.service.save_optimization_results(self.results)
                    final_results = self.results

                    # คำนวณ success rate
                    success_rate = round(1 / (self.e_count + 1) * 100)
                    self.total_success_rates.append(success_rate)
                    print(f"Success Rate (current block): {success_rate}%")
                    print(f"Total Average Success Rate: {round(np.mean(self.total_success_rates))}%")
                    self.e_count = 0 # รีเซ็ต error count เมื่อสำเร็จ
                    
                except Exception as e_optimize:
                    self.e_count += 1
                    print(f"Optimization error: {e_optimize}")
                            
                if self.e_count > self.MAX_RETRY_COUNT:
                    print("[red]Error Exceed. Stopping optimization loop.")
                    break
                    
                # หยุดสักครู่ระหว่างการลอง
                sleep(0.5)
            # ---- จบส่วน retry mechanism ----

            self.finished.emit(final_results)
        except Exception as e:
            traceback.print_exc()
            self.finished.emit({"error": f"RuntimeError: {str(e)}"})
    
    def progress_callback(self, value):
        # ปรับ progress จาก optimization ให้สอดคล้องกับ retry loop
        # Note: การใช้ self.e_count (error count) เป็นฐานอาจทำให้ progress ไม่ราบรื่น
        # หากเกิดข้อผิดพลาดบ่อยครั้ง
        adjusted_progress = (value / 100) * (1 / self.LENGTH)
        self.progress.emit(
            (self.e_count / self.LENGTH + adjusted_progress) * 100
        )

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # เรียกใช้ monkey_patch_excepthook ก่อนสร้าง widgets
        monkey_patch_excepthook()
        self.setWindowTitle(f"Paper Cutting Optimization - {QLocale().toString(QDateTime.currentDateTime(), QLocale.FormatType.LongFormat)}")
        self.setGeometry(100, 100, 600, 400)

        self._create_widgets()
        self._setup_layout()
        self._connect_signals()

    def _create_widgets(self):
        # Start date
        self.start_date_edit = QDateEdit(self)
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate())

        # End date
        self.stop_date_edit = QDateEdit(self)
        self.stop_date_edit.setCalendarPopup(True)
        self.stop_date_edit.setDate(QDate.currentDate().addDays(7))

        # ROLL_PAPER dropdown
        self.roll_paper_combo = QComboBox(self)
        # Convert integers in ROLL_PAPER to strings before adding to ComboBox
        self.roll_paper_combo.addItems([str(paper) for paper in ROLL_PAPER])

        # File selection
        self.file_path_line_edit = QLineEdit(self)
        self.file_browse_button = QPushButton("Browse...", self)
        # In MainWindow._create_widgets:
        self.file_db_button = QPushButton("Manage CSV Files", self)

        # Buttons
        self.start_button = QPushButton("Start", self)
        self.view_button = QPushButton("View", self)
        self.reset_button = QPushButton("Reset", self)

    def _setup_layout(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        main_layout = QVBoxLayout(main_widget)
        form_layout = QFormLayout()

        form_layout.addRow("Start Date:", self.start_date_edit)
        form_layout.addRow("Stop Date:", self.stop_date_edit)
        form_layout.addRow("Roll Paper:", self.roll_paper_combo)

        file_selection_layout = QHBoxLayout()
        file_selection_layout.addWidget(self.file_path_line_edit)
        file_selection_layout.addWidget(self.file_browse_button)
        file_selection_layout.addWidget(self.file_db_button)  # NEW
        form_layout.addRow("File Selection:", file_selection_layout)

        main_layout.addLayout(form_layout)

        button_layout = QHBoxLayout()
        button_layout.addStretch(1) # To align buttons to the right
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.view_button)
        button_layout.addWidget(self.reset_button)

        main_layout.addLayout(button_layout)
        main_layout.addStretch(1) # To push content to the top

    def _connect_signals(self):
        self.file_browse_button.clicked.connect(self._browse_file)
        self.start_button.clicked.connect(self._on_start_clicked)
        self.view_button.clicked.connect(self._on_view_clicked)
        self.reset_button.clicked.connect(self._on_reset_clicked)
        self.file_db_button.clicked.connect(self._show_file_manager)

    def _browse_file(self):
        try: # เพิ่ม try-except block
            file_name, _ = QFileDialog.getOpenFileName(self, "Select File", "", "CSV Files (*.csv)")
            if file_name:
                self.file_path_line_edit.setText(file_name)
                print(f"Selected File: {file_name}")
                
                # Save file metadata to database
                adapter = PyQt6SQLAdapter()
                try:
                    name = os.path.basename(file_name)
                    now = datetime.now().isoformat()
                    
                    # Insert CSV file metadata
                    adapter.conn.execute(
                        "INSERT INTO csvfile (name, file_path, uploaded_at) VALUES (?, ?, ?)",
                        (name, file_name, now)
                    )
                    adapter.conn.commit()
                    print(f"Saved '{name}' to database")
                    
                    # Get the inserted file ID
                    cur = adapter.conn.execute("SELECT last_insert_rowid()")
                    file_id = cur.fetchone()[0]
                    
                    # Process and save orders using ORD class
                    self._process_and_save_orders(adapter, file_id, file_name, now)
                    
                except Exception as e:
                    print(f"Error processing file: {e}")
                    traceback.print_exc()
                    # Optional: Rollback file metadata insert if order processing fails
                    adapter.conn.execute("DELETE FROM csvfile WHERE id=?", (file_id,))
                    adapter.conn.commit()
                finally:
                    adapter.close()
                    
        except Exception as e:
            traceback.print_exc()
            print(f"File Browse Error: {str(e)}")

    def _process_and_save_orders(self, adapter, file_id, file_path, now):
        try:
            # Read CSV file
            orders_df = pd.read_csv(file_path, encoding='utf-8')
            print(f"Loaded {len(orders_df)} raw orders from CSV")
            
            # 'ORDPLAN_PROJECT' แพ็กเกจที่ถูกต้องอาจไม่สามารถเข้าถึงได้โดยตรง
            # ดังนั้นจึงใช้ค่าที่ฮาร์ดโค้ดสำหรับพารามิเตอร์ ORD
            ord_processor = ORD(
                orders=orders_df,
                deadline_scope=0,        # ค่าเริ่มต้น
                size=66,                  # ขนาดกระดาษม้วนเริ่มต้น
                tuning_values=3,          # ตัวหารกระดาษม้วน
                filter_value=16,          # ช่วงคำสั่งที่ยอมรับได้
                _filter_diff=True,        # เปิดใช้งานตัวกรองความแตกต่าง
                common=False,             # ปิดใช้งานตัวกรองทั่วไป
                filler=None,              # ไม่มีฟิลเลอร์
                selector=None,            # ไม่มีตัวเลือก
                first_date_only=False,    # ไม่กรองเฉพาะวันที่ล่าสุด
                preview=False,            # ปิดใช้งานโหมดพรีวิว
            )
            
            # Process orders
            ord_processor.build()
            processed_orders = ord_processor.get()
            print(f"Processed {len(processed_orders)} orders using ORD logic")
              
            # Prepare orders for insertion based on setter.py logic
            orders_to_insert = []
            for _, row in processed_orders.iterrows():
                try:
                    due_date = pd.to_datetime(row["กำหนดส่ง"], format="%m/%d/%y")
                except (ValueError, TypeError):
                    print(f"Warning: Could not parse due_date for order {row.get('เลขที่ใบสั่งขาย', 'N/A')}. Using current time.")
                    due_date = datetime.now()

                order_id = f"{row['เลขที่ใบสั่งขาย'] }-{row['ชนิดส่วนประกอบ']}-{uuid.uuid4()}"

                order_data = (
                    order_id,                # id
                    file_id,                 # file_id
                    row.get("เลขที่ใบสั่งขาย", 0),  # order_number
                    due_date,                # due_date
                    row.get("แผ่นหน้า", "not defined"),      # front_sheet
                    row.get("ลอน C", "not defined"),          # c_wave
                    row.get("แผ่นกลาง", "not defined"),      # middle_sheet
                    row.get("ลอน B", "not defined"),          # b_wave
                    row.get("แผ่นหลัง", "not defined"),      # back_sheet
                    row.get("จน.ชั้น", 0),                   # level
                    round(row.get("กว้างผลิต", 0) / UNIT_CONVERTER, 4),  # width
                    round(row.get("ยาวผลิต", 0) / UNIT_CONVERTER, 4),    # length
                    row.get("ทับเส้นซ้าย", 0),               # left_edge_cut
                    row.get("ทับเส้นกลาง", 0),               # middle_edge_cut
                    row.get("ทับเส้นขวา", 0),                # right_edge_cut
                    row.get("ชนิดส่วนประกอบ", "not defined"), # component_type
                    row.get("จำนวนสั่งขาย", 0),              # quantity
                    row.get("จำนวนสั่งผลิต", 0),             # production_quantity
                    row.get("ประเภททับเส้น", "not defined"),  # edge_type
                    row.get("สถานะใบสั่ง", "not defined"),    # order_status
                    row.get("% ที่เกิน", 0),                  # excess_percentage
                    now,                                      # created_at
                    now                                       # updated_at
                )
                orders_to_insert.append(order_data)
            
            # Insert orders into database
            adapter.conn.executemany(
                """
                INSERT INTO orderlist (
                    id, file_id, order_number, due_date, front_sheet, c_wave, middle_sheet, b_wave, back_sheet,
                    level, width, length, left_edge_cut, middle_edge_cut, right_edge_cut,
                    component_type, quantity, production_quantity, edge_type, order_status, excess_percentage,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                orders_to_insert
            )
            
            adapter.conn.commit()
            print(f"Saved {len(orders_to_insert)} processed orders to database")
            
        except Exception as e:
            traceback.print_exc()
            print(f"Order processing error: {str(e)}")
            # Re-raise the exception to be caught by the outer try-except in _browse_file
            raise

    def _show_file_manager(self):
        dialog = FileManagerDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_file_id:
            adapter = PyQt6SQLAdapter()
            try:
                cur = adapter.conn.cursor()
                cur.execute("SELECT file_path FROM csvfile WHERE id=?", (dialog.selected_file_id,))
                file_path_tuple = cur.fetchone()
                if file_path_tuple:
                    file_path = file_path_tuple[0]
                    self.file_path_line_edit.setText(file_path)
            except Exception as e:
                print(f"Error fetching selected file: {e}")
                traceback.print_exc()
            finally:
                adapter.close()

    def _on_start_clicked(self):
        try: # เพิ่ม try-except block
            self.selected_start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
            self.selected_stop_date = self.stop_date_edit.date().toString("yyyy-MM-dd")
            roll_paper = self.roll_paper_combo.currentText()
            file_path = self.file_path_line_edit.text()
            print(f"Start Clicked!")
            print(f"  Start Date: {self.selected_start_date}")
            print(f"  Stop Date: {self.selected_stop_date}")
            print(f"  Roll Paper: {roll_paper}")
            print(f"  File Path: {file_path}")
            self._show_progress_dialog()
        except Exception as e:
            traceback.print_exc()
            print(f"Start Click Error: {str(e)}")

    def _show_progress_dialog(self):
        # Prepare to run optimization
        start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        stop_date = self.stop_date_edit.date().toString("yyyy-MM-dd")
        roll_paper = self.roll_paper_combo.currentText()
        file_path = self.file_path_line_edit.text()

        # Modify in _show_progress_dialog:
        file_id = None
        if file_path:
            adapter = PyQt6SQLAdapter()
            try:
                cur = adapter.conn.cursor()
                cur.execute("SELECT id FROM csvfile WHERE file_path=?", (file_path,))
                result = cur.fetchone()
                file_id = result[0] if result else None
            except Exception as e:
                print(f"Error getting file ID for path '{file_path}': {e}")
                traceback.print_exc()
            finally:
                adapter.close()
        
        # Ensure file_id is a string, even if None initially
        file_id_str = str(file_id) if file_id is not None else ""
        if not file_id_str:
            print("Warning: No file ID found for the selected path. Proceeding without specific file_id.")
            # If OptimizationService requires a valid file_id, this needs more robust error handling.
            # For this example, we'll pass an empty string and let the service potentially default or error.

        # Create service instance (real or mock)
        if OptimizationService:
            try:
                # Create actual service with parameters
                # ใช้ PyQt6SQLAdapter แทน PyQt Adapter
                self.optimization_service = OptimizationService(
                    order_list_adapter=PyQt6SQLAdapter(),  # ใช้ SQL adapter
                    plan_order_adapter=PyQt6SQLAdapter(),    # ใช้ SQL adapter
                    optimization_plan_adapter=PyQt6SQLAdapter(),  # ใช้ SQL adapter
                    file_id=file_id,  # Pass file ID instead of base name
                    max_trim=MAX_TRIM, 
                    min_trim=MIN_TRIM,
                    roll_paper=ROLL_PAPER,
                    progress_callback=lambda p: self._update_progress(float(p)),
                    order_data_provider=self._get_processed_orders_gui
                )
            except ImportError as e:
                print(f"Failed to create SQL adapters: {e}")
                self.optimization_service = MockOptimizationService() # Fallback to mock
            except Exception as e:
                print(f"Error initializing OptimizationService: {e}")
                traceback.print_exc()
                self.optimization_service = MockOptimizationService() # Fallback to mock
        else:
            self.optimization_service = MockOptimizationService()

        # Create worker thread using QThread
        self.worker_thread = QThread()
        self.optimization_worker = OptimizationWorker(
            self.optimization_service, 
            start_date, 
            stop_date, 
            roll_paper
        )
        self.optimization_worker.moveToThread(self.worker_thread)
        
        # Connect signals
        self.optimization_worker.progress.connect(self._update_progress)
        self.optimization_worker.finished.connect(self._on_optimization_complete)
        self.worker_thread.started.connect(self.optimization_worker.run)
        
        # Handle thread finishing
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        # Setup progress dialog
        self.progress_dialog = QProgressDialog("Processing...", "Cancel", 0, 100, self)
        self.progress_dialog.setWindowTitle("Production Scheduling")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        
        # Connect cancel button
        self.aborted = False
        self.progress_dialog.canceled.connect(self._on_progress_canceled)
        
        # Initialize progress
        self.progress_value = 0
        self.start_time = time.time()
        
        # Start optimization thread
        self.worker_thread.start()
        self.progress_dialog.exec()

    def _update_progress(self, value: float): # เปลี่ยน type hint เป็น float
        """Update progress bar from real service"""
        if hasattr(self, 'progress_dialog') and not self.aborted:
            # Convert float to integer before setting value
            self.progress_value = round(value) # เปลี่ยนตรงนี้
            self.progress_dialog.setValue(self.progress_value) # เปลี่ยนตรงนี้
    
            # Calculate elapsed time
            elapsed_time = int(time.time() - self.start_time)
            minutes = elapsed_time // 60
            seconds = elapsed_time % 60
            time_str = f"{minutes:02d}:{seconds:02d}"
            
            self.progress_dialog.setLabelText(f"Optimizing... ({time_str})")

    def get_processed_orders(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Process orders through HD provider using OrderContainer
        Mirroring get_processed_orders from order_optimization/data_loaders.py
        """
        try:
            # Validate and format data
            if data.empty:
                return pd.DataFrame()
            
            # Process using HD provider (ensure HD is not None)
            if HD is not None:
                print("Creating HD provider...")
                hd_provider = HD(
                    orders=data,
                    common=False,
                    start_date=None,
                    stop_date=None,
                    common_init_order=None
                )
            else:
                raise ImportError("HD class not available. Optimization core imports failed.")
            
            # Wrap in OrderContainer (ensure OrderContainer is not None)
            if OrderContainer is not None:
                print("Creating OrderContainer...")
                container = OrderContainer(provider=hd_provider)
            else:
                raise ImportError("OrderContainer class not available. Optimization core imports failed.")
            
            print("Getting processed orders...")
            return container.get()
        except Exception as e:
            traceback.print_exc()
            print(f"Order processing error: {e}")
            return pd.DataFrame()

    def _get_processed_orders_gui(self, file_id, start_date, stop_date):
        """Load and process orders using OrderContainer and HD provider"""
        print(f"Loading orders for file_id: {file_id}, start_date: {start_date}, stop_date: {stop_date}")
        
        adapter = PyQt6SQLAdapter()
        try:
            # Fetch raw orders
            query = """
            SELECT * FROM orderlist
            WHERE due_date BETWEEN ? AND ?
            """
            params = (start_date, stop_date)
            if file_id is not None:
                query += " AND file_id = ?"
                params = (start_date, stop_date, file_id)
            
            cur = adapter.conn.cursor()
            cur.execute(query, params)
            columns = [col[0] for col in cur.description]
            rows = cur.fetchall()
            
            if not rows:
                print("No orders found in selected date range")
                return pd.DataFrame()
            
            raw_orders = pd.DataFrame(
                [dict(zip(columns, row)) for row in rows],
                columns=columns
            )
            
            # Process orders using OrderContainer and HD
            return self.get_processed_orders(raw_orders)
        except Exception as e:
            traceback.print_exc()
            print(f"Database error: {e}")
            return pd.DataFrame()
        finally:
            adapter.close()

    # Remove the _run_optimization method completely

    def _on_progress_canceled(self):
        self.aborted = True
        # self.progress_timer.stop() # No longer needed with QThread
        self.worker_thread.quit() # Request the worker thread to stop
        self.worker_thread.wait() # Wait for the worker thread to finish
        print("Processing canceled by user!")
        
    def _on_optimization_complete(self, results): # Modify to accept results as argument
        self.results = results # Store results received from the worker
        # self.progress_timer.stop() # No longer needed with QThread
        if "error" in self.results:
            print(f"Optimization Error: {self.results['error']}") # อัปเดตข้อความข้อผิดพลาด
        else:
            print("Production scheduling completed!")
            # self._show_optimization_results(self.results) # Uncomment if you want to show results immediately

    def _show_optimization_results(self, results):
        """Show optimization results in a dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Production Scheduling Results")
        dialog.setGeometry(200, 200, 700, 400)
        dialog.setWindowModality(Qt.WindowModality.WindowModal)

        layout = QVBoxLayout(dialog)
        
        # Add results display here in real implementation
        results_label = QLabel("<h3>Production scheduling model applied successfully!</h3>")
        layout.addWidget(results_label)
        
        # Add a simple table (mock)
        table_widget = QTableWidget()
        layout.addWidget(table_widget)
        table_widget.setRowCount(5)
        table_widget.setColumnCount(3)
        table_widget.setHorizontalHeaderLabels(["Parameter", "Value", "Unit"])
        
        results_data = [
            ["Paper Used", results.get('roll', 'Custom'), "Type"],
            ["Min Rolls", results.get('init_order_number', ''), "Rolls"],
            ["Total Volume", results.get('total', ''), "Tons"],
            ["Trim Waste", abs(results.get('trim', 0)), "cm"],
        ]
        
        for row_idx, row_data in enumerate(results_data):
            for col_idx, text in enumerate(row_data):
                table_widget.setItem(row_idx, col_idx, QTableWidgetItem(str(text)))
        
        table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # Additional buttons
        btn_close = QPushButton("Close", dialog)
        btn_close.clicked.connect(dialog.close)
        layout.addWidget(btn_close)
        
        dialog.exec()
    
    def _on_view_clicked(self):
        try: # เพิ่ม try-except block
            print("View Clicked!")
            # Show progress dialog while loading data
            self.progress_dialog = QProgressDialog("Loading data...", "Cancel", 0, 100, self)
            self.progress_dialog.setWindowTitle("Load Planning Data")
            self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            self.progress_dialog.setMinimumDuration(0) # Show immediately
            self.progress_dialog.show()
            
            # Create thread for fetching data
            self.worker_thread = threading.Thread(target=self._load_optimization_data)
            self.worker_thread.daemon = True
            self.worker_thread.start()
            
            # Set timer for progress update
            self.progress_value = 0
            self.progress_timer = QTimer(self)
            self.progress_timer.timeout.connect(self._update_load_progress)
            self.progress_timer.start(100) # Update every 100ms
        except Exception as e:
            traceback.print_exc()
            print(f"View Click Error: {str(e)}")

    def _load_optimization_data(self):
        try: # เพิ่ม try-except block
            # Fetch data from database using the SQL adapter
            adapter = PyQt6SQLAdapter()
            self.saved_data = adapter.get_saved_orders()
            adapter.close()
            time.sleep(0.5)  # Reduce sleep time to simulate faster loading
            self.saved_data_error = None
        except Exception as e:
            self.saved_data = []
            self.saved_data_error = f"Data load failed: {str(e)}" # อัปเดตข้อความข้อผิดพลาด
            traceback.print_exc() # พิมพ์ stack trace

    def _update_load_progress(self):
        # Simulate progress until worker completes
        # Simulate progress until worker completes
        # Use isRunning() for QThread
        if self.worker_thread.isRunning():
            self.progress_value = min(self.progress_value + 1, 99)
        else:
            self.progress_value = 100
            
        self.progress_dialog.setValue(self.progress_value)
        
        if not self.worker_thread.is_alive() or self.progress_value >= 100:
            self.progress_timer.stop()
            self.progress_dialog.close()
            self._show_saved_orders_table()

    def _show_saved_orders_table(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Production Planning Results")
        dialog.setGeometry(200, 200, 1200, 600)
        dialog.setWindowModality(Qt.WindowModality.WindowModal) # Make it modal

        layout = QVBoxLayout(dialog)
        
        # Create table to display results
        table_widget = QTableWidget()
        layout.addWidget(table_widget)
        
        # Define column headers based on HTML template
        headers = [
            "Paper", "Plan ID", "Blade", "Due Date", 
            "Sales Order No.", "Component Type", "Planned Quantity", 
            "Remaining Quantity", "Cut Width", "Cut Length", 
            "Edge Type", "Out"
        ]
        
        # Check if data is available
        if not hasattr(self, 'saved_data') or not self.saved_data:
            if hasattr(self, 'saved_data_error') and self.saved_data_error: # เพิ่มการตรวจสอบข้อผิดพลาด
                print(self.saved_data_error) # พิมพ์ข้อผิดพลาดออก terminal
                no_data_text = f"No planning data found. Error: {self.saved_data_error}"
            else:
                no_data_text = "No planning data found."

            table_widget.setRowCount(1)
            table_widget.setColumnCount(len(headers)) # Set correct column count for headers
            no_data_item = QTableWidgetItem(no_data_text)
            no_data_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table_widget.setSpan(0, 0, 1, len(headers)) # Span across all columns
            table_widget.setItem(0, 0, no_data_item)
            # Set headers even if no data
            table_widget.setHorizontalHeaderLabels(headers)
            
            # Add export button even if no data
            export_button = QPushButton("Export Data", dialog)
            export_button.clicked.connect(self._on_export_clicked)
            layout.addWidget(export_button)
            
            dialog.exec()
            return

        # Set up table
        table_widget.setRowCount(len(self.saved_data))
        table_widget.setColumnCount(len(headers))
        table_widget.setHorizontalHeaderLabels(headers)
        
        # Add data to table
        for row_idx, item in enumerate(self.saved_data):
            table_widget.setItem(row_idx, 0, QTableWidgetItem(str(item.get("paper_roll", ""))))
            table_widget.setItem(row_idx, 1, QTableWidgetItem(str(item.get("plan_id", "")))) # Use plan_id
            table_widget.setItem(row_idx, 2, QTableWidgetItem(str(item.get("blade_type", ""))))
            table_widget.setItem(row_idx, 3, QTableWidgetItem(str(item.get("due_date", ""))))
            table_widget.setItem(row_idx, 4, QTableWidgetItem(str(item.get("order_number", ""))))
            table_widget.setItem(row_idx, 5, QTableWidgetItem(str(item.get("component_type", ""))))
            table_widget.setItem(row_idx, 6, QTableWidgetItem(str(item.get("plan_quantity", ""))))
            table_widget.setItem(row_idx, 7, QTableWidgetItem(str(item.get("order_leftover", ""))))
            table_widget.setItem(row_idx, 8, QTableWidgetItem(str(item.get("width", ""))))
            table_widget.setItem(row_idx, 9, QTableWidgetItem(str(item.get("length", ""))))
            table_widget.setItem(row_idx, 10, QTableWidgetItem(str(item.get("edge_type", ""))))
            table_widget.setItem(row_idx, 11, QTableWidgetItem(str(item.get("out", ""))))
        
        # Adjust columns to fit content
        table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # Export data button
        export_button = QPushButton("Export Data", dialog)
        export_button.clicked.connect(self._on_export_clicked)
        layout.addWidget(export_button)
        
        dialog.exec()

    def _on_export_clicked(self):
        try: # เพิ่ม try-except block
            options = QFileDialog.Option.DontUseNativeDialog # Use Qt's dialog instead of native one for consistency
            file_name, _ = QFileDialog.getSaveFileName(
                self,
                "Save Data File",
                "",
                "Excel Files (*.xlsx);;CSV Files (*.csv)",
                options=options
            )
            
            if file_name:
                print(f"Exporting data to: {file_name}")
                if hasattr(self, 'saved_data') and self.saved_data:
                    df = pd.DataFrame(self.saved_data)
                    if file_name.endswith('.xlsx'):
                        df.to_excel(file_name, index=False)
                    elif file_name.endswith('.csv'):
                        df.to_csv(file_name, index=False)
                    print("Data exported successfully!")
                else:
                    print("No data to export")
        except Exception as e:
            traceback.print_exc()
            print(f"Export Error: {str(e)}")

    def _on_reset_clicked(self):
        try: # เพิ่ม try-except block
            self.start_date_edit.setDate(QDate.currentDate())
            self.stop_date_edit.setDate(QDate.currentDate())
            self.roll_paper_combo.setCurrentIndex(0)
            self.file_path_line_edit.clear()
            print("Reset Clicked!")
        except Exception as e:
            traceback.print_exc()
            print(f"Reset Click Error: {str(e)}")

# gui_app.py (new class at the end of file)
class FileManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Uploaded CSV Files")
        self.setGeometry(300, 300, 800, 400)
        self.adapter = PyQt6SQLAdapter()
        self.files = []
        self.selected_file_id = None
        self._setup_ui()
        self._load_files()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Path", "Upload Date", "Size"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.doubleClicked.connect(self._select_and_close)

        layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        self.select_btn = QPushButton("Select")
        self.select_btn.clicked.connect(self.select_file)
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_file)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._load_files)
        
        btn_layout.addWidget(self.select_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)

    def _load_files(self):
        self.files = []
        try:
            cur = self.adapter.conn.cursor()
            # Note: The original prompt for FileManagerDialog used 'moved_path' but it's not in the current schema.
            # I'm using 'file_path' as the source of truth for the file location.
            cur.execute("SELECT id, name, file_path, uploaded_at FROM csvfile")
            self.files = cur.fetchall()
            
            self.table.setRowCount(len(self.files))
            for i, row in enumerate(self.files):
                file_path = row[2] # file_path is at index 2
                file_size = os.path.exists(file_path) and os.path.getsize(file_path) or 0
                file_size_h = humanize.naturalsize(file_size)
                
                self.table.setItem(i, 0, QTableWidgetItem(str(row[0]))) # ID
                self.table.setItem(i, 1, QTableWidgetItem(row[1])) # Name
                self.table.setItem(i, 2, QTableWidgetItem(row[2])) # Path
                self.table.setItem(i, 3, QTableWidgetItem(row[3])) # Upload Date
                self.table.setItem(i, 4, QTableWidgetItem(file_size_h)) # Size
                
        except Exception as e:
            print(f"Error loading files: {e}")
            traceback.print_exc()
        self.update_button_states()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)


    def select_file(self):
        row = self.table.currentRow()
        if row >= 0:
            self.selected_file_id = self.files[row][0] # ID is at index 0
            self.accept()

    def delete_file(self):
        row = self.table.currentRow()
        if row >= 0:
            file_id = self.files[row][0]
            adapter = PyQt6SQLAdapter()
            try:
                # Delete related planorder and optimizationplan entries first if they exist
                # This is a simplified cascade delete. A more robust solution would involve
                # checking dependencies or using ON DELETE CASCADE in schema.
                adapter.conn.execute("DELETE FROM optimizationplan_blade1_orders WHERE planorder_id IN (SELECT id FROM planorder WHERE order_id IN (SELECT id FROM orderlist WHERE file_id=?))", (file_id,))
                adapter.conn.execute("DELETE FROM optimizationplan_blade2_orders WHERE planorder_id IN (SELECT id FROM planorder WHERE order_id IN (SELECT id FROM orderlist WHERE file_id=?))", (file_id,))
                adapter.conn.execute("DELETE FROM planorder WHERE order_id IN (SELECT id FROM orderlist WHERE file_id=?)", (file_id,))
                adapter.conn.execute("DELETE FROM orderlist WHERE file_id=?", (file_id,))
                adapter.conn.execute("DELETE FROM csvfile WHERE id=?", (file_id,))
                adapter.conn.commit()
                print(f"Deleted file ID: {file_id} and associated data.")
            except Exception as e:
                print(f"Error deleting file: {e}")
                traceback.print_exc()
            finally:
                adapter.close()
            self._load_files()

    def _select_and_close(self, index):
        self.select_file()
        # No need to call self.accept() here, select_file already calls it.
        # The doubleClicked signal passes a QModelIndex, not a row number.
        # The select_file method uses currentRow(), which is fine.
        # So, just calling select_file is enough.

    def update_button_states(self):
        has_selection = self.table.currentRow() >= 0
        self.select_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Set application locale to Thai
    # This makes QDateEdit and other parts display in Thai
    QLocale.setDefault(QLocale(QLocale.Language.Thai))

    # Set Roboto font
    # Note: Roboto font must be installed on your operating system to work.
    # If not installed, PyQt will use the system's default font instead.
    font = QFont("Roboto")
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
