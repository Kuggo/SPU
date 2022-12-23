import os
from sys import argv, stdout, stderr
from enum import Enum
from typing import List

opcodes = {
    'ADD': 0,
    'SUB': 1,
    'RSH': 2,
    'INC': 3,
    'DEC': 4,
    'NAND': 5,
    'OR': 6,
    'XOR': 7,
    'MOV': 8,
    'IMM': 9,
    'LOAD': 10,
    'STORE': 11,
    'IN': 12,
    'OUT': 13,
    'BRANCH': 14,

    # OTHER instructions
    'NOP': 255,     # 1111_1111
    'HLT': 15,      # 0000_1111
    'RET': 31,      # 0001_1111

    'CAL': 174,     # 1010_1110
}

no_operand_inst = {'HLT', 'RET', }

conditions = {'ZERO': 0, 'NZERO': 1, 'CARRY': 2, 'NCARRY': 3, 'MSB': 4, 'NMSB': 5, 'LSB': 6, 'NLSB': 7}

registers = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'TMP': 2, 'SP': 3}

two_byte_inst = {'BRANCH', 'CAL', 'IMM'}


class E(Enum):
    illegal_char = "Illegal Char '{}'"
    wrong_op = 'Wrong operand for instruction "{}"'
    wrong_op_num = 'Wrong number of operands for instruction "{}"'
    unknown_instruction = 'Unknown instruction "{}"'
    undefined_label = 'Undefined label "{}"'
    duplicate_label = 'Duplicate label defined "{}"'

    def __repr__(self):
        return self.value


class Error:
    def __init__(self, error: E, index: int, line: int, file_name: str, *args) -> None:
        self.error = error
        self.line = line
        self.index = index
        self.args = args
        self.file_name = file_name

    def __repr__(self) -> str:
        return f'{self.file_name}:{self.index}:{self.line}: {self.error.value.format(*self.args)}'


class Instruction:
    def __init__(self, opcode: str, operands: List) -> None:
        self.opcode = opcode
        self.operands = operands
        self.size = 1
        if self.opcode in two_byte_inst:
            self.size = 2

    def bytecode(self) -> List[int]:
        def convert_operand(op, shift) -> int:
            if op.isalpha():  # reg/CND
                if op in registers:
                    return registers[op] << shift
                else:
                    return conditions[op] << shift

            else:  # imm
                return op

        if self.opcode in opcodes:
            byte = opcodes[self.opcode]
            if self.opcode in no_operand_inst:
                return [byte]

            elif self.opcode == 'CAL':
                return [byte, self.operands[0]]

            elif self.opcode == 'BRANCH':
                byte += convert_operand(self.operands[0], 4)
                return [byte, self.operands[1]]

            else:
                byte += convert_operand(self.operands[0], 4)
                byte += convert_operand(self.operands[1], 6)
                return [byte]

    def __repr__(self) -> str:
        out = f'<{self.opcode}'
        for op in self.operands:
            out += ' ' + str(op)
        return out + '>'


