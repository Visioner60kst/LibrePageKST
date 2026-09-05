import fitz

class ImageSelectionManager:
    def __init__(self):
        self.selected_page_index = -1
        self.selected_bbox = None
        self.selected_image_info = None

    def clear_selection(self):
        """Сбрасывает текущее выделение"""
        self.selected_page_index = -1
        self.selected_bbox = None
        self.selected_image_info = None

    def select_image_at(self, page, page_index, pdf_x, pdf_y):
        """
        Проверяет, есть ли изображение по заданным координатам.
        Если есть, сохраняет его параметры и возвращает True.
        """
        click_point = fitz.Point(pdf_x, pdf_y)
        images = page.get_image_info()

        found_image = None
        found_bbox = None

        # Идем с конца списка, чтобы выбрать самое верхнее изображение
        for img in reversed(images):
            bbox = img.get("bbox")
            if bbox:
                rect = fitz.Rect(bbox)
                if rect.contains(click_point):
                    found_image = img
                    found_bbox = rect
                    break

        if found_image:
            self.selected_page_index = page_index
            self.selected_bbox = found_bbox
            self.selected_image_info = found_image
            return True
        else:
            self.clear_selection()
            return False