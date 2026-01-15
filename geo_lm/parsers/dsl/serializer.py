"""
Serialize AST back to DSL text format.

Enables programmatic construction and round-trip editing.
"""

import io
from typing import TextIO

from .ast import (
    Program,
    RockDefinition,
    DepositionEvent,
    ErosionEvent,
    IntrusionEvent,
    TimeValue,
    AbsoluteTime,
    EpochTime,
    UnknownTime,
)


class DSLSerializer:
    """
    Serializes an AST Program back to DSL text.

    Example:
        serializer = DSLSerializer()
        dsl_text = serializer.serialize(program)
    """

    def __init__(self, indent: str = "  "):
        self._indent = indent
        self._output: TextIO = None

    def serialize(self, program: Program) -> str:
        """Serialize program to DSL string."""
        self._output = io.StringIO()
        self._write_program(program)
        return self._output.getvalue()

    def serialize_to_file(self, program: Program, filepath: str):
        """Serialize program to a file."""
        with open(filepath, "w") as f:
            self._output = f
            self._write_program(program)

    def _write_program(self, program: Program):
        """Write complete program."""
        # Rocks first
        for rock in program.rocks:
            self._write_rock(rock)

        if program.rocks and (
            program.depositions or program.erosions or program.intrusions
        ):
            self._output.write("\n")

        # Depositions
        for dep in program.depositions:
            self._write_deposition(dep)

        # Erosions
        for ero in program.erosions:
            self._write_erosion(ero)

        # Intrusions
        for intr in program.intrusions:
            self._write_intrusion(intr)

    def _write_rock(self, rock: RockDefinition):
        """Write a ROCK statement."""
        props = [f'name: "{rock.name}"']
        props.append(f"type: {rock.rock_type.name.lower()}")
        if rock.age:
            props.append(f"age: {self._format_time(rock.age)}")

        self._write_statement("ROCK", rock.id, props)

    def _write_deposition(self, dep: DepositionEvent):
        """Write a DEPOSITION statement."""
        props = [f"rock: {dep.rock_id}"]
        if dep.time:
            props.append(f"time: {self._format_time(dep.time)}")
        if dep.after:
            props.append(f"after: {', '.join(dep.after)}")

        self._write_statement("DEPOSITION", dep.id, props)

    def _write_erosion(self, ero: ErosionEvent):
        """Write an EROSION statement."""
        props = []
        if ero.time:
            props.append(f"time: {self._format_time(ero.time)}")
        if ero.after:
            props.append(f"after: {', '.join(ero.after)}")

        self._write_statement("EROSION", ero.id, props)

    def _write_intrusion(self, intr: IntrusionEvent):
        """Write an INTRUSION statement."""
        props = [f"rock: {intr.rock_id}"]
        if intr.style:
            props.append(f"style: {intr.style.name.lower()}")
        if intr.time:
            props.append(f"time: {self._format_time(intr.time)}")
        if intr.after:
            props.append(f"after: {', '.join(intr.after)}")

        self._write_statement("INTRUSION", intr.id, props)

    def _format_time(self, time: TimeValue) -> str:
        """Format a time value."""
        if isinstance(time, AbsoluteTime):
            unit_str = time.unit.name.lower().capitalize()
            if time.value == int(time.value):
                return f"{int(time.value)}{unit_str}"
            return f"{time.value}{unit_str}"
        elif isinstance(time, EpochTime):
            return time.epoch_name
        elif isinstance(time, UnknownTime):
            return '"?"'
        return str(time)

    def _write_statement(self, keyword: str, id: str, props: list[str]):
        """Write a DSL statement with properties."""
        prop_str = "; ".join(props)
        self._output.write(f"{keyword} {id} [ {prop_str} ]\n")
