import fitz
from PyQt6.QtWidgets import QMessageBox

def cheredov_pages_action(main_window):
    """
    Модуль Чередования: пересобирает страницы в порядке 1, последний, 2, предпоследний...
    """
    if not main_window.current_file_path or not main_window.doc:
        QMessageBox.warning(main_window, "Внимание", "Сначала откройте PDF файл.")
        return

    total_pages = len(main_window.doc)
    if total_pages < 2:
        QMessageBox.information(main_window, "Информация", "Нужно минимум 2 страницы для чередования.")
        return

    reply = QMessageBox.question(
        main_window,
        "Чередование страниц",
        "Выполнить пересборку (1, последний, 2, предпоследний...)?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )

    if reply == QMessageBox.StandardButton.Yes:
        try:
            # Генерация списка новых индексов
            new_order = []
            left = 0
            right = total_pages - 1
            
            while left <= right:
                if left == right:
                    new_order.append(left)
                else:
                    new_order.append(left)
                    new_order.append(right)
                left += 1
                right -= 1
            
            # Перестраиваем документ
            main_window.doc.select(new_order)
            
            # Обновляем UI
            main_window.active_page_index = 0
            main_window.render_all()
            main_window.history_manager.save_state()
            
        except Exception as e:
            QMessageBox.critical(main_window, "Ошибка", f"Ошибка при чередовании: {e}")