import pygame
import random
import sys

# Inicializar Pygame
pygame.init()

# Configuración de la pantalla
WIDTH, HEIGHT = 1200, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Simulador de Colas Multinivel con Retroalimentación")

# Colores
BACKGROUND = (15, 15, 30)
WHITE = (255, 255, 255)
GRAY = (100, 100, 100)
HIGHLIGHT = (70, 130, 180)
RED = (255, 0, 0)
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

    def generate_process(self):
        if self.total_processes_generated < self.max_processes and random.random() < 0.1:
            burst_time = random.randint(5, 50)
            new_process = Process(self.next_pid, self.current_time, burst_time)
            self.queues[0].append(new_process)
            self.next_pid += 1
            self.total_processes_generated += 1

    def update(self):
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

    def draw_completed_processes(self, screen):
        window_rect = pygame.Rect(WIDTH // 4, HEIGHT // 4, WIDTH // 2, HEIGHT // 2)
        pygame.draw.rect(screen, GRAY, window_rect)
        pygame.draw.rect(screen, WHITE, window_rect, 2)

        title = font.render("Procesos Completados", True, WHITE)
        screen.blit(title, (window_rect.x + 10, window_rect.y + 10))

        # Crear una superficie para el contenido con scroll
        content_height = max(window_rect.height - 50, len(self.completed_processes) * 30 + 40)
        content_surface = pygame.Surface((window_rect.width - 20, content_height))
        content_surface.fill(GRAY)

        # Dibujar encabezados de columna
        headers = ["PID", "Llegada", "Ráfaga", "Finalización", "Retorno", "Espera"]
        header_widths = [50, 70, 70, 100, 70, 70]
        x_offset = 10
        for header, width in zip(headers, header_widths):
            text = font.render(header, True, WHITE)
            content_surface.blit(text, (x_offset, 10))
            x_offset += width

        # Dibujar línea separadora
        pygame.draw.line(content_surface, WHITE, (10, 35), (window_rect.width - 30, 35), 2)

        # Dibujar datos de procesos
        for i, process in enumerate(self.completed_processes):
            y_pos = i * 30 + 40 - self.scroll_offset
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
                for value, width in zip(data, header_widths):
                    text = font.render(value, True, WHITE)
                    content_surface.blit(text, (x_offset, y_pos))
                    x_offset += width

        # Dibujar la superficie de contenido en la ventana
        screen.blit(content_surface, (window_rect.x + 10, window_rect.y + 40), 
                    (0, 0, window_rect.width - 20, window_rect.height - 50))

        # Dibujar la barra de desplazamiento
        if content_height > window_rect.height - 50:
            scroll_height = (window_rect.height - 50) * (window_rect.height - 50) / content_height
            scroll_pos = (window_rect.height - 50 - scroll_height) * self.scroll_offset / (content_height - window_rect.height + 50)
            pygame.draw.rect(screen, WHITE, (window_rect.right - 20, window_rect.y + 40 + scroll_pos, 10, scroll_height))

        self.max_scroll = max(0, content_height - window_rect.height + 50)

    def handle_scroll(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:  # Scroll up
                self.scroll_offset = max(0, self.scroll_offset - 30)
            elif event.button == 5:  # Scroll down
                self.scroll_offset = min(self.max_scroll, self.scroll_offset + 30)

def draw_menu(screen):
    screen.fill(BACKGROUND)
    title = title_font.render("Configuración de la Simulación", True, WHITE)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))

    input_boxes = []
    labels = ["Quantum para Cola 0:", "Quantum para Cola 1:", "Número de Procesos:"]
    for i, label in enumerate(labels):
        text = font.render(label, True, WHITE)
        screen.blit(text, (WIDTH // 2 - 200, 200 + i * 60))
        input_box = pygame.Rect(WIDTH // 2 + 50, 195 + i * 60, 100, 32)
        pygame.draw.rect(screen, WHITE, input_box, 2)
        input_boxes.append(input_box)

    start_button = pygame.Rect(WIDTH // 2 - 50, 420, 100, 40)
    pygame.draw.rect(screen, HIGHLIGHT, start_button)
    start_text = font.render("Iniciar", True, WHITE)
    screen.blit(start_text, (start_button.x + 25, start_button.y + 10))

    return input_boxes, start_button

def get_simulation_parameters():
    input_boxes, start_button = draw_menu(screen)
    input_values = ["", "", ""]
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
                    except ValueError:
                        error_message = "Por favor, ingrese valores numéricos válidos."
                for i, box in enumerate(input_boxes):
                    if box.collidepoint(event.pos):
                        active_box = i
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    active_box = (active_box + 1) % 3
                elif event.key == pygame.K_BACKSPACE:
                    input_values[active_box] = input_values[active_box][:-1]
                else:
                    input_values[active_box] += event.unicode

        screen.fill(BACKGROUND)
        input_boxes, start_button = draw_menu(screen)
        for i, box in enumerate(input_boxes):
            txt_surface = font.render(input_values[i], True, WHITE)
            screen.blit(txt_surface, (box.x + 5, box.y + 5))
            pygame.draw.rect(screen, HIGHLIGHT if i == active_box else WHITE, box, 2)

        if error_message:
            error_text = font.render(error_message, True, RED)
            screen.blit(error_text, (WIDTH // 2 - error_text.get_width() // 2, 480))

        pygame.display.flip()

def main():
    # Obtener los parámetros de simulación del menú
    time_quantum, max_processes = get_simulation_parameters()
    num_queues = 3

    mfq = MultilevelFeedbackQueue(num_queues, time_quantum, max_processes)

    # Loop principal
    clock = pygame.time.Clock()
    running = True
    paused = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    paused = not paused
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Clic izquierdo
                    mouse_pos = pygame.mouse.get_pos()
                    # Verificar si se hizo clic en el botón de procesos completados
                    button_rect = mfq.draw_completed_button(screen)
                    if button_rect.collidepoint(mouse_pos):
                        mfq.show_completed = not mfq.show_completed
                    # Verificar si se hizo clic en el botón de reinicio
                    restart_button_rect = pygame.Rect(WIDTH - 110, 60, 100, 40)
                    if restart_button_rect.collidepoint(mouse_pos):
                        return  # Reiniciar el programa
                if mfq.show_completed:
                    mfq.handle_scroll(event)

        screen.fill(BACKGROUND)

        if not paused:
            mfq.update()

        mfq.draw(screen)

        # Dibujar botón de play/pause con efecto hover
        mouse_pos = pygame.mouse.get_pos()
        button_rect = pygame.Rect(WIDTH - 110, 10, 100, 40)
        button_color = HIGHLIGHT if button_rect.collidepoint(mouse_pos) else GRAY
        pygame.draw.rect(screen, button_color, button_rect, border_radius=5)
        text = font.render("Play/Pause", True, WHITE)
        screen.blit(text, (WIDTH - 100, 20))

        # Dibujar botón de reinicio
        restart_button_rect = pygame.Rect(WIDTH - 110, 60, 100, 40)
        restart_button_color = HIGHLIGHT if restart_button_rect.collidepoint(mouse_pos) else GRAY
        pygame.draw.rect(screen, restart_button_color, restart_button_rect, border_radius=5)
        restart_text = font.render("Reiniciar", True, WHITE)
        screen.blit(restart_text, (WIDTH - 100, 70))

        pygame.display.flip()
        clock.tick(10)  # Ajustado para una simulación más rápida

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    while True:
        main()