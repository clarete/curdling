from __future__ import absolute_import, print_function, unicode_literals
from curdling.mapping import Mapping
from curdling import exceptions


def test_filed_packages():
    """Mapping#filed_packages() should return all packages requested based on all requirements we have.

    It will retrieve a unique list of packages, even when the requirement is
    filed more than once.
    """
    # Given that I have a mapping with a few repeated and unique requirements
    mapping = Mapping()
    mapping.requirements.add('sure (1.2.1)')
    mapping.requirements.add('forbiddenfruit (0.1.1)')
    mapping.requirements.add('forbiddenfruit (>= 0.0.5, < 0.0.7)')

    # When I list the filed packages
    packages = sorted(mapping.filed_packages())

    # I see that a list with the all package names was returned without
    # duplications
    packages.should.equal(['forbiddenfruit', 'sure'])


def test_get_requirements_by_package_name():
    "Mapping#get_requirements_by_package_name() Should return a list of requirements that match a given package name"

    # Given that I have a mapping with some repeated requirements
    mapping = Mapping()
    mapping.requirements.add('sure (1.2.1)')
    mapping.requirements.add('forbiddenfruit (0.1.1)')
    mapping.requirements.add('forbiddenfruit (>= 0.0.5, < 0.0.7)')

    # When I filter by the package name 'forbiddenfruit'
    sorted(mapping.get_requirements_by_package_name('forbiddenfruit')).should.equal([
        'forbiddenfruit (0.1.1)',
        'forbiddenfruit (>= 0.0.5, < 0.0.7)',
    ])


def test_available_versions():
    "Mapping#available_versions() should list versions of all wheels for a certain package"

    # Given that I have a mapping with the same requirement filed with different versions
    mapping = Mapping()

    # 0.1.1
    mapping.requirements.add('forbiddenfruit (0.1.1)')
    mapping.wheels['forbiddenfruit (0.1.1)'] = 'forbiddenfruit-0.1.1-cp27-none-macosx_10_8_x86_64.whl'

    # 0.0.6
    mapping.requirements.add('forbiddenfruit (>= 0.0.5, < 0.0.7)')
    mapping.wheels['forbiddenfruit (>= 0.0.5, < 0.0.7)'] = 'forbiddenfruit-0.0.6-cp27-none-macosx_10_8_x86_64.whl'

    # 0.1.1; repeated
    mapping.requirements.add('forbiddenfruit (>= 0.1.0, < 2.0)')
    mapping.wheels['forbiddenfruit (>= 0.1.0, < 2.0)'] = 'forbiddenfruit-0.1.1-cp27-none-macosx_10_8_x86_64.whl'

    # 0.0.9
    mapping.requirements.add('forbiddenfruit (<= 0.0.9)')
    mapping.wheels['forbiddenfruit (<= 0.0.9)'] = 'forbiddenfruit-0.0.9-cp27-none-macosx_10_8_x86_64.whl'

    # And I add another random package to the maestrro
    mapping.requirements.add('sure')

    # When I list all the available versions of forbidden fruit; Then I see it
    # found all the wheels related to that package. Newest first!
    mapping.available_versions('forbiddenfruit').should.equal(['0.1.1', '0.0.9', '0.0.6'])


def test_matching_versions():
    "Mapping#matching_versions() should list versions requirements compatible with a given version"

    # Given that I have a mapping with the same requirement filed with different versions
    mapping = Mapping()

    # 0.1.1
    mapping.requirements.add('pkg (0.1.1)')
    mapping.wheels['pkg (0.1.1)'] = 'pkg-0.1.1-cp27-none-macosx_10_8_x86_64.whl'

    # 0.0.6
    mapping.requirements.add('pkg (>= 0.0.5, < 0.0.7)')
    mapping.wheels['pkg (>= 0.0.5, < 0.0.7)'] = 'pkg-0.0.6-cp27-none-macosx_10_8_x86_64.whl'

    # 0.1.1; repeated
    mapping.requirements.add('pkg (>= 0.1.0, < 2.0)')
    mapping.wheels['pkg (>= 0.1.0, < 2.0)'] = 'pkg-0.1.1-cp27-none-macosx_10_8_x86_64.whl'

    # 0.0.9
    mapping.requirements.add('pkg (<= 0.0.9)')
    mapping.wheels['pkg (<= 0.0.9)'] = 'pkg-0.0.9-cp27-none-macosx_10_8_x86_64.whl'

    # When I query which versions should be listed based on a requirement; Then
    # I see that only the versions that match with the informed requirement
    # were returned (and again, newest first)
    mapping.matching_versions('pkg (>= 0.0.6, <= 0.1.0)').should.equal([
         '0.0.9', '0.0.6',
    ])

def test_matching_versions_with_hyphen():
    "Mapping#matching_versions() Should be aware of hyphens in the version info"

    # Given that I have a mapping that contains a package with hyphens in the
    # version info
    mapping = Mapping()

    # 0.1.1-RC1
    mapping.requirements.add('pkg (0.1.1-RC1)')
    mapping.wheels['pkg (0.1.1-RC1)'] = 'pkg-0.1.1_RC1-cp27-none-macosx_10_8_x86_64.whl'

    # When I filter the matching versions
    mapping.matching_versions('pkg (0.1.1-RC1)').should.equal([
        '0.1.1_RC1',
    ])



