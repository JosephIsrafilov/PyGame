import math
import random
from pygame import Rect
from pgzero.actor import Actor
from collections import deque


TITLE = "Forest Relic"
WIDTH = 640
HEIGHT = 480
SPRITE_SCALE = 1.6
HUGE_SCALE = 1.9
MAX_STAGE = 3
DETECT_RANGE = 260
PLAYER_SPEED = 140
PLAYER_HP = 100
PLAYER_MAG = 30
PLAYER_RESERVE = 90
PLAYER_RELOAD = 1.2
ENEMY_TOUCH_DAMAGE = 10
SPIKE_DAMAGE = 15
BULLET_SPEED = 340
TURRET_BULLET_SPEED = 180
TURRET_RANGE = 320
TURRET_COOLDOWN = 1.8
TURRET_DAMAGE = 10
HEART_HEAL = 20
BULLET_DAMAGE = 20

SKY_TOP = (14, 44, 58)
SKY_BOTTOM = (10, 26, 32)
FLOOR_DARK = (24, 42, 46)
FLOOR_LIGHT = (32, 60, 66)


def clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))


class SpriteAnimation:
    def __init__(self, frames, speed):
        self.frames = frames
        self.speed = speed
        self.index = 0
        self.timer = 0.0

    def reset(self):
        self.index = 0
        self.timer = 0.0

    def update(self, dt):
        self.timer += dt
        if self.timer >= self.speed:
            steps = int(self.timer / self.speed)
            self.timer -= self.speed * steps
            self.index = (self.index + steps) % len(self.frames)

    @property
    def frame(self):
        return self.frames[self.index]


def actor_rect(actor, pos=None):
    x, y = pos if pos else (actor.x, actor.y)
    return Rect((x - actor.width / 2, y - actor.height / 2), (actor.width, actor.height))


class Character:
    def __init__(self, pos, animations):
        self.animations = animations
        self.state = "idle"
        self.actor = Actor(self.animations[self.state].frame, pos=pos)
        self.actor.scale = SPRITE_SCALE

    def set_state(self, state):
        if state != self.state:
            self.state = state
            self.animations[self.state].reset()

    def update_animation(self, dt):
        anim = self.animations[self.state]
        anim.update(dt)
        self.actor.image = anim.frame

    def draw(self):
        self.actor.draw()


class Player(Character):
    def __init__(self, pos):
        animations = {
            "idle": SpriteAnimation([f"hero_idle_{i}" for i in range(1, 4)], 0.18),
            "walk": SpriteAnimation([f"hero_walk_{i}" for i in range(1, 4)], 0.12),
        }
        super().__init__(pos, animations)
        self.speed = PLAYER_SPEED
        self.hp = PLAYER_HP
        self.invulnerable = 0.0
        self.mag_size = PLAYER_MAG
        self.ammo = self.mag_size
        self.reserve = PLAYER_RESERVE
        self.reloading = False
        self.reload_time = PLAYER_RELOAD
        self.reload_timer = 0.0

    def update(self, dt, walls):
        dx = (keyboard.right or keyboard.d) - (keyboard.left or keyboard.a)
        dy = (keyboard.down or keyboard.s) - (keyboard.up or keyboard.w)
        if dx or dy:
            length = math.hypot(dx, dy)
            dx /= length
            dy /= length
            moved = self.try_move(dx, dy, dt, walls)
            if moved:
                self.set_state("walk")
            else:
                self.set_state("idle")
        else:
            self.set_state("idle")

        if self.invulnerable > 0:
            self.invulnerable = max(0, self.invulnerable - dt)

        if self.reloading:
            self.reload_timer -= dt
            if self.reload_timer <= 0:
                need = self.mag_size - self.ammo
                load = min(need, self.reserve)
                self.ammo += load
                self.reserve -= load
                self.reloading = False

        self.update_animation(dt)

    def try_move(self, dx, dy, dt, walls):
        moved = False
        step_x = dx * self.speed * dt
        step_y = dy * self.speed * dt

        new_rect_x = actor_rect(self.actor, (self.actor.x + step_x, self.actor.y))
        if not any(new_rect_x.colliderect(w) for w in walls):
            self.actor.x += step_x
            moved = True

        new_rect_y = actor_rect(self.actor, (self.actor.x, self.actor.y + step_y))
        if not any(new_rect_y.colliderect(w) for w in walls):
            self.actor.y += step_y
            moved = True

        self.actor.x = clamp(self.actor.x, self.actor.width / 2, WIDTH - self.actor.width / 2)
        self.actor.y = clamp(self.actor.y, self.actor.height / 2, HEIGHT - self.actor.height / 2)
        return moved

    def hit(self, amount):
        if self.invulnerable > 0:
            return
        self.hp = max(0, self.hp - amount)
        self.invulnerable = 0.7
        if sound_on:
            sounds.hurt.play()

    def reload(self):
        if self.reloading:
            return
        if self.ammo >= self.mag_size:
            return
        if self.reserve <= 0:
            return
        self.reloading = True
        self.reload_timer = self.reload_time

    def shoot(self, target):
        if self.reloading:
            return None
        if self.ammo <= 0:
            self.reload()
            return None
        self.ammo -= 1
        dx = target[0] - self.actor.x
        dy = target[1] - self.actor.y
        length = math.hypot(dx, dy) or 1
        dx /= length
        dy /= length
        bullet = {
            "x": self.actor.x,
            "y": self.actor.y,
            "dx": dx,
            "dy": dy,
            "speed": BULLET_SPEED,
            "ttl": 2.0,
            "radius": 5,
        }
        return bullet


