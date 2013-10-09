from __future__ import absolute_import, print_function, unicode_literals
from curdling.maestro import Maestro
from curdling import exceptions


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
            'status': Maestro.PENDING,
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
            'status': Maestro.PENDING,
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
            'status': Maestro.PENDING,
            'dependency_of': [None],
            'data': {
                'directory': None,
                'tarball': None,
                'wheel': None,
                'exception': None,
            }
        },

        'forbiddenfruit (0.1.0)': {
            'status': Maestro.PENDING,
            'dependency_of': ['sure (1.2.1)'],
            'data': {
                'directory': None,
                'tarball': None,
                'wheel': None,
                'exception': None,
            }
        }
    })


def test_default_status():
    "Maestro#file_requirement() should add requirements to the default status set"

    # Given that I have a _definitely_ empty maestro
    maestro = Maestro()
    maestro.status_sets[Maestro.PENDING].should.be.empty

    # When I file a new package
    maestro.file_requirement('forbiddenfruit (0.1.1)')

    # Then I see that the filed requirement was added to the PENDING set
    maestro.status_sets[Maestro.PENDING].should.equal(set(['forbiddenfruit (0.1.1)']))


def test_set_status():
    "Maestro#set_status() should change the status of a requirement, adding it to the right internal set"

    # Given that I have a maestro with a requirement
    maestro = Maestro()
    maestro.file_requirement('sure (1.2.1)')

    # When I change the status of a requirement
    maestro.set_status('sure (1.2.1)', Maestro.FAILED)

    # Than I see that the status was changed
    maestro.mapping['sure (1.2.1)']['status'].should.equal(Maestro.FAILED)

    # And I also see that the status sets contain the right value
    maestro.status_sets[Maestro.FAILED].should.equal(set(['sure (1.2.1)']))
    maestro.status_sets[Maestro.PENDING].should.be.empty


def test_get_status():
    "Maestro#get_status() should retrieve the status of a requirement"

    # Given that I have a maestro with a requirement
    maestro = Maestro()
    maestro.file_requirement('sure (1.2.1)')

    # When I change the requirement status
    maestro.set_status('sure (1.2.1)', Maestro.FAILED)

    # Then I see that the retrieved status is correct
    maestro.get_status('sure (1.2.1)').should.equal(Maestro.FAILED)


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
        ValueError, 'Data field `directory` is not empty',
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

    # When I query by PENDING requirements; Then I see both requirements I just
    # filed with their constraints list
    maestro.filter_package_by(Maestro.PENDING).should.equal([
        ('forbiddenfruit', ['>= 0.1.0, < 0.2', '0.1.1']),
        ('sure',  ['1.2.1']),
    ])


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


# ---------------------- Here ----------------------

# def test_get_parents():
#     "Maestro#get_parents() should return a list of requesters of a given package"

#     # Given that I have a maestro with two packages depending on the same library
#     maestro = Maestro()
#     maestro.file_requirement('curdling', dependency_of=None)
#     maestro.file_requirement('requests', dependency_of=None)
#     maestro.file_requirement('urllib3', dependency_of='curdling')
#     maestro.file_requirement('urllib3', dependency_of='requests')

#     # When I get the parents of the `urllib3` package
#     parents = maestro.get_parents('urllib3')

#     # Then I see both packages that depend on `urllib3` were returned
#     parents.should.equal(['curdling', 'requests'])


def test_best_version():
    "Maestro should be able to choose the right version of a package to be installed"

    # Given that I have a maestro with a package that contains more than one
    # version
    maestro = Maestro()
    maestro.mapping = {
        'forbiddenfruit': {
            '>= 0.3.9': {
                'dependency_of': ['luxury'],
                'data': {'path': '/curds/forbiddenfruit-0.3.9.whl'},
            },
            '> 0.0.3': {
                'dependency_of': [],
                'data': {'path': '/curds/forbiddenfruit-0.0.3.whl'},
            },
            '>= 0.0.9': {
                'dependency_of': ['sure (== 0.2)'],
                'data': {'path': '/curds/forbiddenfruit-0.0.9.whl'},
            },
        }
    }

    # When I retrieve the best match
    version, data = maestro.best_version('forbiddenfruit')

    # Then I see I found the entry that was directly requested by the user
    # (IOW: The `dependency_of` field is `None`).
    version.should.equal('> 0.0.3')
    data.should.equal({
        'dependency_of': [],
        'data': {'path': '/curds/forbiddenfruit-0.0.3.whl'},
    })


def test_best_version_filter_out_none_values_before_determining_top_requirements():
    "Maestro#best_version should filter out None values from dependency list before determining top requirements"

    # Given that I have a maestro with a package that contains more than one
    # version
    maestro = Maestro()
    maestro.mapping = {
        'forbiddenfruit': {
            '>= 0.3.9': {
                'dependency_of': ['luxury'],
                'data': {'path': '/curds/forbiddenfruit-0.3.9-cp27.whl'},
            },
            '> 0.0.3': {
                'dependency_of': [None, None],
                'data': {'path': '/curds/forbiddenfruit-0.0.3-cp27.whl'},
            },
            '>= 0.0.9': {
                'dependency_of': ['sure (== 0.2)'],
                'data': {'path': '/curds/forbiddenfruit-0.0.9-cp27.whl'},
            },
        }
    }

    # When I retrieve the best match
    version, data = maestro.best_version('forbiddenfruit')

    # Then I see I found the entry that was directly requested by the user
    # (IOW: The `dependency_of` field is `None`).
    version.should.equal('> 0.0.3')
    data.should.equal({
        'dependency_of': [None, None],
        'data': {'path': '/curds/forbiddenfruit-0.0.3-cp27.whl'},
    })


