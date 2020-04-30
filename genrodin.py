import sys
import xml.etree.ElementTree as ET

from abc import ABC, abstractmethod

def neg(cond):
    return "¬({})".format(cond)

class Construct(ABC):
    @abstractmethod
    def generate_events(self, real_instructions):
        pass

class WhileConstruct:
    def __init__(self, cond, line_no_before, line_no_after):
        self.cond = cond
        self.line_no_before = int(line_no_before)
        self.line_no_after = int(line_no_after)

    def generate_events(self, real_instructions):
        real_instructions[self.line_no_before] = False
        real_instructions[self.line_no_after - 1] = False
        return [
            (self.line_no_before, self.line_no_before + 1, self.cond),
            (self.line_no_before, self.line_no_after, neg(self.cond)),
            (self.line_no_after - 1, self.line_no_before + 1, self.cond),
            (self.line_no_after - 1, self.line_no_after, neg(self.cond)),
        ]

class IfConstruct:
    def __init__(self, cond, line_no_before, line_no_before_else,
                 line_no_after):
        self.cond = cond
        self.line_no_before = int(line_no_before)
        self.line_no_before_else = int(line_no_before_else)
        self.line_no_after = int(line_no_after)

    def generate_events(self, real_instructions):
        real_instructions[self.line_no_before] = False
        real_instructions[self.line_no_before_else] = False
        real_instructions[self.line_no_after - 1] = False
        return [
            (self.line_no_before, self.line_no_before + 1, self.cond),
            (self.line_no_before_else, self.line_no_after, None),
            (self.line_no_before, self.line_no_before_else + 1,
             neg(self.cond)),
            (self.line_no_after - 1, self.line_no_after, None)
        ]

class RodinContextWriter:
    def __init__(self, radical):
        self.root = ET.Element("org.eventb.core.contextFile", {
            "org.eventb.core.configuration": "org.eventb.core.fwd",
            "version": "3"
        })
        self.next_id = 39

    def get_next_id(self):
        next_id = chr(self.next_id)
        self.next_id += 1
        return next_id

    def add_constant(self, name):
        ET.SubElement(self.root, "org.eventb.core.constant", {
            "name": self.get_next_id(),
            "org.eventb.core.identifier": name
        })

    def add_set(self, name):
        ET.SubElement(self.root, "org.eventb.core.carrierSet", {
            "name": self.get_next_id(),
            "org.eventb.core.identifier": name
        })

    def set_set_content(self, set_name, constant_names):
        ET.SubElement(self.root, "org.eventb.core.axiom", {
            "name": self.get_next_id(),
            "org.eventb.core.label": "content_{}".format(set_name),
            "org.eventb.core.predicate": "partition({}, {})".format(
                set_name, ", ".join(
                    "{{{}}}".format(constant_name)
                    for constant_name in constant_names)
            )
        })

    def make(self, final_line_no):
        set_name = "Lines"
        self.add_set(set_name)
        constant_names = []
        for line_no in range(final_line_no + 1):
            constant_name = "l{}".format(line_no)
            self.add_constant(constant_name)
            constant_names.append(constant_name)
        self.set_set_content(set_name, constant_names)
        return ET.tostring(self.root)

class RodinMachineWriter:
    def __init__(self, radical):
        self.root = ET.Element("org.eventb.core.machineFile", {
            "org.eventb.core.configuration": "org.eventb.core.fwd",
            "version": "5"
        })
        self.next_id = 39
        init = ET.SubElement(self.root, "org.eventb.core.event", {
            "name": self.get_next_id(),
            "org.eventb.core.convergence": "0",
            "org.eventb.core.extended": "false",
            "org.eventb.core.label": "INITIALISATION",
        })
        ET.SubElement(init, "org.eventb.core.action", {
            "name": "'",
            "org.eventb.core.assignment": "pc ≔ l0",
            "org.eventb.core.label": "init_pc"
        })
        ET.SubElement(self.root, "org.eventb.core.seesContext", {
            "name": self.get_next_id(),
            "org.eventb.core.target": "{}_context".format(radical)
        })
        ET.SubElement(self.root, "org.eventb.core.variable", {
            "name": self.get_next_id(),
            "org.eventb.core.identifier": "pc"
        })
        ET.SubElement(self.root, "org.eventb.core.invariant", {
            "name": self.get_next_id(),
            "org.eventb.core.label": "type_pc",
            "org.eventb.core.predicate": "pc ∈ Lines"
        })

    def get_next_id(self):
        next_id = chr(self.next_id)
        self.next_id += 1
        return next_id

    def add_tbd_invariant(self, line_no):
        ET.SubElement(self.root, "org.eventb.core.invariant", {
            "name": self.get_next_id(),
            "org.eventb.core.label": "Pl{}".format(line_no),
            "org.eventb.core.predicate": "pc = l{} ⇒ (⊤)".format(line_no),
            "org.eventb.core.comment": "TBD"
        })

    def add_flow_event(self, line_no_from, line_no_to, predicate):
        event_writer = RodinEventWriter(self, line_no_from, line_no_to, False)
        if predicate is not None:
            event_writer.add_guard(predicate, "cond")

    def add_tbd_event(self, line_no_from, line_no_to):
        RodinEventWriter(self, line_no_from, line_no_to, True)

    def make(self, final_line_no, flow_events, tbd_events):
        for line_no in range(final_line_no + 1):
            self.add_tbd_invariant(line_no)
        for flow_event in flow_events:
            self.add_flow_event(*flow_event)
        for tbd_event in tbd_events:
            self.add_tbd_event(*tbd_event)
        return ET.tostring(self.root)


