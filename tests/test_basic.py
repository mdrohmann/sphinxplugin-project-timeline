# -*- coding: utf-8 -*-

import pytest
from docutils import nodes
from datetime import datetime
from sphinx_testing import with_app
from sphinxplugin.projecttimeline import (
    TimelineChunk, TimelineNode, parse_list_items, identify_time_chunk_name)


with_svg_app = with_app(
    srcdir='tests/docs/basic',
    buildername='html',
    write_docstring=True,
    confoverrides={
        'blockdig_html_image_format': 'SVG'
    })


@with_app(buildername='html', srcdir='tests/docs/basic/')
def test_build_html(app, status, warning):
    app.builder.build_all()


def test_parse_list_items():
    p = nodes.paragraph()
    assert parse_list_items(p) == []
    el = nodes.enumerated_list()
    p.append(el)
    item1 = nodes.list_item()
    paragraph1 = nodes.paragraph()
    el.append(item1)
    with pytest.raises(ValueError):
        parse_list_items(p)

    item1.append(paragraph1)
    text1 = nodes.Text('test')
    paragraph1.append(text1)
    assert parse_list_items(p) == ['test']

    item2 = nodes.list_item()
    paragraph2 = nodes.paragraph()
    text21 = nodes.Text('test2')
    text22 = nodes.Text('test3')
    el.append(item2)
    item2.append(paragraph2)
    paragraph2.append(text21)
    paragraph2.append(text22)

    assert parse_list_items(p) == ['test', 'test2 test3']


def test_identify_time_chunk_name():
    aliases = {
        'test': [('test', 2)],
        'non-unique': [('test', 2), ('other', 1)]
    }
    assert identify_time_chunk_name('test I', aliases) == [('test', 0)]
    assert identify_time_chunk_name('test II', aliases) == [('test', 1)]
    assert identify_time_chunk_name('test', aliases) == [('test', 0)]
    assert (
        identify_time_chunk_name('test', aliases, True)
        == [('test', 0), ('test', 1)])
    with pytest.raises(ValueError):
        identify_time_chunk_name('non-unique', aliases)


def test_TimelineNode():
    tn = TimelineNode(None)
    res = tn._parse_list_items(['link1'])
    assert res == [{'time': None, 'xref': 'link1', 'submodules': []}]
    res = tn._parse_list_items(['link1 (I, IV)'])
    assert res == [{'time': None, 'xref': 'link1', 'submodules': [1, 4]}]
    res = tn._parse_list_items(['link1 (i, IV)'])
    assert res == [{'time': None, 'xref': 'link1', 'submodules': [1, 4]}]
    res = tn._parse_list_items(['link1 (i, IV)', 'link2'])
    assert res == [{'time': None, 'xref': 'link1', 'submodules': [1, 4]},
                   {'time': None, 'xref': 'link2', 'submodules': []}]
    res = tn._parse_list_items(
        ['2015-01-01 link1 (i, IV)', '02-01-2012 link2'])
    assert res == [
        {'time': datetime(2015, 1, 1), 'xref': 'link1', 'submodules': [1, 4]},
        {'time': datetime(2012, 2, 1), 'xref': 'link2', 'submodules': []}]


def test_time_delta():

    tc = TimelineChunk(None)
    assert tc.parse_time_delta('1 hr') == 60
    assert tc.parse_time_delta('1') == 60
    assert tc.parse_time_delta('1h') == 60
    assert tc.parse_time_delta('1 hrs') == 60
    assert tc.parse_time_delta('1.5 hrs') == 90
    assert tc.parse_time_delta('1.5 hrs 20m') == 110
    assert tc.parse_time_delta('20 min') == 20
    assert tc.parse_time_delta('20 mins') == 20
    with pytest.raises(ValueError):
        tc.parse_time_delta('')

# class TestTimelineNode(unittest.TestCase):
#
#     def get_doctree(self, app, doctree, fromdocname):
#         self.dt = doctree
#         import pudb
#         pudb.set_trace()
#
#     @with_svg_app
#     def test_milestones(self, app, status, warning):
#         """
#         .. timeline::
#
#             Milestones
#             ----------
#
#             A. subject
#         ..
#         """
#
#         app.connect('doctree-resolved', self.get_doctree)
#         app.builder.build_all()
#
#         import pudb
#         pudb.set_trace()

# @with_app(buildername='latex', srcdir='tests/docs/basic/')
# def test_build_latex(app, status, warning):
#     app.builder.build_all()
# 
# 
# @with_app(buildername='epub', srcdir='tests/docs/basic/')
# def test_build_epub(app, status, warning):
#     app.builder.build_all()
# 
# 
# @with_app(buildername='json', srcdir='tests/docs/basic/')
# def test_build_json(app, status, warning):
#     app.builder.build_all()
