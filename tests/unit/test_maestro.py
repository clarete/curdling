from __future__ import absolute_import, print_function, unicode_literals
from curdling.maestro import Maestro, format_requirement
from curdling import exceptions


def test_format_requirement():
    format_requirement('flask').should.equal('flask')
    format_requirement('flask (== 0.10.1)').should.equal('flask (0.10.1)')
    format_requirement('Jinja (>= 2.4)').should.equal('Jinja (>= 2.4)')
    format_requirement('Babel (>= 0.8, < 1.0)').should.equal('Babel (>= 0.8, < 1.0)')


def test_file_requirement():
    "Maestro#file_requirement() should add a new requirement to the maestro"

    # Given that I have a maestro
    maestro = Maestro()

    # When I file a requirement
    maestro.file_requirement('curdling')

    # Then I see that the mapping attribute has all the data we need to process
    # a requirement
    dict(maestro.mapping).should.equal({
        'curdling': {
            'status': Maestro.Status.PENDING,
            'dependency_of': [None],
            'data': {
                'directory': None,
                'tarball': None,
                'wheel': None,
                'exception': None,
            }
        }
    })


def test_file_requirement_with_constraints():
    "Maestro#file_requirement() should add a new requirement with constraints to the maestro"

    # Given that I have a maestro
    maestro = Maestro()

    # When I file a requirement
    maestro.file_requirement('curdling (>= 0.2.5, < 0.3.0)')

    # And then I see that the mapping attribute has the right values
    dict(maestro.mapping).should.equal({
        'curdling (>= 0.2.5, < 0.3.0)': {
            'status': Maestro.Status.PENDING,
            'dependency_of': [None],
            'data': {
                'directory': None,
                'tarball': None,
                'wheel': None,
                'exception': None,
            }
        }
    })


def test_file_dependencies():
    "Maestro#file_requirement() should be able to remember which requirement requested a given dependency"

    # Given that I have a maestro with a file on it
    maestro = Maestro()
    maestro.file_requirement('sure (1.2.1)')

    # When I file another requirement using the `dependency_of` parameter
    maestro.file_requirement('forbiddenfruit (0.1.0)', dependency_of='sure (1.2.1)')

    # Then I see that the mapping looks right
    dict(maestro.mapping).should.equal({
        'sure (1.2.1)': {
            'status': Maestro.Status.PENDING,
            'dependency_of': [None],
            'data': {
                'directory': None,
                'tarball': None,
                'wheel': None,
                'exception': None,
            }
        },

        'forbiddenfruit (0.1.0)': {
            'status': Maestro.Status.PENDING,
            'dependency_of': ['sure (1.2.1)'],
            'data': {
                'directory': None,
                'tarball': None,
                'wheel': None,
                'exception': None,
            }
        }
    })


def test_file_requirement_update_dependency_list():
    "Maestro#file_requirement() should update the dependency_of list if a requirement is requested more than once and is unique"

    # Given the following maestro loaded with a few packages
    maestro = Maestro()
    maestro.file_requirement('forbiddenfruit (0.1.0)')
    maestro.set_data('forbiddenfruit (0.1.0)', 'tarball', 'package.tar.gz')
    maestro.file_requirement('sure (1.2.1)')
    maestro.file_requirement('forbiddenfruit (0.1.0)', dependency_of='sure (1.2.1)')

    # Then I see that the mapping looks right
    dict(maestro.mapping).should.equal({
        'sure (1.2.1)': {
            'status': Maestro.Status.PENDING,
            'dependency_of': [None],
            'data': {
                'directory': None,
                'tarball': None,
                'wheel': None,
                'exception': None,
            }
        },

        'forbiddenfruit (0.1.0)': {
            'status': Maestro.Status.PENDING,
            'dependency_of': [None, 'sure (1.2.1)'],
            'data': {
                'directory': None,
                'tarball': 'package.tar.gz',
                'wheel': None,
                'exception': None,
            }
        }
    })


