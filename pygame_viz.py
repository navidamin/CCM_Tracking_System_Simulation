"""
CCM Machine Cycle — Interactive Pygame Viewer.

Real-time interactive viewer with:
  - Top view of all 6 strands
  - Play/pause, step forward/backward, speed control
  - Time slider
  - Hover tooltip for billet info
  - Keyboard controls:
      Space     : play/pause
      Right/Left: step forward/backward
      +/-       : increase/decrease speed
      1-6       : highlight strand
      0         : show all strands
      R         : reset to t=0
      Q/Escape  : quit

Usage:
    python pygame_viz.py                     # default v=3.6
    python pygame_viz.py --velocity 2.68     # max safe velocity
    python pygame_viz.py --t-end 500
"""

import argparse
import sys

try:
    import pygame
except ImportError:
    print("pygame not installed. Install with: pip install pygame")
    sys.exit(1)

from machine_cycle_calc import MachineCycleCalculator, MachineState
from viz_common import (
    X_SECURITY_STOPPER, X_INTERMEDIATE_STOPPER, X_FIXED_STOPPER,
    BILLET_LENGTH, STRAND_COLORS, STOPPER_COLORS, TC_COLOR,
    COOLBED_COLOR, CRASH_COLOR, ROLLER_COLOR, strand_y,
    X_TC_RAIL, X_COOLBED_START,
)
from config import NUM_STRANDS, STRAND_TO_COOLBED

# ---------------------------------------------------------------------------
# Display constants
# ---------------------------------------------------------------------------

WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 800
FPS = 60

BG_COLOR = (245, 245, 245)
TEXT_COLOR = (50, 50, 50)
GRID_COLOR = (220, 220, 220)

# World-to-screen mapping
X_MARGIN = 60
Y_MARGIN = 80
PANEL_HEIGHT = WINDOW_HEIGHT - 200  # leave room for controls

