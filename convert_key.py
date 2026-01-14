# test_speed_cached.py
import time
from gsheets import GoogleSheetsManager

gs = GoogleSheetsManager()

print("⚡ Тест скорости С КЭШЕМ:")
print("-" * 40)

# Первый запрос (должен быть медленным)
start = time.time()
tariffs1 = gs.get_available_tariffs()
t1 = time.time() - start
print(f"1. Тарифы (первый): {t1:.2f} сек")

# Второй запрос (должен быть БЫСТРЫМ)
start = time.time()
tariffs2 = gs.get_available_tariffs()
t2 = time.time() - start
print(f"2. Тарифы (второй): {t2:.2f} сек")

# Тренинги (из кэша)
start = time.time()
trainings = gs.get_available_trainings()
t3 = time.time() - start
print(f"3. Тренинги: {t3:.2f} сек")

print("-" * 40)
print(f"Ускорение: {t1/t2:.1f}x быстрее!")