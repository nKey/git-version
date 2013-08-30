#!/usr/bin/env python

"""Version control using git tags."""

import subprocess


_usage = """Usage:
    {command} release [-r <rule> | -s <version>] [-n] [-o <origin>] [<destination> [<source>]]

    {command} hotfix-start [-r <rule> | -s <version>] [-o <origin>] [<branch>]
    {command} hotfix-finish [<version>] [-n] [-o <origin>] [<branch>]

Safe commands:
    {command} bump [<rule>]     calculate next version using a rule (default: {default_rule})
    {command} info <rule>       show rule description
    {command} rules [<branch>]  display list of rules, marking default for given branch
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
    rule. The release -s command allows to manually set the version to be used.

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

    Creating a new release consists in the following steps:

        * create a intermediary release branch from source branch
        * merge this branch to destination branch
        * tag the merge with the new version
        * merge back the tag into the source branch

    It is worth noting that the last two steps only occurr if the new version is
    different from the current version as returned by {command} {under}show build{reset}.

    A hotfix works in similar fashion to a release, the difference being that
    both source and destination branches are the same, and it stops middle way
    to allow commits to be done in the intermediary branch.

{bold}OPTIONS{reset}

    {under}release{reset} [-n] [-r <rule> | -s <version>] [-o <origin>] [<destination> [<source>]]
        Create a new release from source to destination branch with version
        calculated using a rule, or specified directly with the -s option. If
        both options are given, the explicit set version takes precedence. The
        version must match the "<major>.<minor>[.<patch>][.<build>]" format,
        where eachfield is an integer. The resulting merge will be pushed to
        origin unless the -n (dry-run) option is given.

    {under}hotfix-start{reset} [-r <rule> | -s <version>] [<branch>]
        Create a new hotfix branch to work on, based on the specified branch.
        By default the {bold}{hotfix_rule}{reset} rule will be used to set the hotfix version number
        but a different rule can be specified with -r or a version can be set
        directly with the -s option. If both are given, the set version takes
        precedence.

    {under}hotfix-finish{reset} [<version>] [-n] [-o <origin>]
        Merge back and delete the hotfix branch for the given version.

{bold}A NOTE ON BUILD NUMBER{reset}

    You can optionally use a global counter in the last field of the version,
    in the format "<major>.<minor>.<patch>.<build>". This build number always
    gets incremented and is never reset when using any of the increment rules.

"""


def release(branch=None, source=None, origin=None, version=None, rule=None,
        dry_run=False, prefix='release/', *args, **kwargs):
    """
    Perform a new release tagging with the given version or calculating the
    version number using a rule.
    """
    origin = origin or default_origin
    branch = branch or default_branch
    source = source or branch_rules[branch]['source']
    rule = rule or branch_rules[branch]['rule']
    git = Git(**kwargs)
    git.fetch(origin, branch, source)
    git.checkout(source)
    git.merge('--ff-only', source, '%s/%s' % (origin, source))
    git.checkout(branch)
    git.merge('--ff-only', branch, '%s/%s' % (origin, branch))
    version = version or next_version(rule, *args)
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
    return release_branch


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
    if version != current_version('build'):
        git.tag('-a', version, '-m', 'Release %s' % version)
        git.checkout(source)
        git.merge('--no-ff', '--no-edit', version)
    return version


def hotfix(action=None, version=None, branch=None, origin=None, rule=None,
        dry_run=False, prefix='hotfix/', *args, **kwargs):
    origin = origin or default_origin
    branch = branch or hotfix_branch
    rule = rule or hotfix_rule
    git = Git(**kwargs)
    git.fetch(origin, branch)
    git.checkout(branch)
    git.merge('--ff-only', branch, '%s/%s' % (origin, branch))
    version = version or next_version(rule, *args)
    if action == 'start':
        return hotfix_start(version, branch, origin, prefix, **kwargs)
    elif action == 'finish':
        hotfix_finish(version, branch, origin, prefix, **kwargs)
        if not dry_run:
            git.push(origin, branch, version)


