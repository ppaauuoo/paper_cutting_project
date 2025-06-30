import sys
import time
import threading
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QLabel, QDateEdit, QComboBox, QLineEdit, QPushButton,
    QFileDialog, QProgressDialog, QTableWidget, QTableWidgetItem, QHeaderView, QDialog
)
from PyQt6.QtCore import QDate, QTimer, Qt, QLocale, QDateTime, pyqtSignal, QObject
from PyQt6.QtGui import QFont

# Try importing optimization service (as fallback if core not available)
try:
    from core.optimization_service import OptimizationService
    from core.container import ModelContainer
except ImportError:
    OptimizationService = None
    ModelContainer = None

# รายการตัวอย่างสำหรับ ROLL_PAPER
ROLL_PAPER = ["Paper Type A", "Paper Type B", "Paper Type C", "Custom"]

# Mock optimization service if core not available
class MockOptimizationService:
    def run_optimization_pipeline(self, start_date, stop_date, roll_size):
        time.sleep(3)
        return {}

class MockModelContainer:
    fitness_values = 0
    total = 100
    PAPER_SIZE = 100
    output = "Mock Output"

# Worker signals for thread communication
class WorkerSignals(QObject):
    progress = pyqtSignal(int)
    finished = pyqtSignal(object)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"PyQt6 GUI Application - {QLocale().toString(QDateTime.currentDateTime(), QLocale.FormatType.LongFormat)}")
        self.setGeometry(100, 100, 600, 400)

        self._create_widgets()
        self._setup_layout()
        self._connect_signals()

    def _create_widgets(self):
        # วันที่เริ่มต้น
        self.start_date_edit = QDateEdit(self)
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate())

        # วันที่สิ้นสุด
        self.stop_date_edit = QDateEdit(self)
        self.stop_date_edit.setCalendarPopup(True)
        self.stop_date_edit.setDate(QDate.currentDate().addDays(7))

        # ดรอปดาวน์ ROLL_PAPER
        self.roll_paper_combo = QComboBox(self)
        self.roll_paper_combo.addItems(ROLL_PAPER)

        # การเลือกไฟล์
        self.file_path_line_edit = QLineEdit(self)
        self.file_browse_button = QPushButton("Browse...", self)

        # ปุ่มต่างๆ
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
        form_layout.addRow("File Selection:", file_selection_layout)

        main_layout.addLayout(form_layout)

        button_layout = QHBoxLayout()
        button_layout.addStretch(1) # เพื่อให้ปุ่มอยู่ทางขวา
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.view_button)
        button_layout.addWidget(self.reset_button)

        main_layout.addLayout(button_layout)
        main_layout.addStretch(1) # เพื่อให้เนื้อหาอยู่ด้านบน

    def _connect_signals(self):
        self.file_browse_button.clicked.connect(self._browse_file)
        self.start_button.clicked.connect(self._on_start_clicked)
        self.view_button.clicked.connect(self._on_view_clicked)
        self.reset_button.clicked.connect(self._on_reset_clicked)

    def _browse_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select File", "", "All Files (*);;Text Files (*.txt)")
        if file_name:
            self.file_path_line_edit.setText(file_name)
        print(f"Selected File: {file_name}")

    def _on_start_clicked(self):
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

    def _show_progress_dialog(self):
        # Prepare to run optimization
        start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        stop_date = self.stop_date_edit.date().toString("yyyy-MM-dd")
        roll_paper = self.roll_paper_combo.currentText()
        file_path = self.file_path_line_edit.text()

        # Create service instance (real or mock)
        if OptimizationService:
            # In real app pass actual service parameters
            self.optimization_service = OptimizationService(
                order_list_adapter=None,
                plan_order_adapter=None,
                optimization_plan_adapter=None,
                file_id=file_path,
                max_trim=3, min_trim=1,
                roll_paper=None,
                progress_callback=None,
                order_data_provider=None
            )
        else:
            self.optimization_service = MockOptimizationService()

        # Create worker thread
        self.worker_thread = threading.Thread(
            target=self._run_optimization,
            args=(start_date, stop_date, roll_paper)
        )
        self.worker_thread.daemon = True

        # Setup progress dialog
        self.progress_dialog = QProgressDialog("กำลังประมวลผล...", "ยกเลิก", 0, 100, self)
        self.progress_dialog.setWindowTitle("กำหนดการผลิต")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        
        # Connect cancel button
        self.aborted = False
        self.progress_dialog.canceled.connect(self._on_progress_canceled)
        
        # Initialize progress
        self.progress_value = 0
        self.start_time = time.time()
        
        # Use timer to update progress UI.
        # Actual progress updates would come from the service in a real app
        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(lambda: self._update_progress_emulated())
        self.progress_timer.start(100)
        
        # Start optimization thread
        self.worker_thread.start()
        self.progress_dialog.exec()

    def _update_progress_emulated(self):
        # Simulate progress until worker completes
        if self.worker_thread.is_alive():
            self.progress_value = min(self.progress_value + 1, 99)
        else:
            self.progress_value = 100
            
        self.progress_dialog.setValue(self.progress_value)
        
        elapsed_time = int(time.time() - self.start_time)
        minutes = elapsed_time // 60
        seconds = elapsed_time % 60
        time_str = f"{minutes:02d}:{seconds:02d}"
        
        self.progress_dialog.setLabelText(f"กำลังดำเนินการ... ({time_str})")
        
        if not self.worker_thread.is_alive() or self.progress_value >= 100:
            self.progress_timer.stop()
            self.progress_dialog.close()
            self._on_optimization_complete()

    def _run_optimization(self, start_date, stop_date, roll_size):
        """Thread function to run optimization service"""
        try:
            # This would call the real optimization service in production
            self.results = self.optimization_service.run_optimization_pipeline(
                start_date=start_date,
                stop_date=stop_date,
                size=roll_size,
            )
        except Exception as e:
            self.results = {"error": str(e)}
    
    def _on_progress_canceled(self):
        self.aborted = True
        self.progress_timer.stop()
        print("ยกเลิกการประมวลผลโดยผู้ใช้!")
        
    def _on_optimization_complete(self):
        """Handle results after optimization finishes"""
        results = getattr(self, "results", {})
        if "error" in results:
            print(f"เกิดข้อผิดพลาด: {results['error']}")
        else:
            print("การกำหนดการผลิตเสร็จสมบูรณ์!")
            self._show_optimization_results(results)

    def _show_optimization_results(self, results):
        """Show optimization results in a dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("ผลลัพธ์การกำหนดการผลิต")
        dialog.setGeometry(200, 200, 700, 400)
        dialog.setWindowModality(Qt.WindowModality.WindowModal)

        layout = QVBoxLayout(dialog)
        
        # Add results display here in real implementation
        results_label = QLabel("<h3>ปรับใช้โมเดลกำหนดการผลิตสำเร็จ!</h3>")
        layout.addWidget(results_label)
        
        # Add a simple table (mock)
        table_widget = QTableWidget()
        layout.addWidget(table_widget)
        table_widget.setRowCount(5)
        table_widget.setColumnCount(3)
        table_widget.setHorizontalHeaderLabels(["พารามิเตอร์", "ค่า", "หน่วย"])
        
        results_data = [
            ["กระดาษที่ใช้", results.get('roll', 'Custom'), "ชนิด"],
            ["ม้วนขั้นต่ำ", results.get('init_order_number', ''), "ม้วน"],
            ["ปริมาณรวม", results.get('total', ''), "ตัน"],
            ["เศษกระดาษ", abs(results.get('trim', 0)), "ซม"],
        ]
        
        for row_idx, row_data in enumerate(results_data):
            for col_idx, text in enumerate(row_data):
                table_widget.setItem(row_idx, col_idx, QTableWidgetItem(str(text)))
        
        table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # Additional buttons
        btn_close = QPushButton("ปิด", dialog)
        btn_close.clicked.connect(dialog.close)
        layout.addWidget(btn_close)
        
        dialog.exec()
    
    def _on_view_clicked(self):
        print("View Clicked!")
        # If we have results show them, otherwise mock
        if hasattr(self, 'results'):
            self._show_optimization_results(self.results)
        else:
            self._show_data_table_dialog()

    def _show_data_table_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Mock Data Table")
        dialog.setGeometry(200, 200, 700, 400)
        dialog.setWindowModality(Qt.WindowModality.WindowModal)

        layout = QVBoxLayout(dialog)
        table_widget = QTableWidget()
        layout.addWidget(table_widget)

        # Mock Data
        headers = ["ID", "Name", "Value", "Status"]
        data = [
            ["001", "Item A", "123.45", "Completed"],
            ["002", "Item B", "67.89", "Pending"],
            ["003", "Item C", "987.65", "Failed"],
            ["004", "Item D", "432.10", "Completed"],
            ["005", "Item E", "55.55", "Pending"],
        ]

        table_widget.setRowCount(len(data))
        table_widget.setColumnCount(len(headers))
        table_widget.setHorizontalHeaderLabels(headers)

        for row_idx, row_data in enumerate(data):
            for col_idx, item in enumerate(row_data):
                table_widget.setItem(row_idx, col_idx, QTableWidgetItem(str(item)))

        # Auto-resize columns to fit content
        table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # ปุ่ม Export
        export_button = QPushButton("Export Data", dialog)
        export_button.clicked.connect(self._on_export_clicked)

        # เลย์เอาต์สำหรับปุ่มในไดอะล็อก
        dialog_button_layout = QHBoxLayout()
        dialog_button_layout.addStretch(1) # ดันปุ่มไปทางขวา
        dialog_button_layout.addWidget(export_button)
        layout.addLayout(dialog_button_layout) # เพิ่มเลย์เอาต์ปุ่มเข้าสู่เลย์เอาต์หลักของไดอะล็อก

        dialog.exec() # แสดงไดอะล็อกแบบโมดอล

    def _on_export_clicked(self):
        print("Export button clicked!")
        # เพิ่ม logic สำหรับการส่งออกข้อมูลที่นี่
        # ตัวอย่าง: QFileDialog.getSaveFileName(self, "Save Data", "", "CSV Files (*.csv);;Excel Files (*.xlsx)")

    def _on_reset_clicked(self):
        self.start_date_edit.setDate(QDate.currentDate())
        self.stop_date_edit.setDate(QDate.currentDate())
        self.roll_paper_combo.setCurrentIndex(0)
        self.file_path_line_edit.clear()
        print("Reset Clicked!")

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # ตั้งค่า Locale ของแอปพลิเคชันเป็นภาษาไทย
    # เพื่อให้ QDateEdit และส่วนอื่นๆ แสดงผลเป็นภาษาไทย
    QLocale.setDefault(QLocale(QLocale.Language.Thai))

    # ตั้งค่าฟอนต์ Roboto
    # หมายเหตุ: ฟอนต์ Roboto ต้องถูกติดตั้งบนระบบปฏิบัติการของคุณเพื่อให้ทำงานได้
    # หากไม่ได้ติดตั้ง PyQt จะใช้ฟอนต์เริ่มต้นของระบบแทน
    font = QFont("Roboto")
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
