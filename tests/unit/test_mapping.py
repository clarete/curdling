from __future__ import absolute_import, print_function, unicode_literals
from curdling.mapping import Mapping
from curdling import exceptions


def test_file_requirement():
    "Mapping#file_requirement() should add a new requirement to the mapping"

    # Given that I have a mapping
    mapping = Mapping()

    # When I file a requirement
    mapping.file_requirement('curdling')

    # Then I see that the mapping attribute has all the data we need to process
    # a requirement
    dict(mapping.mapping).should.equal({
        'curdling': {
            'dependency_of': [None],
            'wheel': None,
            'exception': None,
        }
    })


def test_file_requirement_with_constraints():
    "Mapping#file_requirement() should add a new requirement with constraints to the mapping"

    # Given that I have a mapping
    mapping = Mapping()

    # When I file a requirement
    mapping.file_requirement('curdling (>= 0.2.5, < 0.3.0)')

    # And then I see that the mapping attribute has the right values
    dict(mapping.mapping).should.equal({
        'curdling (>= 0.2.5, < 0.3.0)': {
            'dependency_of': [None],
            'wheel': None,
            'exception': None,
        }
    })


def test_file_dependencies():
    "Mapping#file_requirement() should be able to remember which requirement requested a given dependency"

    # Given that I have a mapping with a file on it
    mapping = Mapping()
    mapping.file_requirement('sure (1.2.1)')

    # When I file another requirement using the `dependency_of` parameter
    mapping.file_requirement('forbiddenfruit (0.1.0)', ['sure (1.2.1)'])

    # Then I see that the mapping looks right
    dict(mapping.mapping).should.equal({
        'sure (1.2.1)': {
            'dependency_of': [None],
            'wheel': None,
            'exception': None,
        },

        'forbiddenfruit (0.1.0)': {
            'dependency_of': ['sure (1.2.1)'],
            'wheel': None,
            'exception': None,
        }
    })


def test_file_requirement_update_dependency_list():
    "Mapping#file_requirement() should update the dependency_of list if a requirement is requested more than once and is unique"

    # Given the following mapping loaded with a few packages
    mapping = Mapping()
    mapping.file_requirement('forbiddenfruit (0.1.0)')
    mapping.file_requirement('sure (1.2.1)')
    mapping.file_requirement('forbiddenfruit (0.1.0)', ['sure (1.2.1)'])

    # Then I see that the mapping looks right
    dict(mapping.mapping).should.equal({
        'sure (1.2.1)': {
            'dependency_of': [None],
            'wheel': None,
            'exception': None,
        },

        'forbiddenfruit (0.1.0)': {
            'dependency_of': [None, 'sure (1.2.1)'],
            'wheel': None,
            'exception': None,
        }
    })


def test_set_data():
    "Mapping#set_data() should set keys (wheel or exception) to the `data` field in the requirement"

    # Given that I have a mapping with a requirement
    mapping = Mapping()
    mapping.file_requirement('forbiddenfruit (0.1.1)')

    # When I set the source of the previously added requirement
    mapping.set_data('forbiddenfruit (0.1.1)', 'wheel', '/path/to/the/wheel')

    # Then I see the data was saved in the right place
    mapping.mapping['forbiddenfruit (0.1.1)']['wheel'].should.equal(
        '/path/to/the/wheel'
    )


def test_get_data():
    "Mapping#get_data() should get the content of a given key under the requirements' data key"

    # Given that I have a mapping with a requirement that contains a source
    mapping = Mapping()
    mapping.file_requirement('forbiddenfruit (0.1.1)')
    mapping.set_data('forbiddenfruit (0.1.1)', 'tarball', '/path/to/my/tarball-0.0.1.tar.gz')

    # When I get_data() the requirement above
    tarball = mapping.get_data('forbiddenfruit (0.1.1)', 'tarball')

    # Then I see the source was retrieved properly
    tarball.should.equal('/path/to/my/tarball-0.0.1.tar.gz')


def test_filed_packages():
    """Mapping#filed_packages() should return all packages requested based on all requirements we have.

    It will retrieve a unique list of packages, even when the requirement is
    filed more than once.
    """
    # Given that I have a mapping with a few repeated and unique requirements
    mapping = Mapping()
    mapping.file_requirement('sure (1.2.1)')
    mapping.file_requirement('forbiddenfruit (0.1.1)')
    mapping.file_requirement('forbiddenfruit (>= 0.0.5, < 0.0.7)')

    # When I list the filed packages
    packages = sorted(mapping.filed_packages())

    # I see that a list with the all package names was returned without
    # duplications
    packages.should.equal(['forbiddenfruit', 'sure'])


