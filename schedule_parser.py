import pandas as pd
from config import SCHEDULE_FILE
from typing import Dict, List, Tuple
import os

class ScheduleParser:
    def __init__(self):
        self.schedule_data = None
        self.load_schedule()
    
    def load_schedule(self):
        """Загрузить расписание из CSV файла"""
        try:
            self.schedule_data = pd.read_csv(SCHEDULE_FILE, encoding='utf-8')
            # Удаляем пустые строки
            self.schedule_data = self.schedule_data.dropna(subset=['Направление'])
        except Exception as e:
            print(f"Ошибка загрузки расписания: {e}")
            self.schedule_data = None
    
    def _find_schedule_sheet(self, file_path: str) -> Tuple[str, bool]:
        """Найти лист с расписанием в XLSX файле"""
        try:
            xl_file = pd.ExcelFile(file_path, engine='openpyxl')
            required_columns = ['Направление', 'Преподаватель', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Кабинет']
            
            for sheet_name in xl_file.sheet_names:
                try:
                    # Читаем лист для проверки структуры
                    df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
                    
                    # Проверяем, есть ли нужные колонки
                    if df.shape[1] >= 9:  # Минимум 9 колонок
                        columns_lower = [str(col).lower() for col in df.columns]
                        required_lower = [col.lower() for col in required_columns]
                        
                        # Проверяем, есть ли все нужные колонки
                        found_columns = []
                        for req in required_lower:
                            for col in columns_lower:
                                if req in col:
                                    found_columns.append(req)
                                    break
                        
                        if len(found_columns) >= 7:  # Минимум 7 из 9 колонок
                            print(f"Найден подходящий лист: '{sheet_name}' с колонками: {df.columns.tolist()}")
                            return sheet_name, True
                            
                except Exception as e:
                    print(f"Ошибка при проверке листа '{sheet_name}': {e}")
                    continue
            
            return None, False
            
        except Exception as e:
            print(f"Ошибка при поиске листа: {e}")
            return None, False
    
    def load_xlsx_schedule(self, file_path: str) -> bool:
        """Загрузить расписание из XLSX файла"""
        try:
            # Проверяем расширение файла
            if not file_path.lower().endswith('.xlsx'):
                return False
            
            # Ищем подходящий лист
            sheet_name, found = self._find_schedule_sheet(file_path)
            if not found:
                print("Не найден подходящий лист с расписанием")
                return False
            
            # Читаем XLSX файл с найденного листа
            self.schedule_data = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
            
            # Удаляем пустые строки
            self.schedule_data = self.schedule_data.dropna(subset=['Направление'])
            
            # Сохраняем в CSV для совместимости
            self.schedule_data.to_csv(SCHEDULE_FILE, index=False, encoding='utf-8')
            
            return True
        except Exception as e:
            print(f"Ошибка загрузки XLSX расписания: {e}")
            return False
    
    def validate_xlsx_structure(self, file_path: str) -> Tuple[bool, str]:
        """Проверить структуру XLSX файла"""
        try:
            if not file_path.lower().endswith('.xlsx'):
                return False, "Файл должен иметь расширение .xlsx"
            
            # Ищем подходящий лист
            sheet_name, found = self._find_schedule_sheet(file_path)
            if not found:
                return False, "Не найден лист с правильной структурой расписания"
            
            # Читаем файл для проверки структуры
            df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
            
            # Проверяем обязательные колонки
            required_columns = ['Направление', 'Преподаватель', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Кабинет']
            
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return False, f"Отсутствуют обязательные колонки: {', '.join(missing_columns)}"
            
            # Проверяем, что есть данные
            if df.empty:
                return False, "Файл не содержит данных"
            
            if df['Направление'].isna().all():
                return False, "Колонка 'Направление' пуста"
            
            return True, f"Файл корректный, найден лист: {sheet_name}"
            
        except Exception as e:
            return False, f"Ошибка проверки файла: {str(e)}"
    
    def get_directions(self) -> List[str]:
        """Получить список всех направлений"""
        if self.schedule_data is None:
            return []
        return self.schedule_data['Направление'].tolist()
    
    def get_direction_info(self, direction: str) -> Dict:
        """Получить информацию о направлении"""
        if self.schedule_data is None:
            return {}
        
        row = self.schedule_data[self.schedule_data['Направление'] == direction]
        if row.empty:
            return {}
        
        row = row.iloc[0]
        
        info = {
            'направление': row['Направление'],
            'преподаватель': row['Преподаватель'],
            'кабинет': row['Кабинет'],
            'дни': {}
        }
        
        # Дни недели в том порядке, как в таблице
        days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота']
        
        for day in days:
            if day in row and pd.notna(row[day]) and str(row[day]).strip():
                # Парсим расписание для дня
                schedule_text = str(row[day]).strip()
                info['дни'][day] = self._parse_day_schedule(schedule_text)
        
        return info
    
    def _parse_day_schedule(self, schedule_text: str) -> List[str]:
        """Парсить расписание для конкретного дня"""
        if not schedule_text:
            return []
        
        # Разделяем по группам, если есть несколько
        # Ищем паттерны типа "1гр 14:00 - 14:45"
        groups = []
        
        # Простое разделение по пробелам и поиск групп
        parts = schedule_text.split()
        current_group = []
        
        for part in parts:
            if 'гр' in part:
                if current_group:
                    groups.append(' '.join(current_group))
                current_group = [part]
            else:
                current_group.append(part)
        
        if current_group:
            groups.append(' '.join(current_group))
        
        return groups if groups else [schedule_text]
    
    def get_days_for_direction(self, direction: str) -> List[str]:
        """Получить дни недели для направления"""
        info = self.get_direction_info(direction)
        return list(info.get('дни', {}).keys())
    
    def format_direction_schedule(self, direction: str) -> str:
        """Форматировать расписание направления для отображения"""
        info = self.get_direction_info(direction)
        
        if not info:
            return "Направление не найдено"
        
        text = f"📚 *{info['направление']}*\n\n"
        text += f"👨‍🏫 *Преподаватель:* {info['преподаватель']}\n"
        text += f"🏢 *Кабинет:* {info['кабинет']}\n\n"
        
        if info['дни']:
            text += "*📅 Расписание:*\n\n"
            for day, schedule in info['дни'].items():
                text += f"*{day}:*\n"
                for group_schedule in schedule:
                    text += f"• {group_schedule}\n"
                text += "\n"
        else:
            text += "На данный момент занятий не запланировано"
        
        return text
    
    def get_statistics(self) -> Dict:
        """Получить статистику по расписанию"""
        if self.schedule_data is None:
            return {}
        
        stats = {
            'total_directions': len(self.schedule_data),
            'total_teachers': self.schedule_data['Преподаватель'].nunique(),
            'total_cabinets': self.schedule_data['Кабинет'].nunique(),
            'days_with_lessons': {}
        }
        
        # Подсчитываем дни с занятиями
        days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота']
        for day in days:
            if day in self.schedule_data.columns:
                day_lessons = self.schedule_data[day].notna().sum()
                stats['days_with_lessons'][day] = day_lessons
        
        return stats

# Создаем глобальный экземпляр парсера
schedule_parser = ScheduleParser()