def hotfix_start(version, branch, origin, prefix, **kwargs):
    git = Git(**kwargs)
    hotfix_branch = prefix + version
    git.checkout(branch)
    git.checkout('-b', hotfix_branch)
    return hotfix_branch


def hotfix_finish(version, branch, origin, prefix, **kwargs):
    git = Git(**kwargs)
    hotfix_branch = prefix + version
    git.checkout(branch)
    git.merge('--no-ff', '--no-edit', hotfix_branch)
    git.branch('-d', hotfix_branch)
    git.tag('-a', version, '-m', 'Hotfix %s' % version)
    return version


def current_version(field=None):
    version = git.describe()
    if field not in ('major', 'minor', 'patch', 'build'):
        return version
    major, minor, patch, build = _major_minor_patch_build(version)
    if field == 'build':
        return str.join('.', (major, minor, patch or '0', build or '0'))
    elif field == 'patch':
        return str.join('.', (major, minor, patch or '0'))
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
    command = args.pop(0).rpartition('/')[-1]
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
    kwargs['version'] = kwargs.get('-s')
    try:
        if action in ('release', 'hotfix-start'):
            if kwargs['version'] and not _is_version(kwargs['version']):
                errors = 'fatal: Not a valid version'
            elif action == 'release':
                print release(*option, **kwargs)
            elif action == 'hotfix-start':
                print hotfix(action='start', *option, **kwargs)
        elif action == 'hotfix-finish':
            print hotfix(action='finish', *option, **kwargs)
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
            try:
                rule = branch_rules[option[0] if option else default_branch]['rule']
                print str.join('\n', sorted(
                    ('* ' + r if r == rule else '  ' + r for r in bump_rules),
                    key=lambda v: v.startswith('*') or v))
            except KeyError:
                errors = 'fatal: No rule defined for given branch'
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
                    hotfix_rule=hotfix_rule,
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

def _major_minor_patch_build(version):
    version, _, vcs = version.partition('-')
    major, _, minor = version.partition('.')
    minor, _, patch = minor.partition('.')
    patch, _, build = patch.partition('.')
    return major, minor, patch, build


def _is_version(version):
    if not '.' in version:
        return False
    major, minor, patch, build = _major_minor_patch_build(version)
    if not major or not minor:
        return False
    try:
        map(int, (major, minor, patch or 0, build or 0))
    except ValueError:
        return False
    return True


# Default rules

def major_rule(version, *a, **kw):
    """Increments major number, resetting minor and patch numbers."""
    major, minor, patch, build = _major_minor_patch_build(version)
    major = str(int(major) + 1)
    minor = patch = '0'
    if build:
        patch += '.' + str(int(build) + 1)
    return str.join('.', (major, minor, patch))


def minor_rule(version, *a, **kw):
    """Increments minor number, keeping major and resetting patch number."""
    major, minor, patch, build = _major_minor_patch_build(version)
    minor = str(int(minor) + 1)
    patch = '0'
    if build:
        patch += '.' + str(int(build) + 1)
    return str.join('.', (major, minor, patch))


def patch_rule(version, *a, **kw):
    """Increments patch number, keeping major and minor numbers."""
    major, minor, patch, build = _major_minor_patch_build(version)
    try:
        patch = str(int(patch) + 1) if patch else '0'
    except ValueError:
        patch = '0'
    if build:
        patch += '.' + str(int(build) + 1)
    return str.join('.', (major, minor, patch))


def build_rule(version, build=None, *a, **kw):
    """Set build number to `build` argument, keeping the other numbers."""
    major, minor, patch, old_build = _major_minor_patch_build(version)
    patch = patch or '0'
    if not build:
        build = str(int(old_build) + 1) if old_build else '0'
    return str.join('.', (major, minor, patch, build))


def keep_rule(version, *a, **kw):
    """
    Keep the same version without changes.
    Use of this rule prevents a backmerge from occurring.
    """
    major, minor, patch, build = _major_minor_patch_build(version)
    if build:
        patch += '.' + build
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
hotfix_branch = 'master'


if __name__ == '__main__':
    import sys
    errors = _parse_args(sys.argv)
    sys.exit(errors)