def test_default_status():
    "Maestro#file_requirement() should add requirements to the default status set"

    # Given that I have a _definitely_ empty maestro
    maestro = Maestro()

    # When I file a new package
    maestro.file_requirement('forbiddenfruit (0.1.1)')

    # Then I see that the filed requirement was added to the PENDING set
    maestro.mapping['forbiddenfruit (0.1.1)']['status'].should.equal(Maestro.Status.PENDING)


def test_set_status():
    "Maestro#set_status() should change the status of a requirement, adding it to the right internal set"

    # Given that I have a maestro with a requirement
    maestro = Maestro()
    maestro.file_requirement('sure (1.2.1)')

    # When I change the status of a requirement
    maestro.set_status('sure (1.2.1)', Maestro.Status.FAILED)

    # Than I see that the status was changed
    maestro.mapping['sure (1.2.1)']['status'].should.equal(Maestro.Status.FAILED)


def test_add_status():
    """Maestro#add_status() should add another status to the same requirement

    We need that cause we want to mark requirements as RETRIEVED and BUILT for
    example.
    """

    # Given that I have a maestro with a requirement
    maestro = Maestro()
    maestro.file_requirement('sure (1.2.1)')

    # When I change the status of a requirement
    maestro.add_status('sure (1.2.1)', Maestro.Status.RETRIEVED)

    # Than I see that the new status was added to the previous one
    (maestro.mapping['sure (1.2.1)']['status'] & Maestro.Status.RETRIEVED).should.be.true

    # And When I add another status
    maestro.add_status('sure (1.2.1)', Maestro.Status.BUILT)

    # And Than I see that the build status was added to the previous one
    (maestro.mapping['sure (1.2.1)']['status'] & Maestro.Status.BUILT).should.be.true

    # And Then I still see the RETRIEVED status in this package
    (maestro.mapping['sure (1.2.1)']['status'] & Maestro.Status.RETRIEVED).should.be.true


def test_get_status():
    "Maestro#get_status() should retrieve the status of a requirement"

    # Given that I have a maestro with a requirement
    maestro = Maestro()
    maestro.file_requirement('sure (1.2.1)')

    # When I change the requirement status
    maestro.set_status('sure (1.2.1)', Maestro.Status.FAILED)

    # Then I see that the retrieved status is correct
    maestro.get_status('sure (1.2.1)').should.equal(Maestro.Status.FAILED)


def test_set_data():
    "Maestro#set_data() should set keys (directory, tarball, wheel or exception) to the `data` field in the requirement"

    # Given that I have a maestro with a requirement
    maestro = Maestro()
    maestro.file_requirement('forbiddenfruit (0.1.1)')

    # When I set the source of the previously added requirement
    maestro.set_data('forbiddenfruit (0.1.1)', 'directory', '/path/to/my/requirement/folder')

    # Then I see the data was saved in the right place
    maestro.mapping['forbiddenfruit (0.1.1)']['data']['directory'].should.equal(
        '/path/to/my/requirement/folder'
    )


def test_set_data_only_works_once():
    """Maestro#set_data() should not work more than once to the same requirement's data key

    Meaning that if you set `directory` once through `set_data()` a `ValueError`
    will be raised if you try to set the same field again."""

    # Given that I have a maestro with a requirement that has the `directory`
    # data key fulfilled.
    maestro = Maestro()
    maestro.file_requirement('forbiddenfruit (0.1.1)')
    maestro.set_data('forbiddenfruit (0.1.1)', 'directory', '/path/to/my/requirement/folder')

    # When I try to call this same function again; Then I see that it's going
    # to throw an exception
    maestro.set_data.when.called_with('forbiddenfruit (0.1.1)', 'directory', 'whatever').should.throw(
        ValueError, 'Data field `directory` is not empty for the requirement "forbiddenfruit (0.1.1)"',
    )


def test_get_data():
    "Maestro#get_data() should get the content of a given key under the requirements' data key"

    # Given that I have a maestro with a requirement that contains a source
    maestro = Maestro()
    maestro.file_requirement('forbiddenfruit (0.1.1)')
    maestro.set_data('forbiddenfruit (0.1.1)', 'tarball', '/path/to/my/tarball-0.0.1.tar.gz')

    # When I get_data() the requirement above
    tarball = maestro.get_data('forbiddenfruit (0.1.1)', 'tarball')

    # Then I see the source was retrieved properly
    tarball.should.equal('/path/to/my/tarball-0.0.1.tar.gz')


