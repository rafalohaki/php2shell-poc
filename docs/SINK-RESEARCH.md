# Research: realne sinki `include()` w publicznym kodzie PHP

Data: 2026-10-21. Cel: znaleźć sink **bez doklejania rozszerzenia**,
bo tylko taki przyjmie plik sesji (`/tmp/sess/sess_XXX` bez `.php`).

## Metoda

1. Baza CVE (178k) → CWE-98 (PHP file inclusion) z publicznym PoC
2. `mcpx gh --mode code` → GitHub code search
3. Ręczna analiza kodu źródłowego pobranych aplikacji

## Znalezione i sprawdzone

### WP Travel Engine 6.6.7 (CVE-2025-7634)

```php
// FilterTripsHtml.php:134
wptravelengine_get_template("content-{$view_mode}.php", $details);
// helpers.php:842
include $action_args['located'];
```
**Dokleja `.php`** → ✗ session poisoning nie zadziała

Łańcuch potwierdzony do `{"success":true}` — sink wykonany, ale nie trafia
w plik sesji. Szczegóły: `REAL-PLUGIN-RESULT.md`

### Zen Cart 1.5.8a (CVE-2024-5762)

```php
// admin/index.php:7-23
$cmd = $_GET['cmd'];
require basename($cmd . '.php');              // basename() niszczy traversal
$adminPage = findPluginAdminPage($plugins, $cmd);
require($adminPage);                          // gałąź 2: $page . '.php'
```
**Dokleja `.php`** + `basename()` redukuje do `sess_X.php` → ✗

### All-in-One Video Gallery / ElementsKit / LearnPress

```
AIOVG     : require_once AIOVG_PLUGIN_DIR . '...'    (statyczne)
ElementsKit: include $file_path                       (statyczne przypisanie)
LearnPress : include LP_TEMPLATE_PATH . '...'         (statyczne)
```
Brak sinków z inputem → ✗

### GitHub code search — zaszumione

Zapytania `include $_GET`, `require($_REQUEST[` zwracają:
- listy payloadów (`IntruderPayloads`, `OneListForAll`, `PayloadsAllTheThings`)
- archiwa Exploit-DB
- dokumentację CTF

**Nie realne aplikacje.** Filtr `language:PHP` nie pomaga — wyniki to
głównie pliki z wzorcami ataków, nie kod podatny.

## Wniosek

**Nie znalazłem publicznej aplikacji PHP z `include($user)` bez sufiksu.**

Wzorzec `include($X . '.php')` jest **dominujący** w realnym kodzie, bo:
- autorzy chcą wymusić rozszerzenie
- frameworki (WP, Laravel, Zen Cart) mają własne loadery z sufiksem

## Co to znaczy dla CASE-004

Session poisoning wymaga rzadkiego warunku:

```php
include($user);           // ← BEZ konkatenacji — rzadkie, ale istnieje
```

Realistyczne miejsca:
- prosty `page.php?p=X` w starych aplikacjach
- customowe CMS-y
- kod CTF / laby

**To zawęża CASE-004 do konkretnej klasy aplikacji.** Nazwanie tego
„uniwersalnym RCE" byłoby nieprawdą.

## Co jeszcze można zrobić

1. **Szukać w Exploit-DB** haseł „Local File Inclusion" + PHP — tam są
   konkretne ścieżki do podatnych plików, nie do repo.
2. **Testować znane LFI z CVE** — ale większość ma sufiks lub `basename()`.
3. **Użyć innego prymitywu zapisu** — np. `error_log` do pliku `.php`,
   jeśli aplikacja na to pozwala.

Session poisoning to **jeden z wektorów**, nie uniwersalny.
