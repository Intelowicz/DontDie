import math
import os
import random
import sys

import pygame

pygame.init()

SZER, WYS = 800, 600
ekran = pygame.display.set_mode((SZER, WYS))
pygame.display.set_caption("Kosmiczny Strzelec")
zegar = pygame.time.Clock()

F_MALA = pygame.font.SysFont("dejavusans", 22)
F_SREDNIA = pygame.font.SysFont("dejavusans", 34, bold=True)
F_DUZA = pygame.font.SysFont("dejavusans", 72, bold=True)

KATALOG = os.path.dirname(os.path.abspath(__file__))
PLIK_WYNIKOW = os.path.join(KATALOG, "najlepszy_wynik.txt")

BIALY = (255, 255, 255)
ZOLTY = (255, 220, 60)
CZERWONY = (255, 80, 80)
NIEBIESKI = (80, 170, 255)
FIOLETOWY = (190, 110, 255)
ZIELONY = (90, 255, 140)
BLEKIT = (120, 220, 255)
KOLORY_POWERUPOW = {"zycie": ZIELONY, "szybki": ZOLTY, "tarcza": BLEKIT}

gwiazdy = [
    [random.randint(0, SZER), random.randint(0, WYS), random.uniform(0.5, 3)]
    for _ in range(120)
]


def wczytaj_wynik():
    try:
        with open(PLIK_WYNIKOW) as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return 0


def zapisz_wynik(wynik):
    with open(PLIK_WYNIKOW, "w") as f:
        f.write(str(wynik))


def napis(tekst, font, kolor, pozycja, srodek=False):
    obraz = font.render(tekst, True, kolor)
    if srodek:
        ekran.blit(obraz, obraz.get_rect(center=pozycja))
    else:
        ekran.blit(obraz, obraz.get_rect(topleft=pozycja))


def rysuj_tlo():
    ekran.fill((5, 5, 20))
    for g in gwiazdy:
        g[1] += g[2]
        if g[1] > WYS:
            g[0] = random.randint(0, SZER)
            g[1] = 0
        jasnosc = int(100 + g[2] * 50)
        promien = 1 if g[2] < 2 else 2
        pygame.draw.circle(ekran, (jasnosc, jasnosc, jasnosc), (int(g[0]), int(g[1])), promien)


def przyciemnij():
    tlo = pygame.Surface((SZER, WYS), pygame.SRCALPHA)
    tlo.fill((0, 0, 0, 170))
    ekran.blit(tlo, (0, 0))