class Assembler:
    def __init__(self, text, file_name: str):
        self.errors = []
        self.text: str = text + '\n\n'
        self.instructions: List[(Instruction, str)] = []
        self.i = 0
        self.j = 1
        self.line_nr = 1
        self.file_name = file_name
        return

    def assemble(self) -> None:
        while self.has_next():
            self.next()
            if not self.has_next():
                return
            if self.peak() == ';':
                self.advance()
                continue

            elif self.peak() == '/':
                self.advance()
                if self.has_next() and self.peak() == '/':  # inline comment
                    self.inline_comment()
                elif self.has_next() and self.peak() == '*':
                    self.multi_line_comment()
                else:  # you got your hopes high, but it was just an illegal char :/
                    self.error(E.illegal_char, '/')

            elif self.peak() == '.':
                self.advance()
                word = self.make_word()
                if word is not None:
                    label = '.' + word
                    self.instructions.append(label)

            elif self.peak().isalpha():
                self.next_instruction()

            else:
                self.error(E.illegal_char, self.peak())
                self.advance()

        self.replace_labels()
        return

    def replace_labels(self) -> None:
        labels = {}
        byte_counter = 0
        i = 0
        while i < len(self.instructions):
            inst = self.instructions[i]
            if isinstance(inst, str):
                if inst in labels:
                    self.error(E.duplicate_label, inst)    # dup label
                else:
                    labels[inst] = byte_counter
                self.instructions.pop(i)
                continue
            else:
                byte_counter += inst.size
                i += 1

        for inst in self.instructions:
            for i, op in enumerate(inst.operands):
                if isinstance(op, str) and op[0] == '.':
                    if op in labels:
                        inst.operands[i] = labels[op]
                    else:
                        self.error(E.undefined_label, op)
        return

    def next_instruction(self):
        opcode = self.make_word().upper()
        if opcode not in opcodes:
            self.error(E.unknown_instruction, opcode)
            return
        operands = []
        self.next()
        if opcode in no_operand_inst:
            self.add_inst(opcode, [])
            return

        while self.has_next() and self.peak() != '\n' and self.peak() != ';':
            self.next()
            if self.peak().isalpha():        # reg/CND
                op = self.make_word()
                if (opcode == 'BRANCH' and op in conditions) or \
                        (opcode == 'CAL' and isinstance(op, str) and op[0] == '.') \
                        or op in registers:
                    operands.append(op)
                else:
                    self.error(E.wrong_op, opcode)

            elif self.peak().isnumeric():   # imm
                imm = self.make_word()
                operands.append(int(imm, 0))

            elif self.peak() == '.':        # label
                self.advance()
                label = '.' + self.make_word()
                operands.append(label)

            else:
                return
            while self.has_next() and self.peak() in ' \t':
                self.advance()

        if (opcode in no_operand_inst and len(operands) != 0) or \
                (opcode == 'CAL' and len(operands) != 1) or \
                (opcode != 'CAL' and len(operands) != 2):
            self.error(E.wrong_op_num, opcode)
        else:
            self.add_inst(opcode, operands)
        return

    def make_word(self) -> str:
        word = ''
        while self.has_next() and self.peak().isalnum():
            word += self.peak()
            self.advance()

        if not self.peak().isspace():
            self.error(E.illegal_char, self.peak())
        else:
            return word

    def next(self):
        while self.has_next() and self.peak() in ' ,\t':  # ignore commas and indentation
            self.advance()
        if self.has_next() and self.peak() == '\n':  # change line
            self.new_line()
            self.next()
        return

    def multi_line_comment(self) -> None:
        while self.has_next(1) and (self.peak() != '*' or self.peak() != '/'):
            if self.peak() == '\n':
                self.new_line()
            self.advance()
        self.advance()

    def inline_comment(self) -> None:
        while self.has_next() and self.peak() != '\n':
            self.advance()
        self.advance()
        self.new_line()

    def add_inst(self, opcode, operands: List):
        self.instructions.append(Instruction(opcode, operands))
        return

    def new_line(self):
        self.advance()
        self.j = 1
        self.line_nr += 1
        return

    def advance(self, i=1):
        self.i += i
        self.j += i
        return

    def peak(self) -> str:
        return self.text[self.i]

    def has_next(self, i=0) -> bool:
        return self.i + i < len(self.text)

    def error(self, error: E, extra: str = "") -> None:
        self.errors.append(Error(error, self.j, self.line_nr, self.file_name, extra))

    def bytecode_str(self) -> str:
        string = ''
        for inst in self.instructions:
            for byte in inst.bytecode():
                string += f'{byte:08b}' + '\n'
        return string

    def bytecode_vertical(self) -> str:
        lines: List[str] = ['', '', '', '', '', '', '', '']     # 8 bits
        for inst in self.instructions:
            for byte in inst.bytecode():
                for i, char in enumerate(f'{byte:08b}'):
                    lines[i] += char

        string = ''
        for inst in lines:
            string += inst + '\n'
        return string

    def bytecode(self) -> List[int]:
        byte_code = []
        for inst in self.instructions:
            byte_code += inst.bytecode()
        return byte_code

    def __repr__(self):
        return self.text


def main():
    usage = 'usage: spu <source> <destination>'

    source_name = argv[1] if len(argv) >= 2 else 'program.txt'
    dest_name = argv[2] if len(argv) >= 3 else 'output.txt'

    if source_name == '--help':
        print(usage)
        return

    if source_name is not None:
        if os.path.isfile(source_name):
            with open(source_name, mode='r') as sf:
                source = sf.read().replace("\r", "")
        else:
            print(f'"{source_name}" is not a file', file=stderr)
            exit(1)
    else:
        source = r''''''
        source_name = 'IDE'

    if dest_name is not None:
        dest = open(dest_name, mode="w")
    else:
        dest = stdout

    asm = Assembler(source, source_name)
    asm.assemble()

    if len(asm.errors) > 0:
        for err in asm.errors:
            print(err, file=stderr)
        exit(1)

    print(asm.bytecode_str(), file=dest)
    print('\n', file=dest)

    return


if __name__ == "__main__":
    main()
