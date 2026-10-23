from __future__ import annotations

from typing import Callable, List, Optional, Tuple

import pygame

from .bot import DIFFICULTIES, DIFFICULTY_NAMES, EASY, HARD, NORMAL, Bot
from .cards import Card
from .engine import BOT, HUMAN, Game, IllegalMove
from .save import clear_save, has_save, load_game, save_game
from .sprites import Sprites

WIN_W, WIN_H = 1100, 780
CARD_W, CARD_H = 96, 144
BAR_H = 64
BOT_DELAY_MS = 800
BITO_DELAY_MS = 900
NOTICE_MS = 2200
FPS = 60

FELT = (31, 90, 61)
FELT_LIGHT = (37, 107, 73)
SHADOW = (21, 64, 43)
CARD_FACE = (251, 250, 245)
CARD_DIM = (205, 208, 196)
CARD_LINE = (42, 42, 42)
RED = (198, 40, 40)
BLACK = (27, 27, 27)
GOLD = (242, 182, 50)
BACK_FILL = (29, 63, 122)
BACK_LINE = (143, 176, 230)
BTN = (236, 232, 218)
BTN_HOVER = (255, 252, 240)
BTN_OFF = (110, 130, 118)
TEXT = (243, 239, 226)
TEXT_SOFT = (185, 211, 195)
FONT_NAMES = "segoeui,arial,helveticaneue,dejavusans,liberationsans,freesans"

Action = Callable[[], None]
Hit = Tuple[pygame.Rect, Action, bool]


def draw_suit(surf, suit: str, cx: float, cy: float, s: float, color) -> None:
    def circle(dx, dy, r):
        pygame.draw.circle(surf, color, (int(cx + dx * s), int(cy + dy * s)), max(1, int(r * s)))

    def poly(points):
        pygame.draw.polygon(surf, color, [(cx + x * s, cy + y * s) for x, y in points])

    if suit == "♦":
        poly([(0, -1), (0.7, 0), (0, 1), (-0.7, 0)])
    elif suit == "♥":
        circle(-0.5, -0.35, 0.55)
        circle(0.5, -0.35, 0.55)
        poly([(-1.02, -0.15), (1.02, -0.15), (0, 0.95)])
    elif suit == "♠":
        circle(-0.5, 0.35, 0.55)
        circle(0.5, 0.35, 0.55)
        poly([(-1.02, 0.15), (1.02, 0.15), (0, -0.95)])
        poly([(0, 0.2), (-0.35, 0.95), (0.35, 0.95)])
    else:
        circle(0, -0.5, 0.45)
        circle(-0.5, 0.2, 0.45)
        circle(0.5, 0.2, 0.45)
        poly([(0, 0.1), (-0.3, 0.95), (0.3, 0.95)])


