import ast
import unittest
import pathlib
import os
import json

import analyze
from analyze import funct, cls

class AnalyseTest(unittest.TestCase):
    def test_function_equality(self):
        self.assertTrue(funct('test') == funct('test'))

    def test_function_not_equal(self):
        self.assertFalse(funct('test') ==  funct('not test'))

    def test_class_funcaiton_names(self):
        self.assertEqual(cls("Test", funct("one"), funct('two')).function_names(), ['one', 'two'])


    def test_class_equality(self):
        self.assertTrue(cls('ThingTwo') == cls('ThingTwo'))

    def test_class_not_equal(self):
        self.assertFalse(cls('ThingOne') == cls('ThingTwo'))

    def test_class_equality_with_function(self):
        self.assertTrue(cls('ThingTwo', funct('one')) == cls('ThingTwo', funct('one')))

    def test_class_equality_with_functions(self):
        self.assertTrue(cls('ThingTwo', funct('one'), funct('two')) == cls('ThingTwo', funct('one'), funct('two')))

    def test_function_in(self):
        self.assertIn(funct('test'), [funct('test')])

    def test_find_definitions_in_directory(self):
        definitions = analyze.find_definitions_in_directory('tests/files')
        self.assertIn(funct('start'), definitions)
        self.assertIn(cls('Example', funct('something'), funct('somethingelse')), definitions)
        self.assertIn(cls('ThingThree', funct('baz'), funct('call_cycle')), definitions)


    def test_find_definitions(self):
        definitions = analyze.find_definitions('tests/files/example.py')

        self.assertIn(funct('start'), definitions)
        self.assertIn(cls('ThingTwo', funct('two')), definitions)
        self.assertIn(cls('Example', funct('something'), funct('somethingelse'), funct('takes_params')), definitions)

    def test_find_definitions_calls(self):
        definitions = analyze.find_definitions('tests/files/example.py')
        e_def = definitions[1]

        self.assertEqual(e_def.functs[1].name, 'somethingelse')
        self.assertIn('two', e_def.functs[1].calls)
        self.assertIn('three', e_def.functs[1].calls)
        self.assertIn('bar', e_def.functs[1].calls)

    def test_get_names(self):
        example_file = open("tests/files/example.py", 'r')
        nodes = ast.parse(example_file.read()).body
        example_file.close()

        self.assertEqual(analyze.get_names(nodes[0].body[0]), [] )

    def test_get_name_not_blank(self):
        example_file = open("tests/files/example.py", 'r')
        nodes = ast.parse(example_file.read()).body
        example_file.close()

        self.assertIn('two', analyze.get_names(nodes[1].body[2]))
        self.assertIn('something', analyze.get_names(nodes[1].body[2]))
        self.assertIn('takes_params', analyze.get_names(nodes[1].body[2]))

    def test_get_name_is_not_recursive(self):
        example_file = open("tests/files/example.py", 'r')
        nodes = ast.parse(example_file.read()).body
        example_file.close()

        self.assertIn('somethingelse', analyze.get_names(nodes[2]))


    def test_get_funct_name(self):
        self.assertEqual(cls("Example", funct('testtest')).get_funct('testtest'), funct('testtest'))
        self.assertEqual(cls("Example", funct('testtest')).get_funct('nothere'), None)

    def test_find_class(self):
        definitions = analyze.find_definitions('tests/files/example.py')
        self.assertEqual(cls('Example', funct('somethingelse')), analyze.find_class('somethingelse', definitions))

    def test_find_class_return_none_when_no_match(self):
        definitions = analyze.find_definitions('tests/files/example.py')
        self.assertEqual(None, analyze.find_class('notafunction', definitions))

    def test_find_class_returns_functions(self):
        definitions = analyze.find_definitions('tests/files/example.py')
        self.assertEqual(funct('start'), analyze.find_class('start', definitions))

    def test_find_class_follows_function_class_calls(self):
        definitions = analyze.find_definitions('tests/files/example.py')
        found_funct = analyze.find_class('start', definitions)

        self.assertEqual(found_funct.name, 'start')
        self.assertEqual(len(found_funct.calls), 1)
        self.assertEqual(found_funct.calls[0], cls('Example', funct('somethingelse')))

    def test_find_class_is_recursive(self):
        definitions = analyze.find_definitions('tests/files/example.py')
        found_class = analyze.find_class('somethingelse', definitions)
        print(found_class.calls)
        self.assertEqual(len(found_class.calls), 1)
        self.assertEqual(cls('ThingTwo', funct('two')), found_class.calls[0])


    def test_calls_link_to_their_parent(self):
        definitions = analyze.find_definitions('tests/files/example.py')
        found_class = analyze.find_class('somethingelse', definitions)
        self.assertEqual(cls('Example', funct('somethingelse')), found_class.calls[0].parent)

    def test_ancestors(self):
        definitions = analyze.find_definitions('tests/files/example.py')
        found_class = analyze.find_class('start', definitions)
        ancestors = found_class.calls[0].calls[0].ancestors()
        self.assertEqual(ancestors[0], funct('start'))
        self.assertEqual(ancestors[1], cls('Example', funct('somethingelse')))
        self.assertEqual(ancestors[2], cls("ThingTwo", funct("two")))
        #, cls('Example', funct('somethingelse')), cls("ThingTwo", funct("two")) ])


    def test_cycles_short_circit(self):
        definitions = analyze.find_definitions('tests/files/more_examples.py')
        found_class = analyze.find_class('zed', definitions)
        self.assertEqual(len(found_class.calls), 1)
        self.assertEqual(cls('ThingThree', funct('call_cycle')), found_class.calls[0])
        self.assertTrue(found_class.calls[0].calls[0].cycle)
        self.assertEqual(cls("ContainsCycle", funct('zed')), found_class.calls[0].calls[0])

    def test_create_definitions_files(self):
        import lxml.etree
        import cssselect
        test_files_name ='tests/files/tmp/def_file.html'

        definitions = analyze.find_definitions_in_directory('tests/files')
        analyze.save_definitions(definitions, test_files_name)

        doc = lxml.etree.fromstring(pathlib.Path(test_files_name).read_text())
        results = doc.cssselect('div.class_def h2')
        example_element_h2 = next(filter(lambda r: r.text == "Example", results), None)

        self.assertEqual(example_element_h2.text, "Example")

        method_list_elements = example_element_h2.getparent().cssselect("ul li")
        method_list_elements_text = [ m.text for m in method_list_elements ]

        self.assertIn('something', method_list_elements_text)
        self.assertIn('somethingelse', method_list_elements_text)


        os.remove(test_files_name)
        self.assertFalse(os.path.exists(test_files_name))

    def test_create_graph_file(self):
        import lxml.etree
        import cssselect
        test_files_name ='tests/files/tmp/tree_file.html'

        definitions = analyze.find_definitions_in_directory('tests/files')
        tree = analyze.find_class('start', definitions)
        analyze.save_tree(tree, test_files_name)

        doc = lxml.etree.fromstring(pathlib.Path(test_files_name).read_text())
        first_call_h2_element = doc.cssselect('div.class_def h2')
        self.assertEqual(first_call_h2_element[0].text.strip(), "start")
        second_call_h3_element = first_call_h2_element[0].getparent().cssselect("div.calls h3")
        self.assertEqual(second_call_h3_element[0].text.strip(), 'Example.somethingelse')
        third_call_h3_element = second_call_h3_element[0].getparent().cssselect("div.calls h3")
        self.assertEqual(third_call_h3_element [0].text.strip(), 'ThingTwo.two')

        os.remove(test_files_name)
        self.assertFalse(os.path.exists(test_files_name))

    def test_class_to_dict(self):
        self.assertEqual(
            cls('testclass', funct('foo', calls=['one']), funct('bar'), from_file='testfile.py').to_dict(),
            {   'name':'testclass',
                'type': 'class',
                'from_file': 'testfile.py',
                'functions': [
                    {'name':'foo', 'type':'function', 'calls': ['one'], 'from_file': None},
                    {'name':'bar', 'type':'function', 'calls': [], 'from_file': None}
                ]
            }
        )
    def test_funct_to_dict(self):
        self.assertEqual(
            funct('testfunct', calls=['one', 'foo', 'bar'], from_file='testfile.py').to_dict(),
            {'name':'testfunct', 'type':'function', 'calls': ['one', 'foo', 'bar'], 'from_file':'testfile.py'}
        )

    def test_write_definitions_to_file(self):
        test_files_name ='tests/files/tmp/definitions.def'
        definitions = analyze.find_definitions_in_directory('tests/files')
        analyze.save_definitions_json(definitions, test_files_name )

        def_json = json.loads(pathlib.Path(test_files_name).read_text())

        self.assertEqual(
            [i['name'] for i in def_json],
            ['ThingTwo', 'Example', 'start', 'ThingThree', 'ContainsCycle']
        )

        os.remove(test_files_name)
        self.assertFalse(os.path.exists(test_files_name))

    def test_read_defs_from_files(self):
        test_files_name ='tests/files/tmp/definitions.def'
        definitions = analyze.find_definitions_in_directory('tests/files')
        analyze.save_definitions_json(definitions, test_files_name )
        hydrated_defs = analyze.read_definitions_directory('tests/files/tmp/')

        self.assertEqual(hydrated_defs, definitions)

        os.remove(test_files_name)
        self.assertFalse(os.path.exists(test_files_name))

    def test_find_roots(self):
        definitions = analyze.find_definitions_in_directory('tests/files')
        self.assertTrue('start' in analyze.find_roots(definitions))

    #def test_find_orphans(self):
    #    definitions = analyze.find_definitions_in_directory('tests/files')
    #    self.assertEqual(analyze.find_orphans(definitions), ['Exampe.something'])


    def test_call_names(self):
        definitions = analyze.find_definitions_in_directory('tests/files')
        self.assertEqual(analyze.call_names(definitions[0]), ['two'])
        self.assertEqual(analyze.call_names(definitions[2]), ['start'])

    def test_is_called(self):
        definitions = analyze.find_definitions_in_directory('tests/files')
        self.assertTrue(analyze.is_called('two', definitions))
        self.assertTrue(analyze.is_called('somethingelse', definitions))
        self.assertFalse(analyze.is_called('start', definitions))
        self.assertFalse(analyze.is_called('notafuncation', definitions))






