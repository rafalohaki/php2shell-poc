# php2shell-8512 — RCE on fully-patched PHP 8.5.12

Two variants. Both work. The race variant works on stock session config.

| Variant | `cleanup` setting | Mechanism | Script |
|---|---|---|---|
| base | Off (non-default) | inject, wait, read | `exploit/php2shell_8512.py` |
| **race** | **On (default)** | slow upload + concurrent read | `exploit/php2shell_8512_race.py` |

Both produce `uid=33(www-data)` on PHP 8.5.12 (the 2026-10-21 security
release that fixed CVE-2026-109618/109619). No memory corruption. No ASLR
bypass. Pure session-handling logic bug.

## The bug

`ext/session/session.c:3267-3268` on php-8.5.12:

```c
smart_str_append(&progress->key, PS(rfc1867_prefix));
smart_str_appendl(&progress->key, *data->value, value_len);
```

The rfc1867 hook writes the raw `PHP_SESSION_UPLOAD_PROGRESS` multipart
field value into the session key. No grammar check. Before any script runs.

When the session file is written with `php_serialize` and read with `php`
(a handler mismatch — see preconditions below), the decoder treats the
`inj|` inside that key as its own `key|value` separator. The serialized
object after the pipe lands at a value position. `unserialize()` fires.
The object's `__destruct` runs — either when PHP destroys the half-decoded
session ("Session has been destroyed" does not prevent this), or at
teardown.

## Preconditions

1. `session.serialize_handler` mismatch: write side `php_serialize`
   (set via ini, vhost, per-dir `php_value` — this is the *recommended*
   config in PHP docs), read side `php` (legacy shim, app `ini_set`,
   or a different per-dir scope).

2. A destructor gadget reachable in the reading script's scope. Any class
   whose `__destruct` has a side effect (file write, `system()`, network).
   Common in real code: cache writers, log flushers, temp-file cleaners.

3. `session.upload_progress.enabled=On` — this is the default.

That's it for the race variant. `cleanup=On` (default), `strict_mode=On`
(default), `min_freq` default — all fine. The base variant additionally
needs `cleanup=Off`.

## Race variant: how it beats cleanup

`cleanup=On` deletes the upload-progress key at `MULTIPART_EVENT_END`.
But the key is written at `FILE_START`, and the cleanup only runs when the
multipart body finishes parsing. A slow upload (128 KB chunks at 0.5s
intervals) keeps the body incomplete for ~16 seconds. During that window,
the poisoned key is already in the session file. Any concurrent read with
the `php` handler hits it.

`evidence/window-proof.log` shows the falsification test: same payload,
fast upload (0.00s) produces no exec because cleanup completes first;
slow upload + mid-read produces exec. The window is real.

## Test matrix

From `evidence/matrix.log` — all on PHP 8.5.12, Apache 2.4 prefork
+ mod_php, 5 runs each (3 for cmdexec), session wiped between runs:

```
victim/ (custom ini)            cleanup=Off  1 worker   DeferredWriter  5/5
victim-stock/ (all stock)       cleanup=On   1 worker   DeferredWriter  5/5
victim-bare/ (.htaccess only)   cleanup=On   1 worker   DeferredWriter  5/5
victim-bare/ + mpm-multi        cleanup=On   4-16 wkrs  DeferredWriter  5/5
victim-cmdexec/                 cleanup=On   1 worker   CmdExec         3/3
```

`victim-bare/` has zero custom session ini — the handler mismatch is set
via `.htaccess php_value` (per-directory pattern). `victim-cmdexec/` uses
a gadget that calls `system($cmd)` in the destructor directly, no webshell
file written.

Negative control (`evidence/race-stock.log`): fresh server-issued SID, no
injection, read `legacy.php` — `grep -c uid=` returns 0.

## Quickstart

```bash
# stock victim (cleanup=On, all defaults except save_path)
docker run -d --name vic --network <net> --network-alias vic \
  -v "$PWD/victim-stock/php.ini:/usr/local/etc/php/conf.d/zz.ini:ro" \
  -v "$PWD/victim-stock/html:/var/www/html" p2s-official:8.5.12
docker exec vic sh -c 'mkdir -p /var/www/sess; chmod 1777 /var/www/sess;
  chown -R www-data:www-data /var/www/sess /var/www/html'

# race variant (works on stock config)
python3 exploit/php2shell_8512_race.py vic 80 --cmd id

# base variant (needs cleanup=Off — see victim/php.ini)
python3 exploit/php2shell_8512.py vic 80

# verify the window yourself
python3 verify_window.py
```

## Files

```
exploit/php2shell_8512.py           base variant (cleanup=Off)
exploit/php2shell_8512_race.py      race variant (cleanup=On, stock)
exploit/php2shell_8512_race_cmdexec.py  race + system() gadget (no webshell)
verify_window.py                    falsification test (fast vs slow upload)
victim/                             cleanup=Off lab
victim-stock/                       all-stock session config
victim-bare/                        .htaccess-only mismatch, no custom ini
victim-bare/mpm-multi.conf          multi-worker prefork (4-16)
victim-cmdexec/                     CmdExec gadget (direct system(), no file)
evidence/race-stock.log             5/5 runs + config dump + negative control
evidence/window-proof.log           fast-vs-slow falsification
evidence/matrix.log                 full test matrix
demo/php2shell-8512-demo.mp4        33s video (base variant)
```

## Credits

Technique family: Zero1 "session-gaps" from jackalsyn's php2shell-zeros
(2026-10-21). The serialize_handler mismatch injection class is public
since the mid-2010s. The race-vs-cleanup shape is from the same package
(T3). This repo contains an independent implementation; every claim was
verified against a local build of PHP 8.5.12 from the official tarball.
The class is known upstream under GH-20001. No CVE filed as of 2026-10-22.

For authorised testing only.
