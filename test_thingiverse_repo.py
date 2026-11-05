#
# partcad-thingiverse, 2026
#
# Licensed under Apache License, Version 2.0.
#
"""Tests of the Thingiverse plugin, with Thingiverse answered from a table.

The answers have the shape the REST API's have (things/<id>, things/<id>/files,
search/<term>); nothing here touches the network.
"""

import base64
import importlib.util
import json
import os
import runpy

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_PLUGIN = os.path.join(_HERE, "thingiverse_repo.py")
_SPEC = importlib.util.spec_from_file_location("thingiverse_repo_under_test", _PLUGIN)
plugin = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(plugin)
rm = plugin.rm

API = "https://api.thingiverse.com"

THING = {
    "id": 763622,
    "name": "Cable clip",
    "public_url": "https://www.thingiverse.com/thing:763622",
    "creator": {"name": "ann"},
    "license": "Creative Commons - Attribution",
    "files_url": API + "/things/763622/files",
}
FILES = [
    {
        "id": 1234567,
        "name": "clip.stl",
        "size": 1000,
        "direct_url": "https://cdn.thingiverse.com/assets/clip.stl",
        "download_url": API + "/files/1234567/download",
    },
    {
        "id": 1234568,
        "name": "clip_large.stl",
        "size": 2000,
        "direct_url": "https://cdn.thingiverse.com/assets/clip_large.stl",
        "download_url": API + "/files/1234568/download",
    },
    {"id": 1234569, "name": "clip.scad", "size": 300, "download_url": API + "/files/1234569/download"},
    {"id": 1234570, "name": "photo.jpg", "size": 300, "download_url": API + "/files/1234570/download"},
]


class Wire:
    """Answers requests from a table: {url: (status, body)}; remembers what was asked, and how."""

    def __init__(self, table):
        self.table = table
        self.asked = []

    def __call__(self, url, headers=None, data=None, method=None, timeout=60):
        self.asked.append((url, dict(headers or {})))
        if url not in self.table:
            return rm.Response(404, {}, b"not here", url)
        status, body = self.table[url]
        if not isinstance(body, bytes):
            body = json.dumps(body).encode()
        return rm.Response(status, {}, body, url)


def _site(table, token="secret", tmp_path=None, monkeypatch=None):
    monkeypatch.setenv("PARTCAD_THINGIVERSE_CACHE", str(tmp_path))
    monkeypatch.delenv("THINGIVERSE_TOKEN", raising=False)
    site = plugin.Thingiverse({"parameters": {"token": token}})
    wire = Wire(table)
    site.http.request = wire
    return site, wire


@pytest.fixture
def api(tmp_path, monkeypatch):
    table = {
        API + "/things/763622": (200, THING),
        API + "/things/763622/files": (200, FILES),
        "https://cdn.thingiverse.com/assets/clip.stl": (200, b"solid clip"),
        "https://cdn.thingiverse.com/assets/clip_large.stl": (200, b"solid large"),
        API + "/files/1234569/download": (200, b"cube(1);"),
    }
    return _site(table, tmp_path=tmp_path, monkeypatch=monkeypatch)


def test_a_thing_is_its_best_file(api):
    site, wire = api
    config = site.get("objects/part/763622")
    assert config["type"] == "stl"
    assert config["desc"] == "Cable clip: clip.stl"
    assert config["url"] == "https://www.thingiverse.com/thing:763622"
    assert config["author"] == "ann"
    assert config["license"] == "Creative Commons - Attribution"
    assert config["parameters"]["file"]["default"] == "1234567"
    # Asked with the token, as a bearer.
    assert wire.asked[0] == (API + "/things/763622", {"Authorization": "Bearer secret"})


def test_a_file_is_named_by_its_id_or_its_name(api):
    site, _ = api
    assert site.get("objects/part/763622;file=1234568")["desc"] == "Cable clip: clip_large.stl"
    assert site.get("objects/part/763622;file=clip_large.stl")["desc"] == "Cable clip: clip_large.stl"
    assert site.get("objects/part/763622;format=scad")["type"] == "scad"


def test_a_file_comes_from_the_cdn_without_the_token(api):
    site, wire = api
    path = site.get("objects/part/763622;file=1234567")["path"]
    assert base64.b64decode(site.get("files/" + path)) == b"solid clip"
    url, headers = wire.asked[-1]
    assert url == "https://cdn.thingiverse.com/assets/clip.stl"
    assert "Authorization" not in headers


def test_a_file_with_no_cdn_link_comes_through_the_api_with_the_token(api):
    site, wire = api
    path = site.get("objects/part/763622;format=scad")["path"]
    assert base64.b64decode(site.get("files/" + path)) == b"cube(1);"
    assert wire.asked[-1] == (API + "/files/1234569/download", {"Authorization": "Bearer secret"})


def test_a_search_names_a_part_per_file(api):
    site, wire = api
    site.http.request.table[API + "/search/cable%20clip/?type=things&per_page=60&page=1&sort=relevant"] = (
        200,
        {"total": 1, "hits": [{"id": 763622, "name": "Cable clip", "public_url": THING["public_url"]}]},
    )
    hits = site.get("search/part?q=cable+clip")
    # clip.stl, clip_large.stl and clip.scad are three parts; clip.scad and
    # clip.stl share a stem, so they are one part, and the STL is the better.
    assert list(hits) == ["763622;file=1234567", "763622;file=1234568"]
    assert hits["763622;file=1234567"]["type"] == "stl"


