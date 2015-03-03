.PHONY: test update_readme doc install build clean

all: update_readme

test:
	PYTHONPATH=$$PWD:$$PYTHONPATH py.test -s --junitxml=jUnittest.xml --cov-config .coveragerc  --cov-report html --cov sphinxplugin tests/

%.html: %.rst
	@pandoc -s -c $(abspath ./)/kultiad-serif.css -f rst -t html5 $< > $@

update_readme: README.html

build:
	python setup.py build

install:
	python setup.py install

doc:
	make -C docs html

clean:
	rm -rf htmlcov jUnittest.xml *.pyc build dist
