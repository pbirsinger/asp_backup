from ast import *
from ast_tools import *
import codegen
import scala_ast

BOOLOP_SYMBOLS = {
    And:        'and',
    Or:         'or'
}

BINOP_SYMBOLS = {
    Add:        '+',
    Sub:        '-',
    Mult:       '*',
    Div:        '/',
    FloorDiv:   '//',
    Mod:        '%',
    LShift:     '<<',
    RShift:     '>>',
    BitOr:      '|',
    BitAnd:     '&',
    BitXor:     '^'
}

CMPOP_SYMBOLS = {
    Eq:         '==',
    Gt:         '>',
    GtE:        '>=',
    In:         'in',
    Is:         'is',
    IsNot:      'is not',
    Lt:         '<',
    LtE:        '<=',
    NotEq:      '!=',
    NotIn:      'not in'
}

UNARYOP_SYMBOLS = {
    Invert:     '~',
    Not:        'not',
    UAdd:       '+',
    USub:       '-'
}

TYPES = {
    'int' : 'Int',
    'float': 'Float',
    'double': 'Double',
    'string': 'String', 
    'boolean': 'Boolean',
    'null': 'Unit'
    }

"""
POSSIBLE TYPES:
int
float
double
string
(array, type) i.e. (array, int)
(tuple, type, type [,type..]) i.e. (tuple, int, int)
boolean
specific class name
null
"""

ALL_SYMBOLS = {}
ALL_SYMBOLS.update(BOOLOP_SYMBOLS)
ALL_SYMBOLS.update(BINOP_SYMBOLS)
ALL_SYMBOLS.update(CMPOP_SYMBOLS)
ALL_SYMBOLS.update(UNARYOP_SYMBOLS)


"TODO add a from avro option for special array modifications"
def to_source(node):
    generator = SourceGenerator()
    generator.visit(node)
    return ''.join(generator.result)

def getArrType(elmts, for_schema = True):
    if not elmts:
        raise Exception("Need to provide at least one element of array to specify array type")
    if isinstance(elmts, scala_ast.List):
        return getArrType(elmts.elements)
    first = elmts[0]
    if isinstance(first, scala_ast.List):
        arr_type = getArrType(elmts[0])
        if for_schema: return '{\\"type\\": \\"array\\", \\"items\\": \\"%s\\"}'%(arr_type)   
        else: 
            if arr_type in TYPES.keys():arr_type = TYPES[arr_type]  
            return 'org.apache.avro.generic.GenericData.Array[%s]' %(arr_type)        
    elif isinstance(first, scala_ast.String):
        return 'string'
    elif isinstance(first, scala_ast.Number):
        return 'double'
    else:
        raise Exception("Unrecognized type")
        

def convert_types(input_type):
    #print 'CONVERT TYPES CALLED WITH :'+ str(input_type)
    if len(input_type) == 2 and input_type[0] == 'array':
        #return 'org.apache.avro.generic.GenericData.Array[%s]' % (convert_types(input_type[1]))
        return 'Array[%s]' %(convert_types(input_type[1]))
    elif len(input_type) == 2 and input_type[0] == 'list':
        return 'List[%s]' %(convert_types(input_type[1]))
    elif len(input_type) == 3 and input_type[0] == 'tuple':
        str = '('
        for x in input_type[1:]:
            str += convert_types(x) +','
        return str[0:-1] + ')'
    
    elif input_type in TYPES:
        return TYPES[input_type]
    else:
        print 'WARNING POTENTIAL SCALA TYPE MISMATCH OF:', input_type
        return input_type

