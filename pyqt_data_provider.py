import pandas as pd
from typing import Any, Dict, List, Optional
from datetime import datetime

# นำเข้าโมดูล Logic หลัก
from modules.hd import HD # ตรวจสอบให้แน่ใจว่า path ไปยัง modules.hd ถูกต้องในโครงสร้างโปรเจกต์ PyQt ของคุณ
from core.container import OrderContainer

def load_raw_orders_from_pyqt_source(file_id: str, start_date: Optional[str] = None, stop_date: Optional[str] = None) -> pd.DataFrame:
    """
    จำลองการโหลดข้อมูล Order ดิบจากแหล่งข้อมูลของ PyQt (เช่น ไฟล์ Excel, SQLite DB, หรือ API ภายใน)
    ในตัวอย่างนี้ใช้ข้อมูลจำลอง (dummy data) เพื่อแสดงโครงสร้าง
    """
    print(f"PyQt Data Provider: Loading raw orders for file_id: {file_id}, dates: {start_date} to {stop_date}")

    # ข้อมูลจำลอง (Mock Data) - คุณจะต้องแทนที่ด้วย Logic การโหลดข้อมูลจริงใน PyQt ของคุณ
    # ตรวจสอบให้แน่ใจว่าคอลัมน์และประเภทข้อมูลตรงกับที่ HD class ต้องการ
    dummy_data = {
        'id': [f'order_{i}-{idx}' for i in range(1, 4) for idx in range(1, 3)], # Unique ID
        'order_number': [101, 101, 102, 102, 103, 103],
        'quantity': [50, 20, 70, 30, 40, 10], # จำนวนสั่งขาย
        'width': [20.0, 20.0, 25.0, 25.0, 15.0, 15.0], # กว้างผลิต
        'length': [100.0, 100.0, 120.0, 120.0, 80.0, 80.0], # ยาวผลิต
        'edge_type': ['A', 'A', 'B', 'B', 'A', 'A'],
        'due_date': [
            pd.Timestamp('2025-07-01 00:00:00+0000', tz='UTC'),
            pd.Timestamp('2025-07-05 00:00:00+0000', tz='UTC'),
            pd.Timestamp('2025-07-03 00:00:00+0000', tz='UTC'),
            pd.Timestamp('2025-07-07 00:00:00+0000', tz='UTC'),
            pd.Timestamp('2025-07-02 00:00:00+0000', tz='UTC'),
            pd.Timestamp('2025-07-06 00:00:00+0000', tz='UTC')
        ],
        'front_sheet': ['S1', 'S1', 'S2', 'S2', 'S1', 'S1'],
        'c_wave': ['C1', 'C1', 'C2', 'C2', 'C1', 'C1'],
        'middle_sheet': ['M1', 'M1', 'M2', 'M2', 'M1', 'M1'],
        'b_wave': ['B1', 'B1', 'B2', 'B2', 'B1', 'B1'],
        'back_sheet': ['BK1', 'BK1', 'BK2', 'BK2', 'BK1', 'BK1'],
        'level': [3, 3, 5, 5, 3, 3],
        'left_edge_cut': [1, 1, 2, 2, 1, 1],
        'middle_edge_cut': [0, 0, 0, 0, 0, 0],
        'right_edge_cut': [1, 1, 2, 2, 1, 1],
        'component_type': ['Box', 'Box', 'Panel', 'Panel', 'Box', 'Box'],
        'production_quantity': [50, 20, 70, 30, 40, 10], # จำนวนสั่งผลิต
        'edge_type': ['TypeA', 'TypeA', 'TypeB', 'TypeB', 'TypeA', 'TypeA'],
        'order_status': ['Active', 'Active', 'Active', 'Active', 'Active', 'Active'],
        'excess_percentage': [5, 5, 10, 10, 5, 5],
        'file_id': [file_id]*6 # เชื่อมโยงกับ file_id ที่ส่งมา
    }
    
    df = pd.DataFrame(dummy_data)

    # การกรองวันที่ (ถ้ามี)
    if start_date:
        try:
            start_dt = pd.to_datetime(start_date)
            df = df[df['due_date'].dt.tz_localize(None) >= start_dt]
        except Exception as e:
            print(f"Warning: Could not parse start_date '{start_date}'. Error: {e}")
    if stop_date:
        try:
            stop_dt = pd.to_datetime(stop_date)
            df = df[df['due_date'].dt.tz_localize(None) <= stop_dt]
        except Exception as e:
            print(f"Warning: Could not parse stop_date '{stop_date}'. Error: {e}")

    return df