def test_best_version_no_strict_requirements_but_strict_version():
    "Maestro#best_version should still work when the caller doesn't inform any strict version for a given dependency"

    # Given that I have a maestro with a package that contains more than one
    # version, but none directly requested by the user
    maestro = Maestro()
    maestro.file_requirement('forbiddenfruit', dependency_of='sure (== 0.2.1)')
    maestro.set_data('forbiddenfruit', {'path': '/curds/forbiddenfruit-0.1.0-cp27.whl'})

    # When I retrieve the best match
    version, data = maestro.best_version('forbiddenfruit')

    version.should.be.none
    data.should.equal({
        'dependency_of': ['sure (== 0.2.1)'],
        'data': {'path': '/curds/forbiddenfruit-0.1.0-cp27.whl'},
    })


def test_best_version_dependency():
    "Maestro#best_version() should work for dependencies as well"

    # Given that I have a maestro with a package that contains more than one
    # version, but none directly requested by the user
    maestro = Maestro()
    maestro.file_requirement('forbiddenfruit (> 0.1.0)', dependency_of='luxury (== 0.1.1)')
    maestro.set_data('forbiddenfruit (> 0.1.0)', {'path': '/curds/forbiddenfruit-0.1.1-cp27.whl'})
    maestro.file_requirement('forbiddenfruit (>= 0.0.9)', dependency_of='sure (== 0.2)')
    maestro.set_data('forbiddenfruit (>= 0.0.9)', {'path': '/curds/forbiddenfruit-0.0.9-cp27.whl'})

    # When I retrieve the best match
    version, data = maestro.best_version('forbiddenfruit')

    # Then I see I found the entry that was not directly requested by the user
    # (IOW: The `dependency_of` field is not `None`).
    version.should.equal('> 0.1.0')
    data.should.equal({
        'dependency_of': ['luxury (== 0.1.1)'],
        'data': {'path': '/curds/forbiddenfruit-0.1.1-cp27.whl'},
    })


def test_best_version_should_blow_up_on_version_conflicts():
    "Maestro#best_version should blow up if the versions downloaded can't fulfill all the dependencies"

    # Given that I have a couple versions of the same package but all of them
    # were requested by some other package
    maestro = Maestro()
    maestro.mapping = {
        'forbiddenfruit': {
            '>= 0.1.8': {
                'dependency_of': ['luxury (== 0.1.0)'],
                'data': {'path': '/curds/forbiddenfruit-0.1.8-cp27-none-macosx_10_8_x86_64.whl'},
            },
            '<= 0.1.0': {
                'dependency_of': ['luxury (== 0.0.9)'],
                'data': {'path': '/curds/forbiddenfruit-0.1.0-cp27-none-macosx_10_8_x86_64.whl'},
            },
        }
    }

    maestro.best_version.when.called_with('forbiddenfruit').should.throw(
        exceptions.VersionConflict,
        'Requirement: forbiddenfruit (>= 0.1.8, <= 0.1.0), '
        'Available versions: 0.1.8, 0.1.0'
    )


def test_best_version_skip_broken_dependencies():
    "best_version() should be smart enough to handle package marked as broken"

    # Given that I have a maestro with a package that references a broken
    # package in the dependency list
    maestro = Maestro()
    maestro.file_requirement('sure (0.1.2)')
    maestro.file_requirement('forbiddenfruit (0.1.0)', dependency_of='sure (0.1.2)')
    maestro.mark('failed', 'forbiddenfruit (0.1.0)', {
        'exception': exceptions.BrokenDependency(
            'forbiddenfruit (0.1.0): We\'re doomed, setup.py failed!'),
    })

    exception = maestro.get_data('forbiddenfruit (== 0.1.0)').get('exception')
    exception.should.be.a(exceptions.BrokenDependency)
    exception.message.should.equal("forbiddenfruit (0.1.0): We're doomed, setup.py failed!")

    exception = maestro.get_data('sure (0.1.2)').get('exception')
    exception.should.be.a(exceptions.BrokenDependency)
    exception.message.should.equal("forbiddenfruit (0.1.0)")

    # Sure has problems with this next line cause dependencies are not
    # comparable between each other. It always returns `False`
    #
    # maestro.best_version('forbiddenfruit').should.equal([
    #     (None, {
    #         'name': '== 0.1.0',
    #         'dependency_of': ['sure (0.1.2)'],
    #         'data': {
    #             'exception': exceptions.BrokenDependency(
    #                 "forbiddenfruit (0.1.0): We're doomed, setup.py failed!"),
    #         },
    #     })
    # ])

    broken_packages = maestro.best_version('forbiddenfruit')
    broken_packages[0][0].should.be.none
    broken_packages[0][1]['name'].should.equal('== 0.1.0')
    broken_packages[0][1]['dependency_of'].should.equal(['sure (0.1.2)'])
    str(broken_packages[0][1]['data']['exception']).should.equal(
        "forbiddenfruit (0.1.0): We're doomed, setup.py failed!")
