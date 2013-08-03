#!/usr/bin/env python

"""Version control using git tags."""

import subprocess


_usage = """Usage:
    {command} release [-r <rule>] [-n] [-o <origin>] [<destination> [<source>]]
    {command} release-set <version> [-n] [-o <origin>] [<destination> [<source>]]

    {command} hotfix [-r <rule>] [-n] [-o <origin>] [<branch>]
    {command} hotfix-set <version> [-n] [-o <origin>] [<branch>]

Safe commands:
    {command} bump [<rule>]     calculate next version using a rule (default: {default_rule})
    {command} info <rule>       show rule description
    {command} rules             display list of rules
    {command} show [<field>]    display current version truncating at field (default: all)
"""

_man = """
{bold}NAME{reset}
    {command} - {description}

{bold}SYNOPSIS{reset}
{usage}

{bold}DESCRIPTION{reset}
    Use {command} release when you want to create a new versioned release from
    source to destination branch with the version number calculated using a
    rule. The release-set command allows to manually set the version to be used.

    A rule specifies a function used to change the version number in a certain
    way. The version format is "<major>.<minor>.<patch>" and a rule can operate
    on one or more of the version fields - for example resetting the patch and
    minor numbers when increasing the major number.

    Some combinations of rules and source branches are defined for specific
    destination branches:

{branch_rules}

    This means you can simply specify the destination branch on the commandline
    (eg. {command} {under}release {default_branch}{reset}) and the options will assume the default
    values accordingly (same as {command} {under}release -r {default_rule} {default_branch} {default_source}{reset}).


{bold}OPTIONS{reset}

    {under}release{reset} [-n] [-r <rule>] [-o <origin>] [<destination> [<source>]]
        Create a new release from source to destination branch with version
        calculated using a rule. The result will be pushed to origin, unless
        the -n (dry-run) option is given.

    {under}release-set{reset} <version> [-n] [-o <origin>] [<destination> [<source>]]
        Create a new release with version passed as parameter. The version must
        match the "<major>.<minor>[.<patch>]" format, where each field is an
        integer.

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
    return release_set(version, branch, source, origin, *args, **kwargs)


def release_set(version, branch=None, source=None, origin=None,
        dry_run=False, prefix='release/', *args, **kwargs):
    """
    Perform a new release tagging with the given version.
    """
    origin = origin or default_origin
    branch = branch or default_branch
    source = source or branch_rules[branch]['source']
    git = Git(**kwargs)
    git.fetch(origin, branch, source)
    git.merge('--ff-only', '--no-edit', source, '%s/%s' % (origin, source))
    git.merge('--ff-only', '--no-edit', branch, '%s/%s' % (origin, branch))
    release_start(version, branch, source, origin, prefix, **kwargs)
    release_finish(version, branch, source, origin, prefix, **kwargs)
    if not dry_run:
        git.push(origin, branch, source, version)
    return version


def release_start(version, branch, source, origin, prefix, **kwargs):
    """
    Start a new release branch from develop branch.
    """
    git = Git(**kwargs)
    release_branch = prefix + version
    git.checkout(source)
    git.checkout('-b', release_branch)


def release_finish(version, branch, source, origin, prefix, **kwargs):
    """
    Finish the release from an existing release branch.

    Overview:
        1. release branch -> master
        2. tag master
        3. tag -> develop

    """
    git = Git(**kwargs)
    release_branch = prefix + version
    git.checkout(branch)
    git.merge('--no-ff', '--no-edit', release_branch)
    git.branch('-d', release_branch)
    if version != current_version('patch'):
        git.tag('-a', version, '-m', '"Release %s"' % version)
        git.checkout(source)
        git.merge('--no-ff', '--no-edit', version)


def current_version(field=None):
    version = git.describe()
    if field not in ('major', 'minor', 'patch'):
        return version
    major, minor, patch = _major_minor_patch(version)
    if field == 'patch':
        return str.join('.', (major, minor, patch))
    elif field == 'minor':
        return str.join('.', (major, minor))
    elif field == 'major':
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
    flags = {'-n': 'dry_run', '-v': 'verbose', '--debug': 'debug'}
    flags = {k: f in args and bool(args.pop(args.index(f)))
        for f, k in flags.iteritems()}
    kw_idx = [(i, i + 1) for i, k in enumerate(args) if k.startswith('-')]
    kwargs = {args[i]: args[j] for i, j in kw_idx}
    option = [args[i] for i in range(len(args)) if i not in sum(kw_idx, ())]
    errors = None
    kwargs.update(flags)
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
            usage = _usage.format(command=command, default_rule=default_rule,
                default_origin=default_origin, default_branch=default_branch)
            if action in ('--help', 'help'):
                formatted_branch_rules = str.join('\n',
                    ('{0} -> rule={rule} source={source}'.format(k.rjust(16), **v)
                    for k, v in sorted(branch_rules.iteritems())))
                man = _man.format(command=command, description=__doc__,
                    branch_rules=formatted_branch_rules, usage=usage,
                    default_branch=default_branch, default_rule=default_rule,
                    default_source=branch_rules[default_branch]['source'],
                    bold='\033[1m', under='\033[4m', reset='\033[0m')
                less = subprocess.Popen(['less', '-R'], stdin=subprocess.PIPE)
                less.communicate(man)
            else:
                print usage + "\n'{command} --help' to display extended information.".format(command=command)
    except subprocess.CalledProcessError as call_error:
        errors = call_error.output.strip()
    return errors


class Git(object):
    """Subprocess wrapper to call git commands using dot syntax."""

    def __init__(self, *args, **kwargs):
        self.args = ['git']
        self.debug = kwargs.get('debug')
        self.verbose = kwargs.get('verbose') or self.debug
        self.sh = self._debug_output if self.verbose else self._check_output

    def _check_output(self, *args, **kwargs):
        return subprocess.check_output(
            *args, stderr=subprocess.STDOUT, **kwargs).strip()

    def _debug_output(self, *args, **kwargs):
        print(str.join(' ', *args))
        if not self.debug:
            return subprocess.check_call(*args, **kwargs)

    def __getattr__(self, name):
        git = Git(**self.__dict__)
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
    Keep the same version without changes.
    Use of this rule prevents a backmerge from occurring.
    """
    major, minor, patch = _major_minor_patch(version)
    return str.join('.', (major, minor, patch))


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
hotfix_rule = 'patch'


if __name__ == '__main__':
    import sys
    errors = _parse_args(sys.argv)
    sys.exit(errors)
