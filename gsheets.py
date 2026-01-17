
import gspread
import pandas as pd
import logging
from google.oauth2.service_account import Credentials
from config import config
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class GoogleSheetsManager:
    def __init__(self):
        self.client = None
        self.spreadsheet = None
        self._full_data_cache = None
        self._full_data_time = 0
        self._current_week_cache = None
        self._cache_time = 0
        self.CACHE_TTL = 300  # 5 минут
        self.connect()

    def _get_full_data(self):
        """Получить данные таблицы"""
        import time

        # Если кэш есть и не устарел
        if self._full_data_cache and (time.time() - self._full_data_time < self.CACHE_TTL):
            logger.debug("✅ Использую кэш всех данных")
            return self._full_data_cache

        # Загружаем свежие данные
        logger.debug("🔄 Загружаю свежие данные из таблицы")
        try:
            worksheet = self.spreadsheet.worksheet("Расписание")
            self._full_data_cache = worksheet.get_all_records()
            self._full_data_time = time.time()
            logger.info(f"📊 Данные закэшированы: {len(self._full_data_cache)} строк")
            return self._full_data_cache
        except Exception as e:
            logger.error(f"Ошибка загрузки данных: {e}")
            return []

    def invalidate_cache(self):
        """Очистить кэш (вызывать после записи)"""
        self._full_data_cache = None
        self._full_data_time = 0
        logger.debug("🧹 Кэш очищен")

    def connect(self):
        """ Подключение к Google Sheets"""
        try:
            logger.info(f"🔐 Подключение к таблице...")

            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive.file'
            ]

            credentials = Credentials.from_service_account_info(
                config.GOOGLE_CREDENTIALS,
                scopes=scopes
            )

            self.client = gspread.authorize(credentials)
            self.spreadsheet = self.client.open_by_key(config.SPREADSHEET_ID)

            logger.info("✅ Подключение к Google Sheets успешно")

        except Exception as e:
            logger.error(f"❌ Ошибка подключения: {e}")
            raise

    def get_available_tariffs(self):
        """Получить тарифы из кэша"""
        try:
            data = self._get_full_data()

            if not data:
                return []

            tariffs = set()
            for row in data:
                tariff = str(row.get('Тариф', '')).strip()
                if tariff and tariff != "Тренинг":
                    tariffs.add(tariff)

            result = list(tariffs)
            logger.info(f"Тарифы из кэша: {len(result)}")
            return result

        except Exception as e:
            logger.error(f"Ошибка чтения тарифов: {e}")
            return []

    def get_current_week_number(self) -> int:
        """Читает текущую неделю из Google Sheets (B3), возвращает как есть (даже 0)"""
        try:
            settings_ws = self.spreadsheet.worksheet("Настройки")
            week_cell = settings_ws.cell(3, 2).value  # B3

            if week_cell is None or str(week_cell).strip() == "":
                logger.warning("B3 пустая, возвращаем 0")
                return 0

            try:
                # Возвращаем как есть, даже если 0
                current_week = int(float(str(week_cell).strip()))
                logger.info(f"📅 Текущая неделя из B3: {current_week}")
                return current_week
            except (ValueError, TypeError) as e:
                logger.error(f"Не число в B3: '{week_cell}', ошибка: {e}")
                return 0
        except Exception as e:
            logger.error(f"Не удалось получить неделю из таблицы: {e}")
            return 0

    def get_training_week_number(self) -> int:
        """Читает неделю тренингов из B4, если пусто - берет B3"""
        try:
            settings_ws = self.spreadsheet.worksheet("Настройки")
            week_cell = settings_ws.cell(4, 2).value  # B4

            if week_cell is None or str(week_cell).strip() == "":
                logger.warning("B4 пустая, используем B3")
                return self.get_current_week_number()

            try:
                training_week = int(float(str(week_cell).strip()))
                logger.info(f"📅 Неделя тренингов из B4: {training_week}")
                return training_week
            except (ValueError, TypeError) as e:
                logger.error(f"Не число в B4: '{week_cell}', ошибка: {e}")
                return self.get_current_week_number()
        except Exception as e:
            logger.error(f"Ошибка чтения B4: {e}")
            return self.get_current_week_number()

    def get_available_weeks(self, tariff: str):
        """Возвращает только текущую неделю из B3 (даже если 0)"""
        try:
            current_week = self.get_current_week_number()
            logger.info(f"📅 Текущая неделя для тарифа '{tariff}': {current_week}")
            return [current_week]
        except Exception as e:
            logger.error(f"Ошибка в get_available_weeks: {e}")
            return []

    def get_nearest_available_week(self, tariff: str):
        """Найти ближайшую неделю"""
        try:
            logger.debug(f"Поиск ближайшей недели для тарифа '{tariff}'")

            worksheet = self.spreadsheet.worksheet("Расписание")
            data = worksheet.get_all_records()
            df = pd.DataFrame(data)

            if df.empty:
                return None

            # Нормализуем данные
            df['Тариф_норм'] = df['Тариф'].astype(str).str.strip()
            df['Статус_норм'] = df['Статус'].astype(str).str.strip().str.lower()
            df['Студент_норм'] = df['Студент'].fillna('').astype(str).str.strip()

            # Функция для преобразования недели
            def try_float(x):
                try:
                    return float(str(x).strip())
                except:
                    return None

            df['Неделя_норм'] = df['Неделя'].apply(try_float)

            # Фильтр
            mask = (
                    (df['Тариф_норм'] == tariff.strip()) &
                    (df['Статус_норм'] == 'Активно') &
                    (df['Студент_норм'] == '') &
                    df['Неделя_норм'].notna()
            )

            filtered_df = df[mask]

            if filtered_df.empty:
                logger.info(f"Для тарифа '{tariff}' нет свободных слотов")
                return None

            nearest_week = filtered_df['Неделя_норм'].min()

            logger.info(f"Для тарифа '{tariff}' ближайшая неделя: {nearest_week}")
            return nearest_week

        except Exception as e:
            logger.error(f"Ошибка поиска недели: {e}", exc_info=True)
            return None

    def get_available_slots(self, tariff: str, week: float):
        """Получить слоты на указанной неделе (строгое равенство)"""
        try:
            worksheet = self.spreadsheet.worksheet("Расписание")
            data = worksheet.get_all_records()

            if not data:
                logger.info(f"📭 Таблица 'Расписание' пустая")
                return []

            slots = []

            for idx, row in enumerate(data, start=2):  # start=2 потому что первая строка заголовки
                # Проверяем неделю (строгое равенство)
                row_week_raw = str(row.get('Неделя', '')).strip()

                try:
                    row_week = float(row_week_raw)
                except (ValueError, TypeError):
                    continue  # Пропускаем если неделя не число

                # СТРОГОЕ РАВЕНСТВО недель
                if abs(row_week - float(week)) > 0.01:
                    continue

                # Проверяем тариф
                row_tariff = str(row.get('Тариф', '')).strip()
                if row_tariff != tariff.strip():
                    continue

                # Проверяем статус
                status = str(row.get('Статус', '')).strip().lower()
                if status != 'активно':
                    continue

                # Проверяем дату (только будущие)
                date_str = str(row.get('Дата', '')).split()[0]
                time_str = str(row.get('Время', ''))

                if not self.is_future_date(date_str, time_str):
                    continue

                # Определяем лимит мест
                if tariff == "Базовый":
                    max_seats = 4
                    student_columns = ['Студент1', 'Студент2', 'Студент3', 'Студент4']
                elif tariff == "Основной":
                    max_seats = 3
                    student_columns = ['Студент1', 'Студент2', 'Студент3']
                else:
                    max_seats = 1
                    student_columns = ['Студент1']

                # Считаем занятые места
                booked_count = 0
                for col in student_columns:
                    cell_value = str(row.get(col, '')).strip()
                    if cell_value and cell_value.strip():
                        booked_count += 1

                # Если все места заняты - пропускаем
                if booked_count >= max_seats:
                    continue

                # Форматируем дату и время
                date_display = self.format_date(date_str)
                time_str = str(row.get('Время', ''))
                if ' ' in time_str:
                    time_str = time_str.split()[0][:5]
                else:
                    time_str = time_str[:5]

                slots.append({
                    'row_index': idx,
                    'date': date_display,
                    'time': time_str,
                    'mentor': row.get('Наставник', ''),
                    'tariff': tariff,
                    'week': week,
                    'booked': booked_count,
                    'available': max_seats - booked_count,
                    'max_seats': max_seats
                })

            logger.info(f"Для тарифа '{tariff}', неделя {week} найдено слотов: {len(slots)}")
            return slots

        except Exception as e:
            logger.error(f"Ошибка поиска слотов: {e}", exc_info=True)
            return []

    def get_available_slots_for_user(self, tariff: str, week: float, user_id: int):
        """Возвращает слоты доступные для конкретного пользователя"""
        all_slots = self.get_available_slots(tariff, week)

        if not all_slots:
            return []

        # Проверяем, может ли пользователь записаться на эту неделю
        if not self.can_user_book_this_week(user_id, week):
            return []

        user_slots = []
        user_id_str = str(user_id)

        worksheet = self.spreadsheet.worksheet("Расписание")
        all_data = worksheet.get_all_values()

        for slot in all_slots:
            row_index = slot['row_index']
            row = all_data[row_index - 1] if row_index - 1 < len(all_data) else []

            # Проверяем, записан ли пользователь в этой строке
            user_in_this_row = False
            for col in range(6, 10):  # Колонки 7-10 (G-J)
                if col < len(row):
                    cell_value = str(row[col]).strip()
                    if cell_value and f"{user_id_str}|" in cell_value:
                        user_in_this_row = True
                        break

            if not user_in_this_row:
                user_slots.append(slot)

        return user_slots

    def is_future_date(self, date_str: str, time_str: str) -> bool:
        """Проверяет, что дата и время в будущем"""
        try:
            # Парсим дату
            date_part = str(date_str).strip().split()[0]
            time_part = str(time_str).strip()[:5]  # Берем только часы:минуты

            date_formats = ["%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"]

            parsed_date = None
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(date_part, fmt)
                    break
                except ValueError:
                    continue

            if not parsed_date:
                logger.warning(f"Не удалось распарсить дату: '{date_str}'")
                return True

            try:
                time_obj = datetime.strptime(time_part, "%H:%M")
                parsed_date = parsed_date.replace(hour=time_obj.hour, minute=time_obj.minute)
            except:
                parsed_date = parsed_date.replace(hour=0, minute=0)

            # Сравниваем с текущим временем
            now = datetime.now()
            is_future = parsed_date > now

            logger.debug(f"Дата проверки: {date_str} {time_str} -> {parsed_date}, сейчас: {now}, будущее: {is_future}")
            return is_future

        except Exception as e:
            logger.error(f"Ошибка проверки даты: {e}")
            return True

    def book_slot(self, row_index: int, user_id: int, full_name: str, username: str) -> bool:
        """Запись студента на практику"""
        try:
            worksheet = self.spreadsheet.worksheet("Расписание")

            # 1. Определяем неделю
            week_cell = worksheet.cell(row_index, 2).value  # Колонка B - "Неделя"
            if not week_cell:
                logger.error(f"Не могу определить неделю в строке {row_index}")
                return False

            try:
                week = float(week_cell)
            except:
                logger.error(f"Неверный формат недели: {week_cell}")
                return False

            # 2. Проверяем, не записан ли уже на эту неделю
            if not self.can_user_book_this_week(user_id, week):
                logger.warning(f"Пользователь {user_id} уже записан на неделю {week}")
                return False

            # 3. Проверяем, не записан ли уже в этой строке
            row_values = worksheet.row_values(row_index)
            user_id_str = str(user_id)

            for col in range(7, 11):  # Студент1-4
                if col - 1 < len(row_values):
                    cell_value = str(row_values[col - 1]).strip()
                    if cell_value and f"{user_id_str}|" in cell_value:
                        logger.warning(f"❌ Пользователь {user_id} уже записан в строке {row_index}")
                        return False

            # 4. Определяем тариф и макс. места
            tariff = worksheet.cell(row_index, 1).value
            if tariff == "Базовый":
                max_seats = 4
            elif tariff == "Основной":
                max_seats = 3
            else:
                max_seats = 1

            # 5. Ищем свободное место
            for seat_num in range(1, max_seats + 1):
                col = 6 + seat_num  # 7, 8, 9, 10
                cell_value = worksheet.cell(row_index, col).value

                if not cell_value or str(cell_value).strip() == '':
                    # Записываем
                    student_info = f"{user_id}|{full_name}|{username or 'нет'}"
                    worksheet.update_cell(row_index, col, student_info)

                    logger.info(f"✅ Запись: строка {row_index}, место {seat_num}/{max_seats}, ID={user_id}")

                    # ОЧИЩАЕМ КЭШ ПОСЛЕ УСПЕШНОЙ ЗАПИСИ
                    self.invalidate_cache()

                    return True

            logger.warning(f"❌ Нет свободных мест в строке {row_index}")
            return False

        except Exception as e:
            logger.error(f"❌ Ошибка записи: {e}")
            return False

    def format_date(self, date_str: str) -> str:
        """Форматируем дату: '2024-12-10' → '10 декабря'"""
        try:
            if not any(c.isdigit() for c in date_str):
                return date_str

            date_part = date_str.split()[0]

            # Пробуем разные форматы
            for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y"):
                try:
                    dt = datetime.strptime(date_part, fmt)
                    break
                except ValueError:
                    continue
            else:
                return date_str

            months = {
                1: "января", 2: "февраля", 3: "марта", 4: "апреля",
                5: "мая", 6: "июня", 7: "июля", 8: "августа",
                9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
            }

            return f"{dt.day} {months[dt.month]}"

        except Exception:
            return date_str

    def get_user_bookings(self, user_id: int, username: str = "", full_name: str = ""):
        """Найти записи пользователя"""
        try:
            worksheet = self.spreadsheet.worksheet("Расписание")
            data = worksheet.get_all_records()
            df = pd.DataFrame(data)

            if df.empty:
                return []

            bookings = []

            for _, row in df.iterrows():
                for i in range(1, 26):
                    seat_col = f"Студент{i}"
                    student_cell = str(row.get(seat_col, '')).strip()

                    if not student_cell or '|' not in student_cell:
                        continue

                    # данные студента: "user_id|full_name|username"
                    parts = student_cell.split('|')
                    if len(parts) < 3:
                        continue

                    cell_user_id = parts[0].strip()
                    cell_full_name = parts[1].strip()
                    cell_username = parts[2].strip()

                    # совпадение
                    if (cell_user_id == str(user_id) or
                            (username and f"@{username}" in cell_username) or
                            (full_name and full_name.lower() in cell_full_name.lower())):

                        date_str = str(row['Дата']).split()[0]
                        date_display = self.format_date(date_str)

                        time_str = str(row['Время'])
                        if ' ' in time_str:
                            time_str = time_str.split()[0][:5]
                        else:
                            time_str = time_str[:5]

                        bookings.append({
                            'date': date_display,
                            'time': time_str,
                            'week': row.get('Неделя', ''),
                        })
                        break

            logger.info(f"Найдено записей для user_id={user_id}: {len(bookings)}")
            return bookings

        except Exception as e:
            logger.error(f"Ошибка get_user_bookings: {e}")
            return []

    def is_user_already_booked(self, user_id: int, date_str: str) -> bool:
        """Проверяет, записан ли пользователь уже на эту дату"""
        try:
            worksheet = self.spreadsheet.worksheet("Расписание")
            data = worksheet.get_all_records()
            df = pd.DataFrame(data)

            if df.empty:
                return False

            # Проверяем все столбцы Студент1-4
            for seat_col in ['Студент1', 'Студент2', 'Студент3', 'Студент4']:
                # Фильтруем строки где в этом столбце есть наш user_id
                mask = df[seat_col].astype(str).str.contains(str(user_id))
                matching_rows = df[mask]

                # Проверяем даты в найденных строках
                for _, row in matching_rows.iterrows():
                    row_date = str(row['Дата']).split()[0]
                    if row_date == date_str.split()[0]:
                        logger.info(f"Пользователь {user_id} уже записан на {date_str}")
                        return True

            return False

        except Exception as e:
            logger.error(f"Ошибка проверки дублей: {e}")
            return False

    def can_user_book_this_week(self, user_id: int, week: float, check_only_practice=True) -> bool:
        """Может ли пользователь записаться на эту неделю"""
        try:
            data = self._get_full_data()
            user_id_str = str(user_id)

            logger.info(f"🔍 ПРОВЕРКА недели {week} для user_id={user_id}")
            logger.info(f"📊 Всего записей в кэше: {len(data)}")

            found_in_week = False

            for idx, row in enumerate(data, 1):
                # 1. Получаем неделю из строки
                row_week_raw = str(row.get('Неделя', '')).strip()
                logger.debug(f"Строка {idx}: неделя='{row_week_raw}'")

                try:
                    row_week = float(row_week_raw)
                except:
                    continue  # Не число

                # 2. Сравниваем недели
                if abs(row_week - float(week)) > 0.01:  # Допуск для float
                    continue

                found_in_week = True
                logger.info(f"📅 Нашли запись недели {week}: строка {idx}")
                logger.info(f"   Тариф: '{row.get('Тариф', '')}'")

                # 3. Проверяем все 10 колонок студентов
                user_found_in_row = False
                for i in range(1, 26):
                    col_name = f"Студент{i}"
                    cell_value = str(row.get(col_name, '')).strip()

                    if cell_value and f"{user_id_str}|" in cell_value:
                        user_found_in_row = True
                        logger.info(f"   ❌ Найден в {col_name}: '{cell_value}'")
                        break

                # 4. Если пользователь найден в этой строке
                if user_found_in_row:
                    tariff = str(row.get('Тариф', '')).strip()

                    if tariff == "Тренинг":
                        if check_only_practice:
                            logger.info(f"   📘 Это тренинг, игнорируем для проверки практики")
                            continue
                        else:
                            logger.info(f"   ❌ Уже записан на тренинг недели {week}")
                            return False
                    else:
                        logger.info(f"   ❌ Уже записан на практику недели {week} (тариф: {tariff})")
                        return False

            if not found_in_week:
                logger.info(f"📭 Вообще не найдено записей недели {week}")

            logger.info(f"✅ Пользователь {user_id} может записаться на неделю {week}")
            return True

        except Exception as e:
            logger.error(f"Ошибка проверки недели: {e}", exc_info=True)
            return True

    def get_available_trainings(self, user_id: int = None):
        """Получить тренинги на неделю из B4"""
        try:
            # Берем неделю из B4
            current_week = self.get_training_week_number()
            logger.info(f"🎯 Ищем тренинги на неделю {current_week} из B4")

            # Если неделя = 0, сразу возвращаем пустой список
            if current_week <= 0:
                logger.info("📭 Неделя тренингов = 0, возвращаем пустой список")
                return []

            data = self._get_full_data()

            if not data:
                return []

            trainings = []
            MAX_SEATS = 25

            for idx, row in enumerate(data, start=2):
                # Проверяем тариф
                tariff = str(row.get('Тариф', '')).strip()
                if tariff != "Тренинг":
                    continue

                # Проверяем неделю (строгое равенство)
                try:
                    row_week = float(str(row.get('Неделя', 0)))
                except:
                    continue

                if abs(row_week - current_week) > 0.01:
                    continue

                # Проверяем статус
                status = str(row.get('Статус', '')).strip().lower()
                if status != 'активно':
                    continue

                # Проверка даты
                date_str = str(row.get('Дата', '')).split()[0]
                time_str = str(row.get('Время', ''))

                if not self.is_future_date(date_str, time_str):
                    logger.info(f"Пропускаем прошедший тренинг: {date_str} {time_str}")
                    continue

                # Если передан user_id, проверяем может ли он записаться
                if user_id and not self.can_user_book_this_week(user_id, current_week, check_only_practice=False):
                    logger.info(f"Пользователь {user_id} уже записан на тренинг недели {current_week}")
                    continue

                # Форматируем дату и время
                date_display = self.format_date(date_str)
                if ' ' in time_str:
                    time_str = time_str.split()[0][:5]
                else:
                    time_str = time_str[:5]

                # Считаем занятые места
                booked = 0
                for i in range(1, 26):
                    col_name = f"Студент{i}"
                    cell_value = str(row.get(col_name, '')).strip()
                    if cell_value:
                        booked += 1

                available = MAX_SEATS - booked
                if available > 0:
                    trainings.append({
                        'row_index': idx,
                        'date': date_display,
                        'time': time_str,
                        'available': available,
                        'max_seats': MAX_SEATS,
                        'week': current_week,
                    })

            logger.info(f"Тренинги на неделю {current_week}: {len(trainings)}")
            return trainings

        except Exception as e:
            logger.error(f"Ошибка получения тренингов: {e}")
            return []

    def get_training_details(self, row_index: int):
        try:
            worksheet = self.spreadsheet.worksheet("Расписание")
            row_values = worksheet.row_values(row_index)

            if len(row_values) < 5:
                return None

            date_str = row_values[2].split()[0] if len(row_values) > 2 else ""
            date_display = self.format_date(date_str)

            time_str = row_values[3] if len(row_values) > 3 else ""
            if ' ' in time_str:
                time_str = time_str.split()[0][:5]
            else:
                time_str = time_str[:5]

            return {
                'date': date_display,
                'time': time_str,
                'row_index': row_index
            }

        except Exception as e:
            logger.error(f"Ошибка получения деталей тренинга: {e}")
            return None

    def book_training(self, row_index: int, user_id: int, full_name: str, username: str) -> bool:
        """Запись на тренинг с проверкой недели из B4"""
        try:
            worksheet = self.spreadsheet.worksheet("Расписание")

            # 1. Проверяем неделю тренинга в строке
            week_cell = worksheet.cell(row_index, 2).value
            if week_cell:
                try:
                    training_week_in_row = float(week_cell)
                    # Получаем текущую неделю тренингов ИЗ B4
                    current_training_week = self.get_training_week_number()

                    # Строгое сравнение недель
                    if abs(training_week_in_row - current_training_week) > 0.01:
                        logger.warning(
                            f"❌ Тренинг недели {training_week_in_row} не доступен "
                            f"(текущая неделя тренингов из B4: {current_training_week})"
                        )
                        return False
                except Exception as e:
                    logger.error(f"Ошибка проверки недели: {e}")

            # 2. Проверяем, не прошедший ли тренинг
            date_str = worksheet.cell(row_index, 3).value
            time_str = worksheet.cell(row_index, 4).value

            if not self.is_future_date(date_str, time_str):
                logger.warning(f"❌ Попытка записаться на прошедший тренинг: {date_str} {time_str}")
                return False

            # 3. Проверяем, не записан ли уже
            row_values = worksheet.row_values(row_index)
            user_id_str = str(user_id)

            for col in range(7, 32):
                if col - 1 < len(row_values):
                    cell_value = str(row_values[col - 1]).strip()
                    if cell_value and f"{user_id_str}|" in cell_value:
                        logger.warning(f"❌ Пользователь {user_id} уже записан на этот тренинг")
                        return False

            # 4. Проверяем неделю для ограничения записи
            if week_cell:
                try:
                    week = float(week_cell)
                    if not self.can_user_book_this_week(user_id, week, check_only_practice=False):
                        logger.warning(f"Пользователь {user_id} уже записан на неделю {week} (тренинг или практика)")
                        return False
                except Exception as e:
                    logger.error(f"Ошибка проверки ограничения недели: {e}")

            # 5. Ищем свободное место
            MAX_SEATS = 25

            for seat_num in range(1, MAX_SEATS + 1):
                col = 6 + seat_num  # 7, 8, 9, ..., 31
                cell_value = worksheet.cell(row_index, col).value

                if not cell_value or str(cell_value).strip() == '':
                    # Записываем
                    student_info = f"{user_id}|{full_name}|{username or 'нет'}"
                    worksheet.update_cell(row_index, col, student_info)

                    logger.info(f"✅ Запись на тренинг: строка {row_index}, место {seat_num}/{MAX_SEATS}")

                    # Очищаем кэш
                    self.invalidate_cache()

                    return True

            logger.warning(f"❌ Нет свободных мест на тренинге (строка {row_index})")
            return False

        except Exception as e:
            logger.error(f"❌ Ошибка записи на тренинг: {e}")
            return False


gsheets = GoogleSheetsManager()
