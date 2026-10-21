# Demo

## `php2shell-demo.mp4` — 60 s, 1920×1080

A walkthrough of the mechanism and a **real capture** of the attack:

| Time | Beat |
|---|---|
| 0:00 | The multipart field name is the vector |
| 0:07 | Field name → session-file key, `/tmp/sess_<sid>` |
| 0:18 | **Real asciinema capture**: build lab → poison → session dump → `uid=0(root)` → reverse shell |
| 0:34 | The six conditions (three are not default) |
| 0:46 | Nine measured dead ends; "not universal RCE, an LFI amplifier" |
| 0:55 | Mitigation, and the actual bug: the `include()` |

The terminal segment is an **unmodified asciinema recording** — it is evidence, not a
re-enactment. The source cast is in `asciinema.cast` and can be replayed with
`asciinema play asciinema.cast`.

## Reproducing the capture

```bash
asciinema rec -c "bash demo/record-demo.sh" my.cast
```

The recording shows: `docker build`, poison, session-file dump, and a reverse shell
landing as `root@<container>:/app#`.
