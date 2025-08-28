import asyncio
import aiosqlite
from config import DATABASE_PATH, FIRST_ADMIN_ID

class Database:
    def __init__(self):
        self.db_path = DATABASE_PATH
    
    async def _get_connection(self):
        """Получить соединение с базой данных"""
        return aiosqlite.connect(self.db_path)
    
    async def init_db(self):
        """Инициализация базы данных"""
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица администраторов
            await db.execute('''
                CREATE TABLE IF NOT EXISTS admins (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    added_by INTEGER,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица сообщений обратной связи (заявки)
            await db.execute('''
                CREATE TABLE IF NOT EXISTS feedback_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    message_text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    is_answered BOOLEAN DEFAULT FALSE,
                    answered_by INTEGER,
                    answer_text TEXT,
                    answered_at TIMESTAMP
                )
            ''')
            
            # Добавляем колонку status для существующих записей, если её нет
            try:
                await db.execute('ALTER TABLE feedback_messages ADD COLUMN status TEXT DEFAULT "active"')
                await db.commit()
            except:
                # Колонка уже существует
                pass
            
            # Добавляем колонку direction_id для связи с направлениями
            try:
                await db.execute('ALTER TABLE feedback_messages ADD COLUMN direction_id INTEGER')
                await db.commit()
            except:
                # Колонка уже существует
                pass
            
            # Таблица чатов для уведомлений об обратной связи
            await db.execute('''
                CREATE TABLE IF NOT EXISTS notification_chats (
                    chat_id INTEGER PRIMARY KEY,
                    chat_title TEXT,
                    chat_type TEXT,
                    added_by INTEGER,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            ''')
            
            # Таблица преподавателей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS teachers (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    added_by INTEGER,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            ''')
            
            # Таблица направлений из расписания
            await db.execute('''
                CREATE TABLE IF NOT EXISTS directions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица связи преподавателей и направлений
            await db.execute('''
                CREATE TABLE IF NOT EXISTS teacher_directions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    teacher_id INTEGER NOT NULL,
                    direction_id INTEGER NOT NULL,
                    assigned_by INTEGER,
                    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (teacher_id) REFERENCES teachers (user_id),
                    FOREIGN KEY (direction_id) REFERENCES directions (id),
                    UNIQUE(teacher_id, direction_id)
                )
            ''')
            
            # Таблица логов пользователей (кто когда-либо писал боту)
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users_log (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    first_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_messages INTEGER DEFAULT 1
                )
            ''')
            
            await db.commit()
            
            # Добавляем первого администратора
            await self.add_admin(FIRST_ADMIN_ID, None, "Первый админ", None)
    
    async def add_admin(self, user_id: int, username: str = None, first_name: str = None, added_by: int = None):
        """Добавить администратора"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO admins (user_id, username, first_name, added_by)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, first_name, added_by))
            await db.commit()
    
    async def update_admin_info(self, user_id: int, username: str = None, first_name: str = None):
        """Обновить информацию об администраторе"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE admins 
                SET username = ?, first_name = ?
                WHERE user_id = ?
            ''', (username, first_name, user_id))
            await db.commit()
    
    async def remove_admin(self, user_id: int):
        """Удалить администратора"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM admins WHERE user_id = ?', (user_id,))
            await db.commit()
    
    async def is_admin(self, user_id: int) -> bool:
        """Проверить, является ли пользователь администратором"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT user_id FROM admins WHERE user_id = ?', (user_id,))
            result = await cursor.fetchone()
            return result is not None
    
    async def get_all_admins(self):
        """Получить всех администраторов"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT user_id, username, first_name FROM admins')
            return await cursor.fetchall()
    
    async def save_feedback_message(self, user_id: int, username: str, first_name: str, message_text: str, direction_id: int = None):
        """Сохранить сообщение обратной связи"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                INSERT INTO feedback_messages (user_id, username, first_name, message_text, direction_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, username, first_name, message_text, direction_id))
            await db.commit()
            return cursor.lastrowid
    
    async def mark_message_answered(self, message_id: int, answered_by: int, answer_text: str):
        """Отметить сообщение как отвеченное и закрыть заявку"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE feedback_messages 
                SET is_answered = TRUE, answered_by = ?, answer_text = ?, answered_at = CURRENT_TIMESTAMP, status = 'closed'
                WHERE id = ?
            ''', (answered_by, answer_text, message_id))
            await db.commit()
    
    async def get_feedback_message(self, message_id: int):
        """Получить сообщение обратной связи по ID"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT id, user_id, username, first_name, message_text, created_at, is_answered, status
                FROM feedback_messages WHERE id = ?
            ''', (message_id,))
            return await cursor.fetchone()
    
    async def get_user_conversation(self, user_id: int):
        """Получить всю переписку с пользователем"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT id, message_text, created_at, is_answered, answer_text, answered_at, answered_by, status
                FROM feedback_messages 
                WHERE user_id = ? 
                ORDER BY created_at ASC
            ''', (user_id,))
            return await cursor.fetchall()
    
    async def has_active_request(self, user_id: int) -> bool:
        """Проверить, есть ли у пользователя активная заявка"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT id FROM feedback_messages 
                WHERE user_id = ? AND status = 'active'
                LIMIT 1
            ''', (user_id,))
            result = await cursor.fetchone()
            return result is not None
    
    async def get_active_request(self, user_id: int):
        """Получить активную заявку пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT id, message_text, created_at
                FROM feedback_messages 
                WHERE user_id = ? AND status = 'active'
                ORDER BY created_at DESC
                LIMIT 1
            ''', (user_id,))
            return await cursor.fetchone()
    
    async def close_request(self, message_id: int):
        """Закрыть заявку"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('''
                    UPDATE feedback_messages 
                    SET status = 'closed'
                    WHERE id = ?
                ''', (message_id,))
                await db.commit()
                # Проверяем, была ли обновлена хотя бы одна строка
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error closing request {message_id}: {e}")
            return False
    
    # Методы для работы с чатами уведомлений
    async def add_notification_chat(self, chat_id: int, chat_title: str, chat_type: str, added_by: int):
        """Добавить чат для уведомлений"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO notification_chats (chat_id, chat_title, chat_type, added_by)
                VALUES (?, ?, ?, ?)
            ''', (chat_id, chat_title, chat_type, added_by))
            await db.commit()
    
    async def remove_notification_chat(self, chat_id: int):
        """Удалить чат из уведомлений"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM notification_chats WHERE chat_id = ?', (chat_id,))
            await db.commit()
    
    async def get_notification_chats(self):
        """Получить все активные чаты для уведомлений"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT chat_id, chat_title, chat_type 
                FROM notification_chats 
                WHERE is_active = TRUE
                ORDER BY added_at ASC
            ''')
            return await cursor.fetchall()
    
    async def toggle_notification_chat(self, chat_id: int, is_active: bool):
        """Включить/отключить уведомления для чата"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE notification_chats 
                SET is_active = ? 
                WHERE chat_id = ?
            ''', (is_active, chat_id))
            await db.commit()
    
    async def is_notification_chat(self, chat_id: int) -> bool:
        """Проверить, является ли чат активным для уведомлений"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT chat_id FROM notification_chats 
                WHERE chat_id = ? AND is_active = TRUE
            ''', (chat_id,))
            result = await cursor.fetchone()
            return result is not None
    
    # Методы для работы с преподавателями
    async def add_teacher(self, user_id: int, username: str = None, first_name: str = None, added_by: int = None):
        """Добавить преподавателя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO teachers (user_id, username, first_name, added_by)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, first_name, added_by))
            await db.commit()
    
    async def remove_teacher(self, user_id: int):
        """Удалить преподавателя"""
        async with aiosqlite.connect(self.db_path) as db:
            # Удаляем связи с направлениями
            await db.execute('DELETE FROM teacher_directions WHERE teacher_id = ?', (user_id,))
            # Удаляем преподавателя
            await db.execute('DELETE FROM teachers WHERE user_id = ?', (user_id,))
            await db.commit()
    
    async def is_teacher(self, user_id: int) -> bool:
        """Проверить, является ли пользователь преподавателем"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT user_id FROM teachers WHERE user_id = ? AND is_active = TRUE', (user_id,))
            result = await cursor.fetchone()
            return result is not None
    
    async def get_all_teachers(self):
        """Получить всех преподавателей"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT user_id, username, first_name FROM teachers WHERE is_active = TRUE')
            return await cursor.fetchall()
    
    # Методы для работы с направлениями
    async def sync_directions(self, direction_names: list):
        """Синхронизировать направления из расписания"""
        async with aiosqlite.connect(self.db_path) as db:
            # Добавляем новые направления
            for name in direction_names:
                await db.execute('''
                    INSERT OR IGNORE INTO directions (name) VALUES (?)
                ''', (name,))
            
            # Удаляем направления, которых нет в текущем расписании
            if direction_names:
                placeholders = ','.join(['?' for _ in direction_names])
                await db.execute(f'''
                    DELETE FROM teacher_directions 
                    WHERE direction_id IN (
                        SELECT id FROM directions 
                        WHERE name NOT IN ({placeholders})
                    )
                ''', direction_names)
                
                await db.execute(f'''
                    DELETE FROM directions 
                    WHERE name NOT IN ({placeholders})
                ''', direction_names)
            
            await db.commit()
    
    async def get_all_directions(self):
        """Получить все направления"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT id, name FROM directions ORDER BY name')
            return await cursor.fetchall()
    
    async def get_direction_by_id(self, direction_id: int):
        """Получить направление по ID"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT id, name FROM directions WHERE id = ?', (direction_id,))
            return await cursor.fetchone()
    
    async def get_direction_by_name(self, name: str):
        """Получить направление по названию"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT id, name FROM directions WHERE name = ?', (name,))
            return await cursor.fetchone()
    
    # Методы для работы со связями преподавателей и направлений
    async def assign_teacher_to_direction(self, teacher_id: int, direction_id: int, assigned_by: int):
        """Привязать преподавателя к направлению"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR IGNORE INTO teacher_directions (teacher_id, direction_id, assigned_by)
                VALUES (?, ?, ?)
            ''', (teacher_id, direction_id, assigned_by))
            await db.commit()
    
    async def remove_teacher_from_direction(self, teacher_id: int, direction_id: int):
        """Отвязать преподавателя от направления"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                DELETE FROM teacher_directions 
                WHERE teacher_id = ? AND direction_id = ?
            ''', (teacher_id, direction_id))
            await db.commit()
    
    async def get_teachers_for_direction(self, direction_id: int):
        """Получить всех преподавателей для направления"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT t.user_id, t.username, t.first_name
                FROM teachers t
                JOIN teacher_directions td ON t.user_id = td.teacher_id
                WHERE td.direction_id = ? AND t.is_active = TRUE
            ''', (direction_id,))
            return await cursor.fetchall()
    
    async def get_directions_for_teacher(self, teacher_id: int):
        """Получить все направления преподавателя"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT d.id, d.name
                FROM directions d
                JOIN teacher_directions td ON d.id = td.direction_id
                WHERE td.teacher_id = ?
            ''', (teacher_id,))
            return await cursor.fetchall()
    
    async def get_teacher_requests(self, teacher_id: int):
        """Получить заявки для конкретного преподавателя"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT fm.id, fm.user_id, fm.username, fm.first_name, fm.message_text, 
                       fm.created_at, fm.status, d.name as direction_name
                FROM feedback_messages fm
                JOIN directions d ON fm.direction_id = d.id
                JOIN teacher_directions td ON d.id = td.direction_id
                WHERE td.teacher_id = ? AND fm.status = 'active'
                ORDER BY fm.created_at DESC
            ''', (teacher_id,))
            return await cursor.fetchall()
    
    async def can_teacher_reply_to_request(self, teacher_id: int, request_id: int) -> bool:
        """Проверить, может ли преподаватель ответить на конкретную заявку"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT 1
                FROM feedback_messages fm
                JOIN teacher_directions td ON fm.direction_id = td.direction_id
                WHERE fm.id = ? AND td.teacher_id = ?
                LIMIT 1
            ''', (request_id, teacher_id))
            result = await cursor.fetchone()
            return result is not None
    
    # Методы для работы с логами пользователей
    async def log_user_interaction(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Записать взаимодействие пользователя с ботом"""
        async with aiosqlite.connect(self.db_path) as db:
            # Проверяем, есть ли уже такой пользователь
            cursor = await db.execute('SELECT user_id, total_messages FROM users_log WHERE user_id = ?', (user_id,))
            existing_user = await cursor.fetchone()
            
            if existing_user:
                # Обновляем существующего пользователя
                await db.execute('''
                    UPDATE users_log 
                    SET username = ?, first_name = ?, last_name = ?, 
                        last_interaction = CURRENT_TIMESTAMP, 
                        total_messages = total_messages + 1
                    WHERE user_id = ?
                ''', (username, first_name, last_name, user_id))
            else:
                # Добавляем нового пользователя
                await db.execute('''
                    INSERT INTO users_log (user_id, username, first_name, last_name)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, username, first_name, last_name))
            
            await db.commit()
    
    async def get_all_users_log(self):
        """Получить всех пользователей из лога"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT user_id, username, first_name, last_name, 
                       first_interaction, last_interaction, total_messages
                FROM users_log 
                ORDER BY last_interaction DESC
            ''')
            return await cursor.fetchall()
    
    async def get_users_stats(self):
        """Получить статистику пользователей"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT COUNT(*) FROM users_log')
            total_users = (await cursor.fetchone())[0]
            
            cursor = await db.execute('SELECT SUM(total_messages) FROM users_log')
            total_messages = (await cursor.fetchone())[0] or 0
            
            return {
                'total_users': total_users,
                'total_messages': total_messages
            }

# Создаем глобальный экземпляр базы данных
db = Database()
