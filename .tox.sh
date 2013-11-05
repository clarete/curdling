#!/bin/sh

# I'm just calling make from a file inside of the project to avoid getting an
# annoying warning from tox.
VIRTUAL_ENV="fake_it_for_the_makefile" make