def test_is_primary_requirement():
    """Mapping#is_primary_requirement() True for requirements directly requested by the user

    Either from the command line or from the requirements file informed through
    the `-r` parameter;

    The `secondary` requirements are all the requirements we install without
    asking the user, IOW, dependencies of the primary requirements.
    """

    # Given that I have a mapping with two requirements filed
    mapping = Mapping()

    mapping.requirements.add('sure (1.2.1)')
    mapping.dependencies['sure (1.2.1)'] = [None]

    mapping.requirements.add('forbiddenfruit (0.1.1)')
    mapping.dependencies['forbiddenfruit (0.1.1)'] = ['sure (1.2.1)']

    # When I test if the above requirements are primary
    mapping.is_primary_requirement('sure (1.2.1)').should.be.true
    mapping.is_primary_requirement('forbiddenfruit (0.1.1)').should.be.false


def test_best_version():
    """Mapping#best_version() Should choose the newest compatible version of a requirement to be installed

    By compatible, I mean that this version will match all the other
    requirements present in the mapping.

    """

    # Given that I have a mapping with a package that contains more than one
    # version
    mapping = Mapping()
    mapping.requirements.add('pkg (<= 0.1.1)')
    mapping.wheels['pkg (<= 0.1.1)'] = 'pkg-0.1.1-cp27-none-macosx_10_8_x86_64.whl'  # 0.1.1

    mapping.requirements.add('pkg (>= 0.0.5)')
    mapping.wheels['pkg (>= 0.0.5)'] = 'pkg-0.0.6-cp27-none-macosx_10_8_x86_64.whl'  # 0.0.6

    # When I retrieve the best match
    version, requirement = mapping.best_version('pkg')

    # Then I see that the newest dependency was chosen
    version.should.equal('0.1.1')
    requirement.should.equal('pkg (<= 0.1.1)')


def test_best_version_with_conflicts():
    "Mapping#best_version() Should raise blow up if no version matches all the filed requirements"

    # Given that I have a mapping with a package that contains more than one
    # version
    mapping = Mapping()
    mapping.requirements.add('pkg (>= 0.1.1)')
    mapping.dependencies['pkg (>= 0.1.1)'] = ['blah']
    mapping.wheels['pkg (>= 0.1.1)'] = 'pkg-0.1.1-cp27-none-macosx_10_8_x86_64.whl'  # 0.1.1

    # And the second version is older
    mapping.requirements.add('pkg (>= 0.0.5, < 0.0.7)')
    mapping.dependencies['pkg (>= 0.0.5, < 0.0.7)'] = ['bleh']
    mapping.wheels['pkg (>= 0.0.5, < 0.0.7)'] = 'pkg-0.0.6-cp27-none-macosx_10_8_x86_64.whl'  # 0.0.6

    # When I retrieve the best match
    mapping.best_version.when.called_with('pkg').should.throw(
        exceptions.VersionConflict,
        'Requirement: pkg (>= 0.1.1, >= 0.0.5, < 0.0.7), '
        'Available versions: 0.1.1, 0.0.6'
    )


def test_best_version_with_explicit_requirement():
    """Mapping#best_version() Should always prioritize versions directly specified by the user

    The other versions might have been added by dependencies. So, to manually
    fix craziness between dependencies of dependencies, the user can just force
    a specific version for a package from the command line or from a
    requirements file informed with the `-r` parameter.
    """

    # Given that I have a mapping with a package that contains more than one
    # version
    mapping = Mapping()

    mapping.requirements.add('pkg (>= 0.1.1)')
    mapping.dependencies['pkg (>= 0.1.1)'] = ['other_pkg (0.1)']
    mapping.wheels['pkg (>= 0.1.1)'] = 'pkg-0.1.1-cp27-none-macosx_10_8_x86_64.whl'  # 0.1.1

    # And the second version is older, but has no dependencies
    mapping.requirements.add('pkg (>= 0.0.5, < 0.0.7)')
    mapping.dependencies['pkg (>= 0.0.5, < 0.0.7)'] = [None]
    mapping.wheels['pkg (>= 0.0.5, < 0.0.7)'] = 'pkg-0.0.6-cp27-none-macosx_10_8_x86_64.whl'  # 0.0.6

    # When I retrieve the best match
    version = mapping.best_version('pkg', debug=True)

    # Then I see that we retrieved the oldest version, just because the package
    # is not a dependency.
    version.should.equal(('0.0.6', 'pkg (>= 0.0.5, < 0.0.7)'))


def test_best_version_no_strict_requirements_but_strict_version():
    "Mapping#best_version() should still work for requirements without version info"

    # Given that I have a mapping with two requirements
    mapping = Mapping()
    mapping.requirements.add('forbiddenfruit')
    mapping.dependencies['forbiddenfruit'] = ['sure (== 0.2.1)']
    mapping.wheels['forbiddenfruit'] = 'forbiddenfruit-0.1.0-cp27.whl'

    # When I retrieve the best match
    version = mapping.best_version('forbiddenfruit')

    # Then I see that I still got the version number even though my requirement
    # didn't have version info
    version.should.equal(('0.1.0', 'forbiddenfruit'))
