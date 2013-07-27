#!/usr/bin/env python
#
# Increments version number for current branch
#
# Parses the version file and updates it with the incremented version number.
# Also prints the current and new version numbers to stdout.

initial_version = '1.0.0'
version_file = 'version'


def _split_versions(line):
    branch, _, version = map(str.strip, line.partition(':'))
    return branch, version


def _parse_versions(version_file=version_file):
    versions = {}
    for line in open(version_file):
        branch, version = _split_versions(line)
        if branch:
            versions[branch] = version
    return versions


def _save_versions(versions, version_file=version_file):
    branches = filter(None, (_split_versions(l)[0] for l in open(version_file)))
    output = []
    for branch in branches:
        version = versions.pop(branch)
        output.append('%s: %s' % (branch, version))
    output += ['%s: %s' % (k, v) for k, v in versions.iteritems()]
    open(version_file, 'w').write('\n'.join(output) + '\n')


def default_rule(version, build=None):
    major, _, minor = version.partition('.')
    minor, _, patch = minor.partition('.')
    if not build:
        build = str(int(patch or 0) + 1)
    return str.join('.', (major, minor, build))


rules = {
    'master': default_rule,
    'develop': default_rule,
    'appstore': default_rule,
}

if __name__ == '__main__':
    import sys
    branch_name = sys.argv[1]
    build_number = sys.argv[2]
    if not branch_name in rules:
        sys.exit('No versioning rules found for branch %s' % branch_name)
    versions = _parse_versions()
    current_version = versions.get(branch_name, initial_version)
    next_version = rules[branch_name](current_version, build_number)
    versions[branch_name] = next_version
    _save_versions(versions)
    print current_version, next_version