def test_filter_by():
    "Maestro#filter_by() should give us a list of package names by status"

    # Given that I have a maestro with two requirements filed
    maestro = Maestro()
    maestro.file_requirement('sure (1.2.1)')
    maestro.file_requirement('forbiddenfruit (0.1.1)', dependency_of='sure (1.2.1)')
    maestro.file_requirement('forbiddenfruit (>= 0.1.0, < 0.2)')

    # When I mark a given package as RETRIEVED
    maestro.add_status('forbiddenfruit (0.1.1)', Maestro.Status.RETRIEVED)

    # Than I see it will appear in the filter_by
    maestro.filter_by(Maestro.Status.RETRIEVED).should.equal([
        'forbiddenfruit (0.1.1)',
    ])


def test_filter_by_pending():
    "Maestro#filter_by() should retrieve requirements in the PENDING status even though it evaluates to 0"

    # Given that I have a maestro with a requirement
    maestro = Maestro()
    maestro.file_requirement('sure (1.2.1)')

    # When I change the requirement status
    maestro.set_status('sure (1.2.1)', Maestro.Status.PENDING)

    # Then I see that the retrieved status is correct
    maestro.filter_by(Maestro.Status.PENDING).should.equal(['sure (1.2.1)'])

    maestro.set_status('sure (1.2.1)', Maestro.Status.BUILT)
    maestro.filter_by(Maestro.Status.PENDING).should.be.empty


def test_filed_packages():
    """Maestro#filed_packages() should return all packages requested based on all requirements we have.

    It will retrieve a unique list of packages, even when the requirement is
    filed more than once.
    """
    # Given that I have a maestro with a few repeated and unique requirements
    maestro = Maestro()
    maestro.file_requirement('sure (1.2.1)')
    maestro.file_requirement('forbiddenfruit (0.1.1)')
    maestro.file_requirement('forbiddenfruit (>= 0.0.5, < 0.0.7)')

    # When I list the filed packages
    packages = maestro.filed_packages()

    # I see that a list with the all package names was returned without
    # duplications
    packages.should.equal(['forbiddenfruit', 'sure'])


def test_get_requirements_by_package_name():
    "Maestro#get_requirements_by_package_name() Should return a list of requirements that match a given package name"

    # Given that I have a maestro with some repeated requirements
    maestro = Maestro()
    maestro.file_requirement('sure (1.2.1)')
    maestro.file_requirement('forbiddenfruit (0.1.1)')
    maestro.file_requirement('forbiddenfruit (>= 0.0.5, < 0.0.7)')

    # When I filter by the package name 'forbiddenfruit'
    maestro.get_requirements_by_package_name('forbiddenfruit').should.equal([
        'forbiddenfruit (0.1.1)',
        'forbiddenfruit (>= 0.0.5, < 0.0.7)',
    ])


def test_available_versions():
    "Maestro#available_versions() should list versions of all wheels for a certain package"

    # Given that I have a maestro with the same requirement filed with different versions
    maestro = Maestro()
    maestro.file_requirement('forbiddenfruit (0.1.1)')
    maestro.set_data('forbiddenfruit (0.1.1)', 'wheel',
        '/path/to/wheelhouse/forbiddenfruit-0.1.1-cp27-none-macosx_10_8_x86_64.whl')  # 0.1.1

    maestro.file_requirement('forbiddenfruit (>= 0.0.5, < 0.0.7)')
    maestro.set_data('forbiddenfruit (>= 0.0.5, < 0.0.7)', 'wheel',
        '/path/to/wheelhouse/forbiddenfruit-0.0.6-cp27-none-macosx_10_8_x86_64.whl')  # 0.0.6

    maestro.file_requirement('forbiddenfruit (>= 0.1.0, < 2.0)')
    maestro.set_data('forbiddenfruit (>= 0.1.0, < 2.0)', 'wheel',
        '/path/to/wheelhouse/forbiddenfruit-0.1.1-cp27-none-macosx_10_8_x86_64.whl')  # 0.1.1; repeated

    maestro.file_requirement('forbiddenfruit (<= 0.0.9)')
    maestro.set_data('forbiddenfruit (<= 0.0.9)', 'wheel',
        '/path/to/wheelhouse/forbiddenfruit-0.0.9-cp27-none-macosx_10_8_x86_64.whl')  # 0.0.9

    # When I list all the available versions of forbidden fruit; Then I see it
    # found all the wheels related to that package. Newest first!
    maestro.available_versions('forbiddenfruit').should.equal(['0.1.1', '0.0.9', '0.0.6'])


