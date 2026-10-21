# Test na PRAWDZIWYM pluginie: WP Travel Engine 6.6.7 (CVE-2025-7634)

## Setup

- WordPress **7.1.3** + `wordpress:7.1.3-php8.4-apache`
- Plugin **wp-travel-engine 6.6.7** — prawdziwy, pobrany z wordpress.org
- MariaDB 11.4, `session.upload_progress.cleanup=0`
- WP-CLI: instalacja + aktywacja pluginu

## Znaleziony łańcuch (z prawdziwego kodu)

```
FilterTripsHtml.php:34   ACTION = 'wte_show_ajax_result'     ← nopriv, bez auth
FilterTripsHtml.php:72   $view_mode = $_POST['mode']          ← KONTROLA ATAKUJĄCEGO
FilterTripsHtml.php:134  wptravelengine_get_template("content-{$view_mode}.php")
helpers.php:146          → wte_get_template()
helpers.php:751          → wte_locate_template()
helpers.php:842          include $action_args['located'];     ← SINK
```

**Nonce** jest wymagany, ale generowalny:
```php
wp_create_nonce('wte_show_ajax_result')   // → 99edec399b
```
Nonce z publicznego HTML był **nieprawidłowy** dla tej akcji (inne działanie).

## Co POTWIERDZONE

| Krok | Wynik |
|---|---|
| Plugin aktywny | ✅ `Plugin 'wp-travel-engine' activated` |
| Akcja `nopriv` | ✅ `FilterTripsHtml` w rejestrze |
| Nonce akceptowany | ✅ `{"success":true}` |
| Session poisoning | ✅ `/tmp/sess/sess_XXX` zawiera `upload_progress_<?php ...?>|...` |
| Sink wykonany | ✅ `wptravelengine_get_template()` przeszło |

## BLOKADA — sufiks `.php`

Sink **dokleja `.php`** do `mode`:

```php
wptravelengine_get_template("content-{$view_mode}.php")
    → $default_path . 'content-' . $mode . '.php'
    → .../includes/templates/content-<MODE>.php
```

A plik sesji to `/tmp/sess/sess_XXX` — **bez `.php`**.

Próby:
```
mode = /tmp/sess/sess_XXX
  → content-/tmp/sess/sess_XXX.php        (nie istnieje)

mode = ../../../../tmp/sess/sess_XXX
  → content-../../../../tmp/sess/sess_XXX.php  (nie istnieje)
```

`locate_template()` dodatkowo:
- zwraca `''` dla ścieżek absolutnych
- blokuje traversal (`realpath = false`)

## Wniosek

**CVE-2025-7634 jest realne**, ale **session poisoning nie jest
właściwym wektorem dla tego pluginu** — sufiks `.php` blokuje.

Do wykorzystania CVE-2025-7634 potrzebny jest plik `.php`, który
atakujący może **zapisać** (np. przez inny upload w pluginie),
a nie plik sesji.

## Co to znaczy dla CASE-004

Session poisoning → LFI działa, ale **tylko gdy sink nie dokleja rozszerzenia**:

| Sink | Działa? |
|---|---|
| `include($tpl)` — bez sufiksu | ✅ **TAK** (CASE-004, uid=0) |
| `include($tpl . '.php')` | ❌ NIE |
| `wptravelengine_get_template("content-{$mode}.php")` | ❌ NIE |

To zawęża zasięg techniki do sinków **bez doklejania rozszerzenia**.
