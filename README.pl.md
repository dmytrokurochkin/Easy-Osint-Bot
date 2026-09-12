[English](README.md) · [Українська](README.uk.md) · Polski

# Bot OSINT na Telegramie

Bot na Telegramie do wyszukiwań OSINT po nazwie użytkownika, e-mailu lub numerze telefonu, z użyciem Blackbird, Maigret, Sherlock, Holehe i GHunt. Angielski / ukraiński / polski — każdy użytkownik wybiera własny język w menu bota.

## Zastrzeżenie

Ten projekt jest udostępniany **wyłącznie w celach edukacyjnych i do autoryzowanych badań bezpieczeństwa**. Ma pomóc sprawdzić własny cyfrowy ślad oraz wspierać legalne działania OSINT prowadzone z odpowiednim upoważnieniem.

Zabrania się używania go wobec jakiejkolwiek osoby, konta czy organizacji bez jej wyraźnej zgody lub bez uzasadnionej podstawy prawnej. Używanie go do nękania, śledzenia, doxingu, dyskryminacji lub innej krzywdy wobec innej osoby — albo w jakimkolwiek innym nielegalnym celu — jest surowo zabronione.

To oprogramowanie jest dostarczane "tak jak jest", bez żadnej gwarancji. Autor(zy) nie ponoszą odpowiedzialności za jakiekolwiek szkody, straty ani konsekwencje prawne wynikające z jego użycia lub niewłaściwego użycia. Wyłączną odpowiedzialność za zgodność użytkowania z prawem twojej jurysdykcji oraz z regulaminami każdej odpytywanej platformy ponosisz ty sam.

## Wymagania

- **Python 3.11 lub nowszy**

To wszystko. Blackbird jest osadzony bezpośrednio w tym repozytorium (bez osobnego klonowania), a każda inna zależność instaluje się automatycznie przy pierwszym uruchomieniu.

## Uruchomienie bota

```bash
python main.py
```

Pierwsze uruchomienie samo:

1. Zainstaluje brakujące zależności Pythona (`pip install -r requirements.txt`).
2. Zapyta o `BOT_TOKEN` (od [@BotFather](https://t.me/botfather)) i `ADMIN_ID` (twój numeryczny Telegram ID, od [@userinfobot](https://t.me/userinfobot)), jeśli `.env` jeszcze nie istnieje, i zapisze go.
3. Zainstaluje GHunt przez `pipx`, jeśli nie jest jeszcze zainstalowany.

Każde kolejne uruchomienie pomija to, co już zrobione — `python main.py` to zawsze jedyna potrzebna komenda.

`ghunt login` to jedyny krok, który zawsze pozostaje ręczny — wymaga jednorazowego przepływu przez rozszerzenie przeglądarki. Wykonaj go raz, jeśli chcesz włączyć GHunt (e-mail → rozpoznanie konta Google); włącz go potem w menu ustawień bota.

## Pierwsze użycie

1. Otwórz Telegram i napisz do swojego bota.
2. Wyślij `/start`.
3. **Jako administrator** (ID, które ustawiłeś jako `ADMIN_ID`): masz od razu pełny dostęp. Dodawaj innych przez "⚙️ Ustawienia" → "👥 Użytkownicy" → "➕ Dodaj", albo przełącz na "🔓 Tryb: Otwarty", aby pozwolić każdemu bez zatwierdzania.
4. Wybierz język w dowolnym momencie przyciskiem "🌐 <język>" w menu głównym — jest zapisywany osobno dla każdego użytkownika Telegramu.

## Uruchamianie testów

```bash
pip install -r requirements-dev.txt
pytest
```

## Co robi `python main.py` pod maską

Zobacz `core/bootstrap.py` — krótki, czytelny plik. W skrócie: sprawdza brakujące pakiety pip i je instaluje, sprawdza `.env` i pyta o niego, jeśli go nie ma, sprawdza GHunt i instaluje go przez pipx, jeśli go nie ma. Każdy krok jest idempotentny (bezpiecznie uruchomić ponownie).

## Licencja

Blackbird (osadzony w `blackbird/`) jest na licencji GPLv3 — zobacz `blackbird/docs/LICENSE`. Reszta projektu jest licencjonowana osobnie (zobacz `LICENSE` w katalogu głównym repozytorium, jeśli istnieje) — ta licencja nie obejmuje `blackbird/`.