class Gracz:
    def __init__(self):
        self.rect = pygame.Rect(SZER // 2 - 20, WYS - 70, 40, 40)
        self.zycie = 3
        self.cooldown = 0
        self.tarcza = 0
        self.szybki = 0
        self.nietykalny = 0

    def ruch(self, klawisze):
        predkosc = 6
        if klawisze[pygame.K_LEFT] or klawisze[pygame.K_a]:
            self.rect.x -= predkosc
        if klawisze[pygame.K_RIGHT] or klawisze[pygame.K_d]:
            self.rect.x += predkosc
        if klawisze[pygame.K_UP] or klawisze[pygame.K_w]:
            self.rect.y -= predkosc
        if klawisze[pygame.K_DOWN] or klawisze[pygame.K_s]:
            self.rect.y += predkosc
        self.rect.clamp_ip(ekran.get_rect())


class Wrog:
    def __init__(self, poziom):
        if random.random() < 0.3:
            self.typ, self.hp, self.kolor, rozmiar = "ciezki", 3, FIOLETOWY, 36
        else:
            self.typ, self.hp, self.kolor, rozmiar = "zwykly", 1, CZERWONY, 28
        self.rect = pygame.Rect(0, -rozmiar, rozmiar, rozmiar)
        self.srodek_x = random.randint(40, SZER - 40)
        self.y = float(-rozmiar)
        self.predkosc = random.uniform(1.2, 2.2) + poziom * 0.15
        self.t = random.uniform(0, 2 * math.pi)
        self.amplituda = random.randint(10, 60)
        self.timer_strzalu = random.randint(60, 180)

    def ruch(self):
        self.t += 0.04
        self.y += self.predkosc
        self.rect.y = int(self.y)
        self.rect.x = int(self.srodek_x + math.sin(self.t) * self.amplituda - self.rect.w / 2)

    def czy_strzela(self):
        self.timer_strzalu -= 1
        if self.timer_strzalu <= 0:
            self.timer_strzalu = random.randint(90, 200)
            return True
        return False


class Boss:
    def __init__(self, poziom):
        self.rect = pygame.Rect(SZER // 2 - 80, 40, 160, 80)
        self.hp_max = 25 + poziom * 10
        self.hp = self.hp_max
        self.kierunek = 1
        self.timer = 0

    def ruch(self):
        self.timer += 1
        self.rect.x += 3 * self.kierunek
        if self.rect.left < 0 or self.rect.right > SZER:
            self.kierunek *= -1


class Gra:
    def __init__(self):
        self.gracz = Gracz()
        self.pociski = []          # [x, y, vx, vy] pociski gracza
        self.wrogie_pociski = []   # [x, y, vx, vy] pociski wrogów
        self.wrogowie = []
        self.boss = None
        self.powerupy = []         # {"rect": Rect, "typ": str}
        self.czastki = []          # [x, y, vx, vy, zycie, kolor]
        self.wynik = 0
        self.poziom = 1
        self.zabojstwa = 0         # zabójstwa na tym poziomie
        self.czas_spawn = 0
        self.best = wczytaj_wynik()
        self.koniec = False

    def wybuch(self, x, y, kolor, ile=18):
        for _ in range(ile):
            kat = random.uniform(0, 2 * math.pi)
            v = random.uniform(1, 5)
            self.czastki.append(
                [x, y, math.cos(kat) * v, math.sin(kat) * v, random.randint(20, 40), kolor]
            )

    def trafienie_gracza(self):
        g = self.gracz
        if g.tarcza > 0 or g.nietykalny > 0:
            return
        g.zycie -= 1
        g.nietykalny = 60
        self.wybuch(g.rect.centerx, g.rect.centery, ZOLTY, 25)
        if g.zycie <= 0:
            self.koniec_gry()

    def koniec_gry(self):
        if self.koniec:
            return
        self.koniec = True
        if self.wynik > self.best:
            self.best = self.wynik
            zapisz_wynik(self.best)

    def zabij_wroga(self, w):
        self.wrogowie.remove(w)
        self.wybuch(w.rect.centerx, w.rect.centery, w.kolor)
        self.wynik += 10 if w.typ == "zwykly" else 25
        self.zabojstwa += 1
        if random.random() < 0.15:
            typ = random.choice(list(KOLORY_POWERUPOW))
            self.powerupy.append({
                "rect": pygame.Rect(w.rect.centerx - 10, w.rect.centery, 20, 20),
                "typ": typ,
            })

    def pokonaj_boss(self):
        self.wybuch(self.boss.rect.centerx, self.boss.rect.centery, FIOLETOWY, 80)
        self.wynik += 200
        self.boss = None
        self.poziom += 1
        self.zabojstwa = 0
        self.wrogie_pociski.clear()

    def update(self, klawisze):
        if self.koniec:
            return
        g = self.gracz

        # Timery gracza
        g.ruch(klawisze)
        for atr in ("cooldown", "tarcza", "szybki", "nietykalny"):
            if getattr(g, atr) > 0:
                setattr(g, atr, getattr(g, atr) - 1)

        # Strzelanie: SPACJA
        if klawisze[pygame.K_SPACE] and g.cooldown <= 0:
            self.pociski.append([g.rect.centerx, g.rect.top, 0, -11])
            g.cooldown = 7 if g.szybki > 0 else 16

        # Ruch pocisków
        for lista in (self.pociski, self.wrogie_pociski):
            for p in lista[:]:
                p[0] += p[2]
                p[1] += p[3]
                if not (-20 < p[0] < SZER + 20 and -20 < p[1] < WYS + 20):
                    lista.remove(p)

        # Spawn wrogów albo bossa
        if self.boss is None:
            if self.zabojstwa >= 10:
                self.boss = Boss(self.poziom)
                self.wrogowie.clear()
            else:
                self.czas_spawn -= 1
                if self.czas_spawn <= 0:
                    self.wrogowie.append(Wrog(self.poziom))
                    self.czas_spawn = max(20, 70 - self.poziom * 5)

        # Ruch wrogów i ich strzały
        for w in self.wrogowie[:]:
            w.ruch()
            if w.czy_strzela():
                self.wrogie_pociski.append([w.rect.centerx, w.rect.bottom, 0, 4])
            if w.rect.top > WYS:
                self.wrogowie.remove(w)

        # Boss strzela trzema pociskami co 45 klatek
        if self.boss:
            self.boss.ruch()
            if self.boss.timer % 45 == 0:
                for vx in (-2, 0, 2):
                    self.wrogie_pociski.append(
                        [self.boss.rect.centerx, self.boss.rect.bottom, vx, 4]
                    )

        # Trafienia pocisków gracza
        for p in self.pociski[:]:
            r = pygame.Rect(int(p[0]) - 3, int(p[1]), 6, 12)
            if self.boss and r.colliderect(self.boss.rect):
                self.boss.hp -= 1
                self.pociski.remove(p)
                if self.boss.hp <= 0:
                    self.pokonaj_boss()
                continue
            for w in self.wrogowie[:]:
                if r.colliderect(w.rect):
                    self.pociski.remove(p)
                    w.hp -= 1
                    if w.hp <= 0:
                        self.zabij_wroga(w)
                    break

        # Trafienia pocisków wroga
        for p in self.wrogie_pociski[:]:
            if pygame.Rect(int(p[0]) - 3, int(p[1]), 6, 12).colliderect(g.rect):
                self.wrogie_pociski.remove(p)
                self.trafienie_gracza()

        # Zderzenia z wrogami i bossem
        for w in self.wrogowie[:]:
            if w.rect.colliderect(g.rect):
                self.wrogowie.remove(w)
                self.wybuch(w.rect.centerx, w.rect.centery, w.kolor)
                self.trafienie_gracza()
        if self.boss and self.boss.rect.colliderect(g.rect):
            self.trafienie_gracza()

        # Power-upy
        for pu in self.powerupy[:]:
            pu["rect"].y += 2
            if pu["rect"].colliderect(g.rect):
                if pu["typ"] == "zycie":
                    g.zycie = min(g.zycie + 1, 5)
                elif pu["typ"] == "szybki":
                    g.szybki = 300
                else:
                    g.tarcza = 300
                self.powerupy.remove(pu)
            elif pu["rect"].top > WYS:
                self.powerupy.remove(pu)

        # Cząsteczki
        for c in self.czastki[:]:
            c[0] += c[2]
            c[1] += c[3]
            c[4] -= 1
            if c[4] <= 0:
                self.czastki.remove(c)

    def draw(self):
        rysuj_tlo()

        for pu in self.powerupy:
            pygame.draw.rect(ekran, KOLORY_POWERUPOW[pu["typ"]], pu["rect"], border_radius=5)
            pygame.draw.rect(ekran, BIALY, pu["rect"], 2, border_radius=5)

        for w in self.wrogowie:
            pygame.draw.rect(ekran, w.kolor, w.rect, border_radius=6)

        if self.boss:
            b = self.boss
            pygame.draw.rect(ekran, FIOLETOWY, b.rect, border_radius=12)
            pygame.draw.rect(ekran, BIALY, b.rect, 2, border_radius=12)
            pasek = pygame.Rect(SZER // 2 - 150, 12, 300, 12)
            pygame.draw.rect(ekran, (60, 0, 0), pasek)
            proc = max(b.hp, 0) / b.hp_max
            pygame.draw.rect(ekran, CZERWONY, (pasek.x, pasek.y, int(pasek.w * proc), pasek.h))

        for p in self.pociski:
            pygame.draw.rect(ekran, ZOLTY, (int(p[0]) - 3, int(p[1]), 6, 12))
        for p in self.wrogie_pociski:
            pygame.draw.rect(ekran, CZERWONY, (int(p[0]) - 3, int(p[1]), 6, 12))

        for c in self.czastki:
            pygame.draw.circle(ekran, c[5], (int(c[0]), int(c[1])), 2)

        self.rysuj_gracza()
        self.rysuj_hud()

    def rysuj_gracza(self):
        g = self.gracz
        if g.nietykalny > 0 and (g.nietykalny // 4) % 2:
            return  # migotanie po trafieniu
        r = g.rect
        punkty = [(r.centerx, r.top), (r.left, r.bottom), (r.centerx, r.bottom - 8), (r.right, r.bottom)]
        pygame.draw.polygon(ekran, NIEBIESKI, punkty)
        if g.tarcza > 0:
            pygame.draw.circle(ekran, BLEKIT, r.center, 34, 3)

    def rysuj_hud(self):
        g = self.gracz
        napis(f"Wynik: {self.wynik}", F_MALA, BIALY, (10, 10))
        napis(f"Rekord: {max(self.best, self.wynik)}", F_MALA, ZOLTY, (10, 38))
        napis(f"Poziom: {self.poziom}", F_MALA, BIALY, (10, 66))
        napis(f"Życie: {g.zycie}", F_MALA, ZIELONY, (SZER - 130, 10))
        if g.szybki > 0:
            napis(f"Szybki ogień: {g.szybki // 60 + 1}s", F_MALA, ZOLTY, (SZER - 260, 38))
        if g.tarcza > 0:
            napis(f"Tarcza: {g.tarcza // 60 + 1}s", F_MALA, BLEKIT, (SZER - 260, 66))


def ekran_menu():
    rysuj_tlo()
    napis("KOSMICZNY STRZELEC", F_DUZA, ZOLTY, (SZER // 2, 200), True)
    napis("ENTER - start", F_SREDNIA, BIALY, (SZER // 2, 300), True)
    napis("Strzałki / WASD - ruch, SPACJA - strzał, P - pauza", F_MALA, BIALY, (SZER // 2, 360), True)
    napis(f"Rekord: {wczytaj_wynik()}", F_MALA, ZOLTY, (SZER // 2, 400), True)
    napis("ESC - wyjście", F_MALA, BIALY, (SZER // 2, 440), True)


def main():
    stan = "menu"  # menu / gra / pauza / koniec
    gra = None
    while True:
        for zd in pygame.event.get():
            if zd.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if zd.type != pygame.KEYDOWN:
                continue
            if stan == "menu":
                if zd.key == pygame.K_RETURN:
                    gra = Gra()
                    stan = "gra"
                elif zd.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
            elif stan == "gra" and zd.key == pygame.K_p:
                stan = "pauza"
            elif stan == "pauza" and zd.key in (pygame.K_p, pygame.K_RETURN):
                stan = "gra"
            elif stan == "koniec":
                if zd.key == pygame.K_r:
                    gra = Gra()
                    stan = "gra"
                elif zd.key == pygame.K_m:
                    stan = "menu"

        if stan == "menu":
            ekran_menu()
        elif stan == "gra":
            gra.update(pygame.key.get_pressed())
            if gra.koniec:
                stan = "koniec"
            gra.draw()
        elif stan == "pauza":
            gra.draw()
            przyciemnij()
            napis("PAUZA", F_DUZA, BIALY, (SZER // 2, WYS // 2 - 20), True)
            napis("P - wróć do gry", F_MALA, BIALY, (SZER // 2, WYS // 2 + 40), True)
        elif stan == "koniec":
            gra.draw()
            przyciemnij()
            napis("KONIEC GRY", F_DUZA, CZERWONY, (SZER // 2, WYS // 2 - 60), True)
            napis(f"Wynik: {gra.wynik}", F_SREDNIA, BIALY, (SZER // 2, WYS // 2 + 10), True)
            napis("R - zagraj ponownie, M - menu", F_MALA, BIALY, (SZER // 2, WYS // 2 + 60), True)

        pygame.display.flip()
        zegar.tick(60)


if __name__ == "__main__":
    main()