from __future__ import absolute_import, print_function, unicode_literals
from curdling.maestro import Maestro
from curdling import exceptions


def test_maestro_pending_packages():
    "Maestro will keep the reference of a package if its not done or failed"

    # Given that I have a maestro
    maestro = Maestro()

    # When I file a package under it
    maestro.file_package('curdling', dependency_of=None)

    # Then I see it's still waiting for the dependency checking
    maestro.pending('built').should.equal(['curdling'])


def test_maestro_pending_packages_no_deps():
    "It shoudl be possible to mark packages as built maestro"

    # Given that I have a maestro with a package filed under it
    maestro = Maestro()
    maestro.file_package('curdling', dependency_of=None)

    # When and I mark the package as `checked`,
    # meaning that all the dependencies were checked
    maestro.mark('built', 'curdling', '')

    # Then I see it's still waiting for the dependency checking
    maestro.pending('built').should.equal([])
    maestro.built.should.equal({'curdling'})


def test_maestro_mark_failed():
    "It shoudl be possible to mark packages as failed in the maestro"

    # Given that I have a maestro with a package filed under it
    maestro = Maestro()
    maestro.file_package('curdling', dependency_of=None)

    # When and I mark the package as `failed`, meaning that all the
    # dependencies were checked
    maestro.mark('failed', 'curdling', '')

    # Then I see it's still waiting for the dependency checking
    maestro.pending('built').should.equal([])
    maestro.failed.should.equal({'curdling'})


def test_maestro_get_parents():
    "Maestro#get_parents() should return a list of requesters of a given package"

    # Given that I have a maestro with two packages depending on the same library
    maestro = Maestro()
    maestro.file_package('curdling', dependency_of=None)
    maestro.file_package('requests', dependency_of=None)
    maestro.file_package('urllib3', dependency_of='curdling')
    maestro.file_package('urllib3', dependency_of='requests')

    # When I get the parents of the `urllib3` package
    parents = maestro.get_parents('urllib3')

    # Then I see both packages that depend on `urllib3` were returned
    parents.should.equal(['curdling', 'requests'])


def test_marking_parent_packages_as_failed_when_a_dependency_fails():
    "Packages should be marked as failed when one or more of its dependencies can't be built"

    # Given that I have a maestro with a package and a dependency filed
    maestro = Maestro()
    maestro.file_package('curdling', dependency_of=None)
    maestro.file_package('urllib3', dependency_of='curdling')

    # When I mark the package `urllib3` as failed
    maestro.mark('failed', 'urllib3', Exception('P0wned!!!'))

    # Then I see the `curdling` package was also marked as failed
    maestro.failed.should.equal({'curdling', 'urllib3'})

    # And then I see that we don't have any packages pending
    maestro.pending('built').should.be.empty


def test_maestro_mark_built_update_mapping():

    # Given that I have a maestro with a couple packages filed under it
    maestro = Maestro()
    maestro.file_package('curdling', dependency_of=None)
    maestro.file_package('sure (== 0.1.2)', dependency_of='curdling')
    maestro.file_package('forbiddenfruit (> 0.1.0)', dependency_of='curdling')
    maestro.file_package('forbiddenfruit (>= 0.1.2)', dependency_of='sure (== 0.1.2)')

    # Wehn I mark the files as built
    maestro.mark('built', 'curdling', '/curds/curdling-0.3.5.whl')
    maestro.mark('built', 'sure (== 0.1.2)', '/curds/sure-0.1.2.whl')
    maestro.mark('built', 'forbiddenfruit (> 0.1.0)', '/curds/forbiddenfruit-0.1.2.whl')
    maestro.mark('built', 'forbiddenfruit (>= 0.1.2)', '/curds/forbiddenfruit-0.1.2.whl')

    # Then I see I still have just one entry in the mapping
    dict(maestro.mapping).should.equal({
        'curdling': {
            None: {
                'dependency_of': [],
                'data': '/curds/curdling-0.3.5.whl',
            },
        },
        'sure': {
            '== 0.1.2': {
                'dependency_of': ['curdling'],
                'data': '/curds/sure-0.1.2.whl'
            },
        },
        'forbiddenfruit': {
            '> 0.1.0': {
                'dependency_of': ['curdling'],
                'data': '/curds/forbiddenfruit-0.1.2.whl',
            },
            '>= 0.1.2': {
                'dependency_of': ['sure (== 0.1.2)'],
                'data': '/curds/forbiddenfruit-0.1.2.whl',
            },
        },
    })


