#
# partcad-thingiverse, 2026
#
# Licensed under Apache License, Version 2.0.
#
"""A PartCAD 'basic' repository plugin that serves Thingiverse things as parts.

Published as ``//pub/universe/thingiverse/models``. Nothing is listed: a part
is asked for by the thing's number, and is one file of that thing.

    763622                     the thing's best file (see remote_models.FORMATS)
    763622;format=stl          its best STL
    763622;file=1234567        one file, by its id
    763622;file=clip.stl       or by its name

Things are read through Thingiverse's REST API, which wants an app token: make
an app at https://www.thingiverse.com/apps/create and give its token to the
plugin as THINGIVERSE_TOKEN, or as the repository's 'token' parameter (see the
README). There is no way in without one that is not the site's own web app's:
its "Download all files" link is a page of that app now, not an archive, and
the token the app carries is the app's, not the user's.

PartCAD runs this script once per key (via runpy) with the key in
``request["key"]``; the answer goes in ``output``. What the keys mean, and
everything else that is the same for every model site, is in remote_models.py.
"""

import importlib.util
import os
import sys
import urllib.parse

# When this plugin's answers stopped meaning what they meant before. PartCAD
# keys everything it caches of this package on it, so raise it with any change
# to what is answered - here or in remote_models.py.
#
# v1: things as parts, one per file, read through the REST API; and 'login'.
# v2: a part's 'source' parameter, and the plugin's 'formats' and 'source' preferences;
#     'login' says what to do with nobody at the screen.
CACHE_VERSION = 2


def _shared():
    """remote_models.py, beside this script, under a name of this plugin's own."""
    name = "_partcad_thingiverse_remote_models"
    if name not in sys.modules:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "remote_models.py")
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


rm = _shared()

API = "https://api.thingiverse.com"
WEB = "https://www.thingiverse.com"


def thing_url(thing_id):
    return "%s/thing:%s" % (WEB, thing_id)


