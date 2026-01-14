
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import sys
from aiogram import Bot
from config import config
from gsheets import GoogleSheetsManager
from gsheets import gsheets


def setup_logging(debug: bool = False):
    """Настраивает логирование для notifier"""
    logger = logging.getLogger("notifier")


    level = logging.DEBUG if debug else logging.INFO
    logger.setLevel(level)

    if logger.handlers:
        logger.handlers.clear()

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    logger.addHandler(console_handler)

    return logger

logger = setup_logging(debug=False)


class Notifier:
    """Класс для отправки уведомлений"""

    def __init__(self):
        self.bot: Optional[Bot] = None
        self.gs: Optional[GoogleSheetsManager] = None



    async def setup(self):
        """Инициализация ресурсов"""
        try:
            self.bot = Bot(token=config.BOT_TOKEN)
            self.gs = GoogleSheetsManager()
            logger.info(" Ресурсы инициализированы")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации: {e}")
            raise

    async def cleanup(self):
        """Очистка ресурсов"""
        if self.bot:
            try:
                await self.bot.session.close()
                logger.debug("Сессия бота закрыта")
            except Exception as e:
                logger.error(f"Ошибка закрытия сессии: {e}")

    @staticmethod
    def parse_datetime(date_str: str, time_str: str) -> Optional[datetime]:
        """Парсинг даты и времени из различных форматов"""
        try:
            date_str = str(date_str).strip().split()[0]  # дата
            time_str = str(time_str).strip()[:5]  # ЧЧ:ММ

            formats = [
                ("%Y-%m-%d %H:%M", "ISO"),
                ("%d.%m.%Y %H:%M", "европейский"),
                ("%d/%m/%Y %H:%M", "другой"),
            ]

            for fmt, name in formats:
                try:
                    dt = datetime.strptime(f"{date_str} {time_str}", fmt)
                    logger.debug(f"Дата распарсена ({name}): {dt}")
                    return dt
                except ValueError:
                    continue

            logger.error(f"Не удалось распарсить дату: '{date_str} {time_str}'")
            return None

        except Exception as e:
            logger.error(f"Ошибка парсинга даты: {e}")
            return None

    @staticmethod
    def should_notify(practice_dt: datetime, now: datetime) -> bool:
        time_left = practice_dt - now

        if timedelta(hours=23) < time_left < timedelta(hours=25):
             logger.debug(f"Подходит для уведомления: осталось {time_left}")
             return True

        logger.debug(f"Не подходит: осталось {time_left}")
        return False

    @staticmethod
    def format_notification(practice_dt: datetime, time_str: str, record: Dict) -> str:
        """Форматируем сообщение уведомления"""
        months = {
            1: "января", 2: "февраля", 3: "марта", 4: "апреля",
            5: "мая", 6: "июня", 7: "июля", 8: "августа",
            9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
        }

        date_display = f"{practice_dt.day} {months[practice_dt.month]}"

        return (
            f"⏰ <b>НАПОМИНАНИЕ О ПРАКТИКЕ</b>\n\n"
            f"Завтра <b>{date_display}</b> в <b>{time_str}</b>\n")

    def extract_user_ids(self, record: Dict) -> list[int]:
        """ID всех пользователей из записи (столбцы Студент1-4)"""
        user_ids = []

        for seat_col in ['Студент1', 'Студент2', 'Студент3', 'Студент4']:
            student_cell = str(record.get(seat_col, '')).strip()

            if not student_cell or '|' not in student_cell:
                continue

            try:
                # Формат: "user_id|full_name|username"
                parts = student_cell.split('|')
                if len(parts) < 3:
                    continue

                user_id = int(parts[0].strip())
                user_ids.append(user_id)
                logger.debug(f"Найден студент в {seat_col}: ID={user_id}")

            except (ValueError, IndexError) as e:
                logger.warning(f"Некорректные данные в {seat_col}: '{student_cell}'")
                continue

        return user_ids
    async def process_record(self, record: Dict, index: int) -> bool:
        """Обрабатывает одну запись, отправляет уведомления всем студентам"""
        logger.debug(f"Обработка записи #{index}")

        try:
            # 1. Получаем пользователей из этой строки
            user_ids = self.extract_user_ids(record)
            if not user_ids:
                logger.debug(f"Запись #{index}: нет студентов")
                return False

            # 2. Получаем дату и время
            date_str = record.get('Дата')
            time_str = record.get('Время')
            if not date_str or not time_str:
                logger.debug(f"Запись #{index}: нет даты или времени")
                return False

            # 3. Парсим дату
            practice_dt = self.parse_datetime(date_str, time_str)
            if not practice_dt:
                return False

            # 4. Проверяем что дата в будущем
            now = datetime.now()
            if practice_dt <= now:
                logger.debug(f"Запись #{index}: дата в прошлом")
                return False

            # 5. Проверяем нужно ли отправлять уведомление
            if not self.should_notify(practice_dt, now):
                return False

            # 6. Форматируем сообщение
            clean_time = str(time_str).strip()[:5]
            message = self.format_notification(practice_dt, clean_time, record)

            # 7. Отправляем студентам в этой записи
            notifications_sent = 0
            for user_id in user_ids:
                try:
                    await self.bot.send_message(user_id, message, parse_mode="HTML")
                    logger.info(f"✅ Уведомление отправлено: user_id={user_id}, дата={practice_dt.date()} {clean_time}")
                    notifications_sent += 1

                    # Пауза между отправками
                    await asyncio.sleep(0.3)

                except Exception as e:
                    logger.error(f"Ошибка отправки user_id={user_id}: {e}")

            return notifications_sent > 0

        except Exception as e:
            logger.error(f"💥 Ошибка обработки записи #{index}: {e}")
            return False

    async def run(self):
        """Основной метод запуска"""
        logger.info(" Запуск проверки уведомлений")

        try:
            self.gs = gsheets
            await self.setup()

            # Получаем данные из таблицы
            worksheet = self.gs.spreadsheet.worksheet("Расписание")
            records = worksheet.get_all_records()
            logger.info(f" Загружено записей: {len(records)}")

            # Обрабатываем каждую запись
            notifications_sent = 0
            for i, record in enumerate(records, start=1):
                if await self.process_record(record, i):
                    notifications_sent += 1

            logger.info(f" Проверка завершена. Отправлено уведомлений: {notifications_sent}")

        except Exception as e:
            logger.error(f"Notifier error: {e}")

        finally:
            await self.cleanup()


async def main():
    """Точка входа"""
    notifier = Notifier()
    await notifier.run()


if __name__ == "__main__":
    debug_mode = "--debug" in sys.argv
    if debug_mode:
        logger = setup_logging(debug=True)
        logger.debug("Режим отладки включен")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Остановлено пользователем")
    except Exception as e:
        logger.critical(f"Фатальная ошибка: {e}")
        sys.exit(1)