def test_the_list_answer_of_an_older_api_is_read_too(api):
    site, _ = api
    site.http.request.table[API + "/search/clip/?type=things&per_page=15&page=1&sort=relevant"] = (
        200,
        [{"id": 763622, "name": "Cable clip"}],
    )
    assert list(site.get("search/part?q=clip&limit=5"))[0] == "763622;file=1234567"


def test_without_a_token_a_search_says_what_it_needs(tmp_path, monkeypatch, capsys):
    site, wire = _site({}, token="", tmp_path=tmp_path, monkeypatch=monkeypatch)
    assert rm.serve(site, "search/part?q=clip") is None
    assert "needs a Thingiverse app token" in capsys.readouterr().err
    assert wire.asked == []


def test_without_a_token_a_thing_says_what_it_needs(tmp_path, monkeypatch, capsys):
    site, wire = _site({}, token="", tmp_path=tmp_path, monkeypatch=monkeypatch)
    assert rm.serve(site, "objects/part/763622") is None
    assert "thing 763622 needs a Thingiverse app token" in capsys.readouterr().err
    assert wire.asked == []


def test_the_environment_is_where_the_token_comes_from_by_default(tmp_path, monkeypatch):
    monkeypatch.setenv("THINGIVERSE_TOKEN", "from-env")
    assert plugin.Thingiverse({"parameters": {"token": ""}}).token == "from-env"


def test_partcad_runs_it_and_reads_the_answer_from_output():
    """The runpy contract: 'request' in, 'output' out, with the key PartCAD asked."""
    result = runpy.run_path(_PLUGIN, init_globals={"request": {"key": "meta", "parameters": {}}}, run_name="get")
    meta = result["output"]["result"]
    assert meta["manufacturable"] is False
    assert meta["searchKinds"] == ["part"] and meta["instanceKinds"] == ["part"]


def test_the_cache_version_is_a_literal_partcad_can_read():
    with open(_PLUGIN) as f:
        assert any(line.startswith("CACHE_VERSION = ") and line.split("=")[1].strip().isdigit() for line in f)


def test_the_shared_module_is_the_one_every_model_site_plugin_has():
    """remote_models.py is byte for byte the same in all four plugins; a stray edit shows up here."""
    import hashlib

    with open(os.path.join(_HERE, "remote_models.py"), "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    with open(os.path.join(_HERE, "remote_models.sha256")) as f:
        assert digest == f.read().split()[0], "remote_models.py differs from the shared copy: update all five"


# --- logging in ----------------------------------------------------------------


def test_a_token_is_checked_by_asking_who_it_is(api):
    site, wire = api
    wire.table[API + "/users/me"] = (200, {"name": "ann", "id": 1})
    assert site.whoami({"token": "secret"}) == "ann"
    assert wire.asked[-1] == (API + "/users/me", {"Authorization": "Bearer secret"})
    wire.table[API + "/users/me"] = (401, {"error": "Unauthorized"})
    assert site.whoami({"token": "stale"}) is None


def test_without_an_oauth_app_the_login_asks_for_the_users_own_app_token(api):
    site, _ = api
    spec = site.login_spec()
    assert spec["url"] == "https://www.thingiverse.com/apps/create"
    assert spec["capture"][0]["name"] == "token" and "ask" in spec["capture"][0]


def test_with_partcads_oauth_app_the_login_is_an_implicit_grant(tmp_path, monkeypatch):
    monkeypatch.delenv("THINGIVERSE_TOKEN", raising=False)
    site = plugin.Thingiverse(
        {"parameters": {"token": "", "client_id": "abc", "redirect_uri": "http://127.0.0.1/partcad/login/thingiverse"}}
    )
    spec = site.login_spec()
    assert spec["url"].startswith("https://www.thingiverse.com/login/oauth/authorize?")
    assert "client_id=abc" in spec["url"] and "response_type=token" in spec["url"]
    assert spec["capture"] == [
        {"name": "token", "redirect": {"url": "http://127.0.0.1/partcad/login/thingiverse*", "param": "access_token"}}
    ]


class _BrowserNeeded(BaseException):
    pass


class _Callback:
    def open_browser(self, **spec):
        raise _BrowserNeeded(spec)


def test_partcad_runs_its_login_and_it_asks_for_the_browser(monkeypatch):
    """The runpy contract of 'login': with no token, the callback is called, and its signal passes through."""
    monkeypatch.delenv("THINGIVERSE_TOKEN", raising=False)
    with pytest.raises(_BrowserNeeded) as needed:
        runpy.run_path(
            _PLUGIN,
            init_globals={"request": {"api": "login", "parameters": {"token": ""}}, "partcad_login": _Callback()},
            run_name="login",
        )
    assert needed.value.args[0]["title"] == "Thingiverse"


class _AgentCallback(_Callback):
    non_interactive = True


def test_with_nobody_at_the_screen_the_login_asks_for_an_app_token_and_says_how_to_make_one(monkeypatch):
    """An OAuth grant's token is in the address of a page that never loads: no good to find by hand."""
    monkeypatch.delenv("THINGIVERSE_TOKEN", raising=False)
    parameters = {"token": "", "client_id": "abc", "redirect_uri": "http://127.0.0.1/partcad/login/thingiverse"}
    with pytest.raises(_BrowserNeeded) as needed:
        runpy.run_path(
            _PLUGIN,
            init_globals={"request": {"api": "login", "parameters": parameters}, "partcad_login": _AgentCallback()},
            run_name="login",
        )
    spec = needed.value.args[0]
    assert spec["url"] == "https://www.thingiverse.com/apps/create"
    assert "copy the App Token" in spec["instructions"] and "THINGIVERSE_TOKEN" in spec["instructions"]
