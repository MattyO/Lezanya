import os
import ast
import json
import pathlib


def call_names(definition):
    try:
        if isinstance(definition, funct):
            return [(None, definition.name)]
        else:
            return [(definition.name, c.name) for c in definition.functs ]
    except Exception as ex:
        print(definition)
        raise ex

def is_called(name, definitions):
    all_calls = set()

    for d in definitions:
        if isinstance(d, cls):
            for f in d.functs:
                if name in f.calls:
                    return True
        elif isinstance(d, funct):
            if name in d.calls:
                return True

    return False

def find_roots(defintions):
    roots = []

    for definition in defintions:
        for object_name, cname in call_names(definition):
            if not is_called(cname, defintions): # has a child call
                roots.append(".".join(filter(lambda x: x is not None, [object_name, cname])))

    return roots


def flatten(S):
    if S == []:
        return S
    if isinstance(S[0], list):
        return flatten(S[0]) + flatten(S[1:])
    return S[:1] + flatten(S[1:])

class funct():
    def __init__(self, name, calls=[], from_file=None, info={}):
        if name in calls:
            calls.remove(name)
        self.name = name
        self.calls = calls
        self.parent = None
        self.cycle = False
        self.from_file= from_file
        self.info = info

        for c in self.calls:
            if isinstance(c, cls) or isinstance(c, funct):
                c.parent = self

    def to_dict(self):
        return {'name':self.name, 'type':'function', 'calls': self.calls, 'from_file': self.from_file, 'info': self.info }

    @classmethod
    def from_dict(klass, d):
        return klass(d['name'], calls=d['calls'], from_file=d['from_file'])


    def __repr__(self):
        return "<funct(" + self.name +  ")>"

    def is_function(self):
        return True

    def is_class(self):
        return False

    def set_calls(self, calls):
        self.calls= calls
        for c in self.calls:
            if isinstance(c, cls) or isinstance(c, funct):
                c.parent = self


    def ancestors(self):
        parents = [self]
        temp_parent = self.parent
        while temp_parent is not None:
            parents.append(temp_parent)
            temp_parent = temp_parent.parent
        return list(reversed(parents))

    def get_funct(self, name):
        return self

    def function_names(self):
        return [self.name]

    def __eq__(self, other):
        return type(other) == self.__class__ and other.name == self.name

def find_class(function_name, defintions, parent=None):
    found_class = next((c for c in defintions if function_name in c.function_names()), None)
    found_return = None

    if found_class is not None:
        if isinstance(found_class, cls):
            found_return = cls(found_class.name, funct(function_name))
        if isinstance(found_class, funct):
            found_return = funct(function_name)

        calls = []
        if parent is None:
            found_return.parent = parent
            calls = [find_class(fname, defintions, found_return) for fname in found_class.get_funct(function_name).calls]
            calls = list(filter(lambda i: i is not None, calls))
            found_return.set_calls(calls)
        else:
            if found_return in parent.ancestors():
                found_return.cycle = True
            else:
                found_return.parent = parent
                calls = [find_class(fname, defintions, found_return) for fname in found_class.get_funct(function_name).calls]
                calls = list(filter(lambda i: i is not None, calls))
                found_return.set_calls(calls)



    return found_return

class cls():
    def __init__(self, name, *functs, calls=[], from_file=None, info={}):
        self.name = name
        self.functs = functs
        self.calls = calls
        self.parent = None
        self.cycle = False
        self.from_file= from_file
        self.info = info

        for c in self.calls:
            if isinstance(c, cls) or isinstance(c, funct):
                c.parent = self

    def __repr__(self):
        return "<cls(" + self.name + " functs:[" + ",".join(self.function_names()) + "])>"

    def to_dict(self):
        return {
            'name': self.name,
            'type': 'class',
            'from_file': self.from_file,
            'info': self.info,
            'functions': [ f.to_dict() for f in self.functs]
        }

    @classmethod
    def from_dict(klass, d):
        return klass(d['name'], *[funct.from_dict(d) for d in d['functions']], from_file=d['from_file'])

    def is_function(self):
        return False

    def is_class(self):
        return True

    def set_calls(self, calls):
        self.calls= calls
        for c in self.calls:
            if isinstance(c, cls) or isinstance(c, funct):
                c.parent = self

    def ancestors(self):
        parents = [self]
        temp_parent = self.parent
        while temp_parent is not None:
            parents.append(temp_parent)
            temp_parent = temp_parent.parent
        return list(reversed(parents))

    def function_names(self):
        return [ f.name for f in self.functs ]

    def get_funct(self, funct_name):
        return next((f for f in self.functs if f.name == funct_name), None)

    def __eq__(self, other):
        return  type(other) == self.__class__ and \
                other.name == self.name and \
                self.function_names() == other.function_names()

