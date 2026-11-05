# Thingiverse for PartCAD

Serves Thingiverse's models as PartCAD parts, published as
`//pub/universe/thingiverse/models`.

**Nothing is listed.** A model site's catalog is not something to enumerate,
so `pc list parts` of this package is empty, as is `pc list packages`. A part is
asked for by name, and found with `pc search parts`:

```shell
pc search parts -P //pub/universe/thingiverse/models -k "cable clip"
pc inspect "//pub/universe/thingiverse/models:763622"
```

**No geometry is vendored.** Every file is fetched from Thingiverse the first
time a part is built, and kept by PartCAD from then on.

**Nothing here is manufacturable.** The package says `manufacturable: false`,
and so does the plugin of what it serves: an upload to a model site says
nothing about whether, or how, it is made to be made.

Requires PartCAD 0.9.3 or newer: the first release whose repository plugins
may search their own catalog (`searchKinds`), resolve a parametrized name
themselves (`instanceKinds`), and log in (`pc login`). They are described under
"Repositories" and "Logging in" in PartCAD's plugin documentation.

## Names

A model is a part per file of it that PartCAD reads, and the name says which.
A model is named by the thing's number, as in `thingiverse.com/thing:763622`:

| Name | Is |
| --- | --- |
| `763622` | the model's best file |
| `763622;format=stl` | its best STL |
| `763622;file=<id>` | one file, by its id on Thingiverse |
| `763622;file=<name>` | one file, by its name |

Both parameters may be given, and must then agree. "Best" is by format, in
this order, and among files of one format the first the site lists:

| Format | Read as PartCAD part type | Extensions |
| --- | --- | --- |
| `step` | `step` | `.step`, `.stp` |
| `brep` | `brep` | `.brep`, `.brp` |
| `3mf` | `3mf` | `.3mf` |
| `stl` | `stl` | `.stl` |
| `obj` | `obj` | `.obj` |
| `glb` | `gltf` | `.glb` |
| `scad` | `scad` | `.scad` |

An exact boundary representation beats a mesh of it, and 3MF knows its units
where STL does not. A `.gltf` is not served, since the buffers it names beside
itself do not come with it; an OpenSCAD source is last, because on a model site
it is usually the customizable source of the meshes beside it. A file in any
other format - IGES, SolidWorks, Fusion, a picture - is not a part. A name
that asks for one, or for a file the model has not got, is not found, and the
plugin says why.

These names are resolved by the plugin rather than by PartCAD applying the
parameters to a base part, because another file is another `path` and maybe
another `type`. `pc info` of a part shows the `file` and `format` it resolved
to, which is what to write to pin it: the best file of a model can change when
its designer uploads another.

## Search

`pc search parts -k <words>` asks Thingiverse's own search, and answers with
names of the form above - one per file, so a hit is everything needed to fetch
its geometry. Two files that differ only in their extension (`clip.step`,
`clip.stl`) are one part in two formats, and only the better is named; a model
with no file PartCAD reads is not a hit. `--limit` caps the hits (20 by
default); the plugin asks the site for three times as many models, and reads
their file lists a few at a time until it has enough.

A search is never cached by PartCAD; the plugin keeps what the site answered for
ten minutes.

## Logging in

```shell
pc login //pub/universe/thingiverse:thingiverse_repo
```

checks the token the plugin has by asking Thingiverse whom it belongs to
(`/users/me`), and keeps it if Thingiverse still takes it. Otherwise it opens
your default browser, in PartCAD's own profile with PartCAD's extension in it:

- **With PartCAD's OAuth app** - once `client_id` and `redirect_uri` are set in
  this package's `partcad.yaml` - on Thingiverse's authorization page. Sign in
  and allow it; Thingiverse sends the browser to the registered callback with a
  token in the address (an implicit grant: no client secret is involved, which
  is what lets a public plugin use it), and the extension reads it off the
  address. The callback page never has to load.
- **Until then**, on <https://www.thingiverse.com/apps/create>, pointing at the
  form: make an app (any name, a "Web App"), and paste its **App Token** into
  the PartCAD bar at the top of the page.

The token is saved in your `~/.partcad/config.yaml` as your override of the
repository's `token` parameter, which is where every later command reads it
from. `pc login --check ...` only checks it.

## Credentials, by hand

Thingiverse's REST API wants an app token for everything: make an app at
<https://www.thingiverse.com/apps/create> (a "Web App" is enough) and copy its
**App Token**. There is no way in without one that is not the site's own web
app's: its "Download all files" link is a page of that app now rather than an
archive, and the token the app carries is the app's, not yours.

Give it to the plugin either way, never in a package:

```shell
export THINGIVERSE_TOKEN=...      # read by the plugin; see the note on Docker below
```

```yaml
# ~/.partcad/config.yaml
parameters:
  "//pub/universe/thingiverse:thingiverse_repo":
    token: "..."
```

`pc --extra-param "//pub/universe/thingiverse:thingiverse_repo.token=..."` does
the same for one command. The token is sent to `api.thingiverse.com` as a bearer
token, and to nothing else: a download is taken from the file's CDN link without
it, and a redirect to another host drops it.

**Docker.** PartCAD runs a plugin in its Python sandbox, and the `docker` sandbox
does not carry PartCAD's environment into its container, so an environment
variable does not reach the plugin there. The repository parameter does, being
part of what PartCAD hands the plugin; use that, or `pythonSandbox: venv`.

## Status

Written against Thingiverse's REST API (`things/<id>`, `things/<id>/files`,
`search/<term>`) and tested against answers of that shape (see
`test_thingiverse_repo.py`). It has not been run against the live API with a
token: from where it was written, without one, `www.thingiverse.com` served its
web app and `api.thingiverse.com` a Cloudflare bot check. A bot check is
reported as one, with nothing tried to get past it.

## Layout

| Path | Purpose |
| --- | --- |
| `partcad.yaml` | `//pub/universe/thingiverse`; the `models` external dependency and the `thingiverse_repo` repository that serves it. |
| `thingiverse_repo.py` | The repository plugin: how Thingiverse is asked. |
| `remote_models.py` | What every model-site plugin shares, byte for byte: the names, the formats, HTTP and its cache, the keys PartCAD asks. The same file is in partcad-repo-thingiverse, partcad-repo-makerworld, partcad-repo-grabcad, partcad-repo-printables and partcad-repo-cults3d; `remote_models.sha256` is its digest, and a test fails when the two disagree - change it in all five. |
| `test_*.py` | The tests. Nothing in them touches the network. |

```shell
python -m pytest
```

When what the plugin answers changes - here or in `remote_models.py` - raise
`CACHE_VERSION` in `thingiverse_repo.py`: PartCAD keys everything it caches of this
package on it.

## Caching

PartCAD keeps every answer the plugin gives, files included, under its own
cache, apart from a search. The plugin keeps what Thingiverse answered under
`~/.cache/partcad-thingiverse/` (or `$PARTCAD_THINGIVERSE_CACHE`): a model's details for
a day, a search for ten minutes, and a request that came to nothing for a while
too, so that a refused or throttled run is not repeated in full by the next one
- a 404 for a day, anything else for five minutes. Delete the directory to start
over.

Every request says what it is: `User-Agent: Mozilla/5.0 (compatible;
PartCAD-thingiverse/<version>; +https://github.com/partcad/partcad-repo-thingiverse)`.

## Licensing

The code here is Apache-2.0 (`LICENSE`). Each thing carries its own licence, which the part states (`license`); it is the designer's, not this package's. Thingiverse's terms of use
are at <https://www.thingiverse.com/legal>.