def test_get_requirements_by_package_name():
    "Mapping#get_requirements_by_package_name() Should return a list of requirements that match a given package name"

    # Given that I have a mapping with some repeated requirements
    mapping = Mapping()
    mapping.file_requirement('sure (1.2.1)')
    mapping.file_requirement('forbiddenfruit (0.1.1)')
    mapping.file_requirement('forbiddenfruit (>= 0.0.5, < 0.0.7)')

    # When I filter by the package name 'forbiddenfruit'
    sorted(mapping.get_requirements_by_package_name('forbiddenfruit')).should.equal([
        'forbiddenfruit (0.1.1)',
        'forbiddenfruit (>= 0.0.5, < 0.0.7)',
    ])


def test_available_versions():
    "Mapping#available_versions() should list versions of all wheels for a certain package"

    # Given that I have a mapping with the same requirement filed with different versions
    mapping = Mapping()
    mapping.file_requirement('forbiddenfruit (0.1.1)')
    mapping.set_data('forbiddenfruit (0.1.1)', 'wheel',
        '/path/to/wheelhouse/forbiddenfruit-0.1.1-cp27-none-macosx_10_8_x86_64.whl')  # 0.1.1

    mapping.file_requirement('forbiddenfruit (>= 0.0.5, < 0.0.7)')
    mapping.set_data('forbiddenfruit (>= 0.0.5, < 0.0.7)', 'wheel',
        '/path/to/wheelhouse/forbiddenfruit-0.0.6-cp27-none-macosx_10_8_x86_64.whl')  # 0.0.6

    mapping.file_requirement('forbiddenfruit (>= 0.1.0, < 2.0)')
    mapping.set_data('forbiddenfruit (>= 0.1.0, < 2.0)', 'wheel',
        '/path/to/wheelhouse/forbiddenfruit-0.1.1-cp27-none-macosx_10_8_x86_64.whl')  # 0.1.1; repeated

    mapping.file_requirement('forbiddenfruit (<= 0.0.9)')
    mapping.set_data('forbiddenfruit (<= 0.0.9)', 'wheel',
        '/path/to/wheelhouse/forbiddenfruit-0.0.9-cp27-none-macosx_10_8_x86_64.whl')  # 0.0.9

    # And I add another random package to the maestrro
    mapping.file_requirement('sure')

    # When I list all the available versions of forbidden fruit; Then I see it
    # found all the wheels related to that package. Newest first!
    mapping.available_versions('forbiddenfruit').should.equal(['0.1.1', '0.0.9', '0.0.6'])


def test_matching_versions():
    "Mapping#matching_versions() should list versions requirements compatible with a given version"

    # Given that I have a mapping with the same requirement filed with different versions
    mapping = Mapping()
    mapping.file_requirement('pkg (0.1.1)')
    mapping.set_data('pkg (0.1.1)', 'wheel',
        '/path/pkg-0.1.1-cp27-none-macosx_10_8_x86_64.whl')  # 0.1.1

    mapping.file_requirement('pkg (>= 0.0.5, < 0.0.7)')
    mapping.set_data('pkg (>= 0.0.5, < 0.0.7)', 'wheel',
        '/path/pkg-0.0.6-cp27-none-macosx_10_8_x86_64.whl')  # 0.0.6

    mapping.file_requirement('pkg (>= 0.1.0, < 2.0)')
    mapping.set_data('pkg (>= 0.1.0, < 2.0)', 'wheel',
        '/path/pkg-0.1.1-cp27-none-macosx_10_8_x86_64.whl')  # 0.1.1; repeated

    mapping.file_requirement('pkg (<= 0.0.9)')
    mapping.set_data('pkg (<= 0.0.9)', 'wheel',
        '/path/pkg-0.0.9-cp27-none-macosx_10_8_x86_64.whl')  # 0.0.9

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
    mapping.file_requirement('pkg (0.1.1-RC1)')
    mapping.set_data('pkg (0.1.1-RC1)', 'wheel',
        '/path/pkg-0.1.1_RC1-cp27-none-macosx_10_8_x86_64.whl')  # 0.1.1

    # When I filter the matching versions
    mapping.matching_versions('pkg (0.1.1-RC1)').should.equal([
        '0.1.1_RC1',
    ])


