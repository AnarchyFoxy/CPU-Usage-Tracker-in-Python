import threading
import signal
import time
import psutil

MAX_CPUS = psutil.cpu_count(logical=False)
LOG_FILE_PATH = "cpu_usage.log"

# Struktura przechowująca dane o zużyciu procesora
class CPUData:
    def __init__(self):
        self.cpu_name = ""
        self.usage = 0.0

# Globalne zmienne
curr_cpu_data = [CPUData() for _ in range(MAX_CPUS)]
num_cpus = MAX_CPUS
data_mutex = threading.Lock()
data_ready = threading.Condition(data_mutex)
program_running = True
log_file = None
log_mutex = threading.Lock()

iteration = 0
continue_flag = True

# Funkcja odczytu danych o zużyciu procesora
def read_cpu_data():
    global curr_cpu_data
    try:
        cpu_percentages = psutil.cpu_percent(interval=1, percpu=True)
        for i, cpu_percent in enumerate(cpu_percentages):
            curr_cpu_data[i].cpu_name = f"CPU{i}"
            curr_cpu_data[i].usage = cpu_percent
    except Exception as e:
        print("Błąd przy odczycie informacji o CPU:", str(e))
        exit(1)

# Funkcja wątku Reader
def reader_thread():
    global iteration, continue_flag, program_running
    while program_running:
        read_cpu_data()
        with data_ready:
            data_ready.notify()
        iteration += 1

        if iteration % 10 == 0:
            print("Czy kontynuować? (n - kontynuuj, q - wyjdź)")
            response = input()
            if response == "n":
                continue_flag = True
                print("Kontynuowanie...")
            elif response == "q":
                print("Zakończono na żądanie użytkownika.")
                program_running = False
                with data_ready:
                    data_ready.notify()

        time.sleep(1)

# Funkcja wątku Analyzer
def analyzer_thread():
    while program_running:
        with data_ready:
            data_ready.wait()

# Funkcja wątku Printer
def printer_thread():
    while program_running:
        with data_ready:
            data_ready.wait()

        # Wydrukuj zużycie procesora
        for i in range(num_cpus):
            print(f"{curr_cpu_data[i].cpu_name}: {curr_cpu_data[i].usage:.2f}%")
        print()

        time.sleep(1)

# Funkcja wątku Watchdog
def watchdog_thread():
    while program_running:
        time.sleep(2)
        with data_ready:
            data_ready.notify()

# Funkcja wątku Logger
def logger_thread():
    global log_file
    while program_running:
        # Tutaj można zaimplementować zapisywanie logów do pliku w sposób zsynchronizowany
        if log_file is not None:
            with log_mutex:
                log_file.write("Log message\n")
                log_file.flush()
        time.sleep(1)

# Obsługa sygnału SIGTERM
def sigterm_handler(signum, frame):
    global program_running
    program_running = False
    with data_ready:
        data_ready.notify()

if __name__ == "__main__":
    # Zarejestruj obsługę sygnału SIGTERM
    signal.signal(signal.SIGTERM, sigterm_handler)

    # Otwórz plik logu
    try:
        log_file = open(LOG_FILE_PATH, "w")
    except Exception as e:
        print("Nie można otworzyć pliku logu:", str(e))
        exit(1)

    # Inicjalizacja wątków
    reader = threading.Thread(target=reader_thread)
    analyzer = threading.Thread(target=analyzer_thread)
    printer = threading.Thread(target=printer_thread)
    watchdog = threading.Thread(target=watchdog_thread)
    logger = threading.Thread(target=logger_thread)

    reader.start()
    analyzer.start()
    printer.start()
    watchdog.start()
    logger.start()

    # Oczekuj na zakończenie wątków
    reader.join()
    analyzer.join()
    printer.join()
    watchdog.join()
    logger.join()

    # Zamknij plik logu
    if log_file is not None:
        log_file.close()