class Thingiverse(rm.Site):
    NAME = "thingiverse"
    TITLE = "Thingiverse"
    URL = WEB
    DESC = "Things on Thingiverse, a part per file, by the thing's number. Nothing is listed; search instead."
    VERSION = CACHE_VERSION
    LOGIN_INSTRUCTIONS = (
        "Thingiverse's API wants a token for everything. The simplest to make by hand is an App Token: sign in at "
        "https://www.thingiverse.com, create an app at https://www.thingiverse.com/apps/create (any name, a desktop "
        "app), and copy the App Token its page shows."
    )

    CREDENTIALS = {"token": "THINGIVERSE_TOKEN"}

    def __init__(self, request=None):
        super().__init__(request)
        self.token = rm.credential(self.request, "token", "THINGIVERSE_TOKEN")
        # The OAuth app PartCAD registers with Thingiverse, when it has: its
        # client id and the callback it registered. Not credentials - every
        # user of the package shares them - so they are the package's
        # parameters, set in its partcad.yaml.
        parameters = self.request.get("parameters") or {}
        self.client_id = str(parameters.get("client_id") or "").strip()
        self.redirect_uri = str(parameters.get("redirect_uri") or "").strip()

    # -- logging in --

    def whoami(self, credentials):
        token = credentials.get("token")
        if not token:
            return None
        status, me = self.http.probe(
            API + "/users/me", "who the Thingiverse token is", headers={"Authorization": "Bearer " + token}
        )
        if status in (401, 403):
            return None
        if status != 200 or not isinstance(me, dict):
            raise rm.SiteError("thingiverse: asking who the token is answered HTTP %d" % status)
        return me.get("name") or me.get("full_name") or "a Thingiverse user"

    def login_spec(self):
        # With nobody at the screen, the token has to be found by hand, and an
        # App Token is what a person can find: an OAuth grant's lives in the
        # address of a page that never loads.
        if self.client_id and self.redirect_uri and not self.non_interactive:
            # OAuth, implicit: Thingiverse sends the browser to the registered
            # callback with the token in the fragment. That page never has to
            # load; the extension reads the token off the address it was sent to.
            return {
                "url": "https://www.thingiverse.com/login/oauth/authorize?"
                + urllib.parse.urlencode(
                    {"client_id": self.client_id, "redirect_uri": self.redirect_uri, "response_type": "token"}
                ),
                "title": "Thingiverse",
                "capture": [{"name": "token", "redirect": {"url": self.redirect_uri + "*", "param": "access_token"}}],
                "guide": [
                    {
                        "url": "https://www.thingiverse.com/login*",
                        "selector": "input[type=email], input[name=username], input[type=text]",
                        "text": "Sign in to Thingiverse",
                    },
                    {
                        "url": "https://www.thingiverse.com/login/oauth/authorize*",
                        "selector": "button[type=submit], input[type=submit]",
                        "text": "Let PartCAD read your Thingiverse account",
                    },
                ],
            }
        # No app registered: the user's own. Thingiverse shows an app's token
        # on the app's page once it is made; it is pasted into the banner.
        return {
            "url": "https://www.thingiverse.com/apps/create",
            "title": "Thingiverse",
            "capture": [
                {
                    "name": "token",
                    "ask": {"label": "The App Token of the app you created", "secret": True},
                    "match": "^[A-Za-z0-9_-]{16,}$",
                }
            ],
            "guide": [
                {
                    # Not signed in, the key page sends the browser here first.
                    "url": "https://www.thingiverse.com/login*",
                    "selector": "input[type=email], input[name=username], input[type=text]",
                    "text": "Sign in to Thingiverse; you come back to the app page after",
                },
                {
                    # A sign-in button, by its text: a bare 'button' points at
                    # whatever button comes first ("Try again", on an error page).
                    "url": "https://www.thingiverse.com/*",
                    "selector": "button, a",
                    "contains": "^\\s*(log|sign) ?in\\s*$",
                    "text": "Sign in to Thingiverse",
                },
                {
                    "url": "https://www.thingiverse.com/apps/create*",
                    "selector": "form input[type=text], form input:not([type=hidden])",
                    "text": "Create an app (any name; type 'Web App'), then paste its App Token into the PartCAD bar",
                },
            ],
        }

    def valid_id(self, model_id):
        return model_id.isdigit()

    # -- the API --

    def api(self, path, what, ttl=rm.DAY):
        if not self.token:
            raise rm.NeedsCredentials(
                "thingiverse: %s needs a Thingiverse app token: make an app at "
                "https://www.thingiverse.com/apps/create and set THINGIVERSE_TOKEN, "
                "or the 'token' parameter of the repository (see the README)" % what
            )
        return self.http.json(API + path, what, headers={"Authorization": "Bearer " + self.token}, ttl=ttl)

    def model(self, model_id):
        thing = self.api("/things/%s" % model_id, "thing %s" % model_id)
        if not isinstance(thing, dict) or not thing.get("id"):
            raise rm.NotFound("thingiverse: thing %s: not found" % model_id)
        files = self.api("/things/%s/files" % model_id, "the files of thing %s" % model_id)
        if isinstance(files, dict):
            # Some answers wrap a list; take the one that is there.
            files = next((v for v in files.values() if isinstance(v, list)), [])
        return rm.Model(
            model_id,
            title=thing.get("name"),
            url=thing.get("public_url") or thing_url(model_id),
            author=(thing.get("creator") or {}).get("name"),
            license=thing.get("license"),
            files=[
                rm.File(
                    f.get("id"),
                    f.get("name") or str(f.get("id")),
                    size=f.get("size"),
                    direct_url=f.get("direct_url"),
                    download_url=f.get("download_url") or "%s/files/%s/download" % (API, f.get("id")),
                )
                for f in files or []
                if isinstance(f, dict) and f.get("id") is not None
            ],
        )

    def download(self, model, file):
        direct = file.extra.get("direct_url")
        if direct:
            try:
                return self.http.download(direct, "%s of thing %s" % (file.name, model.id))
            except rm.SiteError:
                pass  # the API's own link below, with the token, is the one that has to work
        return self.http.download(
            file.extra["download_url"],
            "%s of thing %s" % (file.name, model.id),
            headers={"Authorization": "Bearer " + self.token} if self.token else None,
        )

    def search(self, text, limit):
        answer = self.api(
            "/search/%s/?%s"
            % (
                urllib.parse.quote(text, safe=""),
                urllib.parse.urlencode({"type": "things", "per_page": limit, "page": 1, "sort": "relevant"}),
            ),
            "a search for '%s'" % text,
            ttl=600,
        )
        hits = answer.get("hits") if isinstance(answer, dict) else answer
        models = []
        for hit in hits or []:
            if not isinstance(hit, dict) or hit.get("id") is None:
                continue
            thing_id = str(hit["id"])
            models.append(
                rm.Model(
                    thing_id,
                    title=hit.get("name"),
                    url=hit.get("public_url") or thing_url(thing_id),
                    author=(hit.get("creator") or {}).get("name"),
                )
            )
        return models


def get(key):
    return rm.serve(Thingiverse(globals().get("request")), key)


# Last, so that everything above is defined when PartCAD runs this.
if __name__ == "get":
    output = {"result": get(request["key"])}  # noqa: F821 - injected by the runtime
elif __name__ == "login":
    output = {"result": rm.login(Thingiverse(globals().get("request")), globals().get("partcad_login"))}
else:
    output = {}
