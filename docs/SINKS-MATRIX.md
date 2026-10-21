# Macierz sinków — session poisoning → LFI → RCE

Wszystkie testy na **PHP 8.5.11** (latest), `uid=0` potwierdzone.

## Wyniki

| Sink | Wzorzec | Parametr | RCE | Realny odpowiednik |
|---|---|---|---|---|
| **Custom PHP** | `include($_GET['tpl'])` | `tpl` | ✅ | własny kod |
| **WP plugin (CWE-98)** | `include($_REQUEST['template'])` | `template` | ✅ | CVE-2025-9993, -7634, -8142 |
| **Laravel View::file** | `include($path)` po `file_exists` | `view` | ✅ | `View::file($user)` |
| WP core 7.1.3 | — | — | ❌ | brak LFI w core |
| Laravel 11 core | — | — | ❌ | `View::make()` sanityzuje |

## Kluczowa obserwacja

**Wszystkie trzy działają identycznie** — bo to ten sam mechanizm:

```
PHP_SESSION_UPLOAD_PROGRESS = "<?php ... ?>"
        ↓
/tmp/sess_<sid> zawiera: upload_progress_<?php ... ?>|a:5:{...}
        ↓
include($sink_param) na tej sciezce
        ↓
RCE
```

**Sink nie musi być `include($_GET)`** — wystarczy, że końcowy `include()`
dostaje ścieżkę, którą kontroluje atakujący. `file_exists()` przed
`include()` NIE chroni (plik sesji istnieje).

## Wymagania

| # | Warunek | Domyślne? |
|---|---|---|
| 1 | `upload_progress.enabled=On` | ✅ tak |
| 2 | `upload_progress.cleanup=Off` | ❌ NIE |
| 3 | `session.save_path` znany | ✅ `/tmp` |
| 4 | Znany/przewidywalny SID | ✅ |
| 5 | Sink `include()` na ścieżce usera | ❗ wąskie gardło |

## Warunek 2 — jak obejść `cleanup=On`

**Nie udało się** (testowane: polling co 50 ms, Apache prefork, CLI server).
PHP **nie zapisuje treści** sesji podczas uploadu przy `cleanup=On` —
plik jest tworzony pusty i usuwany na końcu.

**Wniosek:** technika wymaga `cleanup=Off`. To zawęża zasięg do aplikacji,
które mają tę opcję wyłączoną (np. dla paska postępu uploadu).

## Pliki labów

- `lab/` — custom PHP (`index.php` + `view.php`)
- `sinks/wordpress-plugin/` — `plugin.php` + `lab_standalone.php`
- `sinks/laravel/` — `lab.php` (`View::file` pattern)
- `scripts/exploit_generic.py` — **uniwersalny** (host, port, path, param)
- `scripts/pwn.py` — oryginalny (CASE-004)

## Użycie

```bash
python3 scripts/exploit_generic.py <host> <port> <path> <param> [save_path]

# przyklady:
python3 scripts/exploit_generic.py lv 8800 /lab.php view
python3 scripts/exploit_generic.py wps 8700 /lab_standalone.php template
```

## Uczciwe ograniczenie

To **wzmacniacz LFI**, nie uniwersalne RCE:
- wymaga `cleanup=Off` (nie domyślne)
- wymaga realnego sinku w aplikacji
- WordPress core i Laravel core **nie mają** takiego sinku

Wartość: zamienia „czytam pliki" w „wykonuję kod" i omija filtry
rozszerzeń uploadu (PHP ląduje w pliku bez `.php`).
