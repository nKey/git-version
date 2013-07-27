# Version Control

Increments version number for current branch being built.


## Dependencies

* [Git Plugin](https://wiki.jenkins-ci.org/display/JENKINS/Git+Plugin)
* [EnvInject Plugin](https://wiki.jenkins-ci.org/display/JENKINS/EnvInject+Plugin)


## Jenkins Configuration

### Build steps:

* Execute shell: `python ${WORKSPACE}/version.py ${GIT_BRANCH} ${BUILD_NUMBER} > envvars`
* Inject environment variables - Properties File Path: `envvars`

The following variables will then be available to use in your build environment:

* `CURRENT_VERSION`: the number read from the version file for the branch being built.
* `NEXT_VERSION`: the calculated next version number, that is also updated on the version file.


## Git Project Setup

* Copy the `version.py` file to your project and create version increment rules for each branch.
* Create a file named `version` inside your project in git, containing the initial version numbers you want for each branch.


## Example

Increment rules:

    rules = {
        'master': major_rule,
        'develop': build_rule,
    }

Initial versions:

    master: 1.0.0
    develop: 1.0.86

In this example, for the next build of the master branch Jenkins will tag it as `1.0.0`, increment it to `2.0.0` (according to `major_rule`), and push the new tag and modified version file to the remote origin.

And for the next build of the develop branch, Jenkins will just increment it by the build number given as parameter on the script call, and push the modified version file to the remote origin.
