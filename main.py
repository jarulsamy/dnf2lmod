import io
import logging
import platform
import re
import sys
import tarfile
from collections import defaultdict
from pathlib import Path
from pprint import pprint
from urllib.request import urlretrieve

import dnf
import hawkey
import rpmfile


def build_pkg_tree(modulefiles_dir: Path):
    tree = defaultdict(list)
    for d in modulefiles_dir.iterdir():
        for f in d.glob("*.lua"):
            tree[d.name].append(f.stem)
    return tree


def process_user_query(pkg_name) -> list:
    """Parse out a user query and calculate the packages that need to be installed."""
    base = dnf.Base()
    conf = base.conf
    conf.substitutions["basearch"] = platform.machine()
    base.read_all_repos()
    base.fill_sack()
    g = hawkey.Goal(base.sack)

    # Assume the user gave a nevra string,
    # just like any other dnf command invocation.
    subject = dnf.subject.Subject(pkg_name)
    query = subject.get_best_query(base.sack)
    if len(query) < 1:
        raise Exception(f"Could not find package '{pkg_name}'")
    pkg = query[0]
    # if pkg.installed:
    #     raise Exception(f"Package {pkg} already installed")

    g.install(pkg)
    if not g.run():
        raise Exception(f"Failed to find package named {pkg}")

    pkgs_to_install = [*g.list_installs()]

    return pkgs_to_install


def filter_installed_dependencies(pkg_list, installed_tree):
    """Remove already installed packages from the package listing."""
    new_pkg_list = []
    archs = ("noarch", platform.machine())

    for i in pkg_list:
        # Filter out any non-my-arch packages as well
        if i.arch in archs:
            if i.version not in installed_tree.get(i.name, []):
                new_pkg_list.append(i)

    return new_pkg_list


def download_pkgs(pkg_list):
    for i in pkg_list:
        url = i.remote_location()
        print(url)
        buffer = io.BytesIO()
        rpm_path, _ = urlretrieve(url)
        with rpmfile.open(rpm_path) as rpm:
            print(rpm.getmembers())


install_dir = Path("./software")
modulefiles_dir = Path("./modulefiles")
pkg_name = sys.argv[1]

installed_tree = build_pkg_tree(modulefiles_dir)
pkg_list = process_user_query(pkg_name)
pkg_list = filter_installed_dependencies(pkg_list, installed_tree)

pprint(pkg_list)
pprint(installed_tree)
pprint(download_pkgs(pkg_list))