class DurakApp:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Дурак: 1 на 1 с ботом")
        self.screen = pygame.display.set_mode((WIN_W, WIN_H), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()

        self.f_title = pygame.font.SysFont(FONT_NAMES, 96, bold=True)
        self.f_status = pygame.font.SysFont(FONT_NAMES, 25, bold=True)
        self.f_text = pygame.font.SysFont(FONT_NAMES, 17)
        self.f_bold = pygame.font.SysFont(FONT_NAMES, 17, bold=True)
        self.f_small = pygame.font.SysFont(FONT_NAMES, 15)
        self.f_rank = pygame.font.SysFont(FONT_NAMES, 22, bold=True)
        self.f_result = pygame.font.SysFont(FONT_NAMES, 58, bold=True)
        self.sprites = Sprites((CARD_W, CARD_H))

        self.running = True
        self.screen_name = "menu"
        self.difficulty = NORMAL
        self.stats = {"human": 0, "bot": 0, "draw": 0}
        self.game: Optional[Game] = None
        self.bot: Optional[Bot] = None
        self.bot_due: Optional[int] = None
        self.bito_due: Optional[int] = None
        self.counted = False
        self.notice = ""
        self.notice_until = 0
        self.can_continue = has_save()
        self.hits: List[Hit] = []
        self.hand_hits: List[Tuple[pygame.Rect, Card]] = []
        self.playable: set = set()
        self.hovered: Optional[Card] = None
        self.lift: dict = {}

    def new_game(self) -> None:
        self.game = Game()
        self.game.manual_bito = True
        self.bot = Bot(BOT, self.difficulty)
        self.counted = False
        self.bot_due = None
        self.bito_due = None
        self.notice = ""
        self.lift.clear()
        self.screen_name = "game"
        self.persist()

    def continue_game(self) -> None:
        loaded = load_game()
        if loaded is None:
            self.can_continue = False
            return
        self.game, self.difficulty = loaded
        self.game.manual_bito = True
        self.bot = Bot(BOT, self.difficulty)
        self.counted = False
        self.bot_due = None
        self.lift.clear()
        self.screen_name = "game"

    def to_menu(self) -> None:
        self.persist()
        self.screen_name = "menu"
        self.bot_due = None
        self.can_continue = has_save()

    def open_difficulty(self) -> None:
        self.can_continue = has_save()
        self.screen_name = "difficulty"

    def start_with(self, difficulty: str) -> None:
        self.difficulty = difficulty
        self.new_game()

    def quit(self) -> None:
        self.running = False

    def persist(self) -> None:
        if self.game is None:
            return
        if self.game.over:
            if not self.counted:
                self.counted = True
                self.stats[self.game.result] += 1
            clear_save()
        else:
            save_game(self.game, self.difficulty)

    def flash(self, text: str) -> None:
        self.notice = text
        self.notice_until = pygame.time.get_ticks() + NOTICE_MS

    def update(self, now: int) -> None:
        if self.screen_name != "game" or self.game is None:
            return
        game = self.game
        if self.notice and now > self.notice_until:
            self.notice = ""
        if game.over:
            self.persist()
            self.bot_due = None
            self.bito_due = None
            return
        if game.bito_called:
            if self.bito_due is None:
                self.bito_due = now + BITO_DELAY_MS
            elif now >= self.bito_due:
                self.bito_due = None
                game.confirm_bito()
                self.persist()
            return
        self.bito_due = None
        if game.turn() == BOT:
            if self.bot_due is None:
                self.bot_due = now + BOT_DELAY_MS
            elif now >= self.bot_due:
                self.bot.act(game)
                self.bot_due = None
                self.persist()
        else:
            self.bot_due = None

    def on_card_click(self, card: Card) -> None:
        game = self.game
        if game is None or game.over or game.turn() != HUMAN:
            return
        try:
            if game.turn() == game.attacker:
                game.attack(card)
            else:
                game.defend(card)
        except IllegalMove as err:
            self.flash(str(err))
            return
        self.persist()

    def on_take(self) -> None:
        game = self.game
        if (game is None or game.turn() != HUMAN or game.turn() != game.defender
                or game.bito_called):
            return
        try:
            game.take()
        except IllegalMove as err:
            self.flash(str(err))
            return
        self.persist()

    def on_done(self) -> None:
        game = self.game
        if game is None or game.over or game.turn() != HUMAN or not game.table:
            return
        try:
            if game.bito_called:
                game.confirm_bito()
            elif game.turn() == game.attacker:
                game.finish()
            else:
                return
        except IllegalMove as err:
            self.flash(str(err))
            return
        self.persist()

    def on_click(self, pos) -> None:
        for rect, callback, enabled in self.hits:
            if enabled and rect.collidepoint(pos):
                callback()
                return
        if self.screen_name == "game":
            for rect, card in reversed(self.hand_hits):
                if rect.collidepoint(pos):
                    self.on_card_click(card)
                    return

    def on_key(self, key) -> None:
        if key == pygame.K_ESCAPE:
            if self.screen_name == "game":
                self.to_menu()
            elif self.screen_name == "difficulty":
                self.to_menu()
            else:
                self.quit()
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE) and self.screen_name == "game":
            self.on_done()

    def text(self, label: str, font, color, pos, anchor: str = "center") -> None:
        img = font.render(label, True, color)
        rect = img.get_rect()
        setattr(rect, anchor, pos)
        self.screen.blit(img, rect)

    def draw_button(self, rect: pygame.Rect, label: str, enabled: bool, mouse) -> None:
        hover = enabled and rect.collidepoint(mouse)
        fill = BTN_OFF if not enabled else (BTN_HOVER if hover else BTN)
        pygame.draw.rect(self.screen, fill, rect, border_radius=10)
        pygame.draw.rect(self.screen, CARD_LINE, rect, width=2, border_radius=10)
        color = (70, 85, 76) if not enabled else BLACK
        self.text(label, self.f_bold, color, rect.center)

    def draw_card(self, rect: pygame.Rect, card: Card, dim: bool = False) -> None:
        s = self.screen
        pygame.draw.rect(s, SHADOW, rect.move(4, 5), border_radius=10)
        img = self.sprites.card(card)
        if img is not None:
            s.blit(img, rect)
        else:
            self._draw_plain_card(rect, card)
        if dim:
            veil = pygame.Surface(rect.size, pygame.SRCALPHA)
            veil.fill((0, 0, 0, 110))
            s.blit(veil, rect)

    def _draw_plain_card(self, rect: pygame.Rect, card: Card) -> None:
        s = self.screen
        color = RED if card.is_red else BLACK
        pygame.draw.rect(s, CARD_FACE, rect, border_radius=10)
        pygame.draw.rect(s, CARD_LINE, rect, width=2, border_radius=10)
        label = self.f_rank.render(card.rank_label, True, color)
        s.blit(label, (rect.x + 8, rect.y + 6))
        draw_suit(s, card.suit, rect.centerx, rect.centery, 22, color)

    def draw_back(self, rect: pygame.Rect) -> None:
        s = self.screen
        pygame.draw.rect(s, SHADOW, rect.move(4, 5), border_radius=10)
        img = self.sprites.back()
        if img is not None:
            s.blit(img, rect)
            return
        pygame.draw.rect(s, BACK_FILL, rect, border_radius=10)
        pygame.draw.rect(s, BACK_LINE, rect.inflate(-14, -14), width=2, border_radius=6)

    @staticmethod
    def hand_layout(count: int, width: int, gap: int, margin: int = 40) -> Tuple[float, float]:
        if count <= 0:
            return 0, 0
        if count == 1:
            return (width - CARD_W) / 2, 0
        step = min(CARD_W + gap, (width - 2 * margin - CARD_W) / (count - 1))
        total = CARD_W + step * (count - 1)
        return (width - total) / 2, step

    @staticmethod
    def set_cursor(active: bool) -> None:
        try:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if active else pygame.SYSTEM_CURSOR_ARROW)
        except (pygame.error, AttributeError):
            pass

    def render_menu(self) -> None:
        s = self.screen
        w, h = s.get_size()
        mouse = pygame.mouse.get_pos()
        s.fill(FELT)
        pygame.draw.ellipse(s, FELT_LIGHT, pygame.Rect(w * 0.1, h * 0.1, w * 0.8, h * 0.8))

        top = int(h * 0.2)
        self.text("ДУРАК", self.f_title, TEXT, (w / 2, top))
        self.text("1 на 1 с ботом", self.f_status, TEXT_SOFT, (w / 2, top + 70))
        st = self.stats
        self.text(f"Вы {st['human']} : {st['bot']} Бот    ничьих {st['draw']}",
                  self.f_text, TEXT_SOFT, (w / 2, top + 108))

        items: List[Tuple[str, Action, bool]] = [
            ("Продолжить", self.continue_game, self.can_continue),
            ("Новая игра", self.open_difficulty, True),
            ("Выход", self.quit, True),
        ]
        self.hits = []
        y = int(h * 0.42)
        for label, callback, enabled in items:
            rect = pygame.Rect(0, 0, 340, 56)
            rect.midtop = (w // 2, y)
            self.draw_button(rect, label, enabled, mouse)
            self.hits.append((rect, callback, enabled))
            y += 56 + 18

        self.text("Продолжить доступно, если партия не закончена. Сохранение автоматическое.",
                  self.f_small, TEXT_SOFT, (w / 2, h - 36))
        self.hand_hits = []
        self.set_cursor(any(en and r.collidepoint(mouse) for r, _, en in self.hits))

    def render_difficulty(self) -> None:
        s = self.screen
        w, h = s.get_size()
        mouse = pygame.mouse.get_pos()
        s.fill(FELT)
        pygame.draw.ellipse(s, FELT_LIGHT, pygame.Rect(w * 0.1, h * 0.1, w * 0.8, h * 0.8))

        top = int(h * 0.2)
        self.text("Новая игра", self.f_result, TEXT, (w / 2, top))
        self.text("Выберите сложность", self.f_status, TEXT_SOFT, (w / 2, top + 62))

        hints = {
            EASY: "ходит почти наугад",
            NORMAL: "играет по уму",
            HARD: "ходит парами, бережёт козыри",
        }
        self.hits = []
        y = int(h * 0.42)
        for level in DIFFICULTIES:
            rect = pygame.Rect(0, 0, 340, 56)
            rect.midtop = (w // 2, y)
            self.draw_button(rect, DIFFICULTY_NAMES[level], True, mouse)
            self.hits.append((rect, lambda lv=level: self.start_with(lv), True))
            self.text(hints[level], self.f_small, TEXT_SOFT, (rect.centerx, rect.bottom + 12))
            y += 56 + 38
        back = pygame.Rect(0, 0, 340, 56)
        back.midtop = (w // 2, y + 6)
        self.draw_button(back, "Назад", True, mouse)
        self.hits.append((back, self.to_menu, True))

        self.hand_hits = []
        self.set_cursor(any(en and r.collidepoint(mouse) for r, _, en in self.hits))

    def render_game(self) -> None:
        s = self.screen
        w, h = s.get_size()
        th = h - BAR_H
        cy = th / 2
        game = self.game
        mouse = pygame.mouse.get_pos()
        human_turn = game.turn() == HUMAN

        s.fill(FELT)
        pygame.draw.ellipse(s, FELT_LIGHT, pygame.Rect(w * 0.08, th * 0.12, w * 0.84, th * 0.76))

        bot_cards = len(game.hands[BOT])
        x0, step = self.hand_layout(bot_cards, w, 4, 120)
        for i in range(bot_cards):
            self.draw_back(pygame.Rect(int(x0 + step * i), 20, CARD_W, CARD_H))
        self.text(f"Бот: карт {bot_cards}", self.f_text, TEXT_SOFT, (w / 2, 20 + CARD_H + 18))

        st = self.stats
        self.text(f"Вы {st['human']} : {st['bot']} Бот    ничьих {st['draw']}",
                  self.f_text, TEXT_SOFT, (w - 20, 18), "topright")
        self.text(f"Сложность: {DIFFICULTY_NAMES[self.difficulty]}", self.f_text, TEXT_SOFT,
                  (20, 18), "topleft")

        self.draw_deck(24, int(cy - CARD_H / 2))

        if game.discard:
            dx = w - CARD_W - 28
            self.draw_back(pygame.Rect(dx, int(cy - CARD_H / 2), CARD_W, CARD_H))
            self.text(f"Бито: {len(game.discard)}", self.f_text, TEXT_SOFT,
                      (dx + CARD_W / 2, cy + CARD_H / 2 + 18))

        n = len(game.table)
        if n:
            left, right = 190, w - 150
            spacing = min(132, (right - left) / n)
            total = spacing * (n - 1) + CARD_W
            tx = left + (right - left - total) / 2
            ty = int(cy - CARD_H / 2 - 12)
            for i, pair in enumerate(game.table):
                px = int(tx + spacing * i)
                self.draw_card(pygame.Rect(px, ty, CARD_W, CARD_H), pair.attack)
                if pair.defense is not None:
                    self.draw_card(pygame.Rect(px + 22, ty + 26, CARD_W, CARD_H), pair.defense)

        status_y = cy + CARD_H / 2 + 42
        self.text(self.status_text(), self.f_status, TEXT, (w / 2, status_y))
        sub = self.notice or game.last_event
        self.text(sub, self.f_text, GOLD if self.notice else TEXT_SOFT, (w / 2, status_y + 28))

        self.draw_hand(w, th, human_turn, mouse)

        pygame.draw.rect(s, SHADOW, (0, th, w, BAR_H))
        can_take = human_turn and game.turn() == game.defender and not game.bito_called
        can_done = human_turn and bool(game.table) and (
            game.turn() == game.attacker or game.bito_called)
        done_label = "Хватит" if game.taking else "Бито"
        self.hits = []
        buttons = [
            (pygame.Rect(14, th + 12, 130, 40), "Беру", self.on_take, can_take),
            (pygame.Rect(158, th + 12, 130, 40), done_label, self.on_done, can_done),
            (pygame.Rect(w - 144, th + 12, 130, 40), "В меню", self.to_menu, True),
        ]
        for rect, label, callback, enabled in buttons:
            self.draw_button(rect, label, enabled, mouse)
            self.hits.append((rect, callback, enabled))

        if game.over:
            self.draw_result(w, th)

        over_card = self.hovered is not None and self.hovered in self.playable
        over_button = any(en and r.collidepoint(mouse) for r, _, en in self.hits)
        self.set_cursor(over_card or over_button)

    def draw_hand(self, w: int, th: int, human_turn: bool, mouse) -> None:
        game = self.game
        hand = game.hands[HUMAN]
        if human_turn and not game.bito_called:
            self.playable = set(game.legal_attacks() if game.turn() == game.attacker
                                else game.legal_defends())
        else:
            self.playable = set()

        hovered = None
        for rect, card in reversed(self.hand_hits):
            if rect.collidepoint(mouse):
                hovered = card
                break
        self.hovered = hovered

        x0, step = self.hand_layout(len(hand), w, 12)
        base_y = th - CARD_H - 26
        hits: List[Tuple[pygame.Rect, Card]] = []
        for i, card in enumerate(hand):
            playable = card in self.playable
            target = (16 + (10 if card == hovered else 0)) if playable else 0
            cur = self.lift.get(card, 0.0)
            cur += (target - cur) * 0.25
            self.lift[card] = cur
            rect = pygame.Rect(int(x0 + step * i), int(base_y - cur), CARD_W, CARD_H)
            self.draw_card(rect, card, dim=human_turn and not game.bito_called and not playable)
            hits.append((rect, card))
        self.hand_hits = hits
        self.text(f"Ваши карты: {len(hand)}", self.f_text, TEXT_SOFT, (w / 2, th - 10))

    def draw_deck(self, x: int, y: int) -> None:
        game = self.game
        left = len(game.deck)
        if left > 0:
            self.draw_card(pygame.Rect(x, y, CARD_W, CARD_H), game.trump_card)
            if left > 1:
                self.draw_back(pygame.Rect(x + 30, y, CARD_W, CARD_H))
        else:
            center = (x + CARD_W // 2, y + CARD_H // 2)
            pygame.draw.circle(self.screen, CARD_FACE, center, 36)
            color = RED if game.trump in "♥♦" else BLACK
            draw_suit(self.screen, game.trump, center[0], center[1], 18, color)
        self.text(f"Колода: {left}", self.f_text, TEXT_SOFT, (x + CARD_W / 2, y + CARD_H + 18))
        self.text(f"Козырь {game.trump}", self.f_bold, GOLD, (x + CARD_W / 2, y + CARD_H + 40))

    def status_text(self) -> str:
        game = self.game
        if game.over:
            return "Партия окончена"
        if game.turn() == HUMAN:
            if game.bito_called:
                return "Вы отбились"
            if game.turn() == game.attacker:
                if game.taking:
                    return "Бот берёт карты. Подкиньте или нажмите «Хватит»"
                if not game.table:
                    return "Ваш ход: выберите карту"
                return "Подкиньте карту или нажмите «Бито»"
            return f"Побейте {game.unbeaten()[0].attack} или нажмите «Беру»"
        return "Бот думает…"

    def draw_result(self, w: int, h: int) -> None:
        shade = pygame.Surface((w, h), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 150))
        self.screen.blit(shade, (0, 0))
        result = self.game.result
        if result == "human":
            title, sub = "Вы победили!", "Бот остался в дураках"
        elif result == "bot":
            title, sub = "Вы проиграли", "Вы остались в дураках"
        else:
            title, sub = "Ничья", "Карты закончились у обоих"
        title_img = self.f_result.render(title, True, BLACK)
        sub_img = self.f_status.render(sub, True, (70, 70, 70))
        box_w = min(w - 40, max(500, title_img.get_width() + 80, sub_img.get_width() + 80))
        box = pygame.Rect(0, 0, box_w, 230)
        box.center = (w // 2, h // 2 - 20)
        pygame.draw.rect(self.screen, CARD_FACE, box, border_radius=16)
        pygame.draw.rect(self.screen, GOLD, box, width=3, border_radius=16)
        self.screen.blit(title_img, title_img.get_rect(center=(box.centerx, box.y + 58)))
        self.screen.blit(sub_img, sub_img.get_rect(center=(box.centerx, box.y + 120)))

        mouse = pygame.mouse.get_pos()
        again = pygame.Rect(0, 0, 200, 46)
        again.center = (box.centerx - 115, box.bottom - 42)
        menu = pygame.Rect(0, 0, 200, 46)
        menu.center = (box.centerx + 115, box.bottom - 42)
        for rect, label, callback in ((again, "Новая игра", self.open_difficulty),
                                      (menu, "В меню", self.to_menu)):
            self.draw_button(rect, label, True, mouse)
            self.hits.append((rect, callback, True))

    def render(self) -> None:
        if self.screen_name == "menu":
            self.render_menu()
        elif self.screen_name == "difficulty":
            self.render_difficulty()
        else:
            self.render_game()

    def run(self) -> None:
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.on_click(event.pos)
                elif event.type == pygame.KEYDOWN:
                    self.on_key(event.key)
            self.update(pygame.time.get_ticks())
            self.hits = []
            self.render()
            pygame.display.flip()
            self.clock.tick(FPS)
        self.persist()
        pygame.quit()


def run() -> None:
    DurakApp().run()
