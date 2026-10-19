"""Modern themes supporting Dark and Light mode with refined aesthetics."""

DARK_THEME = """
/* Global Window */
QMainWindow, QWidget#centralWidget {
    background-color: #0F172A; /* Deep slate */
    color: #F8FAFC;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 13px;
}

/* Menu Bar & Menus */
QMenuBar {
    background-color: #1E293B;
    color: #E2E8F0;
    border-bottom: 1px solid #334155;
    padding: 2px 4px;
    font-size: 13px;
    font-weight: 500;
}

QMenuBar::item {
    background: transparent;
    padding: 5px 10px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #334155;
    color: #FFFFFF;
}

QMenu {
    background-color: #1E293B;
    color: #F8FAFC;
    border: 1px solid #475569;
    border-radius: 8px;
    padding: 6px;
}

QMenu::item {
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
    font-size: 13px;
}

QMenu::item:selected {
    background-color: #0284C7;
    color: #FFFFFF;
}

QMenu::item:disabled {
    color: #64748B;
}

QMenu::separator {
    height: 1px;
    background-color: #334155;
    margin: 4px 0px;
}

QLabel {
    color: #E2E8F0;
}

/* Sidebar Navigation */
QFrame#sidebarFrame {
    background-color: #1E293B;
    border-right: 1px solid #334155;
}

QLabel#appTitle {
    color: #FFFFFF;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.3px;
}

QPushButton.navBtn {
    background-color: transparent;
    color: #94A3B8;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
}

QPushButton.navBtn:hover {
    background-color: #334155;
    color: #F8FAFC;
}

QPushButton.navBtn:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3B82F6, stop:1 #6366F1);
    color: #FFFFFF;
    font-weight: 600;
}

/* Buttons */
QPushButton.primaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #4F46E5);
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: 600;
}

QPushButton.primaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1D4ED8, stop:1 #4338CA);
}

QPushButton.primaryBtn:pressed {
    background-color: #1E40AF;
}

QPushButton.primaryBtn:disabled {
    background: #1E293B;
    color: #475569;
    border: 1px solid #334155;
}

QPushButton.secondaryBtn {
    background-color: #1E293B;
    color: #E2E8F0;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 7px 15px;
    font-weight: 500;
}

QPushButton.secondaryBtn:hover {
    background-color: #334155;
    border-color: #475569;
    color: #FFFFFF;
}

QPushButton.secondaryBtn:disabled {
    background-color: #0F172A;
    color: #475569;
    border-color: #1E293B;
}

/* Action Cards */
QFrame.actionCard {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 18px;
}

QFrame.actionCard:hover {
    background-color: #273549;
    border-color: #6366F1;
}

QLabel.cardTitle {
    color: #F8FAFC;
    font-size: 15px;
    font-weight: 600;
}

QLabel.cardDesc {
    color: #94A3B8;
    font-size: 12px;
    line-height: 1.4;
}

/* Typography & Section Headers */
QLabel#sectionHeader {
    font-size: 15px;
    font-weight: 600;
    color: #F8FAFC;
}

QLabel#welcomeTitle {
    font-size: 24px;
    font-weight: 700;
    color: #FFFFFF;
}

QLabel#welcomeSubtitle, QLabel#pageInfoLbl {
    font-size: 13px;
    color: #94A3B8;
}

/* Sidebar Info Card */
QFrame#sidebarInfoCard {
    background-color: #141E33;
    border-radius: 8px;
    padding: 10px;
    border: 1px solid #293548;
}

QLabel#privacyTitle {
    color: #34D399;
    font-weight: 600;
    font-size: 11px;
}

QLabel#privacyDesc {
    color: #94A3B8;
    font-size: 10px;
}

/* Drop Zone */
QFrame#dropZone {
    background-color: #162032;
    border: 2px dashed #3B82F6;
    border-radius: 16px;
}

QFrame#dropZone:hover {
    background-color: #1C2B44;
    border-color: #60A5FA;
}

/* Controls */
QComboBox, QSpinBox, QLineEdit {
    background-color: #0F172A;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 6px 12px;
    color: #F8FAFC;
}

QComboBox:focus, QSpinBox:focus, QLineEdit:focus {
    border: 1px solid #6366F1;
}

QComboBox QAbstractItemView {
    background-color: #1E293B;
    color: #F8FAFC;
    selection-background-color: #4F46E5;
    border: 1px solid #334155;
}

/* Sliders */
QSlider::groove:horizontal {
    height: 6px;
    background: #334155;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #3B82F6;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #60A5FA;
    border: 2px solid #FFFFFF;
    width: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}

/* Checkboxes */
QCheckBox {
    color: #E2E8F0;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #475569;
    border-radius: 4px;
    background-color: #0F172A;
}

QCheckBox::indicator:checked {
    background-color: #2563EB;
    border-color: #3B82F6;
}

/* Lists */
QListWidget {
    background-color: #0F172A;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 6px;
}

QListWidget::item {
    border-radius: 6px;
    padding: 8px;
    color: #E2E8F0;
}

QListWidget::item:selected {
    background-color: #1E3A8A;
    border: 1px solid #3B82F6;
}

QStatusBar {
    background-color: #0B1120;
    border-top: 1px solid #1E293B;
    color: #94A3B8;
}

QLabel#privacyBadge {
    color: #34D399;
    font-weight: 600;
}

/* Acrobat-style PDF Viewer Toolbar & Tools */
QFrame#pdfViewerToolbar {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 2px 6px;
}

QFrame#pdfSearchBar {
    background-color: #1E293B;
    border: 1px solid #3B82F6;
    border-radius: 8px;
    padding: 4px;
}

QPushButton.toolIconBtn {
    background-color: transparent;
    color: #E2E8F0;
    border: 1px solid transparent;
    border-radius: 6px;
    font-size: 13px;
    font-weight: bold;
}

QPushButton.toolIconBtn:hover {
    background-color: #334155;
    border-color: #475569;
    color: #FFFFFF;
}

QPushButton.toolIconBtn:pressed {
    background-color: #2563EB;
}

QPushButton.toolIconBtn:disabled {
    color: #475569;
    background-color: transparent;
    border-color: transparent;
}

QPushButton.toolSmallBtn {
    background-color: #0F172A;
    color: #CBD5E1;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 500;
}

QPushButton.toolSmallBtn:hover {
    background-color: #334155;
    color: #FFFFFF;
    border-color: #3B82F6;
}

QPushButton.toolSmallBtn:checked {
    background-color: #1E3A8A;
    color: #93C5FD;
    border-color: #3B82F6;
    font-weight: 600;
}

QPushButton.toolSmallBtn:disabled {
    background-color: #0F172A;
    color: #475569;
    border-color: #1E293B;
}

QTabWidget::pane {
    border: 1px solid #334155;
    border-radius: 8px;
    background-color: #0F172A;
}

QTabBar::tab {
    background-color: #1E293B;
    color: #94A3B8;
    border: 1px solid #334155;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 6px 12px;
    margin-right: 2px;
    font-weight: 500;
}

QTabBar::tab:selected {
    background-color: #0F172A;
    color: #38BDF8;
    border-color: #38BDF8;
    font-weight: 600;
}

QTreeView {
    background-color: #0F172A;
    border: 1px solid #334155;
    border-radius: 8px;
    color: #E2E8F0;
    padding: 4px;
}

QTreeView::item {
    padding: 4px;
    border-radius: 4px;
}

QTreeView::item:hover {
    background-color: #1E293B;
}

QTreeView::item:selected {
    background-color: #1E3A8A;
    color: #FFFFFF;
}
"""

