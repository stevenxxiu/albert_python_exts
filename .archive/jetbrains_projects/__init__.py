# -*- coding: utf-8 -*-

"""List and open JetBrains IDE projects."""

#  Copyright (c) 2022 Manuel Schneider

import os
from shutil import which
from xml.etree import ElementTree

from albertv0 import *

__iid__ = "PythonInterface/v0.1"
__prettyname__ = "Jetbrains IDE Projects"
__version__ = "1.3"
__trigger__ = "jb "
__author__ = "Markus Richter, Thomas Queste"
__dependencies__ = []

default_icon = os.path.dirname(__file__) + "/jetbrains.svg"
HOME_DIR = os.environ["HOME"]
JETBRAINS_XDG_CONFIG_DIR = os.path.join(HOME_DIR, ".config/JetBrains")

paths = [  # <Name for config directory>, <possible names for the binary/icon>
    ["AndroidStudio", "android-studio"],
    ["CLion", "clion"],
    ["DataGrip", "datagrip"],
    ["GoLand", "goland"],
    ["IntelliJIdea",
     "intellij-idea-ue-bundled-jre intellij-idea-ultimate-edition idea-ce-eap idea-ue-eap idea idea-ultimate"],
    ["PhpStorm", "phpstorm"],
    ["PyCharm", "pycharm pycharm-eap charm"],
    ["RubyMine", "rubymine jetbrains-rubymine jetbrains-rubymine-eap"],
    ["WebStorm", "webstorm"],
]


# find the executable path and icon of a program described by space-separated lists of possible binary-names
def find_exec(namestr: str):
    for name in namestr.split(" "):
        executable = which(name)
        if executable:
            icon = iconLookup(name) or default_icon
            return executable, icon
    return None


# parse the xml at path, return all recent project paths and the time they were last open
def get_proj(path):
    r = ElementTree.parse(path).getroot()  # type:ElementTree.Element
    add_info = None
    items = dict()
    for o in r[0]:  # type:ElementTree.Element
        if o.attrib["name"] == 'recentPaths':
            for i in o[0]:
                items[i.attrib["value"]] = 0

        else:
            if o.attrib["name"] == 'additionalInfo':
                add_info = o[0]

    if len(items) == 0:
        return []

    if add_info is not None:
        for i in add_info:
            for o in i[0][0]:
                if o.tag == 'option' and 'name' in o.attrib and o.attrib["name"] == 'projectOpenTimestamp':
                    items[i.attrib["key"]] = int(o.attrib["value"])
    return [(items[e], e.replace("$USER_HOME$", HOME_DIR)) for e in items]


def handleQuery(query):
    if query.isTriggered:
        binaries = {}
        projects = []

        for app in paths:
            config_path = "options/recentProjects.xml"

            full_config_path = None

            # newer versions (since 2020.1) put their configuration here
            if os.path.isdir(JETBRAINS_XDG_CONFIG_DIR):
                # dirs contains possibly multiple directories for a program (eg. .GoLand2018.1 and .GoLand2017.3)
                dirs = [f for f in os.listdir(JETBRAINS_XDG_CONFIG_DIR) if
                        os.path.isdir(os.path.join(JETBRAINS_XDG_CONFIG_DIR, f)) and f.startswith(app[0])]
                # take the newest
                dirs.sort(reverse=True)
                if len(dirs) != 0:
                    full_config_path = os.path.join(JETBRAINS_XDG_CONFIG_DIR, dirs[0], config_path)

            # if no config was found in the newer path, repeat for the old ones
            if full_config_path is None or not os.path.exists(full_config_path):
                if app[0] != "IntelliJIdea" and app[0] != "AndroidStudio":
                    config_path = "options/recentProjectDirectories.xml"
                # dirs contains possibly multiple directories for a program (eg. .GoLand2018.1 and .GoLand2017.3)
                dirs = [f for f in os.listdir(HOME_DIR) if
                        os.path.isdir(os.path.join(HOME_DIR, f)) and f.startswith("." + app[0])]
                # take the newest
                dirs.sort(reverse=True)
                if len(dirs) == 0:
                    continue

                full_config_path = os.path.join(HOME_DIR, dirs[0], "config", config_path)
                if not os.path.exists(full_config_path):
                    continue

            # extract the binary name and icon
            binaries[app[0]] = find_exec(app[1])

            # add all recently opened projects
            projects.extend([[e[0], e[1], app[0]] for e in get_proj(full_config_path)])
        projects.sort(key=lambda s: s[0], reverse=True)

        # List all projects or the one corresponding to the query
        if query.string:
            projects = [p for p in projects if p[1].lower().find(query.string.lower()) != -1]

        items = []
        for p in projects:
            last_update = p[0]
            project_path = p[1]
            project_dir = project_path.split("/")[-1]
            product_name = p[2]
            binary = binaries[product_name]
            if not binary:
                continue

            executable = binaries[p[2]][0]
            icon = binaries[p[2]][1]

            items.append(Item(
                id="-" + str(last_update),
                icon=icon,
                text=project_dir,
                subtext=project_path,
                completion=__trigger__ + project_dir,
                actions=[
                    ProcAction("Open in %s" % product_name, [executable, project_path])
                ]
            ))

        return items
