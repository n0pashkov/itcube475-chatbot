import pandas as pd
from config import SCHEDULE_FILE
from typing import Dict, List, Tuple

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

# Создаем глобальный экземпляр парсера
schedule_parser = ScheduleParser()



