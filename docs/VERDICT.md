# CASE-004 — WERDYKT KOŃCOWY

| Pole | Wartość |
|---|---|
| **ID** | CASE-004 |
| **Nazwa** | Session-file poisoning → LFI → RCE |
| **CVE** | **brak** — wada aplikacji, nie PHP core |
| **Typ** | LFI → RCE (CWE-98 → CWE-78) |
| **Werdykt** | **confirmed (warunkowe)** |
| **Data zamknięcia** | 2026-10-21 |
| **PHP** | 8.5.11 (latest) + 8.4 |

---

## 1. Co zostało potwierdzone

**RCE działa** — `uid=0(root)`, wielokrotnie, na PHP 8.5.11:

```
POST field PHP_SESSION_UPLOAD_PROGRESS = "<?php system($_GET['c']);?>"
    ↓
/tmp/sess_<sid> zawiera: upload_progress_<?php ... ?>|a:5:{...}
    ↓
include($sink) na ścieżce atakującego
    ↓
uid=0(root)
```

**Trzy wzorce sinków, wszystkie `uid=0`:**
1. `include($_GET['tpl'])` — custom PHP
2. `include($_REQUEST['template'])` — wzorzec WP plugin
3. `include($path)` po `file_exists()` — wzorzec Laravel `View::file()`

**PRAWDZIWY SHELL (nie tylko system()):**
```
root@a4182db64e00:/app#        ← interaktywny shell przez reverse TCP
```
Dowód: `shell/REVERSE-SHELL-PROOF.md`

**TRWAŁY WEBSHELL:**
```
[persist] PAYLOAD_PERSISTED   [cmd] <dowolna komenda>   [read] /etc/passwd
trzy osobne wywolania na tym samym SID bez re-poison -> dziala
```
Dowód: `webshell/WEBSHELL-PROOF.md`

**`php://filter` na pliku sesji** — działa dodatkowo, gdy sink nie ma
guardu na wrappery (przechodzi przez `allow_url_include=Off`).

---

## 2. Warunki konieczne (wszystkie)

| # | Warunek | Domyślne w PHP? | Ocena |
|---|---|---|---|
| 1 | `session.upload_progress.enabled=On` | ✅ **TAK** | darmowy |
| 2 | `session.upload_progress.cleanup=Off` | ❌ **NIE** (domyślnie On) | **wąskie gardło** |
| 3 | `session.save_path` znany | ✅ zwykle `/tmp` | darmowy |
| 4 | Znany/przewidywalny SID | ✅ cookie | darmowy |
| 5 | **`include()` na ścieżce usera** | ❌ | **wąskie gardło** |
| 6 | Sink **nie dokleja** rozszerzenia | ❌ | **wąskie gardło** |

**Trzy z sześciu warunków nie są domyślne.** Dlatego werdykt jest
„confirmed (warunkowe)", nie „confirmed (uniwersalne)".

---

## 3. Co zostało OBMIERZONE jako nieosiągalne

| Próba | Wynik | Powód |
|---|---|---|
| `cleanup=On` + race | ❌ | plik nie powstaje nawet na 10 ms (300 prób, Apache prefork) |
| SID z `.php` / `.phar` | ❌ | PHP waliduje SID, odrzuca kropki |
| `data://` | ❌ | `allow_url_include=Off` |
| `php://input` przez `include` | ❌ | `allow_url_include=Off` (ale `file_get_contents` działa!) |
| `/proc/self/fd` | ❌ | body w pamięci, nie w deskryptorze (cli-server i mod_php) |
| `phar://` deserializacja | ❌ | phar musi być na początku pliku, sesja ma prefiks |
| `error_log` injection | ❌ | PHP HTML-encoduje payload |
| `basename()` w sinku | ❌ | redukuje ścieżkę do nazwy pliku |
| `include($x.'.php')` | ❌ | sufiks blokuje plik sesji |

**Dziewięć wektorów, wszystkie poza session poisoning trafiają w twardą
blokadę PHP.** To udokumentowane granice, nie brak prób.

---

## 4. Test na PRAWDZIWYM pluginie

**WP Travel Engine 6.6.7** (CVE-2025-7634, CWE-98, bez auth):
- Łańcuch znaleziony i potwierdzony do `{"success":true}`
- Nonce przełamany (`wp_create_nonce('wte_show_ajax_result')`)
- **Blokada:** sink dokleja `.php`, plik sesji go nie ma
- Szczegóły: `REAL-PLUGIN-RESULT.md`

**Zen Cart 1.5.8a** (CVE-2024-5762):
- `require basename($cmd . '.php')` — `basename()` niszczy traversal
- **Blokada**

---

## 5. Research publicznych sinków

Przeszukane: baza 178k CVE (CWE-98 + PoC), GitHub code search,
7 WP pluginów, 2 aplikacje PHP.

**Wniosek:** wzorzec `include($X . '.php')` **dominuje** w realnym kodzie.
`include($user)` bez sufiksu jest rzadki — dlatego session poisoning
ma wąski zasięg.

Szczegóły: `SINK-RESEARCH.md`

---

## 6. Znaleziony prawdziwy patch (kontekst)

Repo `eness/php2shell-...` zawiera `session-upload-progress-counters.patch`,
który usuwa cached bucket pointers z `php_session_rfc1867_progress`.
To **nie naprawia CASE-004** (bo to wada aplikacji), ale naprawia
Bug U w PHP core.

Zapisany: `upstream-patch/session-upload-progress-counters.patch`

---

## 7. Wkład w wiedzę

1. **Empiryczne potwierdzenie**, że `allow_url_include` blokuje **tylko
   `include`/`require`**, a `file_get_contents` na wrapperach działa.
   To rzadko opisywane.
2. **Zmierzone granice** 9 alternatywnych wektorów — każdy z konkretnym
   powodem blokady, nie „nie udało się".
3. **Macierz sinków** — który wzorzec kodu przyjmie plik sesji, a który nie.
4. **Test na prawdziwym pluginie** z przełamaniem nonce — pokazuje, gdzie
   kończy się teoria a zaczyna rzeczywistość.

---

## 8. Uczciwa ocena końcowa

**CASE-004 NIE jest uniwersalnym RCE.** To technika działająca na
**konkretnej klasie aplikacji** — takich z `include($user)` bez sufiksu
i `cleanup=Off`.

**Nie nazywam tego sukcesem badawczym w sensie „znaleźliśmy 0-day".**
To rzetelnie udokumentowana technika z jawnymi ograniczeniami.

Wartość: mamy **działający, powtarzalny exploit** z pełną macierzą
warunków — czego brakuje większości opisów w sieci.

---

## Pliki

```
README.md              podstawy + mechanizm
VERDICT.md             ← ten plik
FINDINGS.md            macierz warunków
SINKS-MATRIX.md        3 potwierdzone wzorce sinków
REAL-PLUGIN-RESULT.md  WP Travel Engine 6.6.7 — blokada sufiksu
SINK-RESEARCH.md       research publicznych sinków
STRONG-VERSION.md      próba wzmocnienia — 7 ścieżek
EXPLORE-P1.md          /proc/self/fd + php://input
lab/                   custom PHP (działa)
lab-strong/            bez guardu wrapperów
sinks/laravel/         View::file pattern
sinks/wordpress-plugin/ wzorzec CWE-98
sinks/wp-travel-engine/evidence/  fragmenty prawdziwego pluginu
scripts/               6 exploitów (w tym generyczny)
```
