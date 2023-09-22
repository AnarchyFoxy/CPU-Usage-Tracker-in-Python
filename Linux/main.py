import os
import threading
import signal
import time

MAX_CPUS = 32
BUFFER_SIZE = 256
LOG_FILE_PATH = "cpu_usage.log"

# Struktura przechowująca dane o zużyciu procesora
class CPUData:
    def __init__(self):
        self.cpu_name = ""
        self.user = 0
        self.nice = 0
        self.system = 0
        self.idle = 0
        self.iowait = 0
        self.irq = 0
        self.softirq = 0
        self.steal = 0
        self.guest = 0
        self.guest_nice = 0

# Struktura przechowująca dane o zużyciu procesora w %
class CPUUsage:
    def __init__(self):
        self.cpu_name = ""
        self.usage = 0.0

# Globalne zmienne
prev_cpu_data = [CPUData() for _ in range(MAX_CPUS)]
curr_cpu_data = [CPUData() for _ in range(MAX_CPUS)]
num_cpus = 0
data_mutex = threading.Lock()
data_ready = threading.Condition(data_mutex)
program_running = True
log_file = None
log_mutex = threading.Lock()

# Funkcja odczytu danych o zużyciu procesora
def read_cpu_data():
    global curr_cpu_data
    try:
        with open("/proc/stat", "r") as stat_file:
            lines = stat_file.readlines()

            for line in lines:
                if line.startswith("cpu"):
                    fields = line.split()
                    cpu_name = fields[0]
                    if len(cpu_name) > 3 and cpu_name[:3] == "cpu":
                        cpu_id = int(cpu_name[3:])
                        curr_cpu_data[cpu_id].cpu_name = cpu_name
                        curr_cpu_data[cpu_id].user = int(fields[1])
                        curr_cpu_data[cpu_id].nice = int(fields[2])
                        curr_cpu_data[cpu_id].system = int(fields[3])
                        curr_cpu_data[cpu_id].idle = int(fields[4])
                        curr_cpu_data[cpu_id].iowait = int(fields[5])
                        curr_cpu_data[cpu_id].irq = int(fields[6])
                        curr_cpu_data[cpu_id].softirq = int(fields[7])
                        curr_cpu_data[cpu_id].steal = int(fields[8])
                        curr_cpu_data[cpu_id].guest = int(fields[9])
                        curr_cpu_data[cpu_id].guest_nice = int(fields[10])
    except Exception as e:
        print("Błąd przy odczycie informacji o CPU:", str(e))
        os._exit(os.EX_OSERR)

# Funkcja obliczająca zużycie procesora w %
def calculate_cpu_usage(cpu_usage):
    for i in range(num_cpus):
        prev_total = (
            prev_cpu_data[i].user
            + prev_cpu_data[i].nice
            + prev_cpu_data[i].system
            + prev_cpu_data[i].idle
            + prev_cpu_data[i].iowait
            + prev_cpu_data[i].irq
            + prev_cpu_data[i].softirq
            + prev_cpu_data[i].steal
        )
        curr_total = (
            curr_cpu_data[i].user
            + curr_cpu_data[i].nice
            + curr_cpu_data[i].system
            + curr_cpu_data[i].idle
            + curr_cpu_data[i].iowait
            + curr_cpu_data[i].irq
            + curr_cpu_data[i].softirq
            + curr_cpu_data[i].steal
        )
        total_diff = curr_total - prev_total
        idle_diff = curr_cpu_data[i].idle - prev_cpu_data[i].idle
        usage = ((total_diff - idle_diff) / total_diff) * 100.0
        cpu_usage[i].cpu_name = f"CPU{i}"
        cpu_usage[i].usage = usage

# Funkcja wątku Reader
def reader_thread():
    while program_running:
        read_cpu_data()
        with data_ready:
            data_ready.notify()
        time.sleep(1)

# Funkcja wątku Analyzer
def analyzer_thread():
    cpu_usage = [CPUUsage() for _ in range(MAX_CPUS)]
    while program_running:
        with data_ready:
            data_ready.wait()
        calculate_cpu_usage(cpu_usage)

# Funkcja wątku Printer
def printer_thread():
    cpu_usage = [CPUUsage() for _ in range(MAX_CPUS)]
    while program_running:
        with data_ready:
            data_ready.wait()
        calculate_cpu_usage(cpu_usage)

        # Wydrukuj zużycie procesora
        for i in range(num_cpus):
            print(f"{cpu_usage[i].cpu_name}: {cpu_usage[i].usage:.2f}%")
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
        os._exit(os.EX_OSERR)

    # Określ liczbę dostępnych rdzeni CPU
    num_cpus = os.cpu_count()

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

    # Zakończ program
    os._exit(os.EX_OK)
