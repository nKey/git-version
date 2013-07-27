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


def _major_minor_patch(version):
    major, _, minor = version.partition('.')
    minor, _, patch = minor.partition('.')
    return major, minor, patch


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


rules = {
    'master': minor_rule,
    'develop': build_rule,
    'appstore': major_rule,
}

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        sys.exit('Usage: %s [branch_name] [build_number]' % sys.argv[0])
    branch_name = sys.argv[1]
    build_number = sys.argv[2]
    if not branch_name in rules:
        sys.exit('No versioning rules found for branch %s' % branch_name)
    versions = _parse_versions()
    current_version = versions.get(branch_name, initial_version)
    next_version = rules[branch_name](current_version, build_number, versions)
    versions[branch_name] = next_version
    _save_versions(versions)
    print 'CURRENT_VERSION=%s' % current_version
    print 'NEXT_VERSION=%s' % next_version
