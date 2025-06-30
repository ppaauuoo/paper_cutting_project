import sys
import threading
import time

from PyQt6.QtCore import QDate, QDateTime, QLocale, QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QDialog,
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

# Try importing optimization service (as fallback if core not available)
try:
    from core.container import ModelContainer
    from core.optimization_service import OptimizationService
except ImportError:
    OptimizationService = None
    ModelContainer = None

# Example list for ROLL_PAPER
ROLL_PAPER = [66, 68, 70, 73, 74, 75, 79, 82, 85, 88, 91, 93, 95, 97]


# Mock optimization service if core not available
class MockOptimizationService:
    def run_optimization_pipeline(self, **kwargs):  # Changed to accept any keyword arguments
        """Accept required parameters (size, start_date, stop_date)"""
        # Simulate 3 seconds loading time
        time.sleep(3)
        return {
            'roll': '66',
            'init_order_number': 28,  # sample data
            'total': 65.8,  # sample data
            'trim': 0.2     # sample data
        }

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
        
        self.progress_dialog.setLabelText(f"Processing... ({time_str})")
        
        if not self.worker_thread.is_alive() or self.progress_value >= 100:
            self.progress_timer.stop()
            self.progress_dialog.close()
            self._on_optimization_complete()

    def _run_optimization(self, start_date, stop_date, roll_size):
        """Thread for calling the optimization service"""
        try:
            # Convert roll_size from string to float
            size_value = float(roll_size) if roll_size is not None else None
            # This would call the real optimization service in production
            self.results = self.optimization_service.run_optimization_pipeline(
                start_date=start_date,
                stop_date=stop_date,
                size=size_value,  # Pass roll_size as size parameter
            )
        except ValueError as ve:
            self.results = {"error": f"Invalid Roll Size: {ve}"}
        except Exception as e:
            self.results = {"error": str(e)}
    
    def _on_progress_canceled(self):
        self.aborted = True
        self.progress_timer.stop()
        print("Processing canceled by user!")
        
    def _on_optimization_complete(self):
        """Handle results after optimization finishes"""
        results = getattr(self, "results", {})
        if "error" in results:
            print(f"An error occurred: {results['error']}")
        else:
            print("Production scheduling completed!")
            self._show_optimization_results(results)

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

    def _load_optimization_data(self):
        try:
            # Fetch data from database (mock data example)
            self.saved_data = [
                {
                    "paper_roll": "A",
                    "plan_id": "P001", # Use plan_id instead of blade_1_orders__id/blade_2_orders__id
                    "blade_type": "blade_1",
                    "due_date": "2023-10-15",
                    "order_number": "SO001",
                    "component_type": "Front",
                    "plan_quantity": 150,
                    "order_leftover": 0,
                    "width": 45.5,
                    "length": 120.0,
                    "edge_type": "Straight",
                    "out": 2,
                },
                {
                    "paper_roll": "B",
                    "plan_id": "P002",
                    "blade_type": "blade_2",
                    "due_date": "2023-10-16",
                    "order_number": "SO002",
                    "component_type": "Back",
                    "plan_quantity": 200,
                    "order_leftover": 10,
                    "width": 60.0,
                    "length": 150.0,
                    "edge_type": "Curved",
                    "out": 3,
                },
                {
                    "paper_roll": "A",
                    "plan_id": "P001", # Same plan_id as SO001, assuming it's part of the same plan
                    "blade_type": "blade_2",
                    "due_date": "2023-10-15",
                    "order_number": "SO003",
                    "component_type": "Side",
                    "plan_quantity": 75,
                    "order_leftover": 5,
                    "width": 30.0,
                    "length": 80.0,
                    "edge_type": "Straight",
                    "out": 1,
                },
            ]
            time.sleep(2)  # Simulate data loading time
            self.saved_data_error = None
        except Exception as e:
            self.saved_data = []
            self.saved_data_error = f"Data loading failed: {str(e)}"

    def _update_load_progress(self):
        # Simulate progress until worker completes
        if self.worker_thread.is_alive():
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
            table_widget.setRowCount(1)
            table_widget.setColumnCount(len(headers)) # Set correct column count for headers
            no_data_item = QTableWidgetItem("No planning data found")
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
            # In a real application, add code here to export actual data
            # Example:
            # if hasattr(self, 'saved_data') and self.saved_data:
            #     import pandas as pd
            #     df = pd.DataFrame(self.saved_data)
            #     if file_name.endswith('.xlsx'):
            #         df.to_excel(file_name, index=False)
            #     elif file_name.endswith('.csv'):
            #         df.to_csv(file_name, index=False)
            #     print("Data exported successfully!")
            # else:
            #     print("No data to export")

    def _on_reset_clicked(self):
        self.start_date_edit.setDate(QDate.currentDate())
        self.stop_date_edit.setDate(QDate.currentDate())
        self.roll_paper_combo.setCurrentIndex(0)
        self.file_path_line_edit.clear()
        print("Reset Clicked!")

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