def test_maestro_mark_installed():
    "Maestro should be able to track installed packages"

    # Given a maestro with a few packages
    maestro = Maestro()
    maestro.file_package('curdling')
    maestro.file_package('sure')

    # When I mark `curdling` as installed
    maestro.mark('installed', 'sure', data=None)

    # Then I see that the package was marked as installed
    maestro.installed.should.equal({'sure'})


def test_maestro_should_queue():
    "Maestro#should_queue should not allow repeated packages in the maestro"

    # Given that I have an empty maestro
    maestro = Maestro()

    # When I check if I can queue a package that is *not* present in the
    # maestro instance, Then I see it returns true
    maestro.should_queue('curdling').should.be.true

    # After filing this package to the maestro, should_queue will change its
    # results, as you can see here.
    maestro.file_package('curdling')
    maestro.should_queue('curdling').should.be.false


def test_maestro_should_queue_versions():
    "Maestro#should_queue should be aware of versions too"

    # Given that I have a maestro with one package with its version set
    maestro = Maestro()
    maestro.file_package('ejson (0.1.3)')

    # When I try to insert another version of the same package but with a
    # different version; Then I see that it works
    maestro.should_queue('ejson (0.1.5)').should.be.true
    maestro.should_queue('ejson (>= 1.5)').should.be.true


def test_maestro_should_queue_prefer_version_info():
    "Maestro#should_queue should always prefer packages with version info over bare package names"

    # Given that I have a maestro with a package without any strict version
    # requirement
    maestro = Maestro()
    maestro.file_package('ejson')

    # When I try to queue this same package with version info
    should_queue = maestro.should_queue('ejson (0.1.3)')

    # Then I see we always prefer packages with version info
    should_queue.should.be.true


def test_maestro_should_queue_prefer_version_info_2():
    "Maestro#should_queue should prefer packages with version info when there's already a non-versioned package"

    # Given that I have a maestro with a package without any strict version
    # requirement
    maestro = Maestro()
    maestro.file_package('ejson (0.1.3)')

    # When I try to queue this same package without version info
    should_queue = maestro.should_queue('ejson')

    # Then I see it shouldn't be allowed
    should_queue.should.be.false


def test_maestro_get_data():
    "It should be possible to retrieve data of a given requirement"

    # Given that I have a maestro filled with a package
    maestro = Maestro()
    maestro.mapping = {
        'forbiddenfruit': {
            '> 0.1.0': {
                'dependency_of': [],
                'data': '/curds/forbiddenfruit.whl',
            },
        }
    }

    # When I retrieve the data from the following requirement
    data = maestro.get_data('forbiddenfruit (> 0.1.0)')

    # Then I see the correct value retrieved
    data.should.equal('/curds/forbiddenfruit.whl')


