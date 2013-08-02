#!/usr/bin/env python

"""Version control using git tags."""

import subprocess


_usage = """{description}

Usage:
    {command} release [-r <rule>] [-o <origin>] [<destination> [<source>]]
    {command} release-set <version> [-o <origin>] [<destination> [<source>]]

    {command} hotfix [-r <rule>] [-o <origin>] [<destination> [<source>]]
    {command} hotfix-set <version> [-o <origin>] [<destination> [<source>]]

Safe commands:
    {command} bump [<rule>]         calculate next version using a rule (default: {default_rule})
    {command} info <rule>           show rule description
    {command} rules                 display list of rules
    {command} show [<rule>]         display current version (default: all)
"""


def release(branch=None, source=None, origin=None, rule=None, *args, **kwargs):
    """
    Perform a new release calculating the version number using a rule.
    """
    origin = origin or default_origin
    branch = branch or default_branch
    source = source or branch_rules[branch]['source']
    rule = rule or branch_rules[branch]['rule']
    version = next_version(rule, *args)
    return release_set(version, branch, source)


def release_set(version, branch=None, source=None, origin=None,
        prefix='release/', *args, **kwargs):
    """
    Perform a new release tagging with the given version.
    """
    origin = origin or default_origin
    branch = branch or default_branch
    source = source or branch_rules[branch]['source']
    git = Git(check_output=False)
    git.fetch(origin, branch, source)
    git.merge('--ff-only', source, '%s/%s' % (origin, source))
    git.merge('--ff-only', branch, '%s/%s' % (origin, branch))
    release_start(version, branch, source, origin, prefix)
    release_finish(version, branch, source, origin, prefix)
    return version


def release_start(version, branch, source, origin, prefix):
    """
    Start a new release branch from develop branch.
    """
    git = Git(check_output=False)
    release_branch = prefix + version
    git.checkout(source)
    git.checkout('-b', release_branch)


def release_finish(version, branch, source, origin, prefix):
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
    git.checkout(branch)
    git.merge('--no-ff', release_branch)
    git.branch('-d', release_branch)
    git.tag('-a', version, '-m', '"Release %s"' % version)
    git.checkout(source)
    git.merge('--no-ff', version)
    git.push(origin, branch, source, version)


def current_version(rule=None):
    version = git.describe()
    if rule not in ('major', 'minor', 'patch'):
        return version
    major, minor, patch = _major_minor_patch(version)
    if rule == 'patch':
        return str.join('.', (major, minor, patch))
    elif rule == 'minor':
        return str.join('.', (major, minor))
    elif rule == 'major':
        return major


def current_branch():
    return git.rev_parse('--abbrev-ref', 'HEAD')


def next_version(rule=None, *args):
    version = current_version()
    rule = rule or default_rule
    return bump_rules[rule](version, *args)


def _parse_args(args):
    args = args[:]
    command = args.pop(0)
    action = args.pop(0) if args else None
    kw_idx = [(i, i + 1) for i, k in enumerate(args) if k.startswith('-')]
    kwargs = {args[i]: args[j] for i, j in kw_idx}
    option = [args[i] for i in range(len(args)) if i not in sum(kw_idx, ())]
    errors = None
    kwargs['rule'] = kwargs.get('-r')
    kwargs['origin'] = kwargs.get('-o')
    try:
        if action == 'release':
            print release(*option, **kwargs)
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
                print bump_rules[option[0]].__doc__.strip()
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
            print current_version(*option)
        else:
            print _usage.format(command=command, description=__doc__,
                default_origin=default_origin, default_branch=default_branch,
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


def keep_rule(version, *a, **kw):
    """
    Keep the same version, without changing.
    Use of this rule prevents a backmerge from occurring.
    """
    return version


bump_rules = {
    'major': major_rule,
    'minor': minor_rule,
    'patch': patch_rule,
    'build': build_rule,
    'keep': keep_rule,
}

branch_rules = {
    'master': {'rule': 'patch', 'source': 'develop'},
    'appstore': {'rule': 'keep', 'source': 'master'},
}

default_origin = 'origin'
default_branch = 'master'
default_rule = branch_rules[default_branch]['rule']


if __name__ == '__main__':
    import sys
    errors = _parse_args(sys.argv)
    sys.exit(errors)