class Enemy(Character):
    def __init__(self, pos, animations, area, speed):
        super().__init__(pos, animations)
        self.area = area
        self.speed = speed
        self.pause_timer = 0.0
        self.hp = 40

    def keep_inside(self):
        self.actor.x = clamp(self.actor.x, self.area.left + self.actor.width / 2, self.area.right - self.actor.width / 2)
        self.actor.y = clamp(self.actor.y, self.area.top + self.actor.height / 2, self.area.bottom - self.actor.height / 2)

    def take_damage(self, amount):
        self.hp -= amount
        if sound_on:
            try:
                sounds.hit.play()
            except Exception:
                pass

    def move_with_collisions(self, dx, dy, dt, walls):
        step_x = dx * self.speed * dt
        step_y = dy * self.speed * dt
        rect_x = actor_rect(self.actor, (self.actor.x + step_x, self.actor.y))
        if not any(rect_x.colliderect(w) for w in walls):
            self.actor.x += step_x
        rect_y = actor_rect(self.actor, (self.actor.x, self.actor.y + step_y))
        if not any(rect_y.colliderect(w) for w in walls):
            self.actor.y += step_y
        self.keep_inside()

    def push_from_player(self, player_pos, walls):
        dx = self.actor.x - player_pos[0]
        dy = self.actor.y - player_pos[1]
        dist = math.hypot(dx, dy)
        if dist == 0:
            dx, dy = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
            dist = 1
        dx /= dist
        dy /= dist
        self.move_with_collisions(dx, dy, 0.12, walls)


class Slime(Enemy):
    def __init__(self, pos, area):
        animations = {
            "idle": SpriteAnimation([f"slime_idle_{i}" for i in range(1, 4)], 0.24),
            "walk": SpriteAnimation([f"slime_walk_{i}" for i in range(1, 4)], 0.16),
        }
        super().__init__(pos, animations, area, speed=65)
        self.direction = random.choice([-1, 1])

    def update(self, dt):
        if self.pause_timer > 0:
            self.pause_timer -= dt
            self.set_state("idle")
        else:
            px, py = player.actor.pos
            dx = px - self.actor.x
            dy = py - self.actor.y
            dist = math.hypot(dx, dy)
            if dist <= DETECT_RANGE and has_line_of_sight(self.actor.pos, player.actor.pos, walls):
                dx /= dist or 1
                dy /= dist or 1
                self.move_with_collisions(dx, dy, dt, walls)
            else:
                self.move_with_collisions(self.direction, 0, dt, walls)
                if self.actor.left <= self.area.left or self.actor.right >= self.area.right or any(
                    actor_rect(self.actor).colliderect(w) for w in walls
                ):
                    self.direction *= -1
                    self.pause_timer = 0.45
            self.set_state("walk")

        self.keep_inside()
        self.update_animation(dt)