LIGHT_THEME = """
/* Global Window */
QMainWindow, QWidget#centralWidget {
    background-color: #F8FAFC; /* Clean off-white */
    color: #0F172A;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 13px;
}

/* Menu Bar & Menus (Light) */
QMenuBar {
    background-color: #FFFFFF;
    color: #1E293B;
    border-bottom: 1px solid #E2E8F0;
    padding: 2px 4px;
    font-size: 13px;
    font-weight: 500;
}

QMenuBar::item {
    background: transparent;
    padding: 5px 10px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #F1F5F9;
    color: #0F172A;
}

QMenu {
    background-color: #FFFFFF;
    color: #1E293B;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 6px;
}

QMenu::item {
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
    font-size: 13px;
}

QMenu::item:selected {
    background-color: #DBEAFE;
    color: #1E40AF;
}

QMenu::item:disabled {
    color: #94A3B8;
}

QMenu::separator {
    height: 1px;
    background-color: #E2E8F0;
    margin: 4px 0px;
}

QLabel {
    color: #1E293B;
}

/* Sidebar Navigation */
QFrame#sidebarFrame {
    background-color: #FFFFFF;
    border-right: 1px solid #E2E8F0;
}

QLabel#appTitle {
    color: #0F172A;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.3px;
}

QPushButton.navBtn {
    background-color: transparent;
    color: #334155;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    text-align: left;
    font-size: 13px;
    font-weight: 600;
}

QPushButton.navBtn:hover {
    background-color: #E2E8F0;
    color: #0F172A;
}

QPushButton.navBtn:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #4F46E5);
    color: #FFFFFF;
    font-weight: 600;
}

/* Buttons */
QPushButton.primaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #4F46E5);
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: 600;
}

QPushButton.primaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1D4ED8, stop:1 #4338CA);
}

QPushButton.primaryBtn:pressed {
    background-color: #1E40AF;
}

QPushButton.primaryBtn:disabled {
    background: #E2E8F0;
    color: #94A3B8;
    border: 1px solid #CBD5E1;
}

QPushButton.secondaryBtn {
    background-color: #FFFFFF;
    color: #1E293B;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 7px 15px;
    font-weight: 500;
}

QPushButton.secondaryBtn:hover {
    background-color: #F1F5F9;
    border-color: #94A3B8;
}

QPushButton.secondaryBtn:disabled {
    background-color: #F8FAFC;
    color: #94A3B8;
    border-color: #E2E8F0;
}

/* Action Cards */
QFrame.actionCard {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 18px;
}

QFrame.actionCard:hover {
    background-color: #F8FAFC;
    border-color: #6366F1;
}

QLabel.cardTitle {
    color: #0F172A;
    font-size: 15px;
    font-weight: 600;
}

QLabel.cardDesc {
    color: #64748B;
    font-size: 12px;
    line-height: 1.4;
}

/* Typography & Section Headers */
QLabel#sectionHeader {
    font-size: 15px;
    font-weight: 600;
    color: #0F172A;
}

QLabel#welcomeTitle {
    font-size: 24px;
    font-weight: 700;
    color: #0F172A;
}

QLabel#welcomeSubtitle, QLabel#pageInfoLbl {
    font-size: 13px;
    color: #64748B;
}

/* Sidebar Info Card */
QFrame#sidebarInfoCard {
    background-color: #F1F5F9;
    border-radius: 8px;
    padding: 10px;
    border: 1px solid #E2E8F0;
}

QLabel#privacyTitle {
    color: #059669;
    font-weight: 600;
    font-size: 11px;
}

QLabel#privacyDesc {
    color: #64748B;
    font-size: 10px;
}

/* Drop Zone */
QFrame#dropZone {
    background-color: #FFFFFF;
    border: 2px dashed #93C5FD;
    border-radius: 16px;
}

QFrame#dropZone:hover {
    background-color: #EFF6FF;
    border-color: #3B82F6;
}

/* Controls */
QComboBox, QSpinBox, QLineEdit {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 6px 12px;
    color: #0F172A;
}

QComboBox:focus, QSpinBox:focus, QLineEdit:focus {
    border: 1px solid #4F46E5;
}

QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    color: #0F172A;
    selection-background-color: #3B82F6;
    selection-color: #FFFFFF;
    border: 1px solid #CBD5E1;
}

/* Sliders */
QSlider::groove:horizontal {
    height: 6px;
    background: #E2E8F0;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #2563EB;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #FFFFFF;
    border: 2px solid #2563EB;
    width: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}

/* Checkboxes */
QCheckBox {
    color: #334155;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #CBD5E1;
    border-radius: 4px;
    background-color: #FFFFFF;
}

QCheckBox::indicator:checked {
    background-color: #2563EB;
    border-color: #2563EB;
}

/* Lists */
QListWidget {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 6px;
}

QListWidget::item {
    border-radius: 6px;
    padding: 8px;
    color: #334155;
}

QListWidget::item:selected {
    background-color: #DBEAFE;
    color: #1E40AF;
    border: 1px solid #93C5FD;
}

QStatusBar {
    background-color: #FFFFFF;
    border-top: 1px solid #E2E8F0;
    color: #64748B;
}

QLabel#privacyBadge {
    color: #059669;
    font-weight: 600;
}

/* Acrobat-style PDF Viewer Toolbar & Tools (Light) */
QFrame#pdfViewerToolbar {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 2px 6px;
}

QFrame#pdfSearchBar {
    background-color: #FFFFFF;
    border: 1px solid #3B82F6;
    border-radius: 8px;
    padding: 4px;
}

QPushButton.toolIconBtn {
    background-color: transparent;
    color: #475569;
    border: 1px solid transparent;
    border-radius: 6px;
    font-size: 13px;
    font-weight: bold;
}

QPushButton.toolIconBtn:hover {
    background-color: #F1F5F9;
    border-color: #CBD5E1;
    color: #0F172A;
}

QPushButton.toolIconBtn:pressed {
    background-color: #2563EB;
    color: #FFFFFF;
}

QPushButton.toolIconBtn:disabled {
    color: #CBD5E1;
    background-color: transparent;
    border-color: transparent;
}

QPushButton.toolSmallBtn {
    background-color: #F8FAFC;
    color: #334155;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 500;
}

QPushButton.toolSmallBtn:hover {
    background-color: #E2E8F0;
    color: #0F172A;
    border-color: #2563EB;
}

QPushButton.toolSmallBtn:checked {
    background-color: #DBEAFE;
    color: #1E40AF;
    border-color: #3B82F6;
    font-weight: 600;
}

QPushButton.toolSmallBtn:disabled {
    background-color: #F1F5F9;
    color: #94A3B8;
    border-color: #E2E8F0;
}

QTabWidget::pane {
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    background-color: #FFFFFF;
}

QTabBar::tab {
    background-color: #F1F5F9;
    color: #64748B;
    border: 1px solid #E2E8F0;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 6px 12px;
    margin-right: 2px;
    font-weight: 500;
}

QTabBar::tab:selected {
    background-color: #FFFFFF;
    color: #2563EB;
    border-color: #2563EB;
    font-weight: 600;
}

QTreeView {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    color: #0F172A;
    padding: 4px;
}

QTreeView::item {
    padding: 4px;
    border-radius: 4px;
}

QTreeView::item:hover {
    background-color: #F1F5F9;
}

QTreeView::item:selected {
    background-color: #DBEAFE;
    color: #1E40AF;
}
"""
