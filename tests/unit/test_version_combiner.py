from __future__ import absolute_import, print_function, unicode_literals
from curdling.lib import combine_requirements
from nose.tools import nottest


def test_combining_compatible_requirements():
    "Version Combiner should combine compatible versions"

    # Given that I have a couple different versions of the same package
    requirements = ['forbiddenfruit (>= 0.1.2)', 'forbiddenfruit (< 2.0)']

    # When I combine both versions
    combined = combine_requirements(requirements)

    # Then I see they were combined
    combined.should.equal('forbiddenfruit (>= 0.1.2, < 2.0)')


def test_combining_incompatible_requirements():
    "Version Combiner should report incompatible versions"

    # Given that I have a couple different versions of the same package
    requirements = ['forbiddenfruit (<=0.1.2)', 'forbiddenfruit (>=2.0)']

    # When I combine both versions, Then I see that it will just explode with a
    # nice exception
    combine_requirements.when.called_with(requirements).should.throw(
        RuntimeError, "Incompatible versions")


def test_combining_requirements_with_incompatible_strict_versions():
    "Version Combiner should fail when mixing incompatible strict versions"

    # Given that I have a list of requirements
    requirements = ['forbiddenfruit (0.1.2)', 'forbiddenfruit (0.1.5)']

    # When I combine both versions, Then I see that it will just explode with a
    # nice exception
    combine_requirements.when.called_with(requirements).should.throw(
        RuntimeError, "Incompatible versions")


def test_combining_requirements_with_incompatible_strict_version():
    "Version Combiner should fail when mixing specific versions with incompatible ranges"

    # Given that I have a list of requirements
    requirements = ['forbiddenfruit (<= 0.1.2)', 'forbiddenfruit (0.1.5)']

    # When I combine both versions, Then I see that it will just explode with a
    # nice exception
    combine_requirements.when.called_with(requirements).should.throw(
        RuntimeError, "Incompatible versions")


def test_combining_range_with_strict_versions():
    "Version Combiner should always choose strict versions over ranges"

    # Given that I have a couple different versions of the same package
    requirements = ['forbiddenfruit (<= 1.5, >= 0.1.2)', 'forbiddenfruit (0.1.5)']

    # When I try to combine the requirements above
    combined = combine_requirements(requirements)

    # Then I see that the chosen one was the strict version
    combined.should.equal('forbiddenfruit (0.1.5)')


def test_combining_range_with_compatible_negative_versions():
    "Version Combiner should work with negative versions"

    # Given that I have a couple different versions of the same package
    requirements = [
        'forbiddenfruit (> 0.1.4)',
        'forbiddenfruit (!= 0.1.5)',
        'forbiddenfruit (< 0.1.7)',
    ]

    # When I try to combine the requirements above
    combined = combine_requirements(requirements)

    # Then I see it worked cause the negative is compatible with the two
    # informed ranges
    combined.should.equal('forbiddenfruit (> 0.1.4, < 0.1.7, != 0.1.5)')


@nottest
def test_combining_range_with_negatives():
    "Version Combiner should take negative versions into account when checking for compatibility"

    # Given that I have a couple different versions of the same package
    requirements = [
        'forbiddenfruit (> 0.1.4)',
        'forbiddenfruit (!= 0.1.5)',
        'forbiddenfruit (< 0.1.6)',
    ]

    # When I try to combine the requirements above; Then I see it won't work
    # cause the set above is just broken
    combine_requirements.when.called_with(requirements).should.throw(
        RuntimeError, "Incompatible versions")
