#!/usr/bin/env python

"""Show or increment version number for current branch based on git tags."""

import subprocess


_usage = """usage: {command} [action [options]]

{description}

 bump [rule] \t Calculate next version using a rule (default: branch name)
 set <string> \t Set version to specified value and create new tag
"""


def current_version():
    return git.describe()


def next_version(rule=None, *args):
    version = git.describe()
    if rule not in rules:
        # use current branch name to match rule
        rule = git.rev_parse('--abbrev-ref', 'HEAD')
    return rules[rule](version, *args)


def set_version(version, *args):
    git.tag('-a', version, '-m', '"Release %s"' % version)


def _parse_args(args):
    args = args[:]
    command = args.pop(0)
    action = args.pop(0) if args else None
    option = args
    errors = None
    try:
        if not action:
            print current_version()
        elif action == 'bump':
            print next_version(*option)
        elif action == 'set':
            print set_version(*option)
        else:
            print _usage.format(command=command, description=__doc__)
    except subprocess.CalledProcessError as call_error:
        errors = call_error.output.strip()
    return errors


class Git(object):

    def __init__(self, baked_args=None):
        self.args = ['git']
        self.baked_args = baked_args or {}

    def __getattr__(self, name):
        git = Git()
        git.args += [name.replace('_', '-')]
        return git

    def __call__(self, *args):
        return subprocess.check_output(self.args + list(args),
            stderr=subprocess.STDOUT, **self.baked_args).strip()

git = Git()


def _major_minor_patch(version):
    major, _, minor = version.partition('.')
    minor, _, patch = minor.partition('.' if '.' in minor else '-')
    return major, minor, patch


# Default rules

def major_rule(version, *a, **kw):
    """Increments major number, resetting minor and patch numbers."""
    major, minor, patch = _major_minor_patch(version)
    major = str(int(major) + 1)
    minor = patch = '0'
    return str.join('.', (major, minor, patch))


def minor_rule(version, *a, **kw):
    """Increments minor number, keeping major and resetting patch number."""
    major, minor, patch = _major_minor_patch(version)
    minor = str(int(minor) + 1)
    patch = '0'
    return str.join('.', (major, minor, patch))


def build_rule(version, build=None, *a, **kw):
    """Set patch number to `build` argument, keeping major and minor number."""
    major, minor, patch = _major_minor_patch(version)
    if not build:
        build = str(int(patch or 0) + 1)
    return str.join('.', (major, minor, build))


# Zamurai rules

def master_rule(version, *a, **kw):
    """
    Increments the patch version.

    Used by the build machine when building the master branch. It will base the
    version on the previous git tag, so to increment the minor or major version
    there must be a tag on the branch that merged to the master before building.

    """
    major, minor, patch = _major_minor_patch(version)
    try:
        patch = str(int(patch or 0) + 1)
    except ValueError:
        patch = '0'
    return str.join('.', (major, minor, patch))


def develop_rule(version, *a, **kw):
    """
    Increments the minor version.

    Used by the developer before releasing a new minor version. It will base
    the version on the previous git tag and not set the patch number so that
    the next build on master assumes patch number zero.

    """
    major, minor, patch = _major_minor_patch(version)
    minor = str(int(minor) + 1)
    return str.join('.', (major, minor))


def appstore_rule(version, *a, **kw):
    """
    Does not increment, just uses last tag version.

    Used by the build machine when building the AppStore release from latest
    master branch or from a hotfix branch.

    """
    return version


rules = {
    'master': master_rule,
    'develop': develop_rule,
    'appstore': appstore_rule,
    'major': major_rule,
    'minor': minor_rule,
    'build': build_rule,
}


if __name__ == '__main__':
    import sys
    errors = _parse_args(sys.argv)
    sys.exit(errors)