def test_maestro_best_version():
    "Maestro should be able to choose the right version of a package to be installed"

    # Given that I have a maestro with a package that contains more than one
    # version
    maestro = Maestro()
    maestro.mapping = {
        'forbiddenfruit': {
            '>= 0.3.9': {
                'dependency_of': ['luxury'],
                'data': '/curds/forbiddenfruit.whl',
            },
            '> 0.0.3': {
                'dependency_of': [],
                'data': '/curds/forbiddenfruit.whl',
            },
            '>= 0.0.9': {
                'dependency_of': ['sure (== 0.2)'],
                'data': '/curds/forbiddenfruit.whl',
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
        'data': '/curds/forbiddenfruit.whl',
    })


def test_maestro_best_version_no_direct_req():
    "best_version() with no direct requirements"

    # Given that I have a maestro with a package that contains more than one
    # version, but none directly requested by the user
    maestro = Maestro()
    maestro.mapping = {
        'forbiddenfruit': {
            '> 0.1.0': {
                'dependency_of': ['luxury (== 0.1.0)'],
                'data': '/curds/forbiddenfruit-0.1.0.whl',
            },
            '>= 0.0.9': {
                'dependency_of': ['sure (== 0.2)'],
                'data': '/curds/forbiddenfruit-0.1.0.whl',
            },
        }
    }

    # When I retrieve the best match
    version, data = maestro.best_version('forbiddenfruit')

    # Then I see I found the entry that was not directly requested by the user
    # (IOW: The `dependency_of` field is not `None`).
    version.should.equal('> 0.1.0')
    data.should.equal({
        'dependency_of': ['luxury (== 0.1.0)'],
        'data': '/curds/forbiddenfruit-0.1.0.whl',
    })


def test_maestro_best_version_no_direct_req_with_null():
    "best_version() with no direct requirements"

    # Given that I have a maestro with a package that contains more than one
    # version, but none directly requested by the user
    maestro = Maestro()
    maestro.mapping = {
        None: {
            'dependency_of': ['moto'],
            'data': '/curds/forbiddenfruit-0.1.2.whl',
        },
        'forbiddenfruit': {
            '> 0.1.0': {
                'dependency_of': ['luxury (== 0.1.0)'],
                'data': '/curds/forbiddenfruit-0.1.2.whl',
            },
            '>= 0.0.9': {
                'dependency_of': ['sure (== 0.2)'],
                'data': '/curds/forbiddenfruit-0.1.2.whl',
            },
        }
    }

    # When I retrieve the best match
    version, data = maestro.best_version('forbiddenfruit')

    # Then I see I found the entry that was not directly requested by the user
    version.should.equal('> 0.1.0')


def test_best_version_should_prefer_newest_version():
    "Maestro#best_version should prefer newest versions when there's no override"

    # Given that I have a couple versions of the same package but all of them
    # were requested by some other package
    maestro = Maestro()
    maestro.mapping = {
        'forbiddenfruit': {
            '>= 0.0.9': {
                'dependency_of': ['sure (== 0.2)'],
                'data': '/curds/forbiddenfruit-0.1.0-cp27-none-macosx_10_8_x86_64.whl',
            },
            '<= 0.1.8': {
                'dependency_of': ['luxury (== 0.1.0)'],
                'data': '/curds/forbiddenfruit-0.1.8-cp27-none-macosx_10_8_x86_64.whl',
            },
            '>= 0.1.7': {
                'dependency_of': ['luxury (== 0.1.0)'],
                'data': '/curds/forbiddenfruit-0.1.7-cp27-none-macosx_10_8_x86_64.whl',
            },
        }
    }

    maestro.best_version('forbiddenfruit').should.equal(
        ('<= 0.1.8', {
        'dependency_of': ['luxury (== 0.1.0)'],
        'data': '/curds/forbiddenfruit-0.1.8-cp27-none-macosx_10_8_x86_64.whl',
        })
    )


def test_best_version_should_blow_up_on_version_conflicts():
    "Maestro#best_version should blow up if the versions downloaded can't fulfill all the dependencies"

    # Given that I have a couple versions of the same package but all of them
    # were requested by some other package
    maestro = Maestro()
    maestro.mapping = {
        'forbiddenfruit': {
            '>= 0.1.8': {
                'dependency_of': ['luxury (== 0.1.0)'],
                'data': '/curds/forbiddenfruit-0.1.8-cp27-none-macosx_10_8_x86_64.whl',
            },
            '<= 0.1.0': {
                'dependency_of': ['luxury (== 0.0.9)'],
                'data': '/curds/forbiddenfruit-0.1.0-cp27-none-macosx_10_8_x86_64.whl',
            },
            '>= 0.0.9': {
                'dependency_of': ['sure (== 0.2)'],
                'data': '/curds/forbiddenfruit-0.1.0-cp27-none-macosx_10_8_x86_64.whl',
            },
        }
    }

    maestro.best_version.when.called_with('forbiddenfruit').should.throw(
        exceptions.VersionConflict,
        'Requirement: forbiddenfruit (>= 0.1.8, <= 0.1.0, >= 0.0.9), '
        'Available versions: 0.1.8, 0.1.0'
    )