class Phantom(Enemy):
    def __init__(self, pos, area):
        animations = {
            "idle": SpriteAnimation([f"phantom_idle_{i}" for i in range(1, 4)], 0.22),
            "walk": SpriteAnimation([f"phantom_walk_{i}" for i in range(1, 4)], 0.14),
        }
        super().__init__(pos, animations, area, speed=80)
        self.angle = random.random() * math.pi * 2

    def update(self, dt):
        if self.pause_timer > 0:
            self.pause_timer -= dt
            self.set_state("idle")
        else:
            self.angle += dt * 1.3
            px, py = player.actor.pos
            dxp = px - self.actor.x
            dyp = py - self.actor.y
            dist = math.hypot(dxp, dyp)
            if dist <= DETECT_RANGE and has_line_of_sight(self.actor.pos, player.actor.pos, walls):
                dx = dxp / (dist or 1)
                dy = dyp / (dist or 1)
            else:
                dx = math.cos(self.angle)
                dy = math.sin(self.angle)
            self.move_with_collisions(dx, dy, dt, walls)
            if not self.area.collidepoint(self.actor.x, self.actor.y):
                self.angle += math.pi
                self.pause_timer = 0.5
            self.set_state("walk")

        self.keep_inside()
        self.update_animation(dt)


class Charger(Enemy):
    def __init__(self, pos, area):
        animations = {
            "idle": SpriteAnimation([f"slime_idle_{i}" for i in range(1, 4)], 0.14),
            "walk": SpriteAnimation([f"slime_walk_{i}" for i in range(1, 4)], 0.1),
        }
        super().__init__(pos, animations, area, speed=120)
        self.hp = 50
        self.dash_cooldown = 1.2
        self.dash_timer = random.random()
        self.dash_speed = 200
        self.dashing = False
        self.dash_time = 0.4

    def update(self, dt):
        self.dash_timer -= dt
        speed = self.dash_speed if self.dashing else self.speed
        if self.dash_timer <= 0:
            self.dash_timer = self.dash_cooldown
            self.dashing = True
            self.dash_time = 0.35
        if self.dashing:
            self.dash_time -= dt
            if self.dash_time <= 0:
                self.dashing = False
        dx = player.actor.x - self.actor.x
        dy = player.actor.y - self.actor.y
        dist = math.hypot(dx, dy) or 1
        if dist <= DETECT_RANGE and has_line_of_sight(self.actor.pos, player.actor.pos, walls):
            dx /= dist
            dy /= dist
        else:
            dx = random.choice([-1, 1])
            dy = random.choice([-1, 1])
        self.move_with_collisions(dx * (speed / self.speed), dy * (speed / self.speed), dt, walls)
        self.keep_inside()
        self.set_state("walk" if dist > 4 else "idle")
        self.update_animation(dt)


class Button:
    def __init__(self, rect, text, action):
        self.rect = rect
        self.text = text
        self.action = action

    def draw(self):
        hovered = False
        try:
            hovered = self.rect.collidepoint(mouse.pos)
        except Exception:
            hovered = False
        base_color = (70, 110, 160) if hovered else (50, 80, 130)
        border = (255, 255, 255) if hovered else (210, 220, 240)
        screen.draw.filled_rect(self.rect, base_color)
        screen.draw.rect(self.rect, border)
        screen.draw.text(
            self.text,
            center=self.rect.center,
            fontsize=28,
            color=(235, 242, 255),
        )

    def handle_click(self, pos):
        if self.rect.collidepoint(pos):
            self.action()
            return True
        return False


