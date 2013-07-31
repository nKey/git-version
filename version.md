# Version Control

Increments version number based on git tags.


## Git Project Setup

* Install the `version.py` file to your develop and build machines. <br />`cp version.py /usr/local/bin/version`
* Run `version` and read the command line usage help.
* Hack your code, commiting on the develop branch as normal.
* When ready, run `version release` to create a new release from the develop to the master branch, pushing the changes to origin.


## Jenkins Configuration

### Dependencies

* [Git Plugin](https://wiki.jenkins-ci.org/display/JENKINS/Git+Plugin)
* [EnvInject Plugin](https://wiki.jenkins-ci.org/display/JENKINS/EnvInject+Plugin)

### Source code management:

Configure your git repository URL and branch to build, then click advanced and set:

* Skip internal tag: true
* Use shallow clone: false

Otherwise you'll get the wrong version number.

### Build steps:

* Execute shell: <br />`echo CURRENT_VERSION=$(python "/usr/local/bin/version.py" show) > envvars`
* Inject environment variables - Properties File Path: `envvars`

The `CURRENT_VERSION` variable will then be available to use in your build environment, containing the version obtained from the most recent git tag.
