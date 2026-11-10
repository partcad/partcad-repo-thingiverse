# Thingiverse for PartCAD

Serves Thingiverse's models as PartCAD parts, published as
`//pub/collection/thingiverse/models`.

**Nothing is listed.** A model site's catalog is not something to enumerate,
so `pc list parts` of this package is empty, as is `pc list packages`. A part is
asked for by name, and found with `pc search parts`:

```shell
pc search parts -P //pub/collection/thingiverse/models -k "cable clip"
pc inspect "//pub/collection/thingiverse/models:763622"
```

**No geometry is vendored.** Every file is fetched from Thingiverse the first
time a part is built, and kept by PartCAD from then on.

**Nothing here is manufacturable.** The package says `manufacturable: false`,
and so does the plugin of what it serves: an upload to a model site says
nothing about whether, or how, it is made to be made.

Requires PartCAD 0.9.20 or newer, the first release with the toolkit the plugin
is written with (`plugin_models`). 0.9.3 was the first release whose repository plugins
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

Both may be given, and must then agree; a third, `source`, and the plugin's
own `formats` are under [Parameters](#parameters). "Best" is by format, in
this order unless `formats` says otherwise, and among files of one format the first the site lists:

| Format | Read as PartCAD part type | Extensions |
| --- | --- | --- |
| `step` | `step` | `.step`, `.stp` |
| `brep` | `brep` | `.brep`, `.brp` |
| `iges` | `iges` | `.iges`, `.igs` |
| `3mf` | `3mf` | `.3mf` |
| `stl` | `stl` | `.stl` |
| `obj` | `obj` | `.obj` |
| `glb` | `gltf` | `.glb` |
| `usd` | `usd` | `.usdz`, `.usd`, `.usdc`, `.usda` |
| `sldprt` | `sldprt` | `.sldprt` |
| `ipt` | `ipt` | `.ipt` |
| `catpart` | `catpart` | `.catpart` |
| `f3d` | `f3d` | `.f3d` |
| `fcstd` | `fcstd` | `.fcstd` |
| `sat` | `sat` | `.sat`, `.sab` |
| `pvz` | `pvz` | `.pvz` |
| `scad` | `scad` | `.scad` |

An exact boundary representation beats a mesh of it, and 3MF knows its units
where STL does not. A `.gltf` is not served, since the buffers it names beside
itself do not come with it. IGES is exact too, after STEP and BREP; OpenUSD - a
`.usdz`, a stage packed with its textures - comes after glTF; and the native
documents of CAD applications (SolidWorks, Inventor, CATIA, Fusion, FreeCAD,
ACIS, Creo View), which PartCAD reads through a converter it downloads on first
use, come after the meshes, to be taken when a model has nothing else or when
asked for. An OpenSCAD source is last, because on a model site
it is usually the customizable source of the meshes beside it. A file in any
other format - SketchUp, Blender, AMF, a picture - is not a part. A name
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
pc login //pub/collection/thingiverse:thingiverse_repo
```

checks the token the plugin has by asking Thingiverse whom it belongs to
(`/users/me`), and keeps it if Thingiverse still takes it. Otherwise it opens
your default browser, in PartCAD's own profile with PartCAD's extension in it:

- **Without an OAuth app**, which is how it is unless you register one, on
  <https://www.thingiverse.com/apps/create>, pointing at the form: make an app
  (any name, a "Web App"), and paste its **App Token** into the PartCAD bar at
  the top of the page.
- **With an OAuth app of your own** - registered at
  <https://www.thingiverse.com/apps/create> with a callback URL, and its
  `client_id` and `redirect_uri` set in your `~/.partcad/config.yaml` like the
  token below - on Thingiverse's authorization page. Sign in and allow it;
  Thingiverse sends the browser to the registered callback with a token in the
  address (an implicit grant: no client secret is involved), and the extension
  reads it off the address. The callback page never has to load.

PartCAD registers no app with Thingiverse: the credentials, an App Token or an
OAuth app, are yours to provide.

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
  "//pub/collection/thingiverse:thingiverse_repo":
    token: "..."
```

`pc --extra-param "//pub/collection/thingiverse:thingiverse_repo.token=..."` does
the same for one command. The token is sent to `api.thingiverse.com` as a bearer
token, and to nothing else: a download is taken from the file's CDN link without
it, and a redirect to another host drops it.

**Docker.** PartCAD runs a plugin in its Python sandbox, and the `docker` sandbox
does not carry PartCAD's environment into its container, so an environment
variable does not reach the plugin there. The repository parameter does, being
part of what PartCAD hands the plugin; use that, or `pythonSandbox: venv`.

## Parameters

The plugin's parameters, declared in `partcad.yaml`, are a default for every
Thingiverse part:

| Parameter | Default | What it is |
| --- | --- | --- |
| `formats` | all, in the order above | The formats to take a thing in, best first, separated by commas. A format left out is not taken - `stl,3mf` is meshes only - unless a part asks for it by its own `format` or `file`. |
| `source` | `auto` | Which of a thing's files: Thingiverse has no preview meshes of its own, so `auto` and `original` are the same here and `preview` finds nothing. |
| `token` | empty | An App Token of an app of your own, or the token an OAuth app was granted. Thingiverse's API wants it for everything. `THINGIVERSE_TOKEN` gives it too. |
| `client_id` | empty | An OAuth app of your own for `pc login` to sign in with instead of asking for an App Token: register one at https://www.thingiverse.com/apps/create and set this, with `redirect_uri`, in your own configuration. PartCAD registers no app. |
| `redirect_uri` | empty | The callback URL registered with that app. It is never loaded. |

They are yours to set without touching this package - every one of them, the
credentials included, and the OAuth or API-key settings beside them:

- in your own `~/.partcad/config.yaml`, by the plugin's name, which is where
  `pc login` keeps the credentials:

  ```yaml
  parameters:
    "//pub/collection/thingiverse:thingiverse_repo":
      formats: stl,3mf
  ```

- or, for anything but the credentials, in a package of your own, as an enrich
  of the plugin and a package it serves - `//thingiverse_meshes:<thing>` in a
  package at the root:

  ```yaml
  repositories:
    meshes_repo:
      type: enrich
      source: //pub/collection/thingiverse:thingiverse_repo
      with:
        formats: stl,3mf
  dependencies:
    thingiverse_meshes:
      type: external
      plugin: :meshes_repo
  ```

A part's own `file`, `format` and `source` override them for that part - in its
name (`763622;format=stl`), or in the `with` of an enrich of the part:

```yaml
parts:
  clip:
    type: enrich
    source: //pub/collection/thingiverse/models:763622
    with:
      format: stl
```

PartCAD keys what it caches of this package on your overrides of the plugin's
parameters, so a change to one - logging in, too - takes effect at once. An
environment variable is not seen there: after setting one, `pc update`
refreshes what was cached without it.

## Logging in with nobody at the screen

An AI agent, or a script, logs in without a browser:

```shell
pc login --agent //pub/collection/thingiverse:thingiverse_repo
pc login --agent --set token=... //pub/collection/thingiverse:thingiverse_repo
```

The first prints what a person would do in the browser instead of opening one -
where to sign in, what to copy, and the command that hands it over - and exits
with status 3. It asks for an App Token, never the OAuth grant (whose token lives in the address of a page that never loads), and says how to make one. The second hands over what the person found; the
plugin checks it with Thingiverse before PartCAD keeps it. `pc mcp`'s `login`
tool works the same way.

## Status

Written against Thingiverse's REST API (`things/<id>`, `things/<id>/files`,
`search/<term>`) and tested against answers of that shape (see
`test_thingiverse_repo.py`). It has not been run against the live API with a
token: from where it was written, without one, `www.thingiverse.com` served its
web app and `api.thingiverse.com` a Cloudflare bot check. A bot check is
reported as one, with nothing tried to get past it.

`pc login` was run against the live site in a real (headed) Chrome with
PartCAD's extension: the app page sends a visitor to Thingiverse's sign-in,
which the guide covers, but from where it was tested Thingiverse's own web app
answered with its "Something went wrong" page, so the rest - and the OAuth
flow, which needs an OAuth app of the user's own - was not seen live.

## Layout

| Path | Purpose |
| --- | --- |
| `partcad.yaml` | `//pub/collection/thingiverse`; the `models` external dependency and the `thingiverse_repo` repository that serves it. |
| `thingiverse_repo.py` | The repository plugin: how Thingiverse is asked. |
| `test_*.py`, `conftest.py` | The tests. Nothing in them touches the network. They need PartCAD installed: the plugin imports its toolkit, `plugin_models`, from PartCAD's wrappers. |

```shell
python -m pytest
```

What every model-site plugin shares - the names, the formats, HTTP and its
cache, the keys PartCAD asks - is PartCAD's own toolkit, `plugin_models`, one
of its wrappers (PartCAD 0.9.20 and later), which the plugin imports wherever
PartCAD runs it.

When what the plugin answers changes - here, or in the `plugin_models` of a new
PartCAD - raise
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