def test_broken_versions():
    "Mapping#broken_versions() Should return all versions of a requirement without a usable version"

    # Given that I have a mapping with a broken and a good requirement
    mapping = Mapping()
    mapping.file_requirement('pkg (0.1.1)')
    mapping.set_data('pkg (0.1.1)', 'wheel',
        '/path/pkg-0.1.1-cp27-none-macosx_10_8_x86_64.whl')  # 0.1.1
    mapping.set_data('pkg (0.1.1)', 'exception', Exception('P0wned!!'))  # Oh, openarena!

    mapping.file_requirement('other_pkg (0.1.1)')
    mapping.set_data('other_pkg (0.1.1)', 'wheel',
        '/path/other_pkg-0.1.1-cp27-none-macosx_10_8_x86_64.whl')  # 0.1.1

    # When I list the broken dependencies; Then I see that the package
    # containing an exception will be returned
    mapping.broken_versions('pkg (0.1.1)').should.equal(['0.1.1'])
    mapping.broken_versions('other_pkg (0.1.1)').should.be.empty


def test_is_primary_requirement():
    """Mapping#is_primary_requirement() True for requirements directly requested by the user

    Either from the command line or from the requirements file informed through
    the `-r` parameter;

    The `secondary` requirements are all the requirements we install without
    asking the user, IOW, dependencies of the primary requirements.
    """

    # Given that I have a mapping with two requirements filed
    mapping = Mapping()
    mapping.file_requirement('sure (1.2.1)')
    mapping.file_requirement('forbiddenfruit (0.1.1)', ['sure (1.2.1)'])

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
    mapping.file_requirement('pkg (<= 0.1.1)')
    mapping.set_data('pkg (<= 0.1.1)', 'wheel',
        '/path/pkg-0.1.1-cp27-none-macosx_10_8_x86_64.whl')  # 0.1.1

    mapping.file_requirement('pkg (>= 0.0.5)')
    mapping.set_data('pkg (>= 0.0.5)', 'wheel',
        '/path/pkg-0.0.6-cp27-none-macosx_10_8_x86_64.whl')  # 0.0.6

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
    mapping.file_requirement('pkg (>= 0.1.1)', ['blah'])
    mapping.set_data('pkg (>= 0.1.1)', 'wheel',
        '/path/pkg-0.1.1-cp27-none-macosx_10_8_x86_64.whl')  # 0.1.1

    # And the second version is older
    mapping.file_requirement('pkg (>= 0.0.5, < 0.0.7)', ['bleh'])
    mapping.set_data('pkg (>= 0.0.5, < 0.0.7)', 'wheel',
        '/path/pkg-0.0.6-cp27-none-macosx_10_8_x86_64.whl')  # 0.0.6

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
    mapping.file_requirement('pkg (>= 0.1.1)', ['other_pkg (0.1)'])
    mapping.set_data('pkg (>= 0.1.1)', 'wheel',
        '/path/pkg-0.1.1-cp27-none-macosx_10_8_x86_64.whl')  # 0.1.1

    # And the second version is older, but has no dependencies
    mapping.file_requirement('pkg (>= 0.0.5, < 0.0.7)')
    mapping.set_data('pkg (>= 0.0.5, < 0.0.7)', 'wheel',
        '/path/pkg-0.0.6-cp27-none-macosx_10_8_x86_64.whl')  # 0.0.6

    # When I retrieve the best match
    version = mapping.best_version('pkg')

    # Then I see that we retrieved the oldest version, just because the package
    # is not a dependency.
    version.should.equal(('0.0.6', 'pkg (>= 0.0.5, < 0.0.7)'))


def test_best_version_no_strict_requirements_but_strict_version():
    "Mapping#best_version() should still work for requirements without version info"

    # Given that I have a mapping with two requirements
    mapping = Mapping()
    mapping.file_requirement('forbiddenfruit', ['sure (== 0.2.1)'])
    mapping.set_data('forbiddenfruit', 'wheel', '/curds/forbiddenfruit-0.1.0-cp27.whl')

    # When I retrieve the best match
    version = mapping.best_version('forbiddenfruit')

    # Then I see that I still got the version number even though my requirement
    # didn't have version info
    version.should.equal(('0.1.0', 'forbiddenfruit'))
