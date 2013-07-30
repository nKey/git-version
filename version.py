#!/usr/bin/env python

"""Version control using git tags."""

import subprocess


_usage = """usage: {command} [action [options]]

{description}

Actions:
    release [<rule>]      create new release with version calculated using a rule (default: {default_rule})
    release-set <version> create new release with version passed as parameter

Safe commands:
    bump [<rule>]         calculate next version using a rule (default: {default_rule})
    info <rule>           show rule description
    rules                 display list of rules
    show                  display current version
"""


def release(rule=None, *args):
    """
    Perform a new release calculating the version number using a rule.
    """
    version = next_version(rule or default_rule, *args)
    return release_set(version)


def release_set(version, prefix='release/', *args):
    """
    Perform a new release tagging with the given version.
    """
    git = Git(check_output=False)
    git.fetch('origin', 'master', 'develop')
    git.merge('--ff-only', 'develop', 'origin/develop')
    git.merge('--ff-only', 'master', 'origin/master')
    release_start(version, prefix)
    release_finish(version, prefix)
    return version


def release_start(version, prefix):
    """
    Start a new release branch from develop branch.
    """
    git = Git(check_output=False)
    release_branch = prefix + version
    git.checkout('develop')
    git.checkout('-b', release_branch)


def release_finish(version, prefix):
    """
    Finish the release from an existing release branch.

    Overview:
        1. release branch -> master
        2. tag master
        3. tag -> develop
        4. push changes to origin

    """
    git = Git(check_output=False)
    release_branch = prefix + version
    git.checkout('master')
    git.merge('--no-ff', release_branch)
    git.branch('-d', release_branch)
    git.tag('-a', version, '-m', '"Release %s"' % version)
    git.checkout('develop')
    git.merge('--no-ff', version)
    git.push('origin', 'master', 'develop', version)


def current_version():
    return git.describe()


def current_branch():
    return git.rev_parse('--abbrev-ref', 'HEAD')


def next_version(rule=None, *args):
    version = current_version()
    rule = rule or default_rule
    return rules[rule](version, *args)


def _parse_args(args):
    args = args[:]
    command = args.pop(0)
    action = args.pop(0) if args else None
    option = args
    errors = None
    try:
        if action == 'release':
            print release(*option)
        elif action == 'release-set':
            try:
                if _is_version(option[0]):
                    print release_set(*option)
                else:
                    errors = 'fatal: Not a valid version'
            except IndexError:
                errors = 'fatal: Must specify a version'
        elif action == 'bump':
            print next_version(*option)
        elif action == 'info':
            try:
                print rules[option[0]].__doc__.strip()
            except KeyError:
                errors = 'fatal: Rule is not defined'
            except IndexError:
                errors = 'fatal: Must specify a rule'
        elif action == 'rules':
            print str.join('\n', sorted(
                ('* ' + r if r == default_rule else '  ' + r for r in rules),
                key=lambda v: v.startswith('*') or v)
            )
        elif action == 'show':
            print current_version()
        else:
            print _usage.format(command=command, description=__doc__,
                default_rule=default_rule)
    except subprocess.CalledProcessError as call_error:
        errors = call_error.output.strip()
    return errors


class Git(object):
    """Subprocess wrapper to call git commands using dot syntax."""

    def __init__(self, check_output=True, *args, **kwargs):
        self.args = ['git']
        self.sh = subprocess.check_call
        if check_output:
            self.sh = lambda *a, **kw: subprocess.check_output(*a,
                stderr=subprocess.STDOUT, **kw).strip()

    def __getattr__(self, name):
        git = Git(self.__dict__)
        git.args += [name.replace('_', '-')]
        return git

    def __call__(self, *args):
        return self.sh(self.args + list(args))

git = Git()


# Versioning rules

def _major_minor_patch(version):
    version, _, vcs = version.partition('-')
    major, _, minor = version.partition('.')
    minor, _, patch = minor.partition('.')
    return major, minor, patch


def _is_version(version):
    if not '.' in version:
        return False
    major, minor, patch = _major_minor_patch(version)
    if not major or not minor:
        return False
    try:
        map(int, (major, minor, patch or 0))
    except ValueError:
        return False
    return True


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


def patch_rule(version, *a, **kw):
    """Increments patch number, keeping major and minor numbers."""
    major, minor, patch = _major_minor_patch(version)
    try:
        patch = str(int(patch) + 1) if patch else '0'
    except ValueError:
        patch = '0'
    return str.join('.', (major, minor, patch))


def build_rule(version, build=None, *a, **kw):
    """Set patch number to `build` argument, keeping major and minor number."""
    if not build:
        return patch_rule(version)
    major, minor, patch = _major_minor_patch(version)
    return str.join('.', (major, minor, build))


rules = {
    'major': major_rule,
    'minor': minor_rule,
    'patch': patch_rule,
    'build': build_rule,
}

default_rule = 'patch'


if __name__ == '__main__':
    import sys
    errors = _parse_args(sys.argv)
    sys.exit(errors)
