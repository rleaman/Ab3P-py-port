# Minimal Linux MedPost path probe

The saved Linux run qualified the supplied sanity corpus, but its runner could
not fingerprint `BioC_C++_1.1/MedPost`. It did not record `MEDPOST_HOME`,
`path_medpost` or the executable's compiled default. Saved development output
matches Python segmentation without the bundled `.abbr` list on the `St.` and
`subsp.` cases. This package asks which data path the pinned executable really
used and for one direct execution of three reduced inputs. It does not change
the frozen corpus, retrain a model or require a rebuild.

Input SHA-256 is recorded in `input.sha256`. The returned phase 2 executable
SHA-256 is `ffe44acd5946ab37b614811e274ac89b5c4ff946eda7088454456a50f07f23bb`;
source tree SHA-256 is `e38b3f57c6a5b8f94e29b39033f89259e46336da7e33ff028d73ab3ad587ddd6`;
WordData tree SHA-256 is
`d45ba9b0400aa59e15f5f0d6bd9f5ed00de1be5ae47426b0b29c2806ec3e522e`.
The original source `iret/Makefile` defines
`DEFAULT_MEDPOST_HOME="../MedPost"`; `iret/MPtok.C` can override it through
`MEDPOST_HOME` or `path_medpost`.

On Linux, set `APP` to the actual `BioC-APPL-ABBR` directory and `PROBE` to
this unpacked directory, then run exactly:

```bash
APP=/absolute/path/to/BioC_C++_1.1/BioC-APPL-ABBR
PROBE=/absolute/path/to/medpost_probe_v1
sha256sum "$APP/abbr" "$PROBE/input.xml"
printf 'MEDPOST_HOME=%s\n' "${MEDPOST_HOME-<unset>}"
if test -f "$APP/path_medpost"; then cat "$APP/path_medpost"; else printf 'path_medpost absent\n'; fi
if test -d "$APP/../MedPost"; then find "$APP/../MedPost" -maxdepth 1 -type f -name 'medpost.*' -print; else printf 'app.parent/MedPost absent\n'; fi
(cd "$APP" && ./abbr "$PROBE/input.xml" > "$PROBE/cpp_output.xml" 2> "$PROBE/cpp_stderr.txt")
sha256sum "$PROBE/cpp_output.xml" "$PROBE/cpp_stderr.txt"
```

If `strace` is available, also run from `APP`:

```bash
(cd "$APP" && strace -f -e trace=openat -o "$PROBE/openat.txt" ./abbr "$PROBE/input.xml" > "$PROBE/strace_output.xml" 2> "$PROBE/strace_stderr.txt")
```

Return `cpp_output.xml`, `cpp_stderr.txt`, the command exit code, the printed
path/environment information and, if available, `openat.txt`. The requested
trace fields are the attempted `medpost.abbr` and `medpost.pairs` paths and
open results; full system traces can be narrowed to those filenames before
return. Do not include unrelated environment variables or credentials.
The `MEDPOST_CONTROL` article checks the executable still extracts an ordinary
pair. The two other articles distinguish sentence behavior. This is an
executed-oracle check only after these files are returned; current expectations
are source and saved-output inferences.
