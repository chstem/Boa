# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from importlib import import_module
from ..modules import config

if not config.components.enable or config.components.enable == 'none':
    components_loaded = []
elif config.components.enable == 'all':
    components_loaded = config.components.components_list
elif config.components.enable == 'main':
    components_loaded = ['BoA_online', 'manage_participants', 'manage_abstracts', 'manage_sessions', 'MassMail', 'tools']
else:
    components_loaded = [c for c in config.components.enable if c in config.components.components_list]

def load(app):

    if not config.components.enable:
        return

    # import modules by given string and register blueprints
    for comp in components_loaded:
        mod = import_module('.'+comp, __name__)
        app.register_blueprint(mod.blueprint)
