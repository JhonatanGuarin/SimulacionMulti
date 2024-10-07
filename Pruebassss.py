import pygame
import random
import sys
from collections import deque

# Inicializar Pygame
pygame.init()

# Configuración de la pantalla
WIDTH, HEIGHT = 1200, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Simulador de Planificación de Procesos")

# Colores
BACKGROUND = (15, 15, 30)
WHITE = (255, 255, 255)
GRAY = (100, 100, 100)
HIGHLIGHT = (70, 130, 180)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
PROCESS_COLORS = [(255, 99, 71), (50, 205, 50), (65, 105, 225), (255, 215, 0), (218, 112, 214),
                  (0, 206, 209), (255, 105, 180), (154, 205, 50), (255, 140, 0), (138, 43, 226)]

# Fuentes
font = pygame.font.Font(None, 24)
title_font = pygame.font.Font(None, 36)

class Process:
    def __init__(self, pid, arrival_time, burst_time):
        self.pid = pid
        self.arrival_time = arrival_time
        self.burst_time = burst_time
        self.remaining_time = burst_time
        self.current_queue = 0
        self.x = 0
        self.y = 0
        self.color = random.choice(PROCESS_COLORS)
        self.completion_time = None
        self.turnaround_time = None
        self.waiting_time = None

class MultilevelFeedbackQueue:
    def __init__(self, num_queues, time_quantum, max_processes):
        self.num_queues = num_queues
        self.queues = [[] for _ in range(num_queues)]
        self.time_quantum = time_quantum
        self.current_time = 0
        self.completed_processes = []
        self.current_process = None
        self.time_in_current_queue = 0
        self.next_pid = 1
        self.total_processes_generated = 0
        self.max_processes = max_processes
        self.show_completed = False
        self.scroll_offset = 0
        self.max_scroll = 0
        self.is_paused = False

    def generate_process(self):
        if self.total_processes_generated < self.max_processes and random.random() < 0.1:
            burst_time = random.randint(5, 50)
            new_process = Process(self.next_pid, self.current_time, burst_time)
            self.queues[0].append(new_process)
            self.next_pid += 1
            self.total_processes_generated += 1

    def update(self):
        if self.is_paused:
            return

        self.generate_process()

        if self.current_process:
            self.current_process.remaining_time -= 1
            self.time_in_current_queue += 1
            
            if self.current_process.remaining_time == 0:
                self.current_process.completion_time = self.current_time
                self.current_process.turnaround_time = self.current_time - self.current_process.arrival_time
                self.current_process.waiting_time = self.current_process.turnaround_time - self.current_process.burst_time
                self.completed_processes.append(self.current_process)
                self.current_process = None
                self.time_in_current_queue = 0
            elif self.time_in_current_queue >= self.time_quantum[self.current_process.current_queue]:
                if self.current_process.current_queue < self.num_queues - 1:
                    self.current_process.current_queue += 1
                self.queues[self.current_process.current_queue].append(self.current_process)
                self.current_process = None
                self.time_in_current_queue = 0

        if not self.current_process:
            for q in range(self.num_queues):
                if self.queues[q]:
                    self.current_process = self.queues[q].pop(0)
                    self.time_in_current_queue = 0
                    break

        self.current_time += 1

    def draw(self, screen):
        # Dibujar título
        title = title_font.render("Simulador de Colas Multinivel con Retroalimentación", True, WHITE)
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 20))

        queue_height = (HEIGHT - 300) // self.num_queues
        start_y = 100

        for i, queue in enumerate(self.queues):
            y_pos = start_y + i * (queue_height + 20)
            # Dibujar fondo de la cola con gradiente
            for j in range(queue_height):
                alpha = 100 + (155 * j // queue_height)
                pygame.draw.rect(screen, (*HIGHLIGHT[:3], alpha), (50, y_pos + j, WIDTH - 100, 1))
            
            # Borde de la cola
            pygame.draw.rect(screen, WHITE, (50, y_pos, WIDTH - 100, queue_height), 2)
            
            # Etiqueta de la cola (dentro del recuadro)
            text = font.render(f"Cola {i}: Quantum = {self.time_quantum[i]}", True, WHITE)
            screen.blit(text, (60, y_pos + 10))

            visible_processes = queue[:min(len(queue), 8)]
            for j, process in enumerate(visible_processes):
                process.x = 60 + j * 135
                process.y = y_pos + 40
                self.draw_process(screen, process, is_current=(process == self.current_process))

            if len(queue) > 8:
                text = font.render(f"+{len(queue) - 8} más", True, WHITE)
                screen.blit(text, (WIDTH - 150, y_pos + queue_height // 2))

        if self.current_process:
            self.draw_process(screen, self.current_process, is_current=True, bottom=True)

        # Información general en un recuadro al final
        info_rect = pygame.Rect(50, HEIGHT - 80, WIDTH - 100, 60)
        pygame.draw.rect(screen, GRAY, info_rect)
        pygame.draw.rect(screen, WHITE, info_rect, 2)
        
        info_text = [
            f"Tiempo: {self.current_time}",
            f"Procesos generados: {self.total_processes_generated}/{self.max_processes}",
            f"Procesos completados: {len(self.completed_processes)}"
        ]
        for i, text in enumerate(info_text):
            rendered_text = font.render(text, True, WHITE)
            screen.blit(rendered_text, (info_rect.x + 10 + i * (info_rect.width // 3), info_rect.y + 20))

        # Dibujar botón para mostrar procesos completados
        self.draw_completed_button(screen)

        # Mostrar ventana de procesos completados si está activada
        if self.show_completed:
            self.draw_completed_processes(screen)

        # Dibujar botón de play/pause
        self.draw_play_pause_button(screen)

    def draw_process(self, screen, process, is_current=False, bottom=False):
        bar_width = 120
        bar_height = 30
        x = process.x if not bottom else WIDTH // 2 - bar_width // 2
        y = process.y if not bottom else HEIGHT - 100

        # Dibujar barra de progreso con efecto de brillo
        progress = (process.burst_time - process.remaining_time) / process.burst_time
        pygame.draw.rect(screen, GRAY, (x, y, bar_width, bar_height))
        pygame.draw.rect(screen, process.color, (x, y, int(bar_width * progress), bar_height))
        for i in range(5):
            highlight = (*process.color, 50 - i * 10)
            pygame.draw.line(screen, highlight, (x, y + i), (x + int(bar_width * progress), y + i))

        # Dibujar borde
        pygame.draw.rect(screen, WHITE, (x, y, bar_width, bar_height), 1)
        
        # Texto del proceso
        text = font.render(f"P{process.pid}: {process.remaining_time}", True, WHITE)
        screen.blit(text, (x + 5, y + bar_height // 2 - text.get_height() // 2))
        
        if is_current and not bottom:
            # Indicador de proceso actual en la cola
            pygame.draw.circle(screen, WHITE, (x - 15, y + bar_height // 2), 5)
        
        if bottom:
            # Información adicional para el proceso actual en la parte inferior
            text = font.render("Proceso en ejecución", True, WHITE)
            screen.blit(text, (x, y - 60))
            text = font.render(f"Cola: {process.current_queue}", True, WHITE)
            screen.blit(text, (x, y - 30))

    def draw_completed_button(self, screen):
        button_rect = pygame.Rect(WIDTH - 280, HEIGHT - 120, 230, 30)
        pygame.draw.rect(screen, HIGHLIGHT, button_rect, border_radius=5)
        text = font.render("Ver Procesos Completados", True, WHITE)
        text_rect = text.get_rect(center=button_rect.center)
        screen.blit(text, text_rect)
        return button_rect

    def draw_play_pause_button(self, screen):
        button_rect = pygame.Rect(50, HEIGHT - 120, 100, 30)
        color = GREEN if self.is_paused else RED
        pygame.draw.rect(screen, color, button_rect, border_radius=5)
        text = font.render("Play" if self.is_paused else "Pause", True, WHITE)
        text_rect = text.get_rect(center=button_rect.center)
        screen.blit(text, text_rect)
        return button_rect

    def draw_completed_processes(self, screen):
        window_rect = pygame.Rect(WIDTH // 4, HEIGHT // 4, WIDTH // 2, HEIGHT // 2)
        pygame.draw.rect(screen, GRAY, window_rect)
        pygame.draw.rect(screen, WHITE, window_rect, 2)

        title = font.render("Procesos Completados", True, WHITE)
        screen.blit(title, (window_rect.x + 10, window_rect.y + 10))

        # Definir las columnas y sus anchos
        headers = ["PID", "Llegada", "Ráfaga", "Finalización", "Retorno", "Espera"]
        column_widths = [40, 70, 70, 100, 70, 70]
        total_width = sum(column_widths)

        # Ajustar los anchos de las columnas para que ocupen todo el espacio disponible
        scale_factor = (window_rect.width - 40) / total_width
        column_widths = [int(width * scale_factor) for width in column_widths]

        # Dibujar encabezados
        x_offset = window_rect.x + 10
        for header, width in zip(headers, column_widths):
            text = font.render(header, True, WHITE)
            screen.blit(text, (x_offset, window_rect.y + 40))
            x_offset += width

        # Dibujar línea separadora
        pygame.draw.line(screen, WHITE, (window_rect.x + 10, window_rect.y + 65), 
                         (window_rect.right - 10, window_rect.y + 65), 2)

        # Crear una superficie para el contenido con scroll
        content_height = max(window_rect.height - 100, len(self.completed_processes) * 30 + 10)
        content_surface = pygame.Surface((window_rect.width - 20, content_height))
        content_surface.fill(GRAY)

        # Dibujar datos de procesos
        for i, process in enumerate(self.completed_processes):
            y_pos = i * 30 - self.scroll_offset
            if 0 <= y_pos < content_height:
                x_offset = 10
                data = [
                    str(process.pid),
                    str(process.arrival_time),
                    str(process.burst_time),
                    str(process.completion_time),
                    str(process.turnaround_time),
                    str(process.waiting_time)
                ]
                for value, width in zip(data, column_widths):
                    text = font.render(value, True, WHITE)
                    content_surface.blit(text, (x_offset, y_pos))
                    x_offset += width

        # Dibujar la superficie de contenido en la ventana
        screen.blit(content_surface, (window_rect.x + 10, window_rect.y + 70), 
                    (0, 0, window_rect.width - 20, window_rect.height - 80))

        # Dibujar la barra de desplazamiento
        if content_height > window_rect.height - 80:
            scroll_height = (window_rect.height - 80) * (window_rect.height - 80) / content_height
            scroll_pos = (window_rect.height - 80 - scroll_height) * self.scroll_offset / (content_height - window_rect.height + 80)
            pygame.draw.rect(screen, WHITE, (window_rect.right - 20, window_rect.y + 70 + scroll_pos, 10, scroll_height))

        self.max_scroll = max(0, content_height - window_rect.height + 80)

    def handle_scroll(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:  # Scroll up
                self.scroll_offset = max(0, self.scroll_offset - 30)
            elif event.button == 5:  # Scroll down
                self.scroll_offset = min(self.max_scroll, self.scroll_offset + 30)

class MultiQueueMultiAlgorithm:
    def __init__(self, time_quantum, max_processes):
        self.queues = [deque(), deque(), deque()]  # RR, SJF, FCFS
        self.time_quantum = time_quantum
        self.current_time = 0
        self.completed_processes = []
        self.current_process = None
        self.time_in_current_queue = 0
        self.next_pid = 1
        self.total_processes_generated = 0
        self.max_processes = max_processes
        self.show_completed = False
        self.scroll_offset = 0
        self.max_scroll = 0
        self.is_paused = False

    def generate_process(self):
        if self.total_processes_generated < self.max_processes and random.random() < 0.1:
            burst_time = random.randint(5, 50)
            new_process = Process(self.next_pid, self.current_time, burst_time)
            self.queues[0].append(new_process)
            self.next_pid += 1
            self.total_processes_generated += 1

    def update(self):
        if self.is_paused:
            return

        self.generate_process()

        if self.current_process:
            self.current_process.remaining_time -= 1
            self.time_in_current_queue += 1

            if self.current_process.remaining_time == 0:
                self.complete_process(self.current_process)
                self.current_process = None
                self.time_in_current_queue = 0
            elif self.time_in_current_queue >= self.time_quantum[self.current_process.current_queue]:
                if self.current_process.current_queue < len(self.queues) - 1:
                    self.current_process.current_queue += 1
                self.queues[self.current_process.current_queue].append(self.current_process)
                self.current_process = None
                self.time_in_current_queue = 0

        if not self.current_process:
            for i, queue in enumerate(self.queues):
                if queue:
                    if i == 0:  # Round Robin
                        self.current_process = queue.popleft()
                    elif i == 1:  # SJF
                        self.current_process = min(queue, key=lambda x: x.remaining_time)
                        queue.remove(self.current_process)
                    else:  # FCFS
                        self.current_process = queue.popleft()
                    self.time_in_current_queue = 0
                    break

        self.current_time += 1

    def complete_process(self, process):
        process.completion_time = self.current_time
        process.turnaround_time = self.current_time - process.arrival_time
        process.waiting_time = process.turnaround_time - process.burst_time
        self.completed_processes.append(process)

    def draw(self, screen):
        # Dibujar título
        title = title_font.render("Simulador de Colas Multinivel con Retroalimentación y Algoritmos Diferentes", True, WHITE)
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 20))

        queue_height = (HEIGHT - 300) // 3
        start_y = 100

        algorithms = ["Round Robin", "Shortest Job First", "First Come First Served"]
        for i, (queue, algorithm) in enumerate(zip(self.queues, algorithms)):
            y_pos = start_y + i * (queue_height + 20)
            # Dibujar fondo de la cola con gradiente
            for j in range(queue_height):
                alpha = 100 + (155 * j // queue_height)
                pygame.draw.rect(screen, (*HIGHLIGHT[:3], alpha), (50, y_pos + j, WIDTH - 100, 1))
            
            # Borde de la cola
            pygame.draw.rect(screen, WHITE, (50, y_pos, WIDTH - 100, queue_height), 2)
            
            # Etiqueta de la cola (dentro del recuadro)
            quantum_text = f"Quantum: {self.time_quantum[i]}" if i < 2 else "Quantum: ∞"
            text = font.render(f"Cola {i}: {algorithm} ({quantum_text})", True, WHITE)
            screen.blit(text, (60, y_pos + 10))

            visible_processes = list(queue)[:min(len(queue), 8)]
            for j, process in enumerate(visible_processes):
                process.x = 60 + j * 135
                process.y = y_pos + 40
                self.draw_process(screen, process, is_current=(process == self.current_process))

            if len(queue) > 8:
                text = font.render(f"+{len(queue) - 8} más", True, WHITE)
                screen.blit(text, (WIDTH - 150, y_pos + queue_height // 2))

        if self.current_process:
            self.draw_process(screen, self.current_process, is_current=True, bottom=True)

        # Información general en un recuadro al final
        info_rect = pygame.Rect(50, HEIGHT - 80, WIDTH - 100, 60)
        pygame.draw.rect(screen, GRAY, info_rect)
        pygame.draw.rect(screen, WHITE, info_rect, 2)
        
        info_text = [
            f"Tiempo: {self.current_time}",
            f"Procesos generados: {self.total_processes_generated}/{self.max_processes}",
            f"Procesos completados: {len(self.completed_processes)}"
        ]
        for i, text in enumerate(info_text):
            rendered_text = font.render(text, True, WHITE)
            screen.blit(rendered_text, (info_rect.x + 10 + i * (info_rect.width // 3), info_rect.y + 20))

        # Dibujar botón para mostrar procesos completados
        self.draw_completed_button(screen)

        # Mostrar ventana de procesos completados si está activada
        if self.show_completed:
            self.draw_completed_processes(screen)

        # Dibujar botón de play/pause
        self.draw_play_pause_button(screen)

    def draw_process(self, screen, process, is_current=False, bottom=False):
        bar_width = 120
        bar_height = 30
        x = process.x if not bottom else WIDTH // 2 - bar_width // 2
        y = process.y if not bottom else HEIGHT - 100

        # Dibujar barra de progreso con efecto de brillo
        progress = (process.burst_time - process.remaining_time) / process.burst_time
        pygame.draw.rect(screen, GRAY, (x, y, bar_width, bar_height))
        pygame.draw.rect(screen, process.color, (x, y, int(bar_width * progress), bar_height))
        for i in range(5):
            highlight = (*process.color, 50 - i * 10)
            pygame.draw.line(screen, highlight, (x, y + i), (x + int(bar_width * progress), y + i))

        # Dibujar borde
        pygame.draw.rect(screen, WHITE, (x, y, bar_width, bar_height), 1)
        
        # Texto del proceso
        text = font.render(f"P{process.pid}: {process.remaining_time}", True, WHITE)
        screen.blit(text, (x + 5, y + bar_height // 2 - text.get_height() // 2))
        
        if is_current and not bottom:
            # Indicador de proceso actual en la cola
            pygame.draw.circle(screen, WHITE, (x - 15, y + bar_height // 2), 5)
        
        if bottom:
            # Información adicional para el proceso actual en la parte inferior
            text = font.render("Proceso en ejecución", True, WHITE)
            screen.blit(text, (x, y - 60))
            text = font.render(f"Cola: {process.current_queue}", True, WHITE)
            screen.blit(text, (x, y - 30))

    def draw_completed_button(self, screen):
        button_rect = pygame.Rect(WIDTH - 280, HEIGHT - 120, 230, 30)
        pygame.draw.rect(screen, HIGHLIGHT, button_rect, border_radius=5)
        text = font.render("Ver Procesos Completados", True, WHITE)
        text_rect = text.get_rect(center=button_rect.center)
        screen.blit(text, text_rect)
        return button_rect

    def draw_play_pause_button(self, screen):
        button_rect = pygame.Rect(50, HEIGHT - 120, 100, 30)
        color = GREEN if self.is_paused else RED
        pygame.draw.rect(screen, color, button_rect, border_radius=5)
        text = font.render("Play" if self.is_paused else "Pause", True, WHITE)
        text_rect = text.get_rect(center=button_rect.center)
        screen.blit(text, text_rect)
        return button_rect

    def draw_completed_processes(self, screen):
        window_rect = pygame.Rect(WIDTH // 4, HEIGHT // 4, WIDTH // 2, HEIGHT // 2)
        pygame.draw.rect(screen, GRAY, window_rect)
        pygame.draw.rect(screen, WHITE, window_rect, 2)

        title = font.render("Procesos Completados", True, WHITE)
        screen.blit(title, (window_rect.x + 10, window_rect.y + 10))

        # Definir las columnas y sus anchos
        headers = ["PID", "Llegada", "Ráfaga", "Finalización", "Retorno", "Espera"]
        column_widths = [40, 70, 70, 100, 70, 70]
        total_width = sum(column_widths)

        # Ajustar los anchos de las columnas para que ocupen todo el espacio disponible
        scale_factor = (window_rect.width - 40) / total_width
        column_widths = [int(width * scale_factor) for width in column_widths]

        # Dibujar encabezados
        x_offset = window_rect.x + 10
        for header, width in zip(headers, column_widths):
            text = font.render(header, True, WHITE)
            screen.blit(text, (x_offset, window_rect.y + 40))
            x_offset += width

        # Dibujar línea separadora
        pygame.draw.line(screen, WHITE, (window_rect.x + 10, window_rect.y + 65), 
                         (window_rect.right - 10, window_rect.y + 65), 2)

        # Crear una superficie para el contenido con scroll
        content_height = max(window_rect.height - 100, len(self.completed_processes) * 30 + 10)
        content_surface = pygame.Surface((window_rect.width - 20, content_height))
        content_surface.fill(GRAY)

        # Dibujar datos de procesos
        for i, process in enumerate(self.completed_processes):
            y_pos = i * 30 - self.scroll_offset
            if 0 <= y_pos < content_height:
                x_offset = 10
                data = [
                    str(process.pid),
                    str(process.arrival_time),
                    str(process.burst_time),
                    str(process.completion_time),
                    str(process.turnaround_time),
                    str(process.waiting_time)
                ]
                for value, width in zip(data, column_widths):
                    text = font.render(value, True, WHITE)
                    content_surface.blit(text, (x_offset, y_pos))
                    x_offset += width

        # Dibujar la superficie de contenido en la ventana
        screen.blit(content_surface, (window_rect.x + 10, window_rect.y + 70), 
                    (0, 0, window_rect.width - 20, window_rect.height - 80))

        # Dibujar la barra de desplazamiento
        if content_height > window_rect.height - 80:
            scroll_height = (window_rect.height - 80) * (window_rect.height - 80) / content_height
            scroll_pos = (window_rect.height - 80 - scroll_height) * self.scroll_offset / (content_height - window_rect.height + 80)
            pygame.draw.rect(screen, WHITE, (window_rect.right - 20, window_rect.y + 70 + scroll_pos, 10, scroll_height))

        self.max_scroll = max(0, content_height - window_rect.height + 80)

    def handle_scroll(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:  # Scroll up
                self.scroll_offset = max(0, self.scroll_offset - 30)
            elif event.button == 5:  # Scroll down
                self.scroll_offset = min(self.max_scroll, self.scroll_offset + 30)

def draw_main_menu(screen):
    screen.fill(BACKGROUND)
    title = title_font.render("Simulador de Planificación de Procesos", True, WHITE)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))

    options = [
        "1. Colas Multinivel con Retroalimentación",
        "2. Colas Multinivel con Retroalimentación (Algoritmos Diferentes)"
    ]
    
    buttons = []
    for i, option in enumerate(options):
        button_rect = pygame.Rect(WIDTH // 2 - 200, 200 + i * 60, 400, 50)
        pygame.draw.rect(screen, HIGHLIGHT, button_rect, border_radius=5)
        text = font.render(option, True, WHITE)
        text_rect = text.get_rect(center=button_rect.center)
        screen.blit(text, text_rect)
        buttons.append(button_rect)

    return buttons

def get_simulation_parameters(simulation_type):
    screen.fill(BACKGROUND)
    title = title_font.render("Configuración de la Simulación", True, WHITE)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))

    input_boxes = []
    labels = []
    if simulation_type == "multilevel":
        labels = ["Quantum para Cola 0:", "Quantum para Cola 1:", "Número de Procesos:"]
    else:
        labels = ["Quantum para Cola 0 (RR):", "Quantum para Cola 1 (SJF):", "Número de Procesos:"]

    for i, label in enumerate(labels):
        text = font.render(label, True, WHITE)
        screen.blit(text, (WIDTH // 2 - 200, 200 + i * 60))
        input_box = pygame.Rect(WIDTH // 2 + 50, 195 + i * 60, 100, 32)
        pygame.draw.rect(screen, WHITE, input_box, 2)
        input_boxes.append(input_box)

    start_button = pygame.Rect(WIDTH // 2 - 50, 200 + len(labels) * 60, 100, 40)
    pygame.draw.rect(screen, HIGHLIGHT, start_button)
    start_text = font.render("Iniciar", True, WHITE)
    screen.blit(start_text, (start_button.x + 25, start_button.y + 10))

    input_values = ["" for _ in range(len(labels))]
    active_box = 0
    running = True
    error_message = ""

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if start_button.collidepoint(event.pos):
                    try:
                        if simulation_type == "multilevel":
                            q1 = int(input_values[0])
                            q2 = int(input_values[1])
                            num_processes = int(input_values[2])
                            if q1 <= q2 and num_processes > 0:
                                return [q1, q2, float('inf')], num_processes
                            else:
                                if q1 > q2:
                                    error_message = "El quantum de la Cola 0 debe ser menor o igual al de la Cola 1."
                                else:
                                    error_message = "El número de procesos debe ser positivo."
                        else:
                            q1 = int(input_values[0])
                            q2 = int(input_values[1])
                            num_processes = int(input_values[2])
                            if q1 > 0 and q2 > 0 and num_processes > 0:
                                return [q1, q2, float('inf')], num_processes
                            else:
                                error_message = "Todos los quantums y el número de procesos deben ser positivos."
                    except ValueError:
                        error_message = "Por favor, ingrese valores numéricos válidos."
                for i, box in enumerate(input_boxes):
                    if box.collidepoint(event.pos):
                        active_box = i
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    active_box = (active_box + 1) % len(input_boxes)
                elif event.key == pygame.K_BACKSPACE:
                    input_values[active_box] = input_values[active_box][:-1]
                else:
                    input_values[active_box] += event.unicode

        screen.fill(BACKGROUND)
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))

        for i, (label, box, value) in enumerate(zip(labels, input_boxes, input_values)):
            text = font.render(label, True, WHITE)
            screen.blit(text, (WIDTH // 2 - 200, 200 + i * 60))
            pygame.draw.rect(screen, WHITE, box, 2)
            text_surface = font.render(value, True, WHITE)
            screen.blit(text_surface, (box.x + 5, box.y + 5))

        pygame.draw.rect(screen, HIGHLIGHT, start_button)
        screen.blit(start_text, (start_button.x + 25, start_button.y + 10))

        if error_message:
            error_text = font.render(error_message, True, RED)
            screen.blit(error_text, (WIDTH // 2 - error_text.get_width() // 2, 150))

        pygame.display.flip()

    return None

def main():
    clock = pygame.time.Clock()
    simulation = None
    running = True
    main_menu = True
    completed_button_rect = None
    play_pause_button_rect = None

    while running:
        if main_menu:
            buttons = draw_main_menu(screen)
            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    for i, button in enumerate(buttons):
                        if button.collidepoint(event.pos):
                            if i == 0:
                                time_quantum, max_processes = get_simulation_parameters("multilevel")
                                if time_quantum and max_processes:
                                    simulation = MultilevelFeedbackQueue(3, time_quantum, max_processes)
                                    main_menu = False
                            elif i == 1:
                                time_quantum, max_processes = get_simulation_parameters("multi_algorithm")
                                if time_quantum and max_processes:
                                    simulation = MultiQueueMultiAlgorithm(time_quantum, max_processes)
                                    main_menu = False
        else:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if completed_button_rect and completed_button_rect.collidepoint(event.pos):
                        simulation.show_completed = not simulation.show_completed
                    elif play_pause_button_rect and play_pause_button_rect.collidepoint(event.pos):
                        simulation.is_paused = not simulation.is_paused
                    elif simulation.show_completed:
                        simulation.handle_scroll(event)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        main_menu = True
                        simulation = None

            if simulation:
                simulation.update()
                screen.fill(BACKGROUND)
                simulation.draw(screen)
                completed_button_rect = simulation.draw_completed_button(screen)
                play_pause_button_rect = simulation.draw_play_pause_button(screen)
                pygame.display.flip()

        clock.tick(10)  # Limit to 10 FPS

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()