game_state = "menu"
sound_on = True
music_on = True
gems = []
enemies = []
walls = []
exit_rect = Rect((520, 370), (70, 80))
player = None
total_gems = 0
title_wave = 0.0
game_time = 0.0
exit_unlocked = False
fireflies = []
bullets = []
spikes = []
turrets = []
turret_shots = []
hearts = []
stage = 1


def build_walls():
    return [
        Rect((40, 40), (180, 18)),
        Rect((40, 40), (18, 160)),
        Rect((40, 200), (180, 18)),
        Rect((220, 110), (180, 18)),
        Rect((220, 110), (18, 150)),
        Rect((220, 260), (180, 18)),
        Rect((430, 70), (170, 18)),
        Rect((430, 70), (18, 150)),
        Rect((430, 220), (170, 18)),
        Rect((120, 330), (160, 18)),
        Rect((120, 330), (18, 110)),
        Rect((120, 440), (200, 18)),
        Rect((320, 330), (18, 110)),
        Rect((320, 330), (180, 18)),
    ]


def make_fireflies(count=22):
    bugs = []
    for _ in range(count):
        bugs.append(
            {
                "x": random.uniform(0, WIDTH),
                "y": random.uniform(0, HEIGHT),
                "speed": random.uniform(8, 18),
                "phase": random.random() * math.pi * 2,
            }
        )
    return bugs


def make_spikes():
    pads = [
        Rect((190, 260), (60, 32)),
        Rect((360, 180), (60, 32)),
        Rect((480, 320), (60, 32)),
    ]
    return [{"rect": pad, "timer": 0.0, "period": 1.6, "active": False} for pad in pads]


def make_turrets(walls):
    t_list = []
    cells = reachable_positions((WIDTH / 2, HEIGHT / 2), walls)
    random.shuffle(cells)
    for pos in cells[:3]:
        act = Actor("turret", pos=pos)
        act.scale = HUGE_SCALE
        t_list.append({"actor": act, "cooldown": TURRET_COOLDOWN, "timer": random.random(), "range": TURRET_RANGE})
    return t_list


def create_game_objects():
    global gems, enemies, walls, player, total_gems, exit_unlocked, bullets, spikes, turrets, turret_shots, hearts
    walls = build_walls()
    player_start = (80, 430)
    player_anim = Player(player_start)
    player_anim.actor.scale = HUGE_SCALE
    free_cells = reachable_positions(player_start, walls)

    enemies[:] = []
    spawn_pool = list(free_cells)
    random.shuffle(spawn_pool)

    def pop_spawn(min_dist=120):
        while spawn_pool:
            pos = spawn_pool.pop()
            if math.hypot(pos[0] - player_start[0], pos[1] - player_start[1]) >= min_dist:
                return pos
        return player_start

    for _ in range(2 + stage):
        pos = pop_spawn()
        area = bounded_rect(pos, 160, 120)
        slime = Slime(pos, area)
        slime.actor.scale = HUGE_SCALE
        enemies.append(slime)

    phantom_pos = pop_spawn()
    phantom = Phantom(phantom_pos, bounded_rect(phantom_pos, 200, 160))
    phantom.actor.scale = HUGE_SCALE
    enemies.append(phantom)

    if stage >= 2:
        charge_pos = pop_spawn()
        charger = Charger(charge_pos, bounded_rect(charge_pos, 220, 160))
        charger.actor.scale = HUGE_SCALE
        enemies.append(charger)

    random.shuffle(free_cells)
    gem_positions = free_cells[:4] if len(free_cells) >= 4 else free_cells
    gems = []
    for pos in gem_positions:
        g = Actor("gem", pos=pos)
        g.scale = HUGE_SCALE
        gems.append(g)

    total_gems = len(gems)
    player_anim.hp = PLAYER_HP
    player_anim.invulnerable = 0.0
    exit_unlocked = False
    bullets = []
    spikes = make_spikes()
    turrets = make_turrets(walls)
    turret_shots = []
    hearts = []
    return player_anim


def start_music():
    if music_on:
        try:
            music.set_volume(0.55)
            music.play("music")
        except KeyError:
            if hasattr(sounds, "music"):
                snd = sounds.music
                snd.set_volume(0.55)
                snd.play(-1)
    else:
        music.stop()