# Speed presets (seconds of sim time per real second)
SPEEDS = [0.5, 1, 2, 5, 10, 20, 50]
DEFAULT_SPEED_IDX = 3  # 5x


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color string to RGB tuple."""
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _rgb(hex_or_tuple):
    """Normalize color to RGB tuple."""
    if isinstance(hex_or_tuple, str):
        return _hex_to_rgb(hex_or_tuple)
    return hex_or_tuple


# Pre-convert colors
STRAND_RGB = {sid: _rgb(c) for sid, c in STRAND_COLORS.items()}
STOPPER_RGB = {k: _rgb(v) for k, v in STOPPER_COLORS.items()}
TC_RGB = _rgb(TC_COLOR)
CB_RGB = _rgb(COOLBED_COLOR)
CRASH_RGB = _rgb(CRASH_COLOR)
ROLLER_RGB = _rgb(ROLLER_COLOR)


class PygameViewer:
    """Interactive pygame viewer for the machine cycle."""

    def __init__(self, velocity: float = 3.6, t_end: float = 450.0):
        self.velocity = velocity
        self.t_end = t_end

        # Compute
        self.calc = MachineCycleCalculator(velocity)
        self.calc.compute(t_max=t_end + 100)

        # State
        self.t = 0.0
        self.dt = 0.5  # sim time step per frame update
        self.playing = False
        self.speed_idx = DEFAULT_SPEED_IDX
        self.highlight_strand = 0  # 0 = all
        self.dragging_slider = False

        # World extents
        self.world_x_min = -2.0
        self.world_x_max = X_COOLBED_START + 5.0
        self.world_y_min = -1.0
        self.world_y_max = strand_y(NUM_STRANDS) + 2.0

        # Billet rects for hover detection
        self.billet_rects: list[tuple[pygame.Rect, int, int, str]] = []
        self.hover_billet = None

    def world_to_screen(self, wx: float, wy: float) -> tuple[int, int]:
        """Convert world coordinates to screen pixels."""
        frac_x = (wx - self.world_x_min) / (self.world_x_max - self.world_x_min)
        frac_y = (wy - self.world_y_min) / (self.world_y_max - self.world_y_min)
        sx = int(X_MARGIN + frac_x * (WINDOW_WIDTH - 2 * X_MARGIN))
        sy = int(Y_MARGIN + frac_y * PANEL_HEIGHT)
        return (sx, sy)

    def world_to_screen_w(self, ww: float) -> int:
        """Convert world width to screen pixels."""
        return int(ww / (self.world_x_max - self.world_x_min) *
                   (WINDOW_WIDTH - 2 * X_MARGIN))

    def world_to_screen_h(self, wh: float) -> int:
        """Convert world height to screen pixels."""
        return int(wh / (self.world_y_max - self.world_y_min) * PANEL_HEIGHT)

    def draw(self, screen: pygame.Surface, state: MachineState):
        """Draw the complete frame."""
        screen.fill(BG_COLOR)
        self.billet_rects.clear()

        self._draw_roller_table(screen)
        self._draw_stoppers(screen, state)
        self._draw_billets(screen, state)
        self._draw_tc(screen, state)
        self._draw_coolbed(screen, state)
        self._draw_collision(screen, state)
        self._draw_hud(screen, state)
        self._draw_controls(screen)
        self._draw_slider(screen)
        self._draw_tooltip(screen)

    def _draw_roller_table(self, screen):
        """Draw roller table background."""
        for sid in range(1, NUM_STRANDS + 1):
            y = strand_y(sid)
            sx0, sy = self.world_to_screen(0, y)
            sx1, _ = self.world_to_screen(X_FIXED_STOPPER, y)
            pygame.draw.line(screen, ROLLER_RGB, (sx0, sy), (sx1, sy), 1)

            # Strand label
            font = pygame.font.SysFont(None, 18)
            lx, ly = self.world_to_screen(-1.5, y)
            color = STRAND_RGB.get(sid, TEXT_COLOR)
            label = font.render(f'S{sid}', True, color)
            screen.blit(label, (lx - 10, ly - 8))

        # Stopper reference lines
        for x_stop in [X_SECURITY_STOPPER, X_INTERMEDIATE_STOPPER, X_FIXED_STOPPER]:
            sx, sy0 = self.world_to_screen(x_stop, self.world_y_min)
            _, sy1 = self.world_to_screen(x_stop, self.world_y_max)
            pygame.draw.line(screen, GRID_COLOR, (sx, sy0), (sx, sy1), 1)

        # TC rail
        sx, sy0 = self.world_to_screen(X_TC_RAIL, self.world_y_min)
        _, sy1 = self.world_to_screen(X_TC_RAIL, self.world_y_max)
        pygame.draw.line(screen, TC_RGB, (sx, sy0), (sx, sy1), 2)

    def _draw_stoppers(self, screen, state: MachineState):
        """Draw stopper state indicators."""
        sz = 8
        for sid in range(1, NUM_STRANDS + 1):
            ss = state.stoppers.get(sid)
            if ss is None:
                continue
            y = strand_y(sid) - 0.3

            for x_stop, is_up in [
                (X_SECURITY_STOPPER, ss.security_up),
                (X_INTERMEDIATE_STOPPER, ss.intermediate_up),
            ]:
                sx, sy = self.world_to_screen(x_stop, y)
                color = STOPPER_RGB[is_up]
                pygame.draw.rect(screen, color,
                                 (sx - sz // 2, sy - sz // 2, sz, sz))
                pygame.draw.rect(screen, (0, 0, 0),
                                 (sx - sz // 2, sy - sz // 2, sz, sz), 1)

    def _draw_billets(self, screen, state: MachineState):
        """Draw billets."""
        billet_h = self.world_to_screen_h(0.4)
        tc_max_y = STRAND_TO_COOLBED[1]

        for bid, sid, x, y_pos, phase in state.billet_positions:
            if phase == 'not_born':
                continue

            dim = (self.highlight_strand != 0 and
                   sid != self.highlight_strand)

            if phase in ('on_tc', 'placing'):
                draw_y = tc_max_y - y_pos
                draw_y = min(draw_y, strand_y(NUM_STRANDS) + 1.5)
                x_draw = X_TC_RAIL + 0.5
            elif phase == 'on_coolbed':
                x_draw = X_COOLBED_START + 1.5
                draw_y = strand_y(sid)
            else:
                x_draw = x
                draw_y = strand_y(sid)

            # Screen coords
            sx, sy = self.world_to_screen(x_draw - BILLET_LENGTH,
                                          draw_y - 0.2)
            sw = self.world_to_screen_w(BILLET_LENGTH)

            # Color
            color = STRAND_RGB.get(sid, (100, 100, 100))
            if phase == 'collision':
                color = CRASH_RGB
            elif phase == 'blocked_at_security':
                pass  # normal color, red edge

            if dim:
                color = tuple(min(255, c + 150) for c in color)

            alpha = 60 if phase == 'on_coolbed' else 220
            billet_surf = pygame.Surface((max(sw, 1), max(billet_h, 1)),
                                        pygame.SRCALPHA)
            billet_surf.fill((*color, alpha))
            screen.blit(billet_surf, (sx, sy))

            # Edge
            edge_color = CRASH_RGB if phase in ('collision', 'blocked_at_security') else (0, 0, 0)
            pygame.draw.rect(screen, edge_color,
                             (sx, sy, max(sw, 1), max(billet_h, 1)), 1)

            # Billet ID label
            if phase != 'on_coolbed' and sw > 15:
                font = pygame.font.SysFont(None, 14)
                label = font.render(str(bid), True, (255, 255, 255))
                lx = sx + sw // 2 - label.get_width() // 2
                ly = sy + billet_h // 2 - label.get_height() // 2
                screen.blit(label, (lx, ly))

            # Store rect for hover
            rect = pygame.Rect(sx, sy, max(sw, 1), max(billet_h, 1))
            self.billet_rects.append((rect, bid, sid, phase))

    def _draw_tc(self, screen, state: MachineState):
        """Draw TC position marker."""
        tc_y_rail = state.tc_y
        tc_max_y = STRAND_TO_COOLBED[1]
        draw_y = tc_max_y - tc_y_rail
        draw_y = min(draw_y, strand_y(NUM_STRANDS) + 1.5)

        sx, sy = self.world_to_screen(X_TC_RAIL, draw_y)
        sz = 10
        pygame.draw.circle(screen, TC_RGB, (sx, sy), sz)
        pygame.draw.circle(screen, (255, 255, 255), (sx, sy), sz, 2)

        # Phase label
        if state.tc_phase != 'idle':
            font = pygame.font.SysFont(None, 14)
            label = font.render(state.tc_phase.replace('_', ' '),
                                True, TC_RGB)
            screen.blit(label, (sx + sz + 4, sy - 6))

    def _draw_coolbed(self, screen, state: MachineState):
        """Draw cooling bed area."""
        sx, sy = self.world_to_screen(X_COOLBED_START - 0.5,
                                      self.world_y_min + 0.3)
        sw = self.world_to_screen_w(4.0)
        sh = self.world_to_screen_h(self.world_y_max - self.world_y_min - 1.5)

        cb_surf = pygame.Surface((max(sw, 1), max(sh, 1)), pygame.SRCALPHA)
        cb_surf.fill((*CB_RGB, 30))
        screen.blit(cb_surf, (sx, sy))

        if state.coolbed_count > 0:
            font = pygame.font.SysFont(None, 18)
            label = font.render(f'{state.coolbed_count} billets',
                                True, CB_RGB)
            screen.blit(label, (sx + 5, sy + 5))

    def _draw_collision(self, screen, state: MachineState):
        """Draw collision annotation."""
        if state.collision:
            font = pygame.font.SysFont(None, 28)
            text = f'CRASH at t={state.collision_time:.2f}s (strand {state.collision_strand})'
            label = font.render(text, True, CRASH_RGB)
            x = WINDOW_WIDTH // 2 - label.get_width() // 2
            screen.blit(label, (x, 10))

    def _draw_hud(self, screen, state: MachineState):
        """Draw heads-up display (time, velocity, status)."""
        font = pygame.font.SysFont(None, 22)
        y_pos = WINDOW_HEIGHT - 170

        t_str = f'{self.t:.2f}' if self.t != int(self.t) else f'{self.t:.1f}'
        items = [
            f'v = {self.velocity:.2f} m/min',
            f't = {t_str} s',
            f'Speed: {SPEEDS[self.speed_idx]}x',
            'PLAYING' if self.playing else 'PAUSED',
        ]
        for i, text in enumerate(items):
            color = (0, 150, 0) if 'PLAYING' in text else TEXT_COLOR
            label = font.render(text, True, color)
            screen.blit(label, (X_MARGIN + i * 280, y_pos))

    def _draw_controls(self, screen):
        """Draw keyboard controls help."""
        font = pygame.font.SysFont(None, 16)
        y_pos = WINDOW_HEIGHT - 140
        controls = [
            'Space: Play/Pause',
            'Left/Right: Step',
            '+/-: Speed',
            '1-6: Highlight strand',
            '0: All strands',
            'R: Reset',
            'Q: Quit',
        ]
        text = '  |  '.join(controls)
        label = font.render(text, True, (150, 150, 150))
        screen.blit(label, (X_MARGIN, y_pos))

    def _draw_slider(self, screen):
        """Draw time slider."""
        y = WINDOW_HEIGHT - 50
        x0 = X_MARGIN
        x1 = WINDOW_WIDTH - X_MARGIN
        w = x1 - x0

        # Track
        pygame.draw.line(screen, (200, 200, 200), (x0, y), (x1, y), 3)

        # Crash marker
        if self.calc.crash_time and self.calc.crash_time <= self.t_end:
            frac = self.calc.crash_time / self.t_end
            cx = int(x0 + frac * w)
            pygame.draw.line(screen, CRASH_RGB, (cx, y - 10), (cx, y + 10), 2)

        # Thumb
        frac = min(self.t / self.t_end, 1.0) if self.t_end > 0 else 0
        tx = int(x0 + frac * w)
        pygame.draw.circle(screen, TC_RGB, (tx, y), 8)
        pygame.draw.circle(screen, (255, 255, 255), (tx, y), 8, 2)

        # Time labels
        font = pygame.font.SysFont(None, 16)
        label_start = font.render('0', True, TEXT_COLOR)
        screen.blit(label_start, (x0 - 5, y + 12))
        label_end = font.render(f'{self.t_end:.0f}s', True, TEXT_COLOR)
        screen.blit(label_end, (x1 - 15, y + 12))

        self._slider_rect = pygame.Rect(x0, y - 15, w, 30)
        self._slider_x0 = x0
        self._slider_w = w

    def _draw_tooltip(self, screen):
        """Draw hover tooltip for billet info."""
        if self.hover_billet is None:
            return

        bid, sid, phase = self.hover_billet
        font = pygame.font.SysFont(None, 18)
        lines = [
            f'Billet {bid}',
            f'Strand {sid}',
            f'Phase: {phase}',
        ]

        mx, my = pygame.mouse.get_pos()
        padding = 6
        line_height = 18
        max_w = max(font.size(l)[0] for l in lines) + 2 * padding
        h = len(lines) * line_height + 2 * padding

        tx = min(mx + 15, WINDOW_WIDTH - max_w - 5)
        ty = max(my - h - 5, 5)

        bg = pygame.Surface((max_w, h), pygame.SRCALPHA)
        bg.fill((255, 255, 255, 230))
        screen.blit(bg, (tx, ty))
        pygame.draw.rect(screen, (100, 100, 100), (tx, ty, max_w, h), 1)

        for i, line in enumerate(lines):
            label = font.render(line, True, TEXT_COLOR)
            screen.blit(label, (tx + padding,
                                ty + padding + i * line_height))

    def handle_slider(self, mx: int):
        """Update time from slider position."""
        frac = (mx - self._slider_x0) / self._slider_w
        frac = max(0, min(1, frac))
        self.t = frac * self.t_end

    def run(self):
        """Main loop."""
        pygame.init()
        screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption(
            f'CCM Machine Cycle — v = {self.velocity:.2f} m/min')
        clock = pygame.time.Clock()

        running = True
        while running:
            # --- Events ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    running = self._handle_key(event.key)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        if hasattr(self, '_slider_rect') and \
                           self._slider_rect.collidepoint(event.pos):
                            self.dragging_slider = True
                            self.handle_slider(event.pos[0])
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.dragging_slider = False
                elif event.type == pygame.MOUSEMOTION:
                    if self.dragging_slider:
                        self.handle_slider(event.pos[0])

            # --- Update ---
            if self.playing and not self.dragging_slider:
                self.t += SPEEDS[self.speed_idx] / FPS
                if self.t > self.t_end:
                    self.t = self.t_end
                    self.playing = False

            # --- Hover detection ---
            mx, my = pygame.mouse.get_pos()
            self.hover_billet = None
            for rect, bid, sid, phase in self.billet_rects:
                if rect.collidepoint(mx, my):
                    self.hover_billet = (bid, sid, phase)
                    break

            # --- Draw ---
            state = self.calc.get_state_at(self.t)
            self.draw(screen, state)
            pygame.display.flip()
            clock.tick(FPS)

        pygame.quit()

    def _handle_key(self, key) -> bool:
        """Handle keypress. Returns False to quit."""
        if key in (pygame.K_q, pygame.K_ESCAPE):
            return False
        elif key == pygame.K_SPACE:
            self.playing = not self.playing
        elif key == pygame.K_RIGHT:
            self.t = min(self.t + 2.0, self.t_end)
        elif key == pygame.K_LEFT:
            self.t = max(self.t - 2.0, 0)
        elif key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            self.speed_idx = min(self.speed_idx + 1, len(SPEEDS) - 1)
        elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.speed_idx = max(self.speed_idx - 1, 0)
        elif key == pygame.K_r:
            self.t = 0.0
            self.playing = False
        elif key in range(pygame.K_0, pygame.K_7):
            self.highlight_strand = key - pygame.K_0
        return True


def main():
    parser = argparse.ArgumentParser(
        description='CCM Machine Cycle — Interactive Pygame Viewer')
    parser.add_argument('--velocity', '-v', type=float, default=3.6)
    parser.add_argument('--t-end', type=float, default=450.0)
    args = parser.parse_args()

    viewer = PygameViewer(velocity=args.velocity, t_end=args.t_end)
    viewer.run()


if __name__ == '__main__':
    main()