def find_definitions_in_directory(directory):
    definitions = []
    for root, dirs, files in os.walk(directory):
        for f in files:
            if f.endswith('.py'):
                definitions += find_definitions(os.path.join(root, f))

    return definitions

def calc_info(node):
    return  {'location': (node.lineno, node.col_offset), 'size': node.end_lineno - node.lineno }

def find_definitions(filename):
    defs = []
    example_file = open(filename, 'r')
    nodes = ast.parse(example_file.read()).body
    example_file.close()
    for node in nodes:
        info = {'location': (node.lineno, node.col_offset), 'size': node.end_lineno - node.lineno }
        if type(node) == ast.FunctionDef:
            defs.append(funct(node.name, calls=get_names(node), from_file=filename, info=calc_info(node)))

        if type(node) == ast.ClassDef:
            functs = []
            for b in node.body:
                if type(b) == ast.FunctionDef:
                    call_names = get_names(b)
                    #call_names: call_names.remove(b.name)
                    functs.append(funct(b.name, calls=call_names, info=calc_info(node)))
            defs.append(cls(node.name, *functs, from_file=filename, info=calc_info(node)))

    return defs


#is this a good idea?  will this work?
def walk_tree(node, callback, name=None):
    callback(this_node, name=name)

    for field in node._fields:
        sub_field = getattr(node, field)

        if sub_field is None:
            pass

        elif isinstance(sub_field, list):
            for n in sub_field:
                walk_tree(n, callback)

        elif not isinstance(sub_field, ast.AST):
            callback(sub_field, name=field)

        else:
            walk_tree(sub_field, callback, name=field)



def print_ast(node, tree, field_name=None):
    node_name = getattr(node,'name', str(node))
    if field_name is None:
        field_name= ""
    else:
        field_name += ':'

    this_node = tree.add(f'{field_name}{node_name}:{type(node)}')

    for field in node._fields:
        sub_field = getattr(node, field)

        if sub_field is None:
            pass

        elif isinstance(sub_field, list):
            if len(sub_field) > 0:
                collection_node = this_node.add(field)

            for n in sub_field:
                print_ast(n, collection_node , field_name=None)

        elif not isinstance(sub_field, ast.AST):

            this_node.add(f"{sub_field}:{type(sub_field)}")

        else:
            print_ast(sub_field, this_node, field_name=field)



def get_names(node):
    node_name = node.name if hasattr(node, 'name') else ""
    names = []

    #TODO: this is some duplication here.  we are finding some of the same nodes
    if isinstance(node, ast.Call):
        if(isinstance(node.func, ast.Attribute)):
            names += [node.func.attr]

    for field in node._fields:
        sub_node = getattr(node, field)

        if isinstance(sub_node, ast.Call):
            if(isinstance(sub_node.func, ast.Attribute)):
                names += [sub_node.func.attr]
            # if isinstance of name then we are loading a class

        if hasattr(sub_node, '_fields'):
            names += get_names(sub_node)
        if isinstance(sub_node, list):
            sub_names = [get_names(array_node) for array_node in sub_node if hasattr(array_node, '_fields')]
            if len(sub_names) > 0:
                names += flatten(sub_names)

    return list(set(names))


def save_definitions_json(defintions, path):
    with open(path, 'w') as f:
        f.write(json.dumps([d.to_dict() for d in defintions]))

def read_definitions_directory(directory):
    definitions = []
    for root, dirs, files in os.walk(directory):
        for f in files:
            if f.endswith('.def'):
                def_json = json.loads(pathlib.Path(os.path.join(root, f)).read_text())
                for d in def_json:
                    if d['type'] == 'function':
                        definitions.append(funct.from_dict(d))
                    if d['type'] == 'class':
                        definitions.append(cls.from_dict(d))

    return definitions

def save_definitions(defintions, path):
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    env = Environment(
        loader=FileSystemLoader('templates'),
        autoescape=select_autoescape(['html'])
    )
    template = env.get_template('class_defs.html')
    with open(path, 'w') as f:
        f.write(template.render(defintions=defintions))

def save_tree(tree, path):
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    env = Environment(
        loader=FileSystemLoader('templates'),
        autoescape=select_autoescape(['html'])
    )
    template = env.get_template('call_tree.html')
    with open(path, 'w') as f:
        f.write(template.render(tree=tree))