class RodinEventWriter:
    def __init__(self, parent, line_no_from, line_no_to, is_tbd):
        self.root = ET.SubElement(parent.root, "org.eventb.core.event", {
            "name": parent.get_next_id(),
            "org.eventb.core.convergence": "0",
            "org.eventb.core.extended": "false",
            "org.eventb.core.label": "l{}l{}".format(line_no_from, line_no_to),
            "org.eventb.core.comment": "TBD" if is_tbd else "FLOW"
        })
        self.next_id = 39
        self.add_guard("pc = l{}".format(line_no_from), "pc_control")
        self.add_action("pc ≔ l{}".format(line_no_to), "pc_next")
        if is_tbd:
            self.add_tbd_action()

    def get_next_id(self):
        next_id = chr(self.next_id)
        self.next_id += 1
        return next_id

    def add_guard(self, predicate, label):
        ET.SubElement(self.root, "org.eventb.core.guard", {
            "name": self.get_next_id(),
            "org.eventb.core.label": label,
            "org.eventb.core.predicate": predicate
        })

    def add_action(self, assignement, label):
        ET.SubElement(self.root, "org.eventb.core.action", {
            "name": self.get_next_id(),
            "org.eventb.core.label": label,
            "org.eventb.core.assignment": assignement
        })

    def add_tbd_action(self):
        ET.SubElement(self.root, "org.eventb.core.action", {
            "name": self.get_next_id(),
            "org.eventb.core.label": "act1",
            "org.eventb.core.assignment": "",
            "org.eventb.core.comment": "TBD"
        })


def parse_content(content):
    lines = [line.strip() for line in content.split("\n") if line.strip()]
    final_line_no = int(lines[0])
    constructs = []
    for line in lines[1:]:
        parts = line.split(":")
        if parts[0] == "while":
            constructs.append(WhileConstruct(*parts[1:]))
        elif parts[0] == "if":
            constructs.append(IfConstruct(*parts[1:]))
        else:
            raise Exception("Unrecognized construct")
    return final_line_no, constructs


def main():
    if len(sys.argv) != 3:
        raise Exception("Invalid number of arguments.")
    def_file_path = sys.argv[1]
    radical = sys.argv[2]

    with open(def_file_path, "r", encoding="utf-8") as def_file:
        content = def_file.read()
    final_line_no, constructs = parse_content(content)
    real_instructions = [True] * final_line_no
    flow_events = []
    for construct in constructs:
        flow_events.extend(construct.generate_events(real_instructions))
    tbd_events = []
    for line_no_before, is_real in enumerate(real_instructions):
        if not is_real:
            continue
        else:
            tbd_events.append((line_no_before, line_no_before + 1))
    context_writer = RodinContextWriter(radical)
    context_content = context_writer.make(final_line_no)
    with open("{}_context.buc".format(radical), "w", encoding="utf-8") as context_file:
        context_file.write('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n')
        context_file.write(context_content.decode("utf-8"))
    machine_writer = RodinMachineWriter(radical)
    machine_content = machine_writer.make(
        final_line_no, flow_events, tbd_events)
    with open("{}_machine.bum".format(radical), "w", encoding="utf-8") as machine_file:
        machine_file.write('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n')
        machine_file.write(machine_content.decode("utf-8"))
    print("Generation done !")

if __name__ == "__main__":
    main()