class SourceGenerator(NodeVisitor):
    def __init__(self, func_types):
        self.result = []
        self.new_lines = 0
        self.indentation =0
        self.indent_with=' ' * 4
        self.stored_vals = {}
        self.current_func = ''
        self.prev_func = ''
        self.vars = {}       
        self.types = {}
        self.subl_count = 0
        self.set_func_types(func_types)

    
    def to_source(self, node):
        self.result = []
        self.visit(node)
        return ''.join(self.result)      
     
    def add_func_type(self, type):
        self.types.append(type)
             
    def already_def(self, var):
        if self.current_func in self.vars.keys():
            if var in self.vars[self.current_func]:
                return True
            else: return False
    
    def store_var(self,var):
        if self.current_func in self.vars.keys():
            self.vars[self.current_func].append(var)
        else: self.vars[self.current_func] = [var]            
    
    def write(self,x):
        if self.new_lines:
            if self.result:
                self.result.append('\n' * self.new_lines)
            self.result.append(self.indent_with * self.indentation)
            self.new_lines = 0
        self.result.append(x)
        
    def newline(self, node=None, extra=0):
        if isinstance(node, Call) and self.new_lines ==-1:
            self.new_lines = 0
        else:
            self.new_lines = max(self.new_lines, 1 + extra)

    def body(self, statements):
        self.new_line = True
        self.indentation += 1
        for stmt in statements:
            self.visit(stmt)
        self.indentation -= 1

    def set_func_types(self,types):
        source = []
        for func in types:
            name = func[0]
            #convert types somewhere?
            scala_arg_types, scala_ret_type = [],[]
            for arg in func[1]:
                print 'ARG IS-----------:' + str(arg)
                scala_arg_types.append(convert_types(arg))
            scala_ret_type = convert_types(func[2])
            self.types[name] = [scala_arg_types, scala_ret_type]    
        
    def visit_Number(self, node):
        self.write(repr(node.num))

    def visit_String(self, node):
        self.write('"')
        self.write(node.text)
        self.write('"')
    
    def visit_Name(self, node):
        self.write(node.name)

    def visit_Expression(self, node):
        self.newline(node) #may cause problems in newline()
        self.generic_visit(node)

    def visit_BinOp(self, node):
        if type(node.op) == ast.Pow:
            self.write('math.pow(')
            self.visit(node.left)
            self.write(', ')
            self.visit(node.right)
            self.write(')')
        else:
            self.write('(')
            self.visit(node.left)
            self.write(' ' + node.op + ' ')
            self.visit(node.right)
            self.write(')')
    
    def visit_BoolOp(self,node):
        self.newline(node)
        self.write('(')
        self.write('ADSFASDFASDFASDFDSF')
        print 'NODE OP IS:' , node.op
        print 'NODE OP TYPE IS:' , type(node.op)
        op = BOOLOP_SYMBOLS[type(node.op)]             
        self.visit(node.values[0])
        if op == 'and':
            self.write(' && ')
        elif op == 'or':
            self.write(' || ')
        else:
            raise Error("Unsupported BoolOp type")
        
        self.visit(node.values[1])
        self.write(')')   
    
    def visit_UnaryOp(self, node):
        self.write('(')
        op = UNARYOP_SYMBOLS[type(node.op)] 
        self.write(op)  
        if op == 'not':
            self.write(' ')
        self.visit(node.operand)
        self.write(')')

    def visit_Subscript(self, node):        
        if node.context == 'load':
            if isinstance(node.index, ast.Slice):
                self.write('scala_lib.slice(')
                self.visit(node.value)
                self.write(', ')
                self.visit(node.index.lower)
                self.write(', ')
                self.visit(node.index.upper)
                self.write(')')
            else:
                self.visit(node.value)
                self.write('(')
                self.visit(node.index)
                self.write(')')
        else: 
            self.visit(node.value)
            self.write('.set(')
            if isinstance(node.index, ast.Slice):
                raise Exception("Slice assign not supported")
            self.visit(node.index)
            #will finish this in assign
        
    #what about newline stuff?? sort of n    
    #will need to replace outer 's with "" s ...
    #to do the above, for SString add a flag that if set the 's are removed
    
    def visit_Print(self, node):
        self.newline(node)
        if node.dest:
            self.write('System.err.')
        self.write('println(')
        plus = False
        for t in node.text: 
            if plus: self.write('+" " + ')  
            self.visit(t)
            plus = True
        self.write(')')

    def visit_subList(self, node, lhsvar): 
        elmts = node.elements
        temp_vars = []
        for sublist in elmts:
            temp_name = 'subL%s'%(self.subl_count)
            self.subl_count +=1
            temp_vars.append(temp_name)
            asgn = scala_ast.Assign(scala_ast.Name(temp_name), sublist)
            self.visit_Assign(asgn)
            self.newline(node)
            self.visit(lhsvar)
            self.write(".add(%s)"%(temp_name))
            
    def visit_List(self, node):
        elmts = node.elements
        arr_type = getArrType(elmts)
        if self.already_def('str'):
            if len(arr_type) > 20:
                self.write('str = \"{\\"type\\": \\"array\\", \\"items\\": %s}\"'%(arr_type))
            else:   
                self.write('str = \"{\\"type\\": \\"array\\", \\"items\\": \\"%s\\"}\"'%(arr_type))
        else:
            #self.vars[self.current_func]
            self.store_var('str')            
            if len(arr_type) > 20:
                self.write('var str = \"{\\"type\\": \\"array\\", \\"items\\": %s}\"'%(arr_type))  
            else: 
                self.write('var str = \"{\\"type\\": \\"array\\", \\"items\\": \\"%s\\"}\"'%(arr_type))  
        self.newline(node)
        if self.already_def('schema'):
            self.write('schema = (new Schema.Parser()).parse(str)')
        else: 
            self.store_var('schema')
            self.write('var schema: Schema = (new Schema.Parser()).parse(str)')
        self.newline(node)
        lhsvar = self.stored_vals["lvalue"]
        self.write('var ')
        self.store_var(lhsvar.name)
        self.visit(lhsvar)
        self.write(' = ')
        arr_type = getArrType(elmts, False)
        if arr_type in TYPES.keys():
            arr_type = TYPES[arr_type]
        self.write('new org.apache.avro.generic.GenericData.Array[%s](1,%s)'%(arr_type, 'schema'))
        if elmts and isinstance(elmts[0], scala_ast.List):
            self.visit_subList(node, lhsvar)
        else:
            for e in elmts:            
                self.newline(node)
                self.visit(lhsvar)
                self.write(".add(")
                self.visit(e)
                self.write(')')
                           
    def visit_Attribute(self,node):
        self.visit(node.value)
        self.write('.' + node.attr)
    
    def evaluate_func(self,node):
        if node.func.name == 'range':
            self.write('Range(0,')
            self.visit(node.args[0])
            self.write(')')
        elif node.func.name == 'len':
            self.visit(node.args[0])
            self.write('.length')
        elif node.func.name == 'int':
            self.visit(node.args[0])
            self.write('.asInstanceOf[Int]')
        elif node.func.name == 'str':
            self.write("Integer.parseInt(")
            self.visit(node.args[0])
            self.write(')')
        elif node.func.name == 'float':
            self.visit(node.args[0])
            self.write('.asInstanceOf[Double]')
        elif node.func.name == 'read_avro_file':
            self.write('(new JAvroInter("res.avro", "args.avro")).readModel(')
            self.visit(node.args[0])
            self.write(')')

        else:
            self.visit(node.func)
            self.write('(')
            comma = False
            print 'node.args are:' , node.args
            for a in node.args:
                if comma: self.write(', ')
                self.visit(a)
                comma = True
            self.write(')')         
        
    def evaluate_attr_func(self,node):
        if node.func.attr == 'append':
            self.visit(node.func.value)            
            self.write('.add(')
            self.visit(node.args[0])
            self.write(')')
        elif node.func.attr == 'extend':
            self.write('scala_lib.extend(')
            self.visit(node.func.value)
            self.write(',')
            self.visit(node.args[0])
            self.write(')')
        elif node.func.attr == 'sample':
            self.write('scala_lib.rand_sample(')
            for a in node.args:
                self.visit(a)
                if a != node.args[-1]:
                    self.write(', ')                
            self.write(')')    
        elif node.func.attr == 'choice':
            self.write('scala_lib.rand_choice(')    
            self.visit(node.args[0])
            self.write(')')                        
        elif node.func.attr =='get':
            self.visit(node.func.value)
            self.write('.get(')
            self.visit(node.args[0])
            self.write(').asInstanceOf[org.apache.avro.generic.GenericData.Array[Float]]')
        elif node.func.attr == 'next':
            self.visit(node.func.value)
            self.write('.next().get(1).asInstanceOf[org.apache.avro.generic.GenericData.Array[Float]]')
        else:
            self.visit(node.func)
            self.write('(')
            comma = False
            for a in node.args:
                if comma: self.write(', ')
                self.visit(a)
                comma = True
            self.write(')')                 
        
    def visit_Call(self,node):
        self.newline(node)             
        if isinstance(node.func,scala_ast.Name):
            self.evaluate_func(node)   
        elif isinstance(node.func,scala_ast.Attribute):
            self.evaluate_attr_func(node)
        
    def visit_Function(self,node):
        self.newline(node)
        self.visit(node.declaration)
        self.write('{ ')
        
        self.body(node.body)
        self.current_func = self.prev_func
        self.write("\n}")
    
    def visit_FunctionDeclaration(self,node):
        self.write('def '+node.name+'( ')    
        self.prev_func = self.current_func    
        self.current_func = node.name
        arg_types = self.types[node.name][0]
        ret_type = self.types[node.name][1]
        
        self.visit_Arguments(node.args, arg_types)
        self.write('): %s =' %(ret_type))
        
    def visit_Arguments(self,node, types=None):   
        comma = False     
        for i in range(len(node.args)):
            if comma:self.write(', ')
            arg = node.args[i]
            self.visit(arg)
            if types:
                self.write(': %s' %types[i])
            else:
                self.write(': Any')
            comma = True
    
    def visit_ReturnStatement(self, node):
        self.newline(node)
        self.write('return ')
        self.new_lines = -1
        self.visit(node.retval)
        self.new_lines = 0
        
    def visit_Compare(self,node):
        self.newline(node,-1)
        self.write('(')
        self.visit(node.left)
        self.write(' %s ' %(node.op))
        self.visit(node.right)
        self.write(')')
    
    def visit_AugAssign(self,node):
        self.newline(node)
        self.visit(node.target)
        self.write(' ' + node.op +'= ')
        self.visit(node.value)
                   
    def visit_Assign(self,node):
        try:
            if node.lvalue.name == 'TYPE_DECS':
                self.visit(node.rvalue)
                return 0
        except: pass        
        self.newline(node)       
        self.stored_vals["lvalue"] = node.lvalue
        if isinstance(node.lvalue, Subscript):
            self.visit(node.lvalue)
            self.write(', ')
            self.visit(node.rvalue)
            self.write(')')
        elif isinstance(node.rvalue, scala_ast.List):
            self.visit(node.rvalue)
        else:
            if not self.already_def(node.lvalue.name):
                self.write('var ')
                self.store_var(node.lvalue.name)
            self.visit(node.lvalue)
            self.write(' = ')       
            self.new_lines = -1
            self.visit(node.rvalue)
            self.new_lines = 0
         
    def visit_IfConv(self,node):
        self.newline(node)
        if node.inner_if:
            if isinstance(node.orelse[0], IfConv) :
                self.write('else if (')                                           
            else:
                self.write('else if (')
                self.visit(node.test)
                self.write(') {')
                self.body(node.body)
                self.newline(node)
                self.write("}")
                self.newline(node)
                self.write('else {')
                self.body(node.orelse)
                self.newline(node)
                self.write('}')
                return
        else:       
            self.write('if (')
            
        self.visit(node.test)
        self.write(') {')
        self.body(node.body)
        self.newline(node)
        self.write('}')
        
        if node.orelse:
            self.newline(node)
            self.body(node.orelse)
    
    def visit_For(self,node):
        self.newline(node)
        self.write('for (')
        self.visit(node.target)
        self.write( ' <- ')
        self.visit(node.iter)
        self.write(') {')
        self.body(node.body)
        self.newline(node)
        self.write('}')
    
    def visit_While(self, node):
        self.newline(node)
        self.write('while (')
        #self.new_lines = -1
        self.visit(node.test)
        self.write(') {')
        self.newline(node)
        self.body(node.body)
        self.newline(node)
        self.write('}')
    
    
    
    
    