def test_matching_versions():
    "Maestro#matching_versions() should list versions requirements compatible with a given version"

    # Given that I have a maestro with the same requirement filed with different versions
    maestro = Maestro()
    maestro.file_requirement('pkg (0.1.1)')
    maestro.set_data('pkg (0.1.1)', 'wheel',
        '/path/pkg-0.1.1-cp27-none-macosx_10_8_x86_64.whl')  # 0.1.1

    maestro.file_requirement('pkg (>= 0.0.5, < 0.0.7)')
    maestro.set_data('pkg (>= 0.0.5, < 0.0.7)', 'wheel',
        '/path/pkg-0.0.6-cp27-none-macosx_10_8_x86_64.whl')  # 0.0.6

    maestro.file_requirement('pkg (>= 0.1.0, < 2.0)')
    maestro.set_data('pkg (>= 0.1.0, < 2.0)', 'wheel',
        '/path/pkg-0.1.1-cp27-none-macosx_10_8_x86_64.whl')  # 0.1.1; repeated

    maestro.file_requirement('pkg (<= 0.0.9)')
    maestro.set_data('pkg (<= 0.0.9)', 'wheel',
        '/path/pkg-0.0.9-cp27-none-macosx_10_8_x86_64.whl')  # 0.0.9

    # When I query which versions should be listed based on a requirement; Then
    # I see that only the versions that match with the informed requirement
    # were returned (and again, newest first)
    maestro.matching_versions('pkg (>= 0.0.6, <= 0.1.0)').should.equal([
         '0.0.9', '0.0.6',
    ])


def test_broken_versions():
    "Maestro#broken_versions() Should return all versions of a requirement without a usable version"

    # Given that I have a maestro with a broken and a good requirement
    maestro = Maestro()
    maestro.file_requirement('pkg (0.1.1)')
    maestro.set_data('pkg (0.1.1)', 'wheel',
        '/path/pkg-0.1.1-cp27-none-macosx_10_8_x86_64.whl')  # 0.1.1
    maestro.set_data('pkg (0.1.1)', 'exception', Exception('P0wned!!'))  # Oh, openarena!

    maestro.file_requirement('other_pkg (0.1.1)')
    maestro.set_data('other_pkg (0.1.1)', 'wheel',
        '/path/other_pkg-0.1.1-cp27-none-macosx_10_8_x86_64.whl')  # 0.1.1

    # When I list the broken dependencies; Then I see that the package
    # containing an exception will be returned
    maestro.broken_versions('pkg (0.1.1)').should.equal(['0.1.1'])
    maestro.broken_versions('other_pkg (0.1.1)').should.be.empty


def test_is_primary_requirement():
    """Maestro#is_primary_requirement() True for requirements directly requested by the user

    Either from the command line or from the requirements file informed through
    the `-r` parameter;

    The `secondary` requirements are all the requirements we install without
    asking the user, IOW, dependencies of the primary requirements.
    """

    # Given that I have a maestro with two requirements filed
    maestro = Maestro()
    maestro.file_requirement('sure (1.2.1)')
    maestro.file_requirement('forbiddenfruit (0.1.1)', dependency_of='sure (1.2.1)')

    # When I test if the above requirements are primary
    maestro.is_primary_requirement('sure (1.2.1)').should.be.true
    maestro.is_primary_requirement('forbiddenfruit (0.1.1)').should.be.false