def get_processed_orders_for_pyqt(
    file_id: str,
    common: bool = False,
    start_date: Optional[str] = None, # เปลี่ยนเป็น str เพื่อให้สอดคล้องกับ input จาก UI (ถ้ามาจาก PyQt QDateEdit)
    stop_date: Optional[str] = None,   # เปลี่ยนเป็น str
    common_init_order: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    """
    ส่งผ่าน arguments ไปยัง Order Processor (HD provider)
    และคืนค่า processed orders ในรูปแบบ DataFrame
    """
    raw_orders = load_raw_orders_from_pyqt_source(file_id, start_date, stop_date)

    if raw_orders.empty:
        print("PyQt Data Provider: Raw orders DataFrame is empty.")
        return pd.DataFrame()

    return OrderContainer(
        provider=HD(
            orders=raw_orders,
            common=common,
            start_date=pd.to_datetime(start_date) if start_date else None, # แปลงกลับเป็น Timestamp สำหรับ HD
            stop_date=pd.to_datetime(stop_date) if stop_date else None,   # แปลงกลับเป็น Timestamp
            common_init_order=common_init_order,
        )
    ).get()

# ฟังก์ชันจำลองสำหรับ PyQt UI Integration Example
# นี่คือตัวอย่างการเรียกใช้งานในโค้ด PyQt หลักของคุณ
# จาก PyQt UI ของคุณ:
# from PyQt5.QtWidgets import QProgressBar, QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
# from PyQt5.QtCore import QObject, pyqtSignal, QThread
# import sys
#
# class OptimizationWorker(QObject):
#     finished = pyqtSignal()
#     progress = pyqtSignal(float)
#     results = pyqtSignal(dict)
#     error = pyqtSignal(str)
#
#     def __init__(self, service_instance_params: Dict[str, Any], optimization_params: Dict[str, Any]):
#         super().__init__()
#         self.service_instance_params = service_instance_params
#         self.optimization_params = optimization_params
#
#     def run(self):
#         try:
#             from core.optimization_service import OptimizationService
#             # Instantiate OptimizationService with parameters for PyQt
#             # progress_callback จะถูกเชื่อมต่อกับ signal ของ PyQt
#             service = OptimizationService(
#                 **self.service_instance_params,
#                 progress_callback=self.progress.emit,
#             )
#             output_results = service.run_optimization_pipeline(**self.optimization_params)
#             self.results.emit(output_results)
#         except ValueError as e:
#             self.error.emit(str(e))
#         except Exception as e:
#             self.error.emit(f"An unexpected error occurred: {e}")
#         finally:
#             self.finished.emit()
#
# class MyPyQtApp(QMainWindow):
#     def __init__(self):
#         super().__init__()
#         self.setWindowTitle("PyQt Optimization App")
#         self.setGeometry(100, 100, 800, 600)
#
#         self.progressBar = QProgressBar(self)
#         self.progressBar.setRange(0, 100)
#         self.optimizeButton = QPushButton("Run Optimization", self)
#         self.optimizeButton.clicked.connect(self.start_optimization)
#
#         layout = QVBoxLayout()
#         layout.addWidget(self.progressBar)
#         layout.addWidget(self.optimizeButton)
#
#         container = QWidget()
#         container.setLayout(layout)
#         self.setCentralWidget(container)
#
#         # ตัวแปรสำหรับเก็บ Adapter Instances (ถ้าต้องการใช้ข้อมูลคงที่ใน memory หรือเชื่อมต่อกับ DB เดียว)
#         self.pyqt_order_adapter = PyQtOrderListAdapter(initial_orders_data=[
#                 {'id': 'order_A', 'quantity': 100, 'width': 20.0, 'length': 100.0, 'edge_type': 'A', 'due_date': pd.Timestamp('2025-07-01'), 'order_number': 123, 'front_sheet': 'FS', 'c_wave': 'CW', 'middle_sheet': 'MS', 'b_wave': 'BW', 'back_sheet': 'BS', 'level': 3, 'left_edge_cut': 1, 'middle_edge_cut': 1, 'right_edge_cut': 1, 'component_type': 'BOX', 'production_quantity': 100, 'order_status': 'Active', 'excess_percentage': 5},
#                 {'id': 'order_B', 'quantity': 80, 'width': 25.0, 'length': 120.0, 'edge_type': 'B', 'due_date': pd.Timestamp('2025-07-05'), 'order_number': 456, 'front_sheet': 'FS', 'c_wave': 'CW', 'middle_sheet': 'MS', 'b_wave': 'BW', 'back_sheet': 'BS', 'level': 3, 'left_edge_cut': 1, 'middle_edge_cut': 1, 'right_edge_cut': 1, 'component_type': 'BOX', 'production_quantity': 80, 'order_status': 'Active', 'excess_percentage': 5},
#                 {'id': 'order_C', 'quantity': 60, 'width': 22.0, 'length': 90.0, 'edge_type': 'A', 'due_date': pd.Timestamp('2025-07-03'), 'order_number': 789, 'front_sheet': 'FS', 'c_wave': 'CW', 'middle_sheet': 'MS', 'b_wave': 'BW', 'back_sheet': 'BS', 'level': 3, 'left_edge_cut': 1, 'middle_edge_cut': 1, 'right_edge_cut': 1, 'component_type': 'BOX', 'production_quantity': 60, 'order_status': 'Active', 'excess_percentage': 5},
#         ])
#         self.pyqt_plan_adapter = PyQtPlanOrderAdapter()
#         self.pyqt_optimization_adapter = PyQtOptimizationPlanAdapter()
#
#     def start_optimization(self):
#         self.progressBar.setValue(0)
#         self.optimizeButton.setEnabled(False)
#
#         # Parameters for OptimizationService instantiation
#         service_params = {
#             "order_list_adapter": self.pyqt_order_adapter,
#             "plan_order_adapter": self.pyqt_plan_adapter,
#             "optimization_plan_adapter": self.pyqt_optimization_adapter,
#             "file_id": "pyqt_dummy_file",
#             "max_trim": 3.0,
#             "min_trim": 1.0,
#             "roll_paper": [66, 68, 70, 73, 74, 75, 79, 82, 85, 88, 91, 93, 95, 97],
#             "order_data_provider": get_processed_orders_for_pyqt,
#         }
#
#         # Parameters for run_optimization_pipeline
#         optimization_params = {
#             "start_date": "2025-07-01",
#             "stop_date": "2025-07-31",
#             "size": 200.0,
#         }
#
#         # สร้าง Worker thread เพื่อรัน Logic การ Optimize เพื่อไม่ให้ UI ค้าง
#         self.thread = QThread()
#         self.worker = OptimizationWorker(service_params, optimization_params)
#         self.worker.moveToThread(self.thread)
#
#         self.thread.started.connect(self.worker.run)
#         self.worker.finished.connect(self.thread.quit)
#         self.worker.finished.connect(self.worker.deleteLater)
#         self.thread.finished.connect(self.thread.deleteLater)
#
#         self.worker.progress.connect(lambda p: self.progressBar.setValue(int(p * 100)))
#         self.worker.results.connect(self.on_optimization_success)
#         self.worker.error.connect(self.on_optimization_error)
#         self.thread.start()
#
#     def on_optimization_success(self, results: dict):
#         self.optimizeButton.setEnabled(True)
#         print("Optimization Completed Successfully! Results:", results)
#         # แสดงผลลัพธ์ใน UI หรือทำการบันทึก
#
#     def on_optimization_error(self, error_message: str):
#         self.optimizeButton.setEnabled(True)
#         print("Optimization Failed! Error:", error_message)
#         # แสดงข้อความผิดพลาดใน UI
#
# if __name__ == '__main__':
#     app = QApplication(sys.argv)
#     mainWin = MyPyQtApp()
#     mainWin.show()
#     sys.exit(app.exec_())