def stop_music():
    music.stop()
    if hasattr(sounds, "music"):
        try:
            sounds.music.stop()
        except Exception:
            pass


def start_game():
    global player, game_state, stage
    stage = 1
    player = create_game_objects()
    game_state = "playing"
    start_music()


def toggle_sound():
    global sound_on, music_on
    sound_on = not sound_on
    music_on = sound_on
    if music_on and game_state != "game_over":
        start_music()
    else:
        stop_music()


def quit_game():
    raise SystemExit


menu_buttons = [
    Button(Rect((WIDTH // 2 - 120, 230), (240, 48)), "Start Game", lambda: start_game()),
    Button(Rect((WIDTH // 2 - 120, 290), (240, 48)), "Music & Sounds On/Off", lambda: toggle_sound()),
    Button(Rect((WIDTH // 2 - 120, 350), (240, 48)), "Exit", lambda: quit_game()),
]


def reset_to_menu():
    global game_state
    game_state = "menu"
    stop_music()


def update(dt):
    global title_wave, game_state, game_time, exit_unlocked, bullets, spikes, turret_shots, hearts
    game_time += dt
    if game_state == "menu":
        title_wave += dt
        update_fireflies(dt)
        return

    if game_state != "playing":
        return

    update_fireflies(dt)
    update_spikes(dt)
    update_turrets(dt)
    player.update(dt, walls)
    alive = []
    for enemy in enemies:
        enemy.update(dt)
        if actor_rect(enemy.actor).colliderect(actor_rect(player.actor)):
            player.hit(ENEMY_TOUCH_DAMAGE)
            enemy.push_from_player(player.actor.pos, walls)
        if enemy.hp > 0:
            alive.append(enemy)
        else:
            if random.random() < 0.35:
                hearts.append(make_heart(enemy.actor.pos))
    enemies[:] = alive

    bullets = update_player_shots(dt, enemies, walls, bullets)
    turret_shots = update_turret_shots(dt, walls, turret_shots)

    collect_gems()
    exit_unlocked = len(gems) == 0
    check_victory()
    if player.hp <= 0:
        game_state = "game_over"
        stop_music()


def collect_gems():
    global gems, hearts
    remaining = []
    player_rect = actor_rect(player.actor)
    for gem in gems:
        if player_rect.colliderect(actor_rect(gem)):
            if sound_on:
                sounds.collect.play()
        else:
            remaining.append(gem)
    gems = remaining
    for spike in spikes:
        if spike["active"] and player_rect.colliderect(spike["rect"]):
            player.hit(SPIKE_DAMAGE)
    new_hearts = []
    for h in hearts:
        if player_rect.colliderect(actor_rect(h)):
            player.hp = min(PLAYER_HP, player.hp + HEART_HEAL)
            continue
        new_hearts.append(h)
    hearts = new_hearts


def check_victory():
    global game_state, exit_unlocked, stage, player
    if gems or enemies:
        exit_unlocked = False
        return
    exit_unlocked = True
    player_rect = actor_rect(player.actor)
    if player_rect.colliderect(exit_rect):
        if stage >= MAX_STAGE:
            game_state = "win"
            stop_music()
            if sound_on:
                sounds.hit.play()
        else:
            stage += 1
            player_pos = (player.actor.x, player.actor.y)
            hp_keep = player.hp
            player = create_game_objects()
            player.actor.x, player.actor.y = player_pos
            player.hp = hp_keep


def draw():
    draw_background()
    if game_state == "menu":
        draw_menu()
    elif game_state == "playing":
        draw_playfield()
    elif game_state == "game_over":
        draw_playfield()
        draw_banner("You were defeated! Click to return to menu.", (255, 210, 210))
    elif game_state == "win":
        draw_playfield()
        draw_banner("You escaped with the relic! Click to return.", (210, 255, 210))


def draw_menu():
    draw_fireflies()
    wave = math.sin(title_wave * 2) * 10
    screen.draw.text(
        TITLE,
        center=(WIDTH // 2, 120 + wave),
        fontsize=70,
        color=(230, 240, 255),
    )
    screen.draw.text(
        "Collect all relic shards and reach the exit.",
        center=(WIDTH // 2, 170),
        fontsize=28,
        color=(200, 220, 240),
    )
    for btn in menu_buttons:
        btn.draw()
    screen.draw.text(
        "Controls: Arrow keys to move. Avoid enemies!",
        center=(WIDTH // 2, 420),
        fontsize=24,
        color=(210, 230, 240),
    )


def draw_playfield():
    draw_floor_pattern()
    draw_fireflies()
    for wall in walls:
        screen.draw.filled_rect(wall, (62, 92, 115))
        screen.draw.rect(wall, (30, 45, 60))

    draw_exit()

    for spike in spikes:
        img = "spike_on" if spike["active"] else "spike_off"
        screen.blit(img, (spike["rect"].left, spike["rect"].top))

    for turret in turrets:
        turret["actor"].draw()
    for gem in gems:
        pulse = 6 + math.sin(game_time * 3) * 2
        screen.draw.filled_circle(gem.pos, 12 + pulse, (50, 130, 200))
        screen.draw.circle(gem.pos, 16 + pulse, (160, 210, 255))
        gem.draw()
    for h in hearts:
        h.draw()
    for enemy in enemies:
        enemy.draw()
    draw_player_with_aura()
    draw_bullets()
    draw_hud()


def on_mouse_down(pos):
    global game_state, bullets
    if game_state == "menu":
        for btn in menu_buttons:
            if btn.handle_click(pos):
                break
    elif game_state in ("game_over", "win"):
        reset_to_menu()
    elif game_state == "playing":
        shot = player.shoot(pos)
        if shot:
            bullets.append(shot)


def on_key_down(key):
    if key == keys.ESCAPE:
        reset_to_menu()
    if game_state == "playing" and key == keys.R:
        player.reload()


def draw_background():
    for i in range(16):
        t = i / 15
        r = int(SKY_TOP[0] * (1 - t) + SKY_BOTTOM[0] * t)
        g = int(SKY_TOP[1] * (1 - t) + SKY_BOTTOM[1] * t)
        b = int(SKY_TOP[2] * (1 - t) + SKY_BOTTOM[2] * t)
        screen.draw.filled_rect(Rect((0, i * HEIGHT // 16), (WIDTH, HEIGHT // 16 + 1)), (r, g, b))
    screen.draw.filled_rect(Rect((0, HEIGHT // 3), (WIDTH, HEIGHT)), FLOOR_DARK)
    screen.draw.filled_rect(Rect((0, HEIGHT * 2 // 3), (WIDTH, HEIGHT // 3)), FLOOR_LIGHT)


def draw_floor_pattern():
    for y in range(0, HEIGHT, 24):
        color = (30, 52, 58) if (y // 24) % 2 == 0 else (36, 60, 66)
        screen.draw.filled_rect(Rect((0, y), (WIDTH, 24)), color)
    for x in range(0, WIDTH, 48):
        screen.draw.line((x, 0), (x, HEIGHT), (20, 40, 46))


def update_fireflies(dt):
    for bug in fireflies:
        bug["y"] += math.sin(game_time * 2 + bug["phase"]) * bug["speed"] * dt
        bug["x"] += math.cos(game_time * 1.5 + bug["phase"]) * bug["speed"] * 0.6 * dt
        if bug["x"] < 0:
            bug["x"] += WIDTH
        if bug["x"] > WIDTH:
            bug["x"] -= WIDTH
        if bug["y"] < 0:
            bug["y"] += HEIGHT
        if bug["y"] > HEIGHT:
            bug["y"] -= HEIGHT


def update_spikes(dt):
    for spike in spikes:
        spike["timer"] += dt
        if spike["timer"] >= spike["period"]:
            spike["timer"] = 0.0
            spike["active"] = not spike["active"]


def update_turrets(dt):
    for turret in turrets:
        turret["timer"] -= dt
        if turret["timer"] <= 0:
            turret["timer"] = turret["cooldown"]
            dx = player.actor.x - turret["actor"].x
            dy = player.actor.y - turret["actor"].y
            dist = math.hypot(dx, dy)
            if dist <= turret["range"]:
                if dist == 0:
                    dist = 1
                dx /= dist
                dy /= dist
                turret_shots.append(
                    {
                        "x": turret["actor"].x,
                        "y": turret["actor"].y,
                        "dx": dx,
                        "dy": dy,
                        "speed": TURRET_BULLET_SPEED,
                        "ttl": 3.0,
                        "radius": 4,
                        "damage": TURRET_DAMAGE,
                    }
                )


def draw_fireflies():
    for bug in fireflies:
        pulse = 1.5 + math.sin(game_time * 6 + bug["phase"]) * 0.8
        screen.draw.filled_circle((bug["x"], bug["y"]), 2 + pulse, (230, 255, 200))
        screen.draw.circle((bug["x"], bug["y"]), 4 + pulse, (80, 140, 90))


def draw_player_with_aura():
    player.draw()
    if player.invulnerable > 0:
        pulse = 6 + math.sin(game_time * 12) * 2
        screen.draw.circle(player.actor.pos, player.actor.width + pulse, (255, 180, 180))
    aim = mouse.pos if hasattr(mouse, "pos") else (player.actor.x + 1, player.actor.y)
    vx = aim[0] - player.actor.x
    vy = aim[1] - player.actor.y
    length = math.hypot(vx, vy) or 1
    vx /= length
    vy /= length
    gun_len = player.actor.width * 0.6
    start = (player.actor.x + vx * 10, player.actor.y + vy * 10)
    end = (start[0] + vx * gun_len, start[1] + vy * gun_len)
    tail = (start[0] - vx * 4, start[1] - vy * 4)
    muzzle_end = (end[0] + vx * 8, end[1] + vy * 8)
    perp = (-vy, vx)
    half_w = 5
    for off in range(-half_w, half_w + 1, 2):
        ox = perp[0] * off
        oy = perp[1] * off
        screen.draw.line((tail[0] + ox, tail[1] + oy), (end[0] + ox, end[1] + oy), (35, 40, 55))
    screen.draw.line(tail, end, (180, 200, 255))
    screen.draw.line(end, muzzle_end, (230, 240, 255))


def draw_hud():
    screen.draw.text(f"HP: {player.hp}", topleft=(20, 18), fontsize=26, color=(235, 245, 255))
    screen.draw.text(
        f"Gems: {total_gems - len(gems)}/{total_gems}",
        topleft=(20, 46),
        fontsize=24,
        color=(200, 230, 255),
    )
    screen.draw.text(f"{player.ammo}/{player.reserve}", topleft=(WIDTH - 140, HEIGHT - 50), fontsize=20, color=(235, 245, 255))
    if player.reloading:
        screen.draw.text("Reloading", topleft=(WIDTH - 140, HEIGHT - 30), fontsize=18, color=(240, 200, 120))
    else:
        screen.draw.text("R reload", topleft=(WIDTH - 140, HEIGHT - 30), fontsize=16, color=(200, 220, 230))
    msg = "Exit unlocked! Reach the door." if exit_unlocked else "Clear room and grab all gems."
    screen.draw.text(msg, topright=(WIDTH - 14, 16), fontsize=22, color=(210, 230, 240))
    danger = "Spikes toggling + turrets firing" if spikes else ""
    if danger:
        screen.draw.text(danger, topright=(WIDTH - 14, 42), fontsize=18, color=(240, 180, 150))
    screen.draw.text(f"Stage {stage}/{MAX_STAGE}", topleft=(WIDTH//2 - 40, 14), fontsize=22, color=(230, 230, 255))


def draw_banner(text, color):
    cover = Rect((40, HEIGHT // 2 - 50), (WIDTH - 80, 100))
    screen.draw.filled_rect(cover, (12, 16, 18))
    screen.draw.rect(cover, (230, 230, 230))
    screen.draw.text(text, center=cover.center, fontsize=30, color=color)


def draw_exit():
    img = "exit_open" if exit_unlocked else "exit_closed"
    pos = (exit_rect.left, exit_rect.top)
    screen.draw.rect(exit_rect, (50, 36, 20))
    if exit_unlocked:
        glow = 10 + math.sin(game_time * 6) * 4
        screen.draw.rect(exit_rect.inflate(glow, glow), (230, 210, 120))
        screen.draw.filled_rect(exit_rect.inflate(glow * 1.2, glow * 1.2), (24, 24, 18))
    else:
        screen.draw.rect(exit_rect.inflate(6, 6), (30, 20, 10))
    screen.blit(img, pos)


def draw_bullets():
    for b in bullets:
        screen.draw.filled_circle((b["x"], b["y"]), b["radius"], (230, 250, 255))
        screen.draw.circle((b["x"], b["y"]), b["radius"] + 2, (120, 180, 210))
    for s in turret_shots:
        screen.draw.filled_circle((s["x"], s["y"]), s["radius"], (240, 120, 90))
        screen.draw.circle((s["x"], s["y"]), s["radius"] + 1, (180, 70, 50))


fireflies = make_fireflies()


def make_heart(pos):
    h = Actor("heart", pos=pos)
    h.scale = HUGE_SCALE
    return h


def update_player_shots(dt, enemies, walls, shots):
    updated = []
    for b in shots:
        b["ttl"] -= dt
        if b["ttl"] <= 0:
            continue
        b["x"] += b["dx"] * b["speed"] * dt
        b["y"] += b["dy"] * b["speed"] * dt
        if b["x"] < 0 or b["x"] > WIDTH or b["y"] < 0 or b["y"] > HEIGHT:
            continue
        if any(Rect(w).collidepoint(b["x"], b["y"]) for w in walls):
            continue
        hit_enemy = False
        for enemy in enemies:
            if actor_rect(enemy.actor).collidepoint(b["x"], b["y"]):
                enemy.take_damage(BULLET_DAMAGE)
                hit_enemy = True
                break
        if not hit_enemy:
            updated.append(b)
    return updated


def update_turret_shots(dt, walls, shots):
    updated = []
    for s in shots:
        s["ttl"] -= dt
        if s["ttl"] <= 0:
            continue
        s["x"] += s["dx"] * s["speed"] * dt
        s["y"] += s["dy"] * s["speed"] * dt
        if s["x"] < 0 or s["x"] > WIDTH or s["y"] < 0 or s["y"] > HEIGHT:
            continue
        if any(Rect(w).collidepoint(s["x"], s["y"]) for w in walls):
            continue
        if actor_rect(player.actor).collidepoint(s["x"], s["y"]):
            player.hit(s.get("damage", TURRET_DAMAGE))
            continue
        updated.append(s)
    return updated


def has_line_of_sight(a, b, walls, steps=10):
    ax, ay = a
    bx, by = b
    for i in range(1, steps):
        t = i / steps
        x = ax + (bx - ax) * t
        y = ay + (by - ay) * t
        if any(Rect(w).collidepoint(x, y) for w in walls):
            return False
    return True


def reachable_positions(start, walls, step=24, margin=18):
    start_cell = (int(start[0] // step), int(start[1] // step))
    visited = set()
    q = deque([start_cell])
    visited.add(start_cell)
    results = []
    while q:
        cx, cy = q.popleft()
        x = cx * step + step / 2
        y = cy * step + step / 2
        if margin <= x <= WIDTH - margin and margin <= y <= HEIGHT - margin:
            if not any(Rect(w).collidepoint(x, y) for w in walls):
                results.append((x, y))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if (nx, ny) not in visited:
                        visited.add((nx, ny))
                        q.append((nx, ny))
    return results


def bounded_rect(center, w, h):
    left = clamp(center[0] - w / 2, 0, WIDTH - w)
    top = clamp(center[1] - h / 2, 0, HEIGHT - h)
    return Rect((left, top), (w, h))