def test_best_version():
    """Maestro#best_version() Should choose the newest compatible version of a requirement to be installed

    By compatible, I mean that this version will match all the other
    requirements present in the maestro.

    """

    # Given that I have a maestro with a package that contains more than one
    # version
    maestro = Maestro()
    maestro.file_requirement('pkg (<= 0.1.1)')
    maestro.set_data('pkg (<= 0.1.1)', 'wheel',
        '/path/pkg-0.1.1-cp27-none-macosx_10_8_x86_64.whl')  # 0.1.1

    maestro.file_requirement('pkg (>= 0.0.5)')
    maestro.set_data('pkg (>= 0.0.5)', 'wheel',
        '/path/pkg-0.0.6-cp27-none-macosx_10_8_x86_64.whl')  # 0.0.6

    # When I retrieve the best match
    version, requirement = maestro.best_version('pkg')

    # Then I see that the newest dependency was chosen
    version.should.equal('0.1.1')
    requirement.should.equal('pkg (<= 0.1.1)')


def test_best_version_with_conflicts():
    "Maestro#best_version() Should raise blow up if no version matches all the filed requirements"

    # Given that I have a maestro with a package that contains more than one
    # version
    maestro = Maestro()
    maestro.file_requirement('pkg (>= 0.1.1)', dependency_of='blah')
    maestro.set_data('pkg (>= 0.1.1)', 'wheel',
        '/path/pkg-0.1.1-cp27-none-macosx_10_8_x86_64.whl')  # 0.1.1

    # And the second version is older
    maestro.file_requirement('pkg (>= 0.0.5, < 0.0.7)', dependency_of='bleh')
    maestro.set_data('pkg (>= 0.0.5, < 0.0.7)', 'wheel',
        '/path/pkg-0.0.6-cp27-none-macosx_10_8_x86_64.whl')  # 0.0.6

    # When I retrieve the best match
    maestro.best_version.when.called_with('pkg').should.throw(
        exceptions.VersionConflict,
        'Requirement: pkg (>= 0.1.1, >= 0.0.5, < 0.0.7), '
        'Available versions: 0.1.1, 0.0.6'
    )


def test_best_version_with_explicit_requirement():
    """Maestro#best_version() Should always prioritize versions directly specified by the user

    The other versions might have been added by dependencies. So, to manually
    fix craziness between dependencies of dependencies, the user can just force
    a specific version for a package from the command line or from a
    requirements file informed with the `-r` parameter.
    """

    # Given that I have a maestro with a package that contains more than one
    # version
    maestro = Maestro()
    maestro.file_requirement('pkg (>= 0.1.1)', dependency_of='other_pkg (0.1)')
    maestro.set_data('pkg (>= 0.1.1)', 'wheel',
        '/path/pkg-0.1.1-cp27-none-macosx_10_8_x86_64.whl')  # 0.1.1

    # And the second version is older, but has no dependencies
    maestro.file_requirement('pkg (>= 0.0.5, < 0.0.7)')
    maestro.set_data('pkg (>= 0.0.5, < 0.0.7)', 'wheel',
        '/path/pkg-0.0.6-cp27-none-macosx_10_8_x86_64.whl')  # 0.0.6

    # When I retrieve the best match
    version = maestro.best_version('pkg')

    # Then I see that we retrieved the oldest version, just because the package
    # is not a dependency.
    version.should.equal(('0.0.6', 'pkg (>= 0.0.5, < 0.0.7)'))


def test_best_version_no_strict_requirements_but_strict_version():
    "Maestro#best_version() should still work for requirements without version info"

    # Given that I have a maestro with two requirements
    maestro = Maestro()
    maestro.file_requirement('forbiddenfruit', dependency_of='sure (== 0.2.1)')
    maestro.set_data('forbiddenfruit', 'wheel', '/curds/forbiddenfruit-0.1.0-cp27.whl')

    # When I retrieve the best match
    version = maestro.best_version('forbiddenfruit')

    # Then I see that I still got the version number even though my requirement
    # didn't have version info
    version.should.equal(('0.1.0', 'forbiddenfruit